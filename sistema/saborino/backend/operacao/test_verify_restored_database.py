import os
from contextlib import ExitStack, nullcontext
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from operacao.management.commands.verify_restored_database import Command


COMMAND_MODULE = 'operacao.management.commands.verify_restored_database'
EXPECTED_DATABASE = 'restore_verification_target'


class VerifyRestoredDatabaseTests(SimpleTestCase):
    def _connection(self, *, current_database=EXPECTED_DATABASE,
                    existing_tables=None, invalid_constraints=0):
        connection = MagicMock()
        connection.vendor = 'postgresql'
        connection.settings_dict = {'NAME': EXPECTED_DATABASE}

        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.__exit__.return_value = False
        cursor.fetchone.side_effect = [
            (current_database,),
            (invalid_constraints,),
        ]
        connection.cursor.return_value = cursor

        if existing_tables is None:
            existing_tables = {
                model._meta.db_table
                for model in Command.essential_models
            }
        connection.introspection.table_names.return_value = list(existing_tables)
        return connection, cursor

    def _run(self, *, connection=None, migration_plan=None,
             migration_conflicts=None,
             expected_database=EXPECTED_DATABASE):
        connection, cursor = connection or self._connection()
        stdout = StringIO()
        rollback = MagicMock()
        executor = MagicMock()
        executor.loader.graph.leaf_nodes.return_value = [
            ('accounts', '0001_initial'),
            ('cadastros', '0001_initial'),
            ('operacao', '0001_initial'),
        ]
        executor.migration_plan.return_value = (
            [] if migration_plan is None else migration_plan
        )
        executor.loader.detect_conflicts.return_value = (
            {} if migration_conflicts is None else migration_conflicts
        )

        with ExitStack() as stack:
            stack.enter_context(patch.dict(
                os.environ,
                {Command.expected_database_env: expected_database},
                clear=False,
            ))
            stack.enter_context(patch(
                f'{COMMAND_MODULE}.connections',
                {'default': connection},
            ))
            atomic = stack.enter_context(patch(
                f'{COMMAND_MODULE}.transaction.atomic',
                return_value=nullcontext(),
            ))
            stack.enter_context(patch(
                f'{COMMAND_MODULE}.transaction.set_rollback',
                rollback,
            ))
            migration_executor = stack.enter_context(patch(
                f'{COMMAND_MODULE}.MigrationExecutor',
                return_value=executor,
            ))

            Command(stdout=stdout, no_color=True).handle(database='default')

        return {
            'connection': connection,
            'cursor': cursor,
            'executor': executor,
            'migration_executor': migration_executor,
            'atomic': atomic,
            'rollback': rollback,
            'stdout': stdout.getvalue(),
        }

    def test_requires_expected_database_environment_variable(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesMessage(
                CommandError,
                'code=expected_database_missing',
            ):
                Command(no_color=True).handle(database='default')

    def test_rejects_configured_database_before_opening_connection(self):
        connection, _ = self._connection()
        connection.settings_dict = {'NAME': 'unexpected_database'}

        with self.assertRaises(CommandError) as raised:
            self._run(connection=(connection, connection.cursor.return_value))

        message = str(raised.exception)
        self.assertIn('code=database_name_mismatch', message)
        self.assertNotIn(EXPECTED_DATABASE, message)
        self.assertNotIn('unexpected_database', message)
        connection.cursor.assert_not_called()

    def test_rejects_actual_connected_database_without_disclosing_names(self):
        actual_database = 'another_database'
        connection = self._connection(current_database=actual_database)

        with self.assertRaises(CommandError) as raised:
            self._run(connection=connection)

        message = str(raised.exception)
        self.assertIn('code=database_name_mismatch', message)
        self.assertNotIn(EXPECTED_DATABASE, message)
        self.assertNotIn(actual_database, message)

    def test_requires_all_essential_model_tables(self):
        existing_tables = {
            model._meta.db_table
            for model in Command.essential_models[:-1]
        }
        connection = self._connection(existing_tables=existing_tables)

        with self.assertRaisesMessage(
            CommandError,
            'code=essential_tables_missing count=1',
        ):
            self._run(connection=connection)

    def test_rejects_pending_migration_plan(self):
        connection = self._connection()

        with self.assertRaisesMessage(
            CommandError,
            'code=pending_migrations count=1',
        ):
            self._run(
                connection=connection,
                migration_plan=[(('operacao', '0002_future'), False)],
            )

    def test_rejects_conflicting_migration_leaves(self):
        connection = self._connection()

        with self.assertRaisesMessage(
            CommandError,
            'code=migration_conflicts count=1',
        ):
            self._run(
                connection=connection,
                migration_conflicts={
                    'operacao': {'0002_branch_a', '0002_branch_b'},
                },
            )

    def test_rejects_not_valid_postgresql_constraints(self):
        connection = self._connection(invalid_constraints=2)

        with self.assertRaisesMessage(
            CommandError,
            'code=invalid_constraints count=2',
        ):
            self._run(connection=connection)

    def test_success_is_aggregate_and_transaction_is_forced_read_only(self):
        result = self._run()

        self.assertEqual(
            result['stdout'],
            'restore_database_verification_success checks=4 '
            'essential_models=3 pending_migrations=0 '
            'invalid_constraints=0\n',
        )
        result['atomic'].assert_called_once_with(using='default')
        result['rollback'].assert_called_once_with(True, using='default')
        result['executor'].loader.check_consistent_history.assert_called_once_with(
            result['connection']
        )

        statements = [
            call.args[0].strip()
            for call in result['cursor'].execute.call_args_list
        ]
        self.assertEqual(statements[0], 'SET TRANSACTION READ ONLY')
        self.assertIn('SELECT current_database()', statements)
        self.assertTrue(any('pg_catalog.pg_constraint' in sql for sql in statements))

        direct_sql = ' '.join(statements).upper()
        for write_keyword in (
            'INSERT ', 'UPDATE ', 'DELETE ', 'ALTER ',
            'CREATE ', 'DROP ', 'TRUNCATE ',
        ):
            self.assertNotIn(write_keyword, direct_sql)

    def test_essential_models_are_the_required_saborino_models(self):
        self.assertEqual(
            {
                f'{model._meta.app_label}.{model.__name__}'
                for model in Command.essential_models
            },
            {
                'accounts.CustomUser',
                'cadastros.Competencia',
                'operacao.Venda',
            },
        )
