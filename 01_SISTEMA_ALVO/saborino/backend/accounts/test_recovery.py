from django.test import Client, TestCase, override_settings
from django.utils import timezone

from notifications.crypto import decrypt_json
from notifications.models import EmailOutbox
from .models import AccountActionChallenge, CustomUser


TEST_KEY = 'MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA='


@override_settings(EMAIL_CRYPTO_KEYS=[TEST_KEY], EMAIL_LOOKUP_HMAC_KEY='test-hmac', EMAIL_PROVIDER='fake', EMAIL_DISPATCH_ENABLED=False, PASSWORD_RESET_ENABLED=True, FRONTEND_URL='https://saborino.example')
class PasswordRecoveryTests(TestCase):
    old_password = 'senha antiga longa 2026'
    new_password = 'senha nova bem longa 2026'

    def setUp(self):
        self.user = CustomUser.objects.create_user(username='owner', email='owner@example.com', password=self.old_password, email_verified_at=timezone.now())
        self.client = Client(enforce_csrf_checks=True)

    def csrf(self):
        return self.client.get('/api/v1/auth/csrf/').json()['csrfToken']

    def post(self, path, data):
        return self.client.post(path, data, content_type='application/json', HTTP_X_CSRFTOKEN=self.csrf())

    def test_request_is_uniform_and_cooldown_keeps_latest_link(self):
        self.assertEqual(self.post('/api/v1/auth/password-reset/requests/', {'email': 'missing@example.com'}).status_code, 202)
        first = self.post('/api/v1/auth/password-reset/requests/', {'email': 'OWNER@example.com'})
        self.assertEqual(first.status_code, 202)
        self.assertEqual(AccountActionChallenge.objects.count(), 1)
        self.assertEqual(EmailOutbox.objects.count(), 1)
        self.post('/api/v1/auth/password-reset/requests/', {'email': 'owner@example.com'})
        self.assertEqual(AccountActionChallenge.objects.count(), 1)

    def test_full_reset_is_one_time_and_revokes_old_password(self):
        self.post('/api/v1/auth/password-reset/requests/', {'email': self.user.email})
        context = decrypt_json(EmailOutbox.objects.get(intent='password_reset').encrypted_context)
        token = context['link'].split('#token=', 1)[1]
        exchanged = self.post('/api/v1/auth/password-reset/exchanges/', {'token': token})
        self.assertEqual(exchanged.status_code, 204)
        confirmed = self.post('/api/v1/auth/password-reset/confirmations/', {'password': self.new_password})
        self.assertEqual(confirmed.status_code, 204)
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password(self.old_password))
        self.assertTrue(self.user.check_password(self.new_password))
        self.assertEqual(self.user.credential_version, 2)
        self.assertEqual(self.post('/api/v1/auth/password-reset/exchanges/', {'token': token}).status_code, 400)
        self.assertEqual(EmailOutbox.objects.filter(intent='password_changed').count(), 1)

    @override_settings(DEBUG=False, SECURE_SSL_REDIRECT=False, RECOVERY_COOKIE_NAME='__Host-recovery')
    def test_production_cookie_satisfies_host_prefix_and_deletes_same_path(self):
        self.post('/api/v1/auth/password-reset/requests/', {'email': self.user.email})
        context = decrypt_json(EmailOutbox.objects.get(intent='password_reset').encrypted_context)
        token = context['link'].split('#token=', 1)[1]
        exchanged = self.post('/api/v1/auth/password-reset/exchanges/', {'token': token})
        self.assertEqual(exchanged.status_code, 204)
        cookie = exchanged.cookies['__Host-recovery']
        self.assertEqual(cookie['path'], '/')
        self.assertEqual(cookie['domain'], '')
        self.assertTrue(cookie['secure'])
        self.assertTrue(cookie['httponly'])
        self.assertEqual(cookie['samesite'], 'Strict')
        confirmed = self.post('/api/v1/auth/password-reset/confirmations/', {'password': self.new_password})
        self.assertEqual(confirmed.status_code, 204)
        deletion = confirmed.cookies['__Host-recovery']
        self.assertEqual(deletion['path'], '/')
        self.assertEqual(deletion['max-age'], 0)
        self.assertTrue(deletion['secure'])
