"""Relatórios agregados por competência (dashboard, custo, fechamento)."""
from decimal import Decimal

from django.db.models import Count, DecimalField, F, Sum, Value
from django.db.models.functions import Coalesce

from cadastros.models import Competencia
from .models import (
    Compra, ConfiguracaoFinanceira, ItemVenda, Pagamento, ProducaoProduto, Venda,
)

ZERO = Decimal('0.00')
DEC = DecimalField(max_digits=14, decimal_places=2)


def _soma(qs, campo):
    return qs.aggregate(s=Coalesce(Sum(campo), Value(ZERO), output_field=DEC))['s']


def custo_por_produto(competencia):
    """Custo (compras rateadas) por produto na competência. 'Geral' à parte."""
    linhas = (
        Compra.objects.filter(competencia=competencia)
        .values('produto_rateio', 'produto_rateio__nome')
        .annotate(total=Coalesce(Sum('valor_total'), Value(ZERO), output_field=DEC))
        .order_by('-total')
    )
    resultado = []
    for l in linhas:
        resultado.append({
            'produto': l['produto_rateio'],
            'produto_nome': l['produto_rateio__nome'] or 'Geral',
            'total': l['total'],
        })
    return resultado


def relatorio_por_produto(competencia):
    """Painel por produto: produzido, vendido, faltam vender, receita, custo estimado, margem."""
    vendidos = (
        ItemVenda.objects.filter(venda__competencia=competencia)
        .values('produto', 'produto__nome')
        .annotate(
            qtd=Coalesce(Sum('quantidade'), Value(ZERO), output_field=DEC),
            receita=Coalesce(Sum('subtotal'), Value(ZERO), output_field=DEC),
            custo_snapshot=Coalesce(
                Sum(F('quantidade') * F('custo_unitario'), output_field=DEC),
                Value(ZERO), output_field=DEC,
            ),
        )
    )
    por_produto = {v['produto']: v for v in vendidos}

    producoes = {
        p['produto']: p['q']
        for p in ProducaoProduto.objects.filter(competencia=competencia)
        .values('produto').annotate(q=Coalesce(Sum('quantidade_produzida'), Value(ZERO), output_field=DEC))
    }

    ids = set(por_produto) | set(producoes)
    from cadastros.models import Produto
    nomes = dict(Produto.objects.filter(id__in=ids).values_list('id', 'nome'))

    linhas = []
    for pid in ids:
        v = por_produto.get(pid, {})
        vendido = v.get('qtd', ZERO)
        produzido = producoes.get(pid, ZERO)
        receita = v.get('receita', ZERO)
        linhas.append({
            'produto': pid,
            'produto_nome': v.get('produto__nome') or nomes.get(pid, '?'),
            'produzido': produzido,
            'vendido': vendido,
            'faltam_vender': produzido - vendido,
            'receita': receita,
            'custo_estimado': v.get('custo_snapshot', ZERO),
            'margem_estimada': receita - v.get('custo_snapshot', ZERO),
        })
    linhas.sort(key=lambda x: x['receita'], reverse=True)
    return linhas


def _competencia_anterior(competencia):
    ano, mes = competencia.ano, competencia.mes
    if mes == 1:
        ano, mes = ano - 1, 12
    else:
        mes -= 1
    return Competencia.objects.filter(ano=ano, mes=mes).first()


