import threading
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, close_old_connections, connections, transaction
from django.test import Client, TransactionTestCase, override_settings
from django.utils import timezone

from notifications.crypto import recipient_fingerprint

from .action_tokens import hash_secret, new_grant_secret
from .models import AccountActionChallenge, CustomUser, RecoveryGrant


TEST_KEY = 'MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA='


@override_settings(
    EMAIL_CRYPTO_KEYS=[TEST_KEY], EMAIL_LOOKUP_HMAC_KEY='test-hmac',
    EMAIL_PROVIDER='fake', EMAIL_DISPATCH_ENABLED=False,
    PASSWORD_RESET_ENABLED=True, FRONTEND_URL='https://saborino.example',
)
class AccountConcurrencyTests(TransactionTestCase):
    reset_sequences = True
    password = 'senha antiga concorrente 2026'
    new_password = 'senha nova concorrente 2026'

    def test_unique_email_key_allows_only_one_concurrent_writer(self):
        first = CustomUser.objects.create_user(username='first', email='first@example.com', password=self.password)
        second = CustomUser.objects.create_user(username='second', email='second@example.com', password=self.password)
        barrier = threading.Barrier(2)
        outcomes = []

        def change(user_id):
            close_old_connections()
            try:
                with transaction.atomic():
                    user = CustomUser.objects.get(pk=user_id)
                    user.email = 'claimed@example.com'
                    barrier.wait(timeout=5)
                    user.save(update_fields=['email'])
                outcomes.append('saved')
            except IntegrityError:
                outcomes.append('conflict')
            finally:
                connections.close_all()

        threads = [threading.Thread(target=change, args=(first.pk,)), threading.Thread(target=change, args=(second.pk,))]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertCountEqual(outcomes, ['saved', 'conflict'])
        self.assertEqual(CustomUser.objects.filter(email_key='claimed@example.com').count(), 1)

    def test_only_one_concurrent_reset_confirmation_wins(self):
        user = CustomUser.objects.create_user(
            username='owner', email='owner@example.com', password=self.password,
            email_verified_at=timezone.now(),
        )
        now = timezone.now()
        challenge = AccountActionChallenge.objects.create(
            user=user, purpose=AccountActionChallenge.Purpose.PASSWORD_RESET,
            target_fingerprint=recipient_fingerprint(user.email_key),
            credential_version=user.credential_version,
            expires_at=now + timedelta(minutes=60),
        )
        secret = new_grant_secret()
        RecoveryGrant.objects.create(
            challenge=challenge, secret_hash=hash_secret(secret),
            expires_at=now + timedelta(minutes=15),
        )
        barrier = threading.Barrier(2)
        statuses = []

        def confirm():
            close_old_connections()
            try:
                client = Client(enforce_csrf_checks=True)
                client.cookies[settings.RECOVERY_COOKIE_NAME] = secret
                csrf = client.get('/api/v1/auth/csrf/').json()['csrfToken']
                barrier.wait(timeout=5)
                response = client.post(
                    '/api/v1/auth/password-reset/confirmations/',
                    {'password': self.new_password}, content_type='application/json',
                    HTTP_X_CSRFTOKEN=csrf,
                )
                statuses.append(response.status_code)
            finally:
                connections.close_all()

        threads = [threading.Thread(target=confirm), threading.Thread(target=confirm)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertCountEqual(statuses, [204, 400])
        user.refresh_from_db()
        self.assertEqual(user.credential_version, 2)
        self.assertTrue(user.check_password(self.new_password))

    def test_login_racing_reset_cannot_keep_a_valid_old_session(self):
        user = CustomUser.objects.create_user(
            username='racing', email='racing@example.com', password=self.password,
            email_verified_at=timezone.now(),
        )
        recovery_client = Client(enforce_csrf_checks=True)
        csrf = recovery_client.get('/api/v1/auth/csrf/').json()['csrfToken']
        recovery_client.post(
            '/api/v1/auth/password-reset/requests/', {'email': user.email},
            content_type='application/json', HTTP_X_CSRFTOKEN=csrf,
        )
        from notifications.crypto import decrypt_json
        from notifications.models import EmailOutbox
        token = decrypt_json(EmailOutbox.objects.get(intent='password_reset').encrypted_context)['link'].split('#token=', 1)[1]
        csrf = recovery_client.get('/api/v1/auth/csrf/').json()['csrfToken']
        self.assertEqual(recovery_client.post(
            '/api/v1/auth/password-reset/exchanges/', {'token': token},
            content_type='application/json', HTTP_X_CSRFTOKEN=csrf,
        ).status_code, 204)
        login_client = Client(enforce_csrf_checks=True)
        login_csrf = login_client.get('/api/v1/auth/csrf/').json()['csrfToken']
        recovery_csrf = recovery_client.get('/api/v1/auth/csrf/').json()['csrfToken']
        barrier = threading.Barrier(2)
        statuses = {}

        def login_old():
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                statuses['login'] = login_client.post(
                    '/api/v1/auth/sessions/', {'email': user.email, 'password': self.password},
                    content_type='application/json', HTTP_X_CSRFTOKEN=login_csrf,
                ).status_code
            finally:
                connections.close_all()

        def finish_reset():
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                statuses['reset'] = recovery_client.post(
                    '/api/v1/auth/password-reset/confirmations/', {'password': self.new_password},
                    content_type='application/json', HTTP_X_CSRFTOKEN=recovery_csrf,
                ).status_code
            finally:
                connections.close_all()

        threads = [threading.Thread(target=login_old), threading.Thread(target=finish_reset)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(statuses['reset'], 204)
        self.assertIn(statuses['login'], (204, 401))
        self.assertEqual(login_client.get('/api/v1/me/').status_code, 401)
        user.refresh_from_db()
        self.assertTrue(user.check_password(self.new_password))
