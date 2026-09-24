import hashlib
import json
import uuid
from datetime import timedelta
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.template import Template, Context
from django.utils import timezone
from accounts.identity import canonicalize_email

from .crypto import decrypt_json, decrypt_text, encrypt_json, encrypt_text, recipient_fingerprint
from .models import EmailBudget, EmailOutbox, EmailSuppression, EmailTemplateArtifact, ProviderEvent
from .providers import ProviderError, get_provider


TEMPLATE_KINDS = {
    'password_reset', 'password_changed', 'email_verification',
    'email_change', 'email_changed_old', 'email_changed_new',
}


def template_artifact(kind):
    if kind not in TEMPLATE_KINDS:
        raise ValueError('unknown_email_template')
    base = Path(settings.BASE_DIR) / 'notifications' / 'templates' / 'notifications' / kind / 'v1'
    subject = (base / 'subject.txt').read_text(encoding='utf-8').strip()
    text = (base / 'text.txt').read_text(encoding='utf-8').rstrip()
    html = (base / 'html.html').read_text(encoding='utf-8').rstrip()
    digest = hashlib.sha256(f'{subject}\0{text}\0{html}'.encode()).hexdigest()
    artifact, _ = EmailTemplateArtifact.objects.get_or_create(kind=kind, version=1, defaults={'subject': subject, 'text_body': text, 'html_body': html, 'content_hash': digest})
    if artifact.content_hash != digest:
        raise ValueError('template_artifact_diverged')
    return artifact


