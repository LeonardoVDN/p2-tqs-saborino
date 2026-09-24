from collections import defaultdict

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.identity import canonicalize_email


class Command(BaseCommand):
    help = 'Relatório read-only de e-mails legados; não altera nem verifica contas.'

    def handle(self, *args, **options):
        groups = defaultdict(list)
        invalid = []
        empty = []
        User = get_user_model()
        for user in User.objects.order_by('pk').only('pk', 'email'):
            if not user.email:
                empty.append(user.pk)
                continue
            try:
                groups[canonicalize_email(user.email)].append(user.pk)
            except Exception:
                invalid.append(user.pk)
        duplicates = {key: ids for key, ids in groups.items() if len(ids) > 1}
        self.stdout.write(
            f'total={User.objects.count()} empty={len(empty)} invalid={len(invalid)} '
            f'duplicate_keys={len(duplicates)}'
        )
        if empty:
            self.stdout.write('empty_user_ids=' + ','.join(map(str, empty)))
        if invalid:
            self.stdout.write('invalid_user_ids=' + ','.join(map(str, invalid)))
        for index, (_, ids) in enumerate(sorted(duplicates.items()), start=1):
            self.stdout.write(f'duplicate_group={index} user_ids=' + ','.join(map(str, ids)))
