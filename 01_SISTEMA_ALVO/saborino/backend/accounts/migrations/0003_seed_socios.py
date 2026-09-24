from django.db import migrations


def criar_socios(apps, schema_editor):
    Socio = apps.get_model('accounts', 'Socio')
    for nome in ['Nós', 'Sócio 1', 'Sócio 2']:
        Socio.objects.get_or_create(nome=nome)


def remover(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_socio'),
    ]

    operations = [
        migrations.RunPython(criar_socios, remover),
    ]