def enqueue_email(*, kind, business_key, recipient, email_key, context, send_before):
    artifact = template_artifact(kind)
    canonical = json.dumps({'kind': kind, 'template_hash': artifact.content_hash, 'recipient': email_key, 'context': context}, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    payload_hash = hashlib.sha256(canonical.encode()).hexdigest()
    return EmailOutbox.objects.create(
        business_key=business_key, intent=kind, template=artifact,
        encrypted_recipient=encrypt_text(recipient), recipient_hmac=recipient_fingerprint(email_key),
        encrypted_context=encrypt_json(context), crypto_key_id=settings.EMAIL_CRYPTO_KEY_ID,
        idempotency_key=f'saborino/{kind}/{business_key}', payload_hash=payload_hash, send_before=send_before,
    )


def _reserve_budget(item, now):
    if item.budget_reserved:
        return True
    day = now.strftime('%Y-%m-%d')
    month = now.strftime('%Y-%m')
    daily, _ = EmailBudget.objects.select_for_update().get_or_create(period=day)
    monthly, _ = EmailBudget.objects.select_for_update().get_or_create(period=month)
    if daily.reserved + daily.submitted >= settings.EMAIL_DAILY_BUDGET or monthly.reserved + monthly.submitted >= settings.EMAIL_MONTHLY_BUDGET:
        return False
    daily.reserved += 1; monthly.reserved += 1
    daily.save(update_fields=['reserved']); monthly.save(update_fields=['reserved'])
    item.budget_reserved = True
    item.budget_day = day
    item.budget_month = month
    return True


def _finalize_budget(item, submitted):
    if not item.budget_reserved:
        return
    for period in (item.budget_day, item.budget_month):
        budget = EmailBudget.objects.select_for_update().get(period=period)
        budget.reserved -= 1
        if submitted:
            budget.submitted += 1
        budget.save(update_fields=['reserved', 'submitted', 'updated_at'])
    item.budget_reserved = False


def _challenge_is_sendable(item, now):
    purposes = {
        'password_reset': 'password_reset',
        'email_verification': 'email_verification',
        'email_change': 'email_change',
    }
    purpose = purposes.get(item.intent)
    if not purpose:
        return True
    from accounts.models import AccountActionChallenge

    try:
        challenge = AccountActionChallenge.objects.select_related('user').filter(pk=item.business_key, purpose=purpose).first()
    except (ValidationError, ValueError):
        return False
    if (
        not challenge or challenge.consumed_at or challenge.superseded_at
        or challenge.expires_at <= now or challenge.credential_version != challenge.user.credential_version
        or challenge.target_fingerprint != item.recipient_hmac
    ):
        return False
    if purpose != AccountActionChallenge.Purpose.EMAIL_CHANGE:
        return challenge.user.email_key and recipient_fingerprint(challenge.user.email_key) == item.recipient_hmac
    return True


def dispatch_one(outbox_id):
    if not settings.EMAIL_DISPATCH_ENABLED:
        return 'dispatch_disabled'
    now = timezone.now()
    lease = uuid.uuid4()
    with transaction.atomic():
        item = EmailOutbox.objects.select_for_update().get(pk=outbox_id)
        if item.status not in (EmailOutbox.Status.PENDING, EmailOutbox.Status.LEASED) or item.next_attempt_at > now:
            return item.status
        if item.status == EmailOutbox.Status.LEASED and item.lease_token and item.lease_expires_at and item.lease_expires_at > now:
            return item.status
        if item.send_before <= now:
            _finalize_budget(item, submitted=False)
            item.status = EmailOutbox.Status.EXPIRED
            item.save(update_fields=['status', 'budget_reserved', 'updated_at'])
            return item.status
        if not _challenge_is_sendable(item, now):
            _finalize_budget(item, submitted=False)
            item.status = EmailOutbox.Status.EXPIRED
            item.last_error_code = 'challenge_not_sendable'
            item.save(update_fields=['status', 'last_error_code', 'budget_reserved', 'updated_at'])
            return item.status
        if EmailSuppression.objects.filter(recipient_hmac=item.recipient_hmac, active=True).exists():
            _finalize_budget(item, submitted=False)
            item.status = EmailOutbox.Status.SUPPRESSED
            item.save(update_fields=['status', 'budget_reserved', 'updated_at'])
            return item.status
        if not _reserve_budget(item, now):
            item.status = EmailOutbox.Status.PENDING
            item.lease_token = None
            item.lease_expires_at = None
            item.next_attempt_at = now + timedelta(minutes=5)
            item.save(update_fields=['status', 'lease_token', 'lease_expires_at', 'next_attempt_at', 'updated_at'])
            return item.status
        item.status = EmailOutbox.Status.LEASED; item.lease_token = lease; item.lease_expires_at = now + timedelta(minutes=5); item.attempts += 1
        item.save(update_fields=['status', 'lease_token', 'lease_expires_at', 'attempts', 'budget_reserved', 'budget_day', 'budget_month', 'updated_at'])
    recipient = decrypt_text(item.encrypted_recipient)
    context = decrypt_json(item.encrypted_context)
    actual_template_hash = hashlib.sha256(f'{item.template.subject}\0{item.template.text_body}\0{item.template.html_body}'.encode()).hexdigest()
    canonical = json.dumps({'kind': item.intent, 'template_hash': actual_template_hash, 'recipient': canonicalize_email(recipient), 'context': context}, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    if actual_template_hash != item.template.content_hash or hashlib.sha256(canonical.encode()).hexdigest() != item.payload_hash:
        result = ProviderError('payload_diverged')
    elif settings.EMAIL_TEST_ALLOWLIST and recipient not in settings.EMAIL_TEST_ALLOWLIST:
        result = ProviderError('recipient_not_allowlisted')
    else:
        payload = {'from': settings.EMAIL_FROM, 'to': [recipient], 'reply_to': settings.EMAIL_REPLY_TO, 'subject': item.template.subject, 'text': Template(item.template.text_body).render(Context(context)), 'html': Template(item.template.html_body).render(Context(context)), 'headers': {'X-Entity-Ref-ID': str(item.id)}, 'tags': [{'name': 'intent', 'value': item.intent}, {'name': 'outbox', 'value': str(item.id)}]}
        try: result = get_provider().send(payload, item.idempotency_key)
        except ProviderError as exc: result = exc
    with transaction.atomic():
        current = EmailOutbox.objects.select_for_update().get(pk=item.pk)
        if current.lease_token != lease:
            return current.status
        if isinstance(result, ProviderError):
            current.last_error_code = result.code
            if result.retryable and current.attempts < 7 and timezone.now() < current.send_before:
                delay = result.retry_after or min(600, 2 ** current.attempts)
                current.status = EmailOutbox.Status.PENDING
                current.next_attempt_at = min(current.send_before, timezone.now() + timedelta(seconds=delay))
            else:
                current.status = EmailOutbox.Status.FAILED
                _finalize_budget(current, submitted=False)
        else:
            current.status = EmailOutbox.Status.ACCEPTED; current.provider_message_id = result['id']; current.submitted_at = timezone.now()
            _finalize_budget(current, submitted=True)
        current.lease_token = None; current.lease_expires_at = None
        current.save()
        return current.status


def process_provider_event(event_id):
    with transaction.atomic():
        event = ProviderEvent.objects.select_for_update().get(pk=event_id)
        if event.processed_at:
            return 'already_processed'
        item = EmailOutbox.objects.select_for_update().filter(provider_message_id=event.provider_message_id).first()
        if not item:
            return 'orphan'
        event_type = event.event_type
        if event_type == 'email.complained':
            EmailSuppression.objects.update_or_create(recipient_hmac=item.recipient_hmac, defaults={'reason': 'complaint', 'active': True, 'released_at': None})
            item.status = EmailOutbox.Status.SUPPRESSED
        elif event_type in ('email.bounced', 'email.suppressed'):
            permanent = event_type == 'email.suppressed' or event.normalized_data.get('bounce_type', '').lower() == 'permanent'
            if permanent:
                EmailSuppression.objects.update_or_create(recipient_hmac=item.recipient_hmac, defaults={'reason': 'hard_bounce', 'active': True, 'released_at': None})
                item.status = EmailOutbox.Status.SUPPRESSED
            else:
                item.last_error_code = 'soft_bounce'
        elif event_type == 'email.delivered':
            if item.status != EmailOutbox.Status.SUPPRESSED:
                item.status = EmailOutbox.Status.DELIVERED
                item.delivered_at = event.occurred_at or timezone.now()
        elif event_type == 'email.delivery_delayed':
            item.last_error_code = 'delivery_delayed'
        elif event_type == 'email.failed':
            if item.status not in (EmailOutbox.Status.DELIVERED, EmailOutbox.Status.SUPPRESSED):
                item.status = EmailOutbox.Status.FAILED
                item.last_error_code = 'provider_failed'
        item.save()
        event.processed_at = timezone.now()
        event.save(update_fields=['processed_at'])
        return item.status
