from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import exceptions
from rest_framework.authentication import SessionAuthentication


SESSION_STARTED_AT = 'identity_started_at'
SESSION_LAST_ACTIVITY_AT = 'identity_last_activity_at'
SESSION_CREDENTIAL_VERSION = 'identity_credential_version'


class VersionedSessionAuthentication(SessionAuthentication):
    """Sessão DB-backed com versão, idle e duração absoluta server-side."""

    def authenticate_header(self, request):
        # Faz o DRF preservar 401 (não 403) para sessão ausente/revogada.
        return 'Session'

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, auth = result
        session = request._request.session
        now = timezone.now()
        try:
            started = timezone.datetime.fromisoformat(session[SESSION_STARTED_AT])
            last = timezone.datetime.fromisoformat(session[SESSION_LAST_ACTIVITY_AT])
            version = int(session[SESSION_CREDENTIAL_VERSION])
        except (KeyError, TypeError, ValueError):
            session.flush()
            raise exceptions.AuthenticationFailed('Sessão inválida.', code='invalid_session')

        if timezone.is_naive(started):
            started = timezone.make_aware(started)
        if timezone.is_naive(last):
            last = timezone.make_aware(last)
        idle = timedelta(seconds=settings.WEB_SESSION_IDLE_SECONDS)
        absolute = timedelta(seconds=settings.WEB_SESSION_ABSOLUTE_SECONDS)
        if now - last > idle or now - started > absolute:
            session.flush()
            raise exceptions.AuthenticationFailed('Sessão expirada.', code='session_expired')

        User = get_user_model()
        try:
            current = User.objects.only('credential_version', 'is_active').get(pk=user.pk)
        except User.DoesNotExist:
            session.flush()
            raise exceptions.AuthenticationFailed('Sessão inválida.', code='invalid_session')
        if not current.is_active or current.credential_version != version:
            session.flush()
            raise exceptions.AuthenticationFailed('Sessão revogada.', code='session_revoked')

        if request.method not in ('GET', 'HEAD', 'OPTIONS') or request.path.endswith('/me/'):
            session[SESSION_LAST_ACTIVITY_AT] = now.isoformat()
            session.modified = True
        return user, auth


def initialize_identity_session(request, user):
    now = timezone.now().isoformat()
    request.session[SESSION_STARTED_AT] = now
    request.session[SESSION_LAST_ACTIVITY_AT] = now
    request.session[SESSION_CREDENTIAL_VERSION] = user.credential_version
