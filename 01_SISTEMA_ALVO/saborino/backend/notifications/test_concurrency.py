import threading
from datetime import timedelta

from django.db import close_old_connections, connections
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from .models import EmailBudget, EmailOutbox
from .services import dispatch_one, enqueue_email


TEST_KEY = 'MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA='


@override_settings(
    EMAIL_CRYPTO_KEYS=[TEST_KEY], EMAIL_LOOKUP_HMAC_KEY='test-hmac',
    EMAIL_PROVIDER='fake', EMAIL_DISPATCH_ENABLED=True,
    EMAIL_TEST_ALLOWLIST=['one@example.com', 'two@example.com'],
    EMAIL_DAILY_BUDGET=1, EMAIL_MONTHLY_BUDGET=1,
)
class BudgetConcurrencyTests(TransactionTestCase):
    def test_concurrent_dispatch_cannot_exceed_budget(self):
        items = [
            enqueue_email(
                kind='password_changed', business_key=f'budget-{index}',
                recipient=f'{name}@example.com', email_key=f'{name}@example.com', context={},
                send_before=timezone.now() + timedelta(hours=1),
            )
            for index, name in enumerate(('one', 'two'))
        ]
        barrier = threading.Barrier(2)
        outcomes = []

        def dispatch(item_id):
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                outcomes.append(dispatch_one(item_id))
            finally:
                connections.close_all()

        threads = [threading.Thread(target=dispatch, args=(item.pk,)) for item in items]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertCountEqual(outcomes, [EmailOutbox.Status.ACCEPTED, EmailOutbox.Status.PENDING])
        self.assertEqual(EmailBudget.objects.get(period=timezone.now().strftime('%Y-%m-%d')).submitted, 1)
        self.assertEqual(EmailBudget.objects.get(period=timezone.now().strftime('%Y-%m')).submitted, 1)
