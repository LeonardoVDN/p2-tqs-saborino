import hashlib
import hmac
import json
from cryptography.fernet import Fernet, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _fernet():
    if not settings.EMAIL_CRYPTO_KEYS:
        raise ImproperlyConfigured('EMAIL_CRYPTO_KEYS não configurada.')
    return MultiFernet([Fernet(key.encode()) for key in settings.EMAIL_CRYPTO_KEYS])


def encrypt_text(value):
    return _fernet().encrypt(value.encode()).decode()


def decrypt_text(value):
    return _fernet().decrypt(value.encode()).decode()


def encrypt_json(value):
    return encrypt_text(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False))


def decrypt_json(value):
    return json.loads(decrypt_text(value))


def recipient_fingerprint(email_key):
    if not settings.EMAIL_LOOKUP_HMAC_KEY:
        raise ImproperlyConfigured('EMAIL_LOOKUP_HMAC_KEY não configurada.')
    return hmac.new(settings.EMAIL_LOOKUP_HMAC_KEY.encode(), email_key.encode(), hashlib.sha256).hexdigest()
