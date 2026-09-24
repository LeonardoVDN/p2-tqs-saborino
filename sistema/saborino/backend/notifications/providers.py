import uuid
import httpx
from django.conf import settings


class ProviderError(Exception):
    def __init__(self, code, retryable=False, retry_after=None):
        self.code = code
        self.retryable = retryable
        self.retry_after = retry_after
        super().__init__(code)


class FakeProvider:
    def send(self, payload, idempotency_key):
        return {'id': f'fake-{uuid.uuid5(uuid.NAMESPACE_URL, idempotency_key)}'}


class ResendProvider:
    endpoint = 'https://api.resend.com/emails'

    def send(self, payload, idempotency_key):
        if not isinstance(payload.get('to'), list) or len(payload['to']) != 1:
            raise ProviderError('recipient_count_invalid')
        try:
            response = httpx.post(
                self.endpoint,
                json=payload,
                headers={
                    'Authorization': f'Bearer {settings.RESEND_API_KEY}',
                    'Idempotency-Key': idempotency_key,
                },
                timeout=httpx.Timeout(connect=3.0, read=10.0, write=10.0, pool=3.0),
            )
            if response.status_code >= 400:
                retry_after = None
                if response.headers.get('Retry-After', '').isdigit():
                    retry_after = min(600, max(1, int(response.headers['Retry-After'])))
                raise ProviderError(
                    f'http_{response.status_code}',
                    retryable=response.status_code == 429 or response.status_code >= 500,
                    retry_after=retry_after,
                )
            result = response.json()
            if not isinstance(result.get('id'), str) or not result['id'] or len(result['id']) > 128:
                raise ProviderError('provider_response_invalid')
            return result
        except ProviderError:
            raise
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise ProviderError('transport_ambiguous', retryable=True) from exc
        except ValueError as exc:
            raise ProviderError('provider_response_invalid') from exc


def get_provider():
    if settings.EMAIL_PROVIDER == 'fake':
        return FakeProvider()
    if settings.EMAIL_PROVIDER == 'resend':
        return ResendProvider()
    raise ProviderError('provider_disabled')
