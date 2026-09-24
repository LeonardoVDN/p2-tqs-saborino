from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import uuid

from .identity import canonicalize_email


class CustomUser(AbstractUser):
    email_key = models.CharField(max_length=254, null=True, blank=True, unique=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    credential_version = models.PositiveBigIntegerField(default=1)
    password_changed_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        previous = None
        if self.pk:
            previous = type(self).objects.filter(pk=self.pk).only('email_key', 'email_verified_at').first()
        if self.email:
            self.email = self.email.strip()
            self.email_key = canonicalize_email(self.email)
        else:
            self.email_key = None
        if previous and previous.email_key != self.email_key and self.email_verified_at == previous.email_verified_at:
            self.email_verified_at = None
        if update_fields is not None and 'email' in update_fields:
            kwargs['update_fields'] = set(update_fields) | {'email_key', 'email_verified_at'}
        super().save(*args, **kwargs)

    @property
    def is_email_verified(self):
        return self.email_verified_at is not None

    def revoke_credentials(self):
        self.credential_version += 1
        self.password_changed_at = timezone.now()


class AccountActionChallenge(models.Model):
    class Purpose(models.TextChoices):
        PASSWORD_RESET = 'password_reset', 'Redefinição de senha'
        EMAIL_VERIFICATION = 'email_verification', 'Verificação de e-mail'
        EMAIL_CHANGE = 'email_change', 'Troca de e-mail'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='action_challenges')
    purpose = models.CharField(max_length=32, choices=Purpose.choices)
    target_fingerprint = models.CharField(max_length=64)
    encrypted_target = models.TextField(blank=True)
    credential_version = models.PositiveBigIntegerField()
    issued_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    superseded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'purpose', '-issued_at'])]


class RecoveryGrant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    challenge = models.ForeignKey(AccountActionChallenge, on_delete=models.CASCADE, related_name='grants')
    secret_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)


class SecurityAuditEvent(models.Model):
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    user = models.ForeignKey(CustomUser, null=True, on_delete=models.SET_NULL)
    event_type = models.CharField(max_length=64)
    outcome = models.CharField(max_length=24)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [models.Index(fields=['event_type', '-created_at'])]


class Socio(models.Model):
    """Sócio do negócio (Sócio 1, Sócio 2) ou a entidade compartilhada 'Nós'.

    No MVP as vendas vão todas para caixa comum ('Nós'); o vínculo com o
    usuário e o split de resultado ganham uso na fase de fechamento.
    """

    nome = models.CharField(max_length=60, unique=True)
    usuario = models.OneToOneField(
        'accounts.CustomUser', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='socio',
    )
    percentual_split_padrao = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
    )
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Sócio'
        verbose_name_plural = 'Sócios'
        ordering = ['nome']

    def __str__(self):
        return self.nome
