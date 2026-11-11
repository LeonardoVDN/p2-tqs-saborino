"""Brinde na venda (RF-04), com banco de dados.

Testes criados antes da correção do defeito DEF-005.
"""
from decimal import Decimal

import pytest

from operacao.serializers import VendaSerializer

pytestmark = pytest.mark.django_db


def registrar_venda(cliente, item):
    dados = VendaSerializer(data={'cliente': cliente.id, 'itens_input': [item]})
    assert dados.is_valid(), dados.errors
    return dados.save()


# RF-04 · CT-020
def test_item_com_subtotal_zero_fica_como_brinde(cliente, bolo):
    venda = registrar_venda(cliente, {'produto': bolo.id, 'quantidade': '1', 'subtotal': '0.00'})
    assert venda.itens.get().subtotal == Decimal('0.00')
    assert venda.valor_total == Decimal('0.00')


# RF-04 · CT-013 (sem subtotal, o sistema calcula pelo preço do produto)
def test_item_sem_subtotal_usa_o_preco_do_produto(cliente, bolo):
    venda = registrar_venda(cliente, {'produto': bolo.id, 'quantidade': '2'})
    assert venda.valor_total == Decimal('24.00')
