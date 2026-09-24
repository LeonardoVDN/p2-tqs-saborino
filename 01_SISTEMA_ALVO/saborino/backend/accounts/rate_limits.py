import hashlib
import hmac

import redis
from django.conf import settings


_INCREMENT_WITH_EXPIRY = """
local value = redis.call('INCR', KEYS[1])
if value == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return value
"""


def client_address(request):
    # O edge é o único ingresso da rede backend; o primeiro hop é preservado.
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return (forwarded.split(',', 1)[0].strip() if forwarded else request.META.get('REMOTE_ADDR', 'unknown')) or 'unknown'


def rate_key(bucket, discriminator):
    digest = hmac.new(
        settings.SECRET_KEY.encode(), str(discriminator).encode(), hashlib.sha256,
    ).hexdigest()
    return f'saborino:account-rate:v1:{bucket}:{digest}'


def allow_rate(bucket, discriminator, limit, window_seconds):
    if not settings.ACCOUNT_RATE_LIMIT_ENABLED:
        return True
    try:
        client = redis.Redis.from_url(
            settings.ACCOUNT_RATE_LIMIT_REDIS_URL,
            socket_connect_timeout=1,
            socket_timeout=1,
            decode_responses=True,
        )
        count = int(client.eval(_INCREMENT_WITH_EXPIRY, 1, rate_key(bucket, discriminator), window_seconds))
        return count <= limit
    except (redis.RedisError, ValueError, TypeError):
        # Fluxos de identidade falham fechados quando o limitador está indisponível.
        return False


def allow_request(request, bucket, identity=None, ip_limit=10, identity_limit=5, window_seconds=3600):
    allowed_ip = allow_rate(f'{bucket}:ip', client_address(request), ip_limit, window_seconds)
    allowed_identity = True
    if identity:
        allowed_identity = allow_rate(f'{bucket}:identity', identity, identity_limit, window_seconds)
    return allowed_ip and allowed_identity
