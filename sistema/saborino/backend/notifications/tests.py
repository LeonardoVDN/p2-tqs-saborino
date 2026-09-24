from datetime import timedelta
from datetime import datetime, timezone as dt_timezone
import json
from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from svix.webhooks import Webhook

from .crypto import decrypt_json, decrypt_text
from .models import EmailBudget, EmailOutbox, EmailSuppression, ProviderEvent
from .providers import ProviderError
from .providers import ResendProvider
from .services import dispatch_one, enqueue_email, process_provider_event
from .tasks import apply_email_retention, dispatch_email_outbox, mark_unknown_email_deliveries, sweep_email_leases


TEST_KEY = 'MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA='
WEBHOOK_SECRET = 'whsec_MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA='


@override_settings(EMAIL_CRYPTO_KEYS=[TEST_KEY], EMAIL_LOOKUP_HMAC_KEY='test-hmac', EMAIL_PROVIDER='fake', EMAIL_DISPATCH_ENABLED=True, EMAIL_TEST_ALLOWLIST=['owner@example.com'])
class OutboxTests(TestCase):
    def test_outbox_encrypts_pii_and_fake_dispatch_is_stable(self):
        item = enqueue_email(kind='password_changed', business_key='encryption-1', recipient='owner@example.com', email_key='owner@example.com', context={'detail': 'secret'}, send_before=timezone.now() + timedelta(minutes=15))
        self.assertNotIn('owner@example.com', item.encrypted_recipient)
        self.assertNotIn('secret', item.encrypted_context)
        self.assertEqual(decrypt_text(item.encrypted_recipient), 'owner@example.com')
        self.assertEqual(decrypt_json(item.encrypted_context)['detail'], 'secret')
        self.assertEqual(dispatch_one(item.pk), EmailOutbox.Status.ACCEPTED)
        item.refresh_from_db()
        self.assertTrue(item.provider_message_id.startswith('fake-'))

    def test_transaction_rollback_leaves_no_intention(self):
        from django.db import transaction
        try:
            with transaction.atomic():
                enqueue_email(kind='password_changed', business_key='rolled-back', recipient='owner@example.com', email_key='owner@example.com', context={}, send_before=timezone.now() + timedelta(hours=1))
                raise RuntimeError('rollback')
        except RuntimeError:
            pass
        self.assertFalse(EmailOutbox.objects.filter(business_key='rolled-back').exists())

    @override_settings(EMAIL_TEST_ALLOWLIST=['someone-else@example.com'])
    def test_allowlist_blocks_external_recipient(self):
        item = enqueue_email(kind='password_changed', business_key='blocked', recipient='owner@example.com', email_key='owner@example.com', context={}, send_before=timezone.now() + timedelta(hours=1))
        self.assertEqual(dispatch_one(item.pk), EmailOutbox.Status.FAILED)
        item.refresh_from_db()
        self.assertEqual(item.last_error_code, 'recipient_not_allowlisted')

    def test_retry_keeps_one_budget_reservation_then_accepts(self):
        item = enqueue_email(kind='password_changed', business_key='retry-budget', recipient='owner@example.com', email_key='owner@example.com', context={}, send_before=timezone.now() + timedelta(hours=1))
        with patch('notifications.services.get_provider') as provider:
            provider.return_value.send.side_effect = [ProviderError('transport_ambiguous', retryable=True), {'id': 'accepted-after-retry'}]
            self.assertEqual(dispatch_one(item.pk), EmailOutbox.Status.PENDING)
            item.refresh_from_db()
            self.assertTrue(item.budget_reserved)
            self.assertEqual(sum(EmailBudget.objects.values_list('reserved', flat=True)), 2)
            item.next_attempt_at = timezone.now() - timedelta(seconds=1)
            item.save(update_fields=['next_attempt_at'])
            self.assertEqual(dispatch_one(item.pk), EmailOutbox.Status.ACCEPTED)
        item.refresh_from_db()
        self.assertFalse(item.budget_reserved)
        self.assertEqual(sum(EmailBudget.objects.values_list('reserved', flat=True)), 0)
        self.assertEqual(sum(EmailBudget.objects.values_list('submitted', flat=True)), 2)

    def test_expiry_releases_retry_budget(self):
        item = enqueue_email(kind='password_changed', business_key='expired-budget', recipient='owner@example.com', email_key='owner@example.com', context={}, send_before=timezone.now() + timedelta(hours=1))
        with patch('notifications.services.get_provider') as provider:
            provider.return_value.send.side_effect = ProviderError('transport_ambiguous', retryable=True)
            self.assertEqual(dispatch_one(item.pk), EmailOutbox.Status.PENDING)
        item.send_before = timezone.now() - timedelta(seconds=1)
        item.next_attempt_at = timezone.now() - timedelta(seconds=1)
        item.save(update_fields=['send_before', 'next_attempt_at'])
        self.assertEqual(dispatch_one(item.pk), EmailOutbox.Status.EXPIRED)
        self.assertEqual(sum(EmailBudget.objects.values_list('reserved', flat=True)), 0)

    def test_payload_divergence_fails_without_submission(self):
        item = enqueue_email(kind='password_changed', business_key='diverged', recipient='owner@example.com', email_key='owner@example.com', context={}, send_before=timezone.now() + timedelta(hours=1))
        item.payload_hash = '0' * 64
        item.save(update_fields=['payload_hash'])
        with patch('notifications.services.get_provider') as provider:
            self.assertEqual(dispatch_one(item.pk), EmailOutbox.Status.FAILED)
            provider.assert_not_called()
        item.refresh_from_db()
        self.assertEqual(item.last_error_code, 'payload_diverged')
        self.assertFalse(item.budget_reserved)

    def test_poller_claims_once_and_sweeper_recovers_lost_task(self):
        item = enqueue_email(kind='password_changed', business_key='claim-once', recipient='owner@example.com', email_key='owner@example.com', context={}, send_before=timezone.now() + timedelta(hours=1))
        with patch('notifications.tasks.dispatch_email_by_id.delay') as delay:
            self.assertEqual(dispatch_email_outbox(), 1)
            self.assertEqual(dispatch_email_outbox(), 0)
            delay.assert_called_once_with(str(item.pk))
        item.refresh_from_db()
        item.lease_expires_at = timezone.now() - timedelta(seconds=1)
        item.save(update_fields=['lease_expires_at'])
        self.assertEqual(sweep_email_leases(), 1)
        item.refresh_from_db()
        self.assertEqual(item.status, EmailOutbox.Status.PENDING)

    def test_stale_accepted_delivery_becomes_unknown(self):
        item = enqueue_email(kind='password_changed', business_key='unknown-delivery', recipient='owner@example.com', email_key='owner@example.com', context={}, send_before=timezone.now() + timedelta(hours=1))
        dispatch_one(item.pk)
        EmailOutbox.objects.filter(pk=item.pk).update(submitted_at=timezone.now() - timedelta(hours=25))
        self.assertEqual(mark_unknown_email_deliveries(), 1)
        item.refresh_from_db()
        self.assertEqual(item.status, EmailOutbox.Status.UNKNOWN)

    def test_retention_scrubs_personal_payload_after_seven_days(self):
        item = enqueue_email(kind='password_changed', business_key='retention', recipient='owner@example.com', email_key='owner@example.com', context={'detail': 'private'}, send_before=timezone.now() + timedelta(hours=1))
        dispatch_one(item.pk)
        EmailOutbox.objects.filter(pk=item.pk).update(updated_at=timezone.now() - timedelta(days=8))
        result = apply_email_retention()
        self.assertEqual(result['scrubbed_outbox'], 1)
        item.refresh_from_db()
        self.assertEqual(item.encrypted_recipient, '')
        self.assertEqual(item.encrypted_context, '')

    @override_settings(RESEND_API_KEY='test-key')
    def test_resend_429_captures_bounded_retry_after(self):
        response = type('Response', (), {
            'status_code': 429,
            'headers': {'Retry-After': '900'},
            'json': lambda self: {},
        })()
        with patch('notifications.providers.httpx.post', return_value=response):
            with self.assertRaises(ProviderError) as raised:
                ResendProvider().send({'to': ['owner@example.com']}, 'stable-key')
        self.assertTrue(raised.exception.retryable)
        self.assertEqual(raised.exception.retry_after, 600)


