import uuid
from django.db import models
from django.utils import timezone


class EmailTemplateArtifact(models.Model):
    kind = models.CharField(max_length=64)
    version = models.PositiveIntegerField()
    subject = models.CharField(max_length=200)
    text_body = models.TextField()
    html_body = models.TextField()
    content_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['kind', 'version'], name='notifications_template_kind_version')]


class EmailOutbox(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendente'
        LEASED = 'leased', 'Reservado'
        ACCEPTED = 'accepted', 'Aceito'
        DELIVERED = 'delivered', 'Entregue'
        FAILED = 'failed', 'Falhou'
        EXPIRED = 'expired', 'Expirou'
        SUPPRESSED = 'suppressed', 'Suprimido'
        UNKNOWN = 'unknown', 'Desconhecido'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business_key = models.CharField(max_length=200, unique=True)
    intent = models.CharField(max_length=64)
    template = models.ForeignKey(EmailTemplateArtifact, on_delete=models.PROTECT)
    encrypted_recipient = models.TextField()
    recipient_hmac = models.CharField(max_length=64, db_index=True)
    encrypted_context = models.TextField()
    crypto_key_id = models.CharField(max_length=32)
    idempotency_key = models.CharField(max_length=200, unique=True)
    payload_hash = models.CharField(max_length=64)
    budget_reserved = models.BooleanField(default=False)
    budget_day = models.CharField(max_length=10, blank=True)
    budget_month = models.CharField(max_length=7, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now, db_index=True)
    send_before = models.DateTimeField()
    lease_token = models.UUIDField(null=True, blank=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    provider_message_id = models.CharField(max_length=128, blank=True, db_index=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    last_error_code = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)


class ProviderEvent(models.Model):
    provider = models.CharField(max_length=32)
    event_id = models.CharField(max_length=128)
    event_type = models.CharField(max_length=64)
    provider_message_id = models.CharField(max_length=128, blank=True, db_index=True)
    normalized_data = models.JSONField(default=dict)
    occurred_at = models.DateTimeField(null=True)
    received_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['provider', 'event_id'], name='notifications_provider_event_unique')]


class EmailSuppression(models.Model):
    recipient_hmac = models.CharField(max_length=64, unique=True)
    reason = models.CharField(max_length=32)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    released_at = models.DateTimeField(null=True, blank=True)


class EmailBudget(models.Model):
    period = models.CharField(max_length=10, unique=True)
    reserved = models.PositiveIntegerField(default=0)
    submitted = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
