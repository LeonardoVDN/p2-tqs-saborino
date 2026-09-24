from django.contrib import admin

from .models import (
    Compra, ConfiguracaoFinanceira, ItemVenda, Pagamento, PagamentoAlocacao,
    ProducaoProduto, Recebivel, Venda,
)


class ItemVendaInline(admin.TabularInline):
    model = ItemVenda
    extra = 0


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    list_display = ('id', 'data_venda', 'cliente', 'valor_total', 'competencia', 'socio_destino')
    list_filter = ('competencia', 'socio_destino', 'canal')
    search_fields = ('cliente__nome',)
    inlines = [ItemVendaInline]


class PagamentoAlocacaoInline(admin.TabularInline):
    model = PagamentoAlocacao
    extra = 0


@admin.register(Pagamento)
class PagamentoAdmin(admin.ModelAdmin):
    list_display = ('id', 'data', 'cliente', 'valor', 'forma_pagamento', 'conta_recebimento')
    list_filter = ('competencia', 'forma_pagamento')
    inlines = [PagamentoAlocacaoInline]


@admin.register(Recebivel)
class RecebivelAdmin(admin.ModelAdmin):
    list_display = ('id', 'venda', 'cliente', 'valor_total', 'valor_pago', 'a_receber', 'status')
    search_fields = ('cliente__nome',)


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ('id', 'data', 'descricao', 'valor_total', 'produto_rateio', 'conta_origem', 'situacao')
    list_filter = ('competencia', 'situacao', 'produto_rateio')


@admin.register(ProducaoProduto)
class ProducaoProdutoAdmin(admin.ModelAdmin):
    list_display = ('produto', 'competencia', 'quantidade_produzida', 'meta_producao')
    list_filter = ('competencia',)


admin.site.register(ConfiguracaoFinanceira)
