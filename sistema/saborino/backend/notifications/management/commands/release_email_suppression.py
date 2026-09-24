from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.identity import canonicalize_email
from accounts.models import SecurityAuditEvent
from notifications.crypto import recipient_fingerprint
from notifications.models import EmailSuppression


class Command(BaseCommand):
    help = 'Libera uma supressão após revisão humana e registra auditoria sem PII.'

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True)
        parser.add_argument('--reason', required=True)

    def handle(self, *args, **options):
        try:
            fingerprint = recipient_fingerprint(canonicalize_email(options['email']))
        except Exception as exc:
            raise CommandError('E-mail inválido.') from exc
        reason = options['reason'].strip()
        if len(reason) < 8:
            raise CommandError('Informe uma justificativa de revisão com ao menos 8 caracteres.')
        with transaction.atomic():
            suppression = EmailSuppression.objects.select_for_update().filter(
                recipient_hmac=fingerprint, active=True,
            ).first()
            if not suppression:
                raise CommandError('Nenhuma supressão ativa encontrada.')
            suppression.active = False
            suppression.released_at = timezone.now()
            suppression.save(update_fields=['active', 'released_at'])
            SecurityAuditEvent.objects.create(
                user=None, event_type='email_suppression_released', outcome='success',
                metadata={'reason': reason, 'fingerprint_prefix': fingerprint[:12]},
            )
        self.stdout.write('suppression_released=1 audited=1')
