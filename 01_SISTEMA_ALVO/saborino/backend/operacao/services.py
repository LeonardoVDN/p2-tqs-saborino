"""Regras de negócio de recebíveis e pagamentos.

Concentra a lógica de fiado: registrar um pagamento (parcial ou consolidado),
alocando do recebível mais antigo para o mais novo, e a baixa rápida de uma
venda inteira.
"""
from decimal import Decimal

from django.db import transaction

from .models import Pagamento, PagamentoAlocacao, Recebivel, q2

ZERO = Decimal('0.00')


def recebiveis_abertos_do_cliente(cliente):
    """Recebíveis do cliente com saldo em aberto, do mais antigo ao mais novo."""
    abertos = []
    qs = (
        Recebivel.objects.filter(cliente=cliente)
        .select_related('venda')
        .order_by('venda__data_venda', 'id')
    )
    for receb in qs:
        if receb.a_receber > ZERO:
            abertos.append(receb)
    return abertos


@transaction.atomic
def registrar_pagamento(*, cliente, valor, forma_pagamento, data=None,
                        conta_recebimento=None, registrado_por=None,
                        alocacoes=None, observacoes=''):
    """Cria um Pagamento e o distribui entre recebíveis.

    - Se `alocacoes` (lista de {recebivel, valor}) for informada, usa ela.
    - Senão, aloca automaticamente do mais antigo ao mais novo até esgotar o valor.
    Retorna o Pagamento criado.
    """
    valor = q2(valor)
    pagamento = Pagamento.objects.create(
        cliente=cliente, valor=valor, forma_pagamento=forma_pagamento,
        conta_recebimento=conta_recebimento, registrado_por=registrado_por,
        observacoes=observacoes, **({'data': data} if data else {}),
    )

    if alocacoes is None:
        restante = valor
        for receb in recebiveis_abertos_do_cliente(cliente):
            if restante <= ZERO:
                break
            aplica = min(restante, receb.a_receber)
            if aplica <= ZERO:
                continue
            PagamentoAlocacao.objects.create(
                pagamento=pagamento, recebivel=receb, valor_aplicado=aplica,
            )
            receb.recompute()
            restante = q2(restante - aplica)
    else:
        # Recompute nas MESMAS instâncias recebidas, para que o objeto do
        # chamador (ex.: venda.recebivel) reflita o novo saldo sem re-query.
        recebiveis_tocados = {}
        for item in alocacoes:
            receb = item['recebivel']
            aplica = q2(item['valor'])
            if aplica <= ZERO:
                continue
            PagamentoAlocacao.objects.create(
                pagamento=pagamento, recebivel=receb, valor_aplicado=aplica,
            )
            recebiveis_tocados[receb.pk] = receb
        for receb in recebiveis_tocados.values():
            receb.recompute()

    return pagamento


@transaction.atomic
def quitar_venda(*, venda, forma_pagamento, data=None, conta_recebimento=None,
                 registrado_por=None):
    """Baixa rápida: quita todo o saldo em aberto de uma venda."""
    receb = venda.recebivel
    saldo = receb.a_receber
    if saldo <= ZERO:
        return None
    return registrar_pagamento(
        cliente=venda.cliente, valor=saldo, forma_pagamento=forma_pagamento,
        data=data, conta_recebimento=conta_recebimento, registrado_por=registrado_por,
        alocacoes=[{'recebivel': receb, 'valor': saldo}],
    )
