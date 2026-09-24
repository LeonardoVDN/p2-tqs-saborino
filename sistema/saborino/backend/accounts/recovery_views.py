from datetime import timedelta
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.middleware.csrf import rotate_token
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.crypto import recipient_fingerprint
from notifications.services import enqueue_email
from .action_tokens import challenge_token, grant_expiry, hash_secret, new_grant_secret, read_challenge_token
from .identity import canonicalize_email
from .models import AccountActionChallenge, CustomUser, RecoveryGrant, SecurityAuditEvent
from .rate_limits import allow_request
from .session_views import NoStoreMixin


GENERIC = {'detail': 'Se existir uma conta elegível, enviaremos as instruções.'}


@method_decorator(csrf_protect, name='dispatch')
class PasswordResetRequestView(NoStoreMixin, APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        if not settings.PASSWORD_RESET_ENABLED:
            return Response(GENERIC, status=status.HTTP_202_ACCEPTED)
        try: key = canonicalize_email(request.data.get('email'))
        except Exception: key = None
        if not allow_request(request, 'password-reset-request', identity=key):
            return Response(GENERIC, status=status.HTTP_202_ACCEPTED)
        if key:
            with transaction.atomic():
                user = CustomUser.objects.select_for_update().filter(email_key=key).first()
                if user and user.is_active and user.email_verified_at and user.has_usable_password():
                    now = timezone.now()
                    recent = AccountActionChallenge.objects.filter(user=user, purpose=AccountActionChallenge.Purpose.PASSWORD_RESET, issued_at__gt=now - timedelta(seconds=60), superseded_at__isnull=True, consumed_at__isnull=True).exists()
                    if not recent:
                        AccountActionChallenge.objects.filter(user=user, purpose=AccountActionChallenge.Purpose.PASSWORD_RESET, superseded_at__isnull=True, consumed_at__isnull=True).update(superseded_at=now)
                        challenge = AccountActionChallenge.objects.create(user=user, purpose=AccountActionChallenge.Purpose.PASSWORD_RESET, target_fingerprint=recipient_fingerprint(key), credential_version=user.credential_version, expires_at=now + timedelta(minutes=60))
                        token = challenge_token(challenge)
                        link = f"{settings.FRONTEND_URL.rstrip('/')}/redefinir-senha#token={token}"
                        enqueue_email(kind='password_reset', business_key=str(challenge.pk), recipient=user.email, email_key=key, context={'link': link}, send_before=now + timedelta(minutes=15))
        return Response(GENERIC, status=status.HTTP_202_ACCEPTED)


@method_decorator(csrf_protect, name='dispatch')
class PasswordResetExchangeView(NoStoreMixin, APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        if not allow_request(request, 'password-reset-exchange', ip_limit=30, identity_limit=30):
            return Response({'detail': 'Link inválido ou expirado.'}, status=429)
        try: challenge_id = read_challenge_token(request.data.get('token', ''), AccountActionChallenge.Purpose.PASSWORD_RESET)
        except signing.BadSignature: return Response({'detail': 'Link inválido ou expirado.'}, status=400)
        with transaction.atomic():
            challenge = AccountActionChallenge.objects.select_for_update().select_related('user').filter(pk=challenge_id).first()
            now = timezone.now()
            if not challenge or challenge.expires_at <= now or challenge.consumed_at or challenge.superseded_at or challenge.credential_version != challenge.user.credential_version:
                return Response({'detail': 'Link inválido ou expirado.'}, status=400)
            RecoveryGrant.objects.filter(challenge=challenge, consumed_at__isnull=True, revoked_at__isnull=True).update(revoked_at=now)
            secret = new_grant_secret()
            RecoveryGrant.objects.create(challenge=challenge, secret_hash=hash_secret(secret), expires_at=grant_expiry(challenge))
        response = Response(status=204)
        # __Host- cookies require Path=/; browsers reject narrower paths.
        # The grant is still accepted only by the password-reset endpoints.
        response.set_cookie(settings.RECOVERY_COOKIE_NAME, secret, secure=not settings.DEBUG, httponly=True, samesite='Strict', path='/')
        return response


@method_decorator(csrf_protect, name='dispatch')
class PasswordResetConfirmationView(NoStoreMixin, APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        if not allow_request(request, 'password-reset-confirm', ip_limit=15, identity_limit=15, window_seconds=900):
            return Response({'detail': 'Autorização inválida ou expirada.'}, status=429)
        secret = request.COOKIES.get(settings.RECOVERY_COOKIE_NAME, '')
        try: validate_password(request.data.get('password', ''))
        except ValidationError as exc: return Response({'password': list(exc.messages)}, status=400)
        with transaction.atomic():
            grant = RecoveryGrant.objects.select_for_update().select_related('challenge__user').filter(secret_hash=hash_secret(secret)).first()
            now = timezone.now()
            if not grant or grant.expires_at <= now or grant.consumed_at or grant.revoked_at:
                return Response({'detail': 'Autorização inválida ou expirada.'}, status=400)
            challenge = AccountActionChallenge.objects.select_for_update().get(pk=grant.challenge_id)
            user = CustomUser.objects.select_for_update().get(pk=challenge.user_id)
            if challenge.consumed_at or challenge.superseded_at or challenge.expires_at <= now or challenge.credential_version != user.credential_version:
                return Response({'detail': 'Autorização inválida ou expirada.'}, status=400)
            user.set_password(request.data['password']); user.revoke_credentials(); user.save(update_fields=['password', 'credential_version', 'password_changed_at'])
            challenge.consumed_at = now; challenge.save(update_fields=['consumed_at'])
            grant.consumed_at = now; grant.save(update_fields=['consumed_at'])
            RecoveryGrant.objects.filter(challenge=challenge, consumed_at__isnull=True, revoked_at__isnull=True).exclude(pk=grant.pk).update(revoked_at=now)
            enqueue_email(kind='password_changed', business_key=f'password-changed/{challenge.pk}', recipient=user.email, email_key=user.email_key, context={}, send_before=now + timedelta(hours=23))
            SecurityAuditEvent.objects.create(user=user, event_type='password_reset_completed', outcome='success')
        logout(request); rotate_token(request)
        response = Response(status=204); response.delete_cookie(settings.RECOVERY_COOKIE_NAME, path='/')
        return response
