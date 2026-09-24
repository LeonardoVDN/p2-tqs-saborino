import os

from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, DatabaseError, connections, transaction
from django.db.migrations.executor import MigrationExecutor

from accounts.models import CustomUser
from cadastros.models import Competencia
from operacao.models import Venda


class Command(BaseCommand):
    help = 'Valida, sem escrever dados, um banco PostgreSQL restaurado.'

    requires_system_checks = []

    expected_database_env = 'RESTORE_EXPECTED_DATABASE'
    essential_models = (CustomUser, Competencia, Venda)

    def add_arguments(self, parser):
        parser.add_argument(
            '--database',
            default=DEFAULT_DB_ALIAS,
            help='Alias Django da conexão restaurada a validar.',
        )

    def handle(self, *args, **options):
        expected_database = self._expected_database()
        database_alias = options.get('database') or DEFAULT_DB_ALIAS

        try:
            connection = connections[database_alias]
        except Exception:
            raise self._failure('invalid_database_alias') from None

        if connection.vendor != 'postgresql':
            raise self._failure('unsupported_database_backend')

        configured_database = str(connection.settings_dict.get('NAME') or '')
        if configured_database != expected_database:
            raise self._failure('database_name_mismatch')

        try:
            with transaction.atomic(using=database_alias):
                with connection.cursor() as cursor:
                    # A proteção é aplicada antes de qualquer consulta ao banco.
                    # Mesmo uma regressão futura não poderá persistir alterações.
                    cursor.execute('SET TRANSACTION READ ONLY')

                    current_database = self._current_database(cursor)
                    if current_database != expected_database:
                        raise self._failure('database_name_mismatch')

                    missing_table_count = self._missing_essential_table_count(
                        connection,
                        cursor,
                    )
                    if missing_table_count:
                        raise self._failure(
                            'essential_tables_missing',
                            count=missing_table_count,
                        )

                    pending_migration_count = self._pending_migration_count(connection)
                    if pending_migration_count:
                        raise self._failure(
                            'pending_migrations',
                            count=pending_migration_count,
                        )

                    invalid_constraint_count = self._invalid_constraint_count(cursor)
                    if invalid_constraint_count:
                        raise self._failure(
                            'invalid_constraints',
                            count=invalid_constraint_count,
                        )

                    # A transação é descartada mesmo tendo sido explicitamente
                    # read-only, mantendo a garantia operacional do comando.
                    transaction.set_rollback(True, using=database_alias)
        except CommandError:
            raise
        except DatabaseError:
            raise self._failure('database_validation_failed') from None

        self.stdout.write(self.style.SUCCESS(
            'restore_database_verification_success '
            f'checks=4 essential_models={len(self.essential_models)} '
            'pending_migrations=0 invalid_constraints=0'
        ))

    def _expected_database(self):
        value = os.environ.get(self.expected_database_env)
        if value is None or not value.strip():
            raise self._failure('expected_database_missing')
        if value != value.strip():
            raise self._failure('expected_database_invalid')
        return value

    def _current_database(self, cursor):
        cursor.execute('SELECT current_database()')
        row = cursor.fetchone()
        if not row or not isinstance(row[0], str):
            raise self._failure('database_identity_unavailable')
        return row[0]

    def _missing_essential_table_count(self, connection, cursor):
        existing_tables = set(connection.introspection.table_names(cursor))
        essential_tables = {
            model._meta.db_table
            for model in self.essential_models
        }
        return len(essential_tables - existing_tables)

    def _pending_migration_count(self, connection):
        try:
            executor = MigrationExecutor(connection)
            executor.loader.check_consistent_history(connection)
            conflicts = executor.loader.detect_conflicts()
            if conflicts:
                raise self._failure(
                    'migration_conflicts',
                    count=len(conflicts),
                )
            targets = executor.loader.graph.leaf_nodes()
            return len(executor.migration_plan(targets))
        except CommandError:
            raise
        except Exception:
            raise self._failure('migration_plan_unavailable') from None

    def _invalid_constraint_count(self, cursor):
        cursor.execute(
            '''
            SELECT COUNT(*)
            FROM pg_catalog.pg_constraint AS constraint_row
            INNER JOIN pg_catalog.pg_namespace AS namespace
                ON namespace.oid = constraint_row.connamespace
            WHERE constraint_row.convalidated IS FALSE
              AND namespace.nspname <> 'information_schema'
              AND LEFT(namespace.nspname, 3) <> 'pg_'
            '''
        )
        row = cursor.fetchone()
        if not row or not isinstance(row[0], int):
            raise self._failure('constraint_validation_unavailable')
        return row[0]

    @staticmethod
    def _failure(code, **metadata):
        suffix = ''.join(
            f' {key}={value}'
            for key, value in sorted(metadata.items())
        )
        return CommandError(
            f'restore_database_verification_failed code={code}{suffix}'
        )
