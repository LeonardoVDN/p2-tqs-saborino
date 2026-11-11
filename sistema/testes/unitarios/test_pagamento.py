"""Valor do pagamento (RF-05).

Testes criados antes da correção dos defeitos DEF-007 e DEF-008.
"""
from decimal import Decimal

import pytest
from rest_framework import serializers

from operacao.serializers import RegistrarPagamentoSerializer


def validar_valor(valor):
    return RegistrarPagamentoSerializer().fields['valor'].run_validation(valor)


# RF-05 · CT-026 e CT-027
@pytest.mark.parametrize('valor', ['0.00', '-5.00'])
def test_pagamento_recusa_valor_zero_ou_negativo(valor):
    with pytest.raises(serializers.ValidationError):
        validar_valor(valor)


# RF-05 · CT-021 (o menor valor aceito é um centavo)
@pytest.mark.parametrize('valor', ['0.01', '20.00'])
def test_pagamento_aceita_valor_positivo(valor):
    assert validar_valor(valor) == Decimal(valor)
