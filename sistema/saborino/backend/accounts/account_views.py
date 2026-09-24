from datetime import timedelta

from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.middleware.csrf import rotate_token
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.crypto import decrypt_text, encrypt_text, recipient_fingerprint
from notifications.services import enqueue_email

from .action_tokens import challenge_token, read_challenge_token
from .identity import canonicalize_email
from .models import AccountActionChallenge, CustomUser, RecoveryGrant, SecurityAuditEvent
from .rate_limits import allow_request
from .recovery_views import GENERIC
from .session_views import NoStoreMixin


def _password_errors(password, user):
    try:
        validate_password(password, user=user)
    except ValidationError as exc:
        return Response({'password': list(exc.messages)}, status=400)
    return None


def _new_challenge(user, purpose, email_key, encrypted_target=''):
    now = timezone.now()
    AccountActionChallenge.objects.filter(
        user=user, purpose=purpose, superseded_at__isnull=True, consumed_at__isnull=True,
    ).update(superseded_at=now)
    return AccountActionChallenge.objects.create(
        user=user,
        purpose=purpose,
        target_fingerprint=recipient_fingerprint(email_key),
        encrypted_target=encrypted_target,
        credential_version=user.credential_version,
        expires_at=now + timedelta(minutes=60),
    )


def _valid_challenge(token, purpose):
    try:
        challenge_id = read_challenge_token(token, purpose)
    except signing.BadSignature:
        return None
    now = timezone.now()
    challenge = AccountActionChallenge.objects.select_for_update().select_related('user').filter(pk=challenge_id).first()
    if (
        not challenge or challenge.expires_at <= now or challenge.consumed_at
        or challenge.superseded_at or challenge.credential_version != challenge.user.credential_version
    ):
        return None
    return challenge


