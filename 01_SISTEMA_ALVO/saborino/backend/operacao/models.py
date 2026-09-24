from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from cadastros.enums import FormaPagamento
from cadastros.models import Canal, Cliente, Competencia, Conta, Produto

ZERO = Decimal('0.00')
CENT = Decimal('0.01')


def q2(valor):
    """Quantiza para 2 casas (dinheiro)."""
    return (Decimal(valor)).quantize(CENT)


class SocioDestino(models.TextChoices):
    NOS = 'NOS', 'Nós'
    S1 = 'S1', 'Sócio 1'
    S2 = 'S2', 'Sócio 2'


class SituacaoCompra(models.TextChoices):
    PAGA = 'PAGA', 'Paga'
    A_PAGAR = 'A_PAGAR', 'A pagar'


class Venda(models.Model):
    """Cabeçalho de um pedido de um cliente. Pronta-entrega, caixa comum.
    Ao salvar itens, gera/atualiza o Recebível correspondente."""

    competencia = models.ForeignKey(Competencia, on_delete=models.PROTECT, related_name='vendas')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='vendas')
    data_venda = models.DateField(default=timezone.localdate)
    canal = models.ForeignKey(
        Canal, null=True, blank=True, on_delete=models.SET_NULL, related_name='vendas',
    )
    socio_destino = models.CharField(max_length=5, choices=SocioDestino.choices, default=SocioDestino.NOS)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=ZERO)
    observacoes = models.TextField(blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='vendas_registradas',
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Venda'
        verbose_name_plural = 'Vendas'
        ordering = ['-data_venda', '-id']

    def __str__(self):
        return f'Venda #{self.pk} — {self.cliente} ({self.valor_total})'

    def save(self, *args, **kwargs):
        # Competência é derivada da data (nunca digitada).
        if self.data_venda and not self.competencia_id:
            self.competencia = Competencia.para_data(self.data_venda)
        # Canal padrão vem do cliente, se não houver override.
        if not self.canal_id and self.cliente_id and self.cliente.canal_id:
            self.canal_id = self.cliente.canal_id
        super().save(*args, **kwargs)

    def recompute_total(self, salvar=True):
        total = sum((item.subtotal for item in self.itens.all()), ZERO)
        self.valor_total = q2(total)
        if salvar:
            super().save(update_fields=['valor_total'])
        return self.valor_total

    def sincronizar_recebivel(self):
        """Cria ou atualiza o Recebível espelhando o total da venda."""
        receb, _ = Recebivel.objects.get_or_create(
            venda=self,
            defaults={'cliente': self.cliente, 'valor_total': self.valor_total},
        )
        if receb.cliente_id != self.cliente_id or receb.valor_total != self.valor_total:
            receb.cliente = self.cliente
            receb.valor_total = self.valor_total
            receb.save(update_fields=['cliente', 'valor_total'])
        return receb


class ItemVenda(models.Model):
    """Linha de produto do pedido, com snapshot de preço e custo."""

    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='itens_venda')
    quantidade = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal('1'))
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=ZERO)
    custo_unitario = models.DecimalField(
        max_digits=10, decimal_places=2, default=ZERO,
        help_text='Snapshot analítico. NÃO alimenta o resultado contábil (que usa custo de período).',
    )
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=ZERO)

    class Meta:
        verbose_name = 'Item de venda'
        verbose_name_plural = 'Itens de venda'

    def __str__(self):
        return f'{self.quantidade}x {self.produto} @ {self.preco_unitario}'

    def save(self, *args, **kwargs):
        # Snapshot do preço/custo do catálogo no momento da venda.
        if self.produto_id:
            if not self.preco_unitario:
                self.preco_unitario = self.produto.preco_venda
            if not self.custo_unitario:
                self.custo_unitario = self.produto.custo_estimado_unitario
        if not self.subtotal:
            self.subtotal = q2(Decimal(self.quantidade) * Decimal(self.preco_unitario))
        super().save(*args, **kwargs)


class Recebivel(models.Model):
    """O direito a receber gerado por uma venda (fiado). Status derivado do saldo."""

    class Status(models.TextChoices):
        ABERTO = 'ABERTO', 'Aberto'
        PARCIAL = 'PARCIAL', 'Parcial'
        PAGO = 'PAGO', 'Pago'
        VENCIDO = 'VENCIDO', 'Vencido'

    venda = models.OneToOneField(Venda, on_delete=models.CASCADE, related_name='recebivel')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='recebiveis')
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=ZERO)
    valor_pago = models.DecimalField(max_digits=10, decimal_places=2, default=ZERO)
    data_vencimento = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = 'Recebível'
        verbose_name_plural = 'Recebíveis'
        ordering = ['venda__data_venda', 'id']

    def __str__(self):
        return f'Recebível venda #{self.venda_id} — {self.a_receber} em aberto'

    @property
    def a_receber(self):
        return q2(self.valor_total - self.valor_pago)

    @property
    def status(self):
        if self.valor_pago >= self.valor_total and self.valor_total > ZERO:
            return self.Status.PAGO
        if self.valor_pago > ZERO:
            return self.Status.PARCIAL
        if self.data_vencimento and self.data_vencimento < timezone.localdate():
            return self.Status.VENCIDO
        return self.Status.ABERTO

    def recompute(self, salvar=True):
        total_alocado = self.alocacoes.aggregate(s=models.Sum('valor_aplicado'))['s'] or ZERO
        self.valor_pago = q2(min(total_alocado, self.valor_total)) if self.valor_total else q2(total_alocado)
        if salvar:
            super().save(update_fields=['valor_pago'])
        return self.valor_pago


