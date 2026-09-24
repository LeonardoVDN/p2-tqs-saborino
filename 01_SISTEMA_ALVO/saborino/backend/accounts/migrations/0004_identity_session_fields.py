from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0003_seed_socios')]

    operations = [
        migrations.AddField(
            model_name='customuser', name='credential_version',
            field=models.PositiveBigIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='customuser', name='email_key',
            field=models.CharField(blank=True, max_length=254, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='customuser', name='email_verified_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='customuser', name='password_changed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
