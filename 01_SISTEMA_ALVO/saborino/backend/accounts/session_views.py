from django.contrib.auth import login, logout
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.middleware.csrf import get_token, rotate_token
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import initialize_identity_session
from .identity import canonicalize_email
from .models import CustomUser
from .rate_limits import allow_request

_DUMMY_PASSWORD_HASH = make_password('dummy-password-that-is-never-valid')


class NoStoreMixin:
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response['Cache-Control'] = 'no-store'
        response['Referrer-Policy'] = 'no-referrer'
        return response


@method_decorator(never_cache, name='dispatch')
class CsrfBootstrapView(NoStoreMixin, APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({'csrfToken': get_token(request)})


@method_decorator(csrf_protect, name='dispatch')
class SessionCreateView(NoStoreMixin, APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        try:
            key = canonicalize_email(request.data.get('email'))
        except Exception:
            key = None
        password = request.data.get('password') or ''
        if not allow_request(request, 'login', identity=key, ip_limit=30, identity_limit=10, window_seconds=300):
            check_password(password, _DUMMY_PASSWORD_HASH)
            return Response({'detail': 'E-mail ou senha inválidos.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        user = None
        if key:
            with transaction.atomic():
                candidate = CustomUser.objects.select_for_update().filter(email_key=key).first()
                if (
                    candidate
                    and candidate.is_active
                    and candidate.email_verified_at
                    and check_password(password, candidate.password)
                ):
                    user = candidate
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    initialize_identity_session(request, user)
        if user is None:
            # Mantém custo de hash para identidades inexistentes.
            check_password(password, _DUMMY_PASSWORD_HASH)
            return Response({'detail': 'E-mail ou senha inválidos.'}, status=status.HTTP_401_UNAUTHORIZED)
        rotate_token(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(csrf_protect, name='dispatch')
class SessionDeleteView(NoStoreMixin, APIView):
    permission_classes = [AllowAny]

    def delete(self, request):
        logout(request)
        rotate_token(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(csrf_protect, name='dispatch')
class RevokeAllSessionsView(NoStoreMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        password = request.data.get('password') or ''
        with transaction.atomic():
            user = CustomUser.objects.select_for_update().get(pk=request.user.pk)
            if not user.check_password(password):
                return Response({'detail': 'Senha atual inválida.'}, status=status.HTTP_400_BAD_REQUEST)
            user.revoke_credentials()
            user.save(update_fields=['credential_version', 'password_changed_at'])
        logout(request)
        rotate_token(request)
        return Response(status=status.HTTP_204_NO_CONTENT)
