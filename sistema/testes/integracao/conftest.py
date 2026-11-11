"""Dados fictícios para os testes de integração (com banco de teste criado pelo pytest-django)."""
from decimal import Decimal

import pytest
from django.utils import timezone

from cadastros.models import Canal, Cliente, Produto
from operacao.models import ItemVenda, Venda


@pytest.fixture
def cliente(db):
    canal, _ = Canal.objects.get_or_create(nome='Canal A', defaults={'slug': 'canal-a'})
    return Cliente.objects.create(nome='Cliente Fictício Carla', canal=canal)


@pytest.fixture
def bolo(db):
    return Produto.objects.create(nome='Bolo de Pote Teste', preco_venda=Decimal('12.00'), custo_estimado_unitario=Decimal('5.00'))


@pytest.fixture
def mousse(db):
    return Produto.objects.create(nome='Mousse Teste', preco_venda=Decimal('10.00'), custo_estimado_unitario=Decimal('4.00'))


@pytest.fixture
def venda_de_34(cliente, bolo, mousse):
    """Venda fiado de 2 bolos e 1 mousse: R$ 34,00 a receber."""
    venda = Venda.objects.create(cliente=cliente, data_venda=timezone.localdate())
    ItemVenda(venda=venda, produto=bolo, quantidade=Decimal('2')).save()
    ItemVenda(venda=venda, produto=mousse, quantidade=Decimal('1')).save()
    venda.recompute_total()
    venda.sincronizar_recebivel()
    return venda