class Pagamento(models.Model):
    """Um recebimento do cliente. Pode ser parcial e abater várias vendas."""

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='pagamentos')
    competencia = models.ForeignKey(Competencia, on_delete=models.PROTECT, related_name='pagamentos')
    data = models.DateField(default=timezone.localdate)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    forma_pagamento = models.CharField(max_length=10, choices=FormaPagamento.choices, default=FormaPagamento.PIX)
    conta_recebimento = models.ForeignKey(
        Conta, null=True, blank=True, on_delete=models.SET_NULL, related_name='pagamentos',
    )
    observacoes = models.TextField(blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='pagamentos_registrados',
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Pagamento'
        verbose_name_plural = 'Pagamentos'
        ordering = ['-data', '-id']

    def __str__(self):
        return f'Pagamento {self.valor} de {self.cliente} em {self.data}'

    def save(self, *args, **kwargs):
        if self.data and not self.competencia_id:
            self.competencia = Competencia.para_data(self.data)
        super().save(*args, **kwargs)


class PagamentoAlocacao(models.Model):
    """Liga um pagamento aos recebíveis que ele abate."""

    pagamento = models.ForeignKey(Pagamento, on_delete=models.CASCADE, related_name='alocacoes')
    recebivel = models.ForeignKey(Recebivel, on_delete=models.PROTECT, related_name='alocacoes')
    valor_aplicado = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Alocação de pagamento'
        verbose_name_plural = 'Alocações de pagamento'

    def __str__(self):
        return f'{self.valor_aplicado} do pagamento #{self.pagamento_id} no recebível #{self.recebivel_id}'


class Compra(models.Model):
    """Gasto de insumo com rateio de custo por produto (ou 'Geral')."""

    competencia = models.ForeignKey(Competencia, on_delete=models.PROTECT, related_name='compras')
    data = models.DateField(default=timezone.localdate)
    descricao = models.CharField(max_length=120, help_text='Item comprado (texto livre no MVP).')
    quantidade = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal('1'))
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=ZERO)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=ZERO)
    conta_origem = models.ForeignKey(
        Conta, null=True, blank=True, on_delete=models.SET_NULL, related_name='compras',
    )
    produto_rateio = models.ForeignKey(
        Produto, null=True, blank=True, on_delete=models.SET_NULL, related_name='compras',
        help_text='Produto ao qual o custo é atribuído. Vazio = Geral.',
    )
    situacao = models.CharField(max_length=10, choices=SituacaoCompra.choices, default=SituacaoCompra.PAGA)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='compras_registradas',
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'
        ordering = ['-data', '-id']

    def __str__(self):
        return f'{self.descricao} — {self.valor_total}'

    def save(self, *args, **kwargs):
        if self.data and not self.competencia_id:
            self.competencia = Competencia.para_data(self.data)
        if not self.valor_total:
            self.valor_total = q2(Decimal(self.quantidade) * Decimal(self.preco_unitario))
        super().save(*args, **kwargs)


class ProducaoProduto(models.Model):
    """Produção realizada e meta por (produto, competência). Base do 'faltam vender'."""

    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='producoes')
    competencia = models.ForeignKey(Competencia, on_delete=models.PROTECT, related_name='producoes')
    quantidade_produzida = models.DecimalField(max_digits=10, decimal_places=3, default=ZERO)
    meta_producao = models.DecimalField(max_digits=10, decimal_places=3, default=ZERO)

    class Meta:
        verbose_name = 'Produção do produto'
        verbose_name_plural = 'Produção dos produtos'
        unique_together = ('produto', 'competencia')
        ordering = ['produto__nome']

    def __str__(self):
        return f'{self.produto} — {self.quantidade_produzida} em {self.competencia}'


class ConfiguracaoFinanceira(models.Model):
    """Configuração única (singleton) de dízimo/pró-labore. Usada no fechamento (Fase 7)."""

    dizimo_percentual = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('10.00'))
    dizimo_ativo = models.BooleanField(default=True)
    prolabore_percentual = models.DecimalField(max_digits=5, decimal_places=2, default=ZERO)
    prolabore_valor_fixo = models.DecimalField(max_digits=10, decimal_places=2, default=ZERO)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuração financeira'
        verbose_name_plural = 'Configuração financeira'

    def __str__(self):
        return 'Configuração financeira'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
