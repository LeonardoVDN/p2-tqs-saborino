from unittest.mock import patch

from django.contrib.auth.hashers import identify_hasher
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from notifications.crypto import decrypt_json
from notifications.models import EmailOutbox
from notifications.services import dispatch_one

from .action_tokens import challenge_token
from .models import AccountActionChallenge, CustomUser


TEST_KEY = 'MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA='


@override_settings(
    EMAIL_CRYPTO_KEYS=[TEST_KEY], EMAIL_LOOKUP_HMAC_KEY='test-hmac',
    EMAIL_PROVIDER='fake', EMAIL_DISPATCH_ENABLED=False,
    EMAIL_VERIFICATION_ENABLED=True, EMAIL_CHANGE_ENABLED=True,
    FRONTEND_URL='https://saborino.example',
)
class AccountActionTests(TestCase):
    password = 'senha atual longa 2026'
    new_password = 'senha nova realmente longa 2026'

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='owner', email='owner@example.com', password=self.password,
            email_verified_at=timezone.now(),
        )
        self.client = Client(enforce_csrf_checks=True)

    def csrf(self):
        return self.client.get('/api/v1/auth/csrf/').json()['csrfToken']

    def post(self, path, data):
        return self.client.post(path, data, content_type='application/json', HTTP_X_CSRFTOKEN=self.csrf())

    def login(self):
        response = self.post('/api/v1/auth/sessions/', {'email': self.user.email, 'password': self.password})
        self.assertEqual(response.status_code, 204)

    def test_new_passwords_use_argon2(self):
        self.assertEqual(identify_hasher(self.user.password).algorithm, 'argon2')

    def test_authenticated_password_change_revokes_session_and_enqueues_notice(self):
        self.login()
        response = self.post('/api/v1/auth/password/changes/', {
            'current_password': self.password, 'new_password': self.new_password,
        })
        self.assertEqual(response.status_code, 204)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.new_password))
        self.assertEqual(self.user.credential_version, 2)
        self.assertEqual(self.client.get('/api/v1/me/').status_code, 401)
        self.assertEqual(EmailOutbox.objects.filter(intent='password_changed').count(), 1)

    def test_password_change_rolls_back_if_outbox_fails(self):
        self.login()
        with patch('accounts.account_views.enqueue_email', side_effect=RuntimeError('outbox unavailable')):
            with self.assertRaises(RuntimeError):
                self.post('/api/v1/auth/password/changes/', {
                    'current_password': self.password, 'new_password': self.new_password,
                })
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.password))
        self.assertEqual(self.user.credential_version, 1)

    def test_verification_is_one_time_and_never_activates_suspended_user(self):
        self.user.email_verified_at = None
        self.user.save(update_fields=['email_verified_at'])
        self.assertEqual(self.post('/api/v1/auth/email-verification/requests/', {'email': self.user.email}).status_code, 202)
        context = decrypt_json(EmailOutbox.objects.get(intent='email_verification').encrypted_context)
        token = context['link'].split('token=', 1)[1]
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        self.assertEqual(self.post('/api/v1/auth/email-verification/confirmations/', {'token': token}).status_code, 204)
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.email_verified_at)
        self.assertFalse(self.user.is_active)
        self.assertEqual(self.post('/api/v1/auth/email-verification/confirmations/', {'token': token}).status_code, 400)

    def test_email_change_keeps_old_until_confirm_then_revokes(self):
        self.login()
        self.assertEqual(self.post('/api/v1/auth/email-change/requests/', {
            'current_password': self.password, 'new_email': 'New.Owner@Example.com',
        }).status_code, 202)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email_key, 'owner@example.com')
        context = decrypt_json(EmailOutbox.objects.get(intent='email_change').encrypted_context)
        token = context['link'].split('token=', 1)[1]
        self.assertEqual(self.post('/api/v1/auth/email-change/confirmations/', {'token': token}).status_code, 204)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email_key, 'new.owner@example.com')
        self.assertIsNotNone(self.user.email_verified_at)
        self.assertEqual(self.user.credential_version, 2)
        self.assertEqual(EmailOutbox.objects.filter(intent__startswith='email_changed_').count(), 2)
        self.assertEqual(self.client.get('/api/v1/me/').status_code, 401)

    def test_email_change_rechecks_uniqueness_at_confirmation(self):
        self.login()
        self.post('/api/v1/auth/email-change/requests/', {
            'current_password': self.password, 'new_email': 'claimed@example.com',
        })
        challenge = AccountActionChallenge.objects.get(purpose=AccountActionChallenge.Purpose.EMAIL_CHANGE)
        CustomUser.objects.create_user(username='other', email='claimed@example.com', password=self.password)
        response = self.post('/api/v1/auth/email-change/confirmations/', {'token': challenge_token(challenge)})
        self.assertEqual(response.status_code, 409)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email_key, 'owner@example.com')

    def test_action_purposes_are_not_interchangeable(self):
        self.login()
        self.post('/api/v1/auth/email-change/requests/', {
            'current_password': self.password, 'new_email': 'next@example.com',
        })
        challenge = AccountActionChallenge.objects.get(purpose=AccountActionChallenge.Purpose.EMAIL_CHANGE)
        response = self.post('/api/v1/auth/email-verification/confirmations/', {'token': challenge_token(challenge)})
        self.assertEqual(response.status_code, 400)

    @override_settings(EMAIL_DISPATCH_ENABLED=True, EMAIL_TEST_ALLOWLIST=['owner@example.com'])
    def test_superseded_challenge_is_revalidated_before_send(self):
        self.user.email_verified_at = None
        self.user.save(update_fields=['email_verified_at'])
        self.post('/api/v1/auth/email-verification/requests/', {'email': self.user.email})
        item = EmailOutbox.objects.get(intent='email_verification')
        challenge = AccountActionChallenge.objects.get(pk=item.business_key)
        challenge.superseded_at = timezone.now()
        challenge.save(update_fields=['superseded_at'])
        self.assertEqual(dispatch_one(item.pk), EmailOutbox.Status.EXPIRED)
        item.refresh_from_db()
        self.assertEqual(item.last_error_code, 'challenge_not_sendable')

    def test_password_maximum_is_enforced(self):
        self.login()
        response = self.post('/api/v1/auth/password/changes/', {
            'current_password': self.password, 'new_password': 'x' * 129,
        })
        self.assertEqual(response.status_code, 400)
