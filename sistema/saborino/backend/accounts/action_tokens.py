import hashlib
import secrets
from datetime import timedelta
from django.conf import settings
from django.core import signing
from django.utils import timezone


SALT = 'saborino.accounts.action.v1'


def challenge_token(challenge):
    return signing.dumps(
        {'id': str(challenge.pk), 'purpose': challenge.purpose, 'kid': settings.ACCOUNT_ACTION_SIGNING_KEY_ID},
        key=settings.ACCOUNT_ACTION_SIGNING_KEY, salt=SALT, compress=False,
    )


def read_challenge_token(token, purpose):
    data = signing.loads(token, key=settings.ACCOUNT_ACTION_SIGNING_KEY, salt=SALT, max_age=3600)
    if data.get('purpose') != purpose or data.get('kid') != settings.ACCOUNT_ACTION_SIGNING_KEY_ID:
        raise signing.BadSignature('wrong_purpose')
    return data['id']


def new_grant_secret():
    return secrets.token_urlsafe(32)


def hash_secret(secret):
    return hashlib.sha256(secret.encode()).hexdigest()


def grant_expiry(challenge):
    return min(challenge.expires_at, timezone.now() + timedelta(minutes=15))