@method_decorator(csrf_protect, name='dispatch')
class PasswordChangeView(NoStoreMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        new_password = request.data.get('new_password', '')
        with transaction.atomic():
            user = CustomUser.objects.select_for_update().get(pk=request.user.pk)
            if not user.check_password(request.data.get('current_password', '')):
                return Response({'detail': 'Senha atual inválida.'}, status=400)
            error = _password_errors(new_password, user)
            if error:
                return error
            if user.check_password(new_password):
                return Response({'password': ['A nova senha deve ser diferente da atual.']}, status=400)
            now = timezone.now()
            user.set_password(new_password)
            user.revoke_credentials()
            user.save(update_fields=['password', 'credential_version', 'password_changed_at'])
            enqueue_email(
                kind='password_changed', business_key=f'password-changed/manual/{user.pk}/{user.credential_version}',
                recipient=user.email, email_key=user.email_key, context={}, send_before=now + timedelta(hours=23),
            )
            SecurityAuditEvent.objects.create(user=user, event_type='password_changed', outcome='success')
        logout(request)
        rotate_token(request)
        return Response(status=204)


@method_decorator(csrf_protect, name='dispatch')
class EmailVerificationRequestView(NoStoreMixin, APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        if not settings.EMAIL_VERIFICATION_ENABLED:
            return Response(GENERIC, status=202)
        try:
            key = canonicalize_email(request.data.get('email'))
        except Exception:
            key = None
        if not allow_request(request, 'email-verification-request', identity=key):
            return Response(GENERIC, status=202)
        if key:
            with transaction.atomic():
                user = CustomUser.objects.select_for_update().filter(email_key=key).first()
                if user and user.is_active and not user.email_verified_at and user.has_usable_password():
                    now = timezone.now()
                    recent = AccountActionChallenge.objects.filter(
                        user=user, purpose=AccountActionChallenge.Purpose.EMAIL_VERIFICATION,
                        issued_at__gt=now - timedelta(seconds=60), superseded_at__isnull=True, consumed_at__isnull=True,
                    ).exists()
                    if not recent:
                        challenge = _new_challenge(user, AccountActionChallenge.Purpose.EMAIL_VERIFICATION, key)
                        link = f"{settings.FRONTEND_URL.rstrip('/')}/confirmar-email#purpose=verification&token={challenge_token(challenge)}"
                        enqueue_email(
                            kind='email_verification', business_key=str(challenge.pk), recipient=user.email,
                            email_key=key, context={'link': link}, send_before=now + timedelta(minutes=15),
                        )
        return Response(GENERIC, status=202)


@method_decorator(csrf_protect, name='dispatch')
class EmailVerificationConfirmationView(NoStoreMixin, APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        if not allow_request(request, 'email-verification-confirm', ip_limit=30, identity_limit=30):
            return Response({'detail': 'Link inválido ou expirado.'}, status=429)
        with transaction.atomic():
            challenge = _valid_challenge(request.data.get('token', ''), AccountActionChallenge.Purpose.EMAIL_VERIFICATION)
            if not challenge:
                return Response({'detail': 'Link inválido ou expirado.'}, status=400)
            user = CustomUser.objects.select_for_update().get(pk=challenge.user_id)
            if challenge.target_fingerprint != recipient_fingerprint(user.email_key):
                return Response({'detail': 'Link inválido ou expirado.'}, status=400)
            now = timezone.now()
            user.email_verified_at = now
            user.save(update_fields=['email_verified_at'])
            challenge.consumed_at = now
            challenge.save(update_fields=['consumed_at'])
            SecurityAuditEvent.objects.create(user=user, event_type='email_verified', outcome='success')
        return Response(status=204)


@method_decorator(csrf_protect, name='dispatch')
class EmailChangeRequestView(NoStoreMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not settings.EMAIL_CHANGE_ENABLED:
            return Response({'detail': 'Troca de e-mail indisponível.'}, status=503)
        try:
            new_key = canonicalize_email(request.data.get('new_email'))
        except Exception:
            return Response({'new_email': ['Informe um e-mail válido.']}, status=400)
        with transaction.atomic():
            user = CustomUser.objects.select_for_update().get(pk=request.user.pk)
            if not user.check_password(request.data.get('current_password', '')):
                return Response({'detail': 'Senha atual inválida.'}, status=400)
            if new_key == user.email_key or CustomUser.objects.filter(email_key=new_key).exclude(pk=user.pk).exists():
                return Response({'new_email': ['Este e-mail não está disponível.']}, status=400)
            now = timezone.now()
            challenge = _new_challenge(
                user, AccountActionChallenge.Purpose.EMAIL_CHANGE, new_key,
                encrypted_target=encrypt_text(request.data['new_email'].strip()),
            )
            link = f"{settings.FRONTEND_URL.rstrip('/')}/confirmar-email#purpose=change&token={challenge_token(challenge)}"
            enqueue_email(
                kind='email_change', business_key=str(challenge.pk), recipient=request.data['new_email'].strip(),
                email_key=new_key, context={'link': link}, send_before=now + timedelta(minutes=15),
            )
            SecurityAuditEvent.objects.create(user=user, event_type='email_change_requested', outcome='success')
        return Response(status=202)


@method_decorator(csrf_protect, name='dispatch')
class EmailChangeConfirmationView(NoStoreMixin, APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        if not allow_request(request, 'email-change-confirm', ip_limit=30, identity_limit=30):
            return Response({'detail': 'Link inválido ou expirado.'}, status=429)
        try:
            with transaction.atomic():
                challenge = _valid_challenge(request.data.get('token', ''), AccountActionChallenge.Purpose.EMAIL_CHANGE)
                if not challenge:
                    return Response({'detail': 'Link inválido ou expirado.'}, status=400)
                user = CustomUser.objects.select_for_update().get(pk=challenge.user_id)
                old_email, old_key = user.email, user.email_key
                new_email = decrypt_text(challenge.encrypted_target)
                new_key = canonicalize_email(new_email)
                if challenge.target_fingerprint != recipient_fingerprint(new_key):
                    return Response({'detail': 'Link inválido ou expirado.'}, status=400)
                if CustomUser.objects.filter(email_key=new_key).exclude(pk=user.pk).exists():
                    return Response({'detail': 'Este e-mail não está mais disponível.'}, status=409)
                now = timezone.now()
                user.email = new_email
                user.email_verified_at = now
                user.revoke_credentials()
                user.save(update_fields=['email', 'email_verified_at', 'credential_version', 'password_changed_at'])
                challenge.consumed_at = now
                challenge.save(update_fields=['consumed_at'])
                AccountActionChallenge.objects.filter(
                    user=user, consumed_at__isnull=True, superseded_at__isnull=True,
                ).exclude(pk=challenge.pk).update(superseded_at=now)
                RecoveryGrant.objects.filter(
                    challenge__user=user, consumed_at__isnull=True, revoked_at__isnull=True,
                ).update(revoked_at=now)
                enqueue_email(
                    kind='email_changed_old', business_key=f'email-changed-old/{challenge.pk}',
                    recipient=old_email, email_key=old_key, context={}, send_before=now + timedelta(hours=23),
                )
                enqueue_email(
                    kind='email_changed_new', business_key=f'email-changed-new/{challenge.pk}',
                    recipient=user.email, email_key=user.email_key, context={}, send_before=now + timedelta(hours=23),
                )
                SecurityAuditEvent.objects.create(user=user, event_type='email_changed', outcome='success')
        except IntegrityError:
            return Response({'detail': 'Este e-mail não está mais disponível.'}, status=409)
        if getattr(request._request.user, 'pk', None) == user.pk:
            logout(request)
            rotate_token(request)
        return Response(status=204)
