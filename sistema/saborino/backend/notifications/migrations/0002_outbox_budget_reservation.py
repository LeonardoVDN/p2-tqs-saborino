from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('notifications', '0001_initial')]
    operations = [
        migrations.AddField(model_name='emailoutbox', name='budget_day', field=models.CharField(blank=True, max_length=10)),
        migrations.AddField(model_name='emailoutbox', name='budget_month', field=models.CharField(blank=True, max_length=7)),
        migrations.AddField(model_name='emailoutbox', name='budget_reserved', field=models.BooleanField(default=False)),
    ]
