from django.core.exceptions import ValidationError
from django.core.validators import validate_email


def canonicalize_email(value):
    """Canonicalização conservadora e versionável para o realm único."""
    value = (value or '').strip()
    if not value or len(value) > 254 or '@' not in value:
        raise ValidationError('Endereço de e-mail inválido.')
    local, domain = value.rsplit('@', 1)
    try:
        ascii_domain = domain.encode('idna').decode('ascii').lower()
    except UnicodeError as exc:
        raise ValidationError('Domínio de e-mail inválido.') from exc
    if not local.isascii():
        raise ValidationError('O endereço deve usar local-part ASCII.')
    canonical = f'{local.lower()}@{ascii_domain}'
    validate_email(canonical)
    return canonical
