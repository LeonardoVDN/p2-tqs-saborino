from decimal import Decimal

from django.db import models
from django.utils.text import slugify

from .enums import FormaPagamento

ZERO = Decimal('0.00')
MESES_PT = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
]


class Competencia(models.Model):
    """Mês de referência do negócio. Escopo de vendas, compras e produção.

    Substitui a ideia de "uma planilha por mês". Nunca é digitada nas telas
    operacionais: é derivada da data do lançamento.
    """

    class Status(models.TextChoices):
        ABERTA = 'ABERTA', 'Aberta'
        FECHADA = 'FECHADA', 'Fechada'

    ano = models.PositiveSmallIntegerField()
    mes = models.PositiveSmallIntegerField(help_text='1 a 12')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ABERTA)
    data_fechamento = models.DateField(null=True, blank=True)
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Competência'
        verbose_name_plural = 'Competências'
        unique_together = ('ano', 'mes')
        ordering = ['-ano', '-mes']

    def __str__(self):
        return self.rotulo

    @property
    def rotulo(self):
        nome = MESES_PT[self.mes - 1] if 1 <= self.mes <= 12 else '?'
        return f'{nome}/{self.ano}'

    @property
    def fechada(self):
        return self.status == self.Status.FECHADA

    @classmethod
    def para_data(cls, data):
        """Retorna (criando se preciso) a competência do ano/mês da data."""
        obj, _ = cls.objects.get_or_create(ano=data.year, mes=data.month)
        return obj


class Canal(models.Model):
    """Procedência/origem do cliente (ex.: Canal A, Canal B, Canal C)."""

    nome = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True, blank=True)
    aplica_dizimo = models.BooleanField(
        default=False, help_text='Marca o canal usado como base do dízimo (ex.: Canal B).'
    )
    ordem = models.PositiveSmallIntegerField(default=0)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Canal'
        verbose_name_plural = 'Canais'
        ordering = ['ordem', 'nome']

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)


class Conta(models.Model):
    """Carteira de onde sai o dinheiro das compras e para onde entram os
    recebimentos das vendas (ex.: Conta Corrente, Caixa, Cartão de Crédito)."""

    class Tipo(models.TextChoices):
        CONTA_CORRENTE = 'CONTA_CORRENTE', 'Conta corrente'
        DINHEIRO = 'DINHEIRO', 'Dinheiro'
        CARTAO_CREDITO = 'CARTAO_CREDITO', 'Cartão de crédito'
        CARTAO_TERCEIRO = 'CARTAO_TERCEIRO', 'Cartão de terceiro'

    nome = models.CharField(max_length=60, unique=True)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.CONTA_CORRENTE)
    titular_nome = models.CharField(max_length=60, blank=True, help_text='Ex.: "Terceiro", quando o titular não é sócio.')
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Conta'
        verbose_name_plural = 'Contas'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Produto(models.Model):
    """Item do catálogo vendável. Base da página 'criar produtos'."""

    class Categoria(models.TextChoices):
        BOLO_POTE = 'BOLO_POTE', 'Bolo de pote'
        MOUSSE = 'MOUSSE', 'Mousse'
        PUDIM = 'PUDIM', 'Pudim'
        TORTA = 'TORTA', 'Torta'
        BROWNIE = 'BROWNIE', 'Brownie'
        OVO_PASCOA = 'OVO_PASCOA', 'Ovo de Páscoa'
        ENERGETICO = 'ENERGETICO', 'Energético'
        OUTRO = 'OUTRO', 'Outro'

    class Unidade(models.TextChoices):
        POTE = 'POTE', 'Pote'
        UNIDADE = 'UNIDADE', 'Unidade'
        FATIA = 'FATIA', 'Fatia'
        KG = 'KG', 'Kg'

    nome = models.CharField(max_length=80, unique=True)
    categoria = models.CharField(max_length=20, choices=Categoria.choices, default=Categoria.OUTRO)
    unidade = models.CharField(max_length=10, choices=Unidade.choices, default=Unidade.POTE)
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2, default=ZERO)
    custo_estimado_unitario = models.DecimalField(
        max_digits=10, decimal_places=2, default=ZERO,
        help_text='Estimativa para precificação. NÃO é a fonte do custo contábil.',
    )
    sazonal = models.BooleanField(default=False)
    ativo = models.BooleanField(default=True)
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Cliente(models.Model):
    """Quem compra. Base da página 'cadastro de clientes'."""

    nome = models.CharField(max_length=120)
    canal = models.ForeignKey(
        Canal, null=True, blank=True, on_delete=models.SET_NULL, related_name='clientes',
    )
    contato = models.CharField(max_length=40, blank=True, help_text='Telefone/WhatsApp')
    forma_pagamento_preferida = models.CharField(
        max_length=10, choices=FormaPagamento.choices, blank=True,
    )
    observacoes = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['nome']

    def __str__(self):
        return self.nome
