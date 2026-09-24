from django.contrib import admin

from .models import Canal, Cliente, Competencia, Conta, Produto


@admin.register(Competencia)
class CompetenciaAdmin(admin.ModelAdmin):
    list_display = ('rotulo', 'ano', 'mes', 'status')
    list_filter = ('status', 'ano')


@admin.register(Canal)
class CanalAdmin(admin.ModelAdmin):
    list_display = ('nome', 'aplica_dizimo', 'ordem', 'ativo')
    list_editable = ('aplica_dizimo', 'ordem', 'ativo')
    prepopulated_fields = {'slug': ('nome',)}


@admin.register(Conta)
class ContaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'titular_nome', 'ativo')
    list_filter = ('tipo', 'ativo')


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'categoria', 'preco_venda', 'custo_estimado_unitario', 'sazonal', 'ativo')
    list_filter = ('categoria', 'ativo', 'sazonal')
    search_fields = ('nome',)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'canal', 'contato', 'ativo')
    list_filter = ('canal', 'ativo')
    search_fields = ('nome', 'contato')
