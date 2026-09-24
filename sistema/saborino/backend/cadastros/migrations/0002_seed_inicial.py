from django.db import migrations


def criar_seeds(apps, schema_editor):
    Canal = apps.get_model('cadastros', 'Canal')
    Conta = apps.get_model('cadastros', 'Conta')

    canais = [
        ('Canal A', 'canal-a', False, 1),
        ('Canal B', 'canal-b', True, 2),
        ('Canal C', 'canal-c', False, 3),
    ]
    for nome, slug, dizimo, ordem in canais:
        Canal.objects.get_or_create(
            nome=nome,
            defaults={'slug': slug, 'aplica_dizimo': dizimo, 'ordem': ordem},
        )

    contas = [
        ('Conta Corrente', 'CONTA_CORRENTE', ''),
        ('Caixa', 'DINHEIRO', ''),
        ('Cartão de Crédito', 'CARTAO_CREDITO', ''),
        ('Cartão de Terceiro', 'CARTAO_TERCEIRO', 'Terceiro'),
    ]
    for nome, tipo, titular in contas:
        Conta.objects.get_or_create(nome=nome, defaults={'tipo': tipo, 'titular_nome': titular})


def remover_seeds(apps, schema_editor):
    # Mantém dados em rollback (seed idempotente); nada a desfazer.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(criar_seeds, remover_seeds),
    ]
