"""Quantidade do item de venda (RF-04).

Testes criados na etapa RED do TDD, antes da correção dos defeitos DEF-003 e DEF-004.
"""
from decimal import Decimal

import pytest
from rest_framework import serializers

from operacao.serializers import ItemVendaWriteSerializer


# RF-04 · CT-016 e CT-017
@pytest.mark.parametrize('quantidade', ['0', '-2'])
def test_item_de_venda_recusa_quantidade_zero_ou_negativa(quantidade):
    campo = ItemVendaWriteSerializer().fields['quantidade']
    with pytest.raises(serializers.ValidationError):
        campo.run_validation(quantidade)


# RF-04 · CT-014 (quantidade fracionada continua aceita)
@pytest.mark.parametrize('quantidade', ['0.001', '1.5'])
def test_item_de_venda_aceita_quantidade_positiva(quantidade):
    campo = ItemVendaWriteSerializer().fields['quantidade']
    assert campo.run_validation(quantidade) == Decimal(quantidade)
