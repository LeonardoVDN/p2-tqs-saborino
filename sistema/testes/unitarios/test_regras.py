"""Testes unitários das regras de cálculo do Saborino.

Cada teste usa objetos em memória, sem banco, sem rede e sem interface.
Entre parênteses, o requisito e o caso de teste manual que o teste representa.
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework import serializers

from cadastros.models import Competencia
from operacao.models import Recebivel, q2
from operacao.serializers import VendaSerializer


def recebivel(total, pago, vencimento=None):
    return Recebivel(valor_total=Decimal(total), valor_pago=Decimal(pago), data_vencimento=vencimento)


# RF-04 · CT-014
def test_q2_mantem_duas_casas_para_quantidade_decimal():
    assert q2(Decimal('1.5') * Decimal('7.50')) == Decimal('11.25')


# RF-04 · CT-014
def test_q2_arredonda_a_terceira_casa():
    assert q2(Decimal('0.333') * Decimal('10.00')) == Decimal('3.33')


# RF-05 · CT-013
def test_recebivel_sem_pagamento_fica_aberto():
    assert recebivel('34.00', '0.00').status == Recebivel.Status.ABERTO


# RF-05 · CT-021
def test_recebivel_com_pagamento_parcial_fica_parcial():
    r = recebivel('34.00', '20.00')
    assert r.status == Recebivel.Status.PARCIAL
    assert r.a_receber == Decimal('14.00')


# RF-05 · CT-024
def test_recebivel_pago_por_inteiro_fica_pago():
    r = recebivel('34.00', '34.00')
    assert r.status == Recebivel.Status.PAGO
    assert r.a_receber == Decimal('0.00')


# RF-05
def test_recebivel_com_vencimento_passado_e_sem_pagamento_fica_vencido():
    ontem = timezone.localdate() - timedelta(days=1)
    assert recebivel('34.00', '0.00', ontem).status == Recebivel.Status.VENCIDO


# RF-05
def test_pagamento_parcial_prevalece_sobre_vencimento():
    ontem = timezone.localdate() - timedelta(days=1)
    assert recebivel('34.00', '10.00', ontem).status == Recebivel.Status.PARCIAL


# RF-06 · CT-029
def test_rotulo_da_competencia_usa_nome_do_mes():
    assert Competencia(ano=2026, mes=11).rotulo == 'Novembro/2026'


# RF-04 · CT-015
def test_venda_sem_itens_e_recusada():
    with pytest.raises(serializers.ValidationError):
        VendaSerializer().validate_itens_input([])
