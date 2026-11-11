"""Preço do produto (RF-03).

Testes criados antes da correção do defeito DEF-002.
"""
from decimal import Decimal

import pytest
from rest_framework import serializers

from cadastros.serializers import ProdutoSerializer


def validar_preco(valor):
    return ProdutoSerializer().fields['preco_venda'].run_validation(valor)


# RF-03 · CT-012
def test_produto_recusa_preco_negativo():
    with pytest.raises(serializers.ValidationError):
        validar_preco('-1.00')


# RF-03 · CT-009 (preço zero ou positivo continua aceito)
@pytest.mark.parametrize('valor', ['0.00', '15.50'])
def test_produto_aceita_preco_zero_ou_positivo(valor):
    assert validar_preco(valor) == Decimal(valor)
