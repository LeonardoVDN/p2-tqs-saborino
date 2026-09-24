import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0004_identity_session_fields')]
    operations = [
        migrations.CreateModel(name='AccountActionChallenge', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('purpose', models.CharField(choices=[('password_reset', 'Redefinição de senha'), ('email_verification', 'Verificação de e-mail'), ('email_change', 'Troca de e-mail')], max_length=32)),
            ('target_fingerprint', models.CharField(max_length=64)), ('encrypted_target', models.TextField(blank=True)),
            ('credential_version', models.PositiveBigIntegerField()), ('issued_at', models.DateTimeField(default=django.utils.timezone.now)),
            ('expires_at', models.DateTimeField()), ('consumed_at', models.DateTimeField(blank=True, null=True)),
            ('superseded_at', models.DateTimeField(blank=True, null=True)),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='action_challenges', to='accounts.customuser')),
        ], options={'indexes': [models.Index(fields=['user', 'purpose', '-issued_at'], name='accounts_ac_user_id_be89ad_idx')]}),
        migrations.CreateModel(name='RecoveryGrant', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('secret_hash', models.CharField(max_length=64, unique=True)), ('expires_at', models.DateTimeField()),
            ('consumed_at', models.DateTimeField(blank=True, null=True)), ('revoked_at', models.DateTimeField(blank=True, null=True)),
            ('challenge', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='grants', to='accounts.accountactionchallenge')),
        ]),
        migrations.CreateModel(name='SecurityAuditEvent', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)), ('event_type', models.CharField(max_length=64)),
            ('outcome', models.CharField(max_length=24)), ('metadata', models.JSONField(blank=True, default=dict)),
            ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.customuser')),
        ], options={'indexes': [models.Index(fields=['event_type', '-created_at'], name='accounts_se_event_t_09047c_idx')]}),
    ]