def build_dashboard(competencia):
    vendas = Venda.objects.filter(competencia=competencia)
    compras = Compra.objects.filter(competencia=competencia)
    pagamentos = Pagamento.objects.filter(competencia=competencia)
    itens = ItemVenda.objects.filter(venda__competencia=competencia)

    vendido = _soma(vendas, 'valor_total')
    num_vendas = vendas.count()
    custo_compras = _soma(compras, 'valor_total')

    # A receber (das vendas desta competência) = total - pago, somando recebíveis.
    a_receber = ZERO
    recebido_das_vendas = ZERO
    from .models import Recebivel
    for r in Recebivel.objects.filter(venda__competencia=competencia):
        a_receber += r.a_receber
        recebido_das_vendas += r.valor_pago

    recebido_caixa = _soma(pagamentos, 'valor')
    compras_pagas = _soma(compras.filter(situacao='PAGA'), 'valor_total')

    potes_vendidos = itens.aggregate(
        q=Coalesce(Sum('quantidade'), Value(ZERO), output_field=DEC))['q']
    produzido = ProducaoProduto.objects.filter(competencia=competencia).aggregate(
        q=Coalesce(Sum('quantidade_produzida'), Value(ZERO), output_field=DEC))['q']

    ticket_medio = (vendido / num_vendas) if num_vendas else ZERO

    ranking = list(
        itens.values('produto__nome')
        .annotate(
            qtd=Coalesce(Sum('quantidade'), Value(ZERO), output_field=DEC),
            valor=Coalesce(Sum('subtotal'), Value(ZERO), output_field=DEC),
        ).order_by('-valor')[:10]
    )

    entradas_por_forma = list(
        pagamentos.values('forma_pagamento')
        .annotate(total=Coalesce(Sum('valor'), Value(ZERO), output_field=DEC)).order_by('-total')
    )
    entradas_por_conta = list(
        pagamentos.values('conta_recebimento__nome')
        .annotate(total=Coalesce(Sum('valor'), Value(ZERO), output_field=DEC)).order_by('-total')
    )
    vendas_por_canal = list(
        vendas.values('canal__nome')
        .annotate(total=Coalesce(Sum('valor_total'), Value(ZERO), output_field=DEC)).order_by('-total')
    )

    config = ConfiguracaoFinanceira.get_solo()
    resultado_competencia = vendido - custo_compras
    resultado_caixa = recebido_caixa - compras_pagas
    dizimo = (resultado_competencia * config.dizimo_percentual / Decimal('100')) if config.dizimo_ativo else ZERO

    anterior = _competencia_anterior(competencia)
    vendido_anterior = _soma(Venda.objects.filter(competencia=anterior), 'valor_total') if anterior else None
    delta_vendido = None
    if vendido_anterior and vendido_anterior > ZERO:
        delta_vendido = float((vendido - vendido_anterior) / vendido_anterior * 100)

    feed = list(
        vendas.select_related('cliente').order_by('-id')[:8]
        .values('id', 'data_venda', 'cliente__nome', 'valor_total')
    )

    return {
        'competencia': {'id': competencia.id, 'rotulo': competencia.rotulo, 'status': competencia.status},
        'vendido': vendido,
        'recebido': recebido_das_vendas,
        'a_receber': a_receber,
        'recebido_caixa': recebido_caixa,
        'custo_compras': custo_compras,
        'resultado_competencia': resultado_competencia,
        'resultado_caixa': resultado_caixa,
        'potes_vendidos': potes_vendidos,
        'produzido': produzido,
        'faltam_vender': produzido - potes_vendidos,
        'num_vendas': num_vendas,
        'ticket_medio': ticket_medio,
        'dizimo_estimado': dizimo,
        'delta_vendido_pct': delta_vendido,
        'tem_mes_anterior': anterior is not None,
        'ranking_produtos': ranking,
        'entradas_por_forma': entradas_por_forma,
        'entradas_por_conta': entradas_por_conta,
        'vendas_por_canal': vendas_por_canal,
        'feed': feed,
    }


def build_fechamento(competencia):
    dash = build_dashboard(competencia)
    config = ConfiguracaoFinanceira.get_solo()
    resultado = dash['resultado_competencia']
    dizimo = (resultado * config.dizimo_percentual / Decimal('100')) if config.dizimo_ativo else ZERO
    prolabore = config.prolabore_valor_fixo or (resultado * config.prolabore_percentual / Decimal('100'))

    split = list(
        Venda.objects.filter(competencia=competencia).values('socio_destino')
        .annotate(total=Coalesce(Sum('valor_total'), Value(ZERO), output_field=DEC)).order_by('-total')
    )
    return {
        'competencia': dash['competencia'],
        'vendido': dash['vendido'],
        'custo_compras': dash['custo_compras'],
        'resultado_competencia': resultado,
        'resultado_caixa': dash['resultado_caixa'],
        'dizimo': dizimo,
        'prolabore': prolabore,
        'liquido_depois_deducoes': resultado - dizimo - prolabore,
        'split_por_socio': split,
        'config': {
            'dizimo_percentual': config.dizimo_percentual,
            'dizimo_ativo': config.dizimo_ativo,
            'prolabore_percentual': config.prolabore_percentual,
            'prolabore_valor_fixo': config.prolabore_valor_fixo,
        },
    }
