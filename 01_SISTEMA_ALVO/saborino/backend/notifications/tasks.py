from celery import shared_task
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from .models import EmailOutbox, ProviderEvent
from .services import dispatch_one, process_provider_event


@shared_task(name='notifications.dispatch_email_by_id', rate_limit='1/s')
def dispatch_email_by_id(outbox_id):
    return dispatch_one(outbox_id)


@shared_task(name='notifications.dispatch_email_outbox')
def dispatch_email_outbox():
    now = timezone.now()
    with transaction.atomic():
        items = list(
            EmailOutbox.objects.select_for_update(skip_locked=True)
            .filter(status=EmailOutbox.Status.PENDING, next_attempt_at__lte=now)
            .order_by('created_at')[:20]
        )
        ids = [item.pk for item in items]
        EmailOutbox.objects.filter(pk__in=ids).update(
            status=EmailOutbox.Status.LEASED,
            lease_token=None,
            lease_expires_at=now + timedelta(minutes=5),
        )
    for outbox_id in ids:
        dispatch_email_by_id.delay(str(outbox_id))
    return len(ids)


@shared_task(name='notifications.sweep_email_leases')
def sweep_email_leases():
    return EmailOutbox.objects.filter(status=EmailOutbox.Status.LEASED, lease_expires_at__lt=timezone.now()).update(status=EmailOutbox.Status.PENDING, lease_token=None, lease_expires_at=None)


@shared_task(name='notifications.process_provider_events')
def process_provider_events():
    ids = list(ProviderEvent.objects.filter(processed_at__isnull=True).order_by('received_at').values_list('pk', flat=True)[:100])
    for event_id in ids:
        process_provider_event(event_id)


@shared_task(name='notifications.mark_unknown_email_deliveries')
def mark_unknown_email_deliveries():
    cutoff = timezone.now() - timedelta(hours=24)
    return EmailOutbox.objects.filter(
        status=EmailOutbox.Status.ACCEPTED,
        submitted_at__lt=cutoff,
    ).update(status=EmailOutbox.Status.UNKNOWN, last_error_code='delivery_unconfirmed')


@shared_task(name='notifications.apply_email_retention')
def apply_email_retention():
    from accounts.models import AccountActionChallenge, SecurityAuditEvent

    now = timezone.now()
    terminal = [
        EmailOutbox.Status.ACCEPTED, EmailOutbox.Status.DELIVERED,
        EmailOutbox.Status.FAILED, EmailOutbox.Status.EXPIRED,
        EmailOutbox.Status.SUPPRESSED, EmailOutbox.Status.UNKNOWN,
    ]
    scrubbed = EmailOutbox.objects.filter(
        status__in=terminal, updated_at__lt=now - timedelta(days=7),
    ).exclude(encrypted_recipient='').update(
        encrypted_recipient='', encrypted_context='', crypto_key_id='',
    )
    old_outbox, _ = EmailOutbox.objects.filter(
        status__in=terminal, updated_at__lt=now - timedelta(days=90),
    ).delete()
    old_events, _ = ProviderEvent.objects.filter(received_at__lt=now - timedelta(days=90)).delete()
    old_challenges, _ = AccountActionChallenge.objects.filter(
        expires_at__lt=now - timedelta(days=7),
    ).delete()
    old_audit, _ = SecurityAuditEvent.objects.filter(created_at__lt=now - timedelta(days=365)).delete()
    return {
        'scrubbed_outbox': scrubbed,
        'deleted_outbox_objects': old_outbox,
        'deleted_provider_event_objects': old_events,
        'deleted_challenge_objects': old_challenges,
        'deleted_audit_objects': old_audit,
    }