@override_settings(
    EMAIL_CRYPTO_KEYS=[TEST_KEY], EMAIL_LOOKUP_HMAC_KEY='test-hmac',
    EMAIL_PROVIDER='fake', EMAIL_DISPATCH_ENABLED=True,
    EMAIL_TEST_ALLOWLIST=['owner@example.com'], RESEND_WEBHOOK_SECRET=WEBHOOK_SECRET,
)
class WebhookTests(TestCase):
    def setUp(self):
        self.item = enqueue_email(
            kind='password_changed', business_key='webhook-item',
            recipient='owner@example.com', email_key='owner@example.com', context={},
            send_before=timezone.now() + timedelta(hours=1),
        )
        dispatch_one(self.item.pk)
        self.item.refresh_from_db()

    def signed_post(self, event_type, event_id=None, data=None, svix_id='evt_test_1', timestamp=None):
        event_id = event_id or self.item.provider_message_id
        payload = json.dumps({
            'type': event_type,
            'created_at': timezone.now().isoformat(),
            'data': data or {'email_id': event_id, 'to': ['owner@example.com']},
        }, separators=(',', ':'))
        timestamp = timestamp or datetime.now(dt_timezone.utc)
        signature = Webhook(WEBHOOK_SECRET).sign(svix_id, timestamp, payload)
        return self.client.post(
            '/api/v1/webhooks/email/resend/', data=payload,
            content_type='application/json',
            HTTP_SVIX_ID=svix_id,
            HTTP_SVIX_TIMESTAMP=str(int(timestamp.timestamp())),
            HTTP_SVIX_SIGNATURE=signature,
        )

    def test_signature_duplicate_and_minimal_storage(self):
        response = self.signed_post('email.delivered')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.signed_post('email.delivered').status_code, 200)
        self.assertEqual(ProviderEvent.objects.count(), 1)
        event = ProviderEvent.objects.get()
        self.assertEqual(event.normalized_data, {})
        self.assertNotIn('owner@example.com', json.dumps(event.normalized_data))
        self.assertEqual(process_provider_event(event.pk), EmailOutbox.Status.DELIVERED)

    def test_invalid_and_stale_signatures_are_rejected(self):
        self.assertEqual(self.client.post('/api/v1/webhooks/email/resend/', data=b'{}', content_type='application/json').status_code, 400)
        stale = datetime.now(dt_timezone.utc) - timedelta(minutes=6)
        self.assertEqual(self.signed_post('email.delivered', svix_id='evt_stale', timestamp=stale).status_code, 400)

    def test_complaint_prevails_over_delivered_and_suppresses(self):
        self.signed_post('email.delivered', svix_id='evt_delivered')
        delivered = ProviderEvent.objects.get(event_id='evt_delivered')
        process_provider_event(delivered.pk)
        self.signed_post('email.complained', svix_id='evt_complaint')
        complaint = ProviderEvent.objects.get(event_id='evt_complaint')
        self.assertEqual(process_provider_event(complaint.pk), EmailOutbox.Status.SUPPRESSED)
        self.signed_post('email.delivered', svix_id='evt_delivered_late')
        process_provider_event(ProviderEvent.objects.get(event_id='evt_delivered_late').pk)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, EmailOutbox.Status.SUPPRESSED)
        self.assertTrue(EmailSuppression.objects.get(recipient_hmac=self.item.recipient_hmac).active)

    def test_orphan_remains_pending_for_reconciliation(self):
        self.signed_post('email.delivered', event_id='unknown-provider-id', svix_id='evt_orphan')
        event = ProviderEvent.objects.get(event_id='evt_orphan')
        self.assertEqual(process_provider_event(event.pk), 'orphan')
        event.refresh_from_db()
        self.assertIsNone(event.processed_at)

    def test_database_failure_returns_503(self):
        payload = json.dumps({'type': 'email.delivered', 'data': {'email_id': self.item.provider_message_id}}, separators=(',', ':'))
        now = datetime.now(dt_timezone.utc)
        signature = Webhook(WEBHOOK_SECRET).sign('evt_db_down', now, payload)
        with patch('notifications.webhook.ProviderEvent.objects.get_or_create', side_effect=DatabaseError('down')):
            response = self.client.post('/api/v1/webhooks/email/resend/', data=payload, content_type='application/json', HTTP_SVIX_ID='evt_db_down', HTTP_SVIX_TIMESTAMP=str(int(now.timestamp())), HTTP_SVIX_SIGNATURE=signature)
        self.assertEqual(response.status_code, 503)
