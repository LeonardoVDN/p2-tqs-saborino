import json
from datetime import datetime

from django.conf import settings
from django.db import DatabaseError, transaction
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from svix.webhooks import Webhook, WebhookVerificationError

from .models import ProviderEvent


MAX_WEBHOOK_BYTES = 256 * 1024


def _parse_timestamp(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return parsed if timezone.is_aware(parsed) else timezone.make_aware(parsed)


@csrf_exempt
@require_POST
def resend_webhook(request):
    if request.META.get('CONTENT_LENGTH'):
        try:
            if int(request.META['CONTENT_LENGTH']) > MAX_WEBHOOK_BYTES:
                return HttpResponse(status=413)
        except ValueError:
            return HttpResponse(status=400)
    body = request.body
    if len(body) > MAX_WEBHOOK_BYTES:
        return HttpResponse(status=413)
    if not settings.RESEND_WEBHOOK_SECRET:
        return HttpResponse(status=503)
    headers = {
        'svix-id': request.headers.get('svix-id', ''),
        'svix-timestamp': request.headers.get('svix-timestamp', ''),
        'svix-signature': request.headers.get('svix-signature', ''),
    }
    try:
        Webhook(settings.RESEND_WEBHOOK_SECRET).verify(body, headers)
        payload = json.loads(body)
        event_type = payload['type']
        data = payload.get('data') or {}
        message_id = str(data.get('email_id') or '')
        event_id = headers['svix-id']
        if not event_id or not isinstance(event_type, str) or not isinstance(data, dict):
            raise ValueError('invalid_shape')
        normalized = {}
        bounce = data.get('bounce')
        if isinstance(bounce, dict):
            normalized['bounce_type'] = str(bounce.get('type') or '')[:32]
            normalized['bounce_subtype'] = str(bounce.get('subType') or '')[:64]
        with transaction.atomic():
            ProviderEvent.objects.get_or_create(
                provider='resend', event_id=event_id,
                defaults={
                    'event_type': event_type[:64],
                    'provider_message_id': message_id[:128],
                    'normalized_data': normalized,
                    'occurred_at': _parse_timestamp(payload.get('created_at')),
                },
            )
    except WebhookVerificationError:
        return HttpResponse(status=400)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return HttpResponse(status=400)
    except DatabaseError:
        return HttpResponse(status=503)
    return JsonResponse({'accepted': True})
