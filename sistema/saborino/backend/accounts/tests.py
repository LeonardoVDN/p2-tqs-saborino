from importlib import reload

from django.test import SimpleTestCase, override_settings
from django.urls import Resolver404, clear_url_caches, resolve
from django.utils import timezone
from django.test import Client, TestCase
from datetime import timedelta

import core.urls


class InternalRouteIsolationTests(SimpleTestCase):
    def _reload_urlconf(self):
        clear_url_caches()
        urlconf = reload(core.urls)
        clear_url_caches()
        return urlconf

    def _assert_not_resolved(self, urlconf, path):
        with self.assertRaises(Resolver404):
            resolve(path, urlconf=urlconf)

    def test_internal_routes_are_absent_when_disabled(self):
        try:
            with override_settings(ENABLE_INTERNAL_API=False):
                urlconf = self._reload_urlconf()

                self._assert_not_resolved(urlconf, '/api/internal/test-celery/')
                self._assert_not_resolved(urlconf, '/api/internal/auth/login/')
                self._assert_not_resolved(urlconf, '/api/v1/test-celery/')
                self._assert_not_resolved(urlconf, '/api/v1/auth/login/')

                self.assertEqual(resolve('/api/v1/me/', urlconf=urlconf).url_name, 'me')
                self.assertEqual(
                    resolve('/api/v1/auth/session/', urlconf=urlconf).url_name,
                    'session-delete',
                )
        finally:
            self._reload_urlconf()

    def test_internal_routes_use_only_internal_prefix_when_enabled(self):
        try:
            with override_settings(ENABLE_INTERNAL_API=True):
                urlconf = self._reload_urlconf()

                self.assertIsNotNone(
                    resolve('/api/internal/test-celery/', urlconf=urlconf)
                )
                self.assertIsNotNone(
                    resolve('/api/internal/auth/login/', urlconf=urlconf)
                )
                self._assert_not_resolved(urlconf, '/api/v1/test-celery/')
                self._assert_not_resolved(urlconf, '/api/v1/auth/login/')
        finally:
            self._reload_urlconf()


class IdentityCanonicalizationTests(SimpleTestCase):
    def test_case_idna_and_plus_are_conservative(self):
        from .identity import canonicalize_email

        self.assertEqual(canonicalize_email('  Foo.Bar+tag@BÜCHER.example  '), 'foo.bar+tag@xn--bcher-kva.example')

    def test_unicode_local_part_is_rejected(self):
        from django.core.exceptions import ValidationError
        from .identity import canonicalize_email

        with self.assertRaises(ValidationError):
            canonicalize_email('léon@example.com')

    @override_settings(SECRET_KEY='rate-test-secret')
    def test_rate_limit_keys_do_not_contain_identity(self):
        from .rate_limits import rate_key

        key = rate_key('login:identity', 'Owner@Example.com')
        self.assertNotIn('Owner', key)
        self.assertNotIn('example.com', key)
        self.assertEqual(key, rate_key('login:identity', 'Owner@Example.com'))


@override_settings(API_JWT_ENABLED=False, PUBLIC_ADMIN_ENABLED=False)
class SessionFlowTests(TestCase):
    password = 'uma senha longa e valida 2026'

    def setUp(self):
        from .models import CustomUser

        self.user = CustomUser.objects.create_user(
            username='usuario', email='Usuario@Example.COM', password=self.password,
            email_verified_at=timezone.now(),
        )
        self.client = Client(enforce_csrf_checks=True)

    def csrf(self):
        response = self.client.get('/api/v1/auth/csrf/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('no-store', response['Cache-Control'])
        return response.json()['csrfToken']

    def login(self):
        response = self.client.post(
            '/api/v1/auth/sessions/',
            {'email': 'USUARIO@example.com', 'password': self.password},
            content_type='application/json', HTTP_X_CSRFTOKEN=self.csrf(),
        )
        self.assertEqual(response.status_code, 204)

    def test_login_requires_csrf_and_verified_email(self):
        response = self.client.post(
            '/api/v1/auth/sessions/',
            {'email': self.user.email, 'password': self.password},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)
        self.login()
        self.assertEqual(self.client.get('/api/v1/me/').status_code, 200)

    def test_unverified_email_cannot_login(self):
        self.user.email_verified_at = None
        self.user.save(update_fields=['email_verified_at'])
        response = self.client.post(
            '/api/v1/auth/sessions/',
            {'email': self.user.email, 'password': self.password},
            content_type='application/json', HTTP_X_CSRFTOKEN=self.csrf(),
        )
        self.assertEqual(response.status_code, 401)

    def test_idle_and_absolute_timeouts_are_server_side(self):
        from .authentication import SESSION_LAST_ACTIVITY_AT, SESSION_STARTED_AT

        self.login()
        session = self.client.session
        session[SESSION_LAST_ACTIVITY_AT] = (timezone.now() - timedelta(minutes=31)).isoformat()
        session.save()
        self.assertEqual(self.client.get('/api/v1/me/').status_code, 401)

        self.login()
        session = self.client.session
        session[SESSION_STARTED_AT] = (timezone.now() - timedelta(hours=13)).isoformat()
        session.save()
        self.assertEqual(self.client.get('/api/v1/me/').status_code, 401)

    def test_credential_version_revokes_existing_session(self):
        self.login()
        self.user.credential_version += 1
        self.user.save(update_fields=['credential_version'])
        self.assertEqual(self.client.get('/api/v1/me/').status_code, 401)

    def test_logout_is_idempotent_and_csrf_protected(self):
        self.login()
        token = self.csrf()
        self.assertEqual(
            self.client.delete('/api/v1/auth/session/', HTTP_X_CSRFTOKEN=token).status_code,
            204,
        )

    def test_revoke_all_requires_password_and_ends_current_session(self):
        self.login()
        token = self.csrf()
        bad = self.client.post(
            '/api/v1/auth/sessions/revoke-all/', {'password': 'wrong'},
            content_type='application/json', HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(bad.status_code, 400)
        good = self.client.post(
            '/api/v1/auth/sessions/revoke-all/', {'password': self.password},
            content_type='application/json', HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(good.status_code, 204)
        self.assertEqual(self.client.get('/api/v1/me/').status_code, 401)
        token = self.csrf()
        self.assertEqual(
            self.client.delete('/api/v1/auth/session/', HTTP_X_CSRFTOKEN=token).status_code,
            204,
        )

    def test_jwt_and_public_admin_routes_are_absent(self):
        self.assertEqual(self.client.post('/api/v1/auth/token/').status_code, 404)
        self.assertEqual(self.client.get('/admin/').status_code, 404)

    def test_direct_email_change_invalidates_verification_and_updates_key(self):
        self.user.email = 'Changed@Example.com'
        self.user.save(update_fields=['email'])
        self.user.refresh_from_db()
        self.assertEqual(self.user.email_key, 'changed@example.com')
        self.assertIsNone(self.user.email_verified_at)
