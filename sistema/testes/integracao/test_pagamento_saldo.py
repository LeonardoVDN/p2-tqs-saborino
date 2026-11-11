"""Pagamento e saldo em aberto do cliente (RF-05), com banco de dados.

Testes criados antes da correção do defeito DEF-006.
"""
from decimal import Decimal

import pytest

from operacao.serializers import RegistrarPagamentoSerializer

pytestmark = pytest.mark.django_db


def pagamento(cliente, valor):
    return RegistrarPagamentoSerializer(data={'cliente': cliente.id, 'valor': valor, 'forma_pagamento': 'PIX'})


# RF-05 · CT-025
def test_pagamento_acima_do_saldo_e_recusado(venda_de_34):
    assert venda_de_34.recebivel.a_receber == Decimal('34.00')
    dados = pagamento(venda_de_34.cliente, '34.01')
    assert not dados.is_valid()
    assert 'valor' in dados.errors


# RF-05 · CT-024
def test_pagamento_igual_ao_saldo_e_aceito(venda_de_34):
    dados = pagamento(venda_de_34.cliente, '34.00')
    assert dados.is_valid(), dados.errors
