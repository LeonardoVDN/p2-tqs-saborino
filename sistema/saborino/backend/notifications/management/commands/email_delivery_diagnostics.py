import json

from django.core.management.base import BaseCommand
from django.db.models import Count

from notifications.models import EmailBudget, EmailOutbox, EmailSuppression, ProviderEvent


class Command(BaseCommand):
    help = 'Exibe diagnóstico agregado de entrega sem destinatários nem conteúdo de mensagens.'

    def handle(self, *args, **options):
        statuses = {
            row['status']: row['count']
            for row in EmailOutbox.objects.values('status').annotate(count=Count('id')).order_by('status')
        }
        payload = {
            'outbox_by_status': statuses,
            'unprocessed_provider_events': ProviderEvent.objects.filter(processed_at__isnull=True).count(),
            'active_suppressions': EmailSuppression.objects.filter(active=True).count(),
            'budgets': list(EmailBudget.objects.order_by('-period').values('period', 'reserved', 'submitted')[:35]),
            'provider_replay': 'Use o dashboard Resend com acesso administrativo; a chave send-only não consulta eventos.',
        }
        self.stdout.write(json.dumps(payload, sort_keys=True))
