from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from cadastros.models import Cliente, Conta, Produto
from cadastros.enums import FormaPagamento

from . import services
from .models import (
    Compra, ConfiguracaoFinanceira, ItemVenda, Pagamento, PagamentoAlocacao,
    ProducaoProduto, Recebivel, Venda,
)


# ---------- Itens de venda ----------

class ItemVendaWriteSerializer(serializers.Serializer):
    produto = serializers.PrimaryKeyRelatedField(queryset=Produto.objects.all())
    quantidade = serializers.DecimalField(max_digits=10, decimal_places=3, default=Decimal('1'))
    preco_unitario = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)


class ItemVendaReadSerializer(serializers.ModelSerializer):
    produto_nome = serializers.CharField(source='produto.nome', read_only=True)

    class Meta:
        model = ItemVenda
        fields = ['id', 'produto', 'produto_nome', 'quantidade', 'preco_unitario', 'custo_unitario', 'subtotal']


# ---------- Recebível (leitura) ----------

class RecebivelMiniSerializer(serializers.ModelSerializer):
    a_receber = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Recebivel
        fields = ['id', 'valor_total', 'valor_pago', 'a_receber', 'status', 'data_vencimento']


class RecebivelSerializer(serializers.ModelSerializer):
    a_receber = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    status = serializers.CharField(read_only=True)
    cliente_nome = serializers.CharField(source='cliente.nome', read_only=True)
    data_venda = serializers.DateField(source='venda.data_venda', read_only=True)

    class Meta:
        model = Recebivel
        fields = [
            'id', 'venda', 'cliente', 'cliente_nome', 'data_venda',
            'valor_total', 'valor_pago', 'a_receber', 'status', 'data_vencimento',
        ]
        read_only_fields = fields


# ---------- Venda ----------

class VendaSerializer(serializers.ModelSerializer):
    itens = ItemVendaReadSerializer(many=True, read_only=True)
    itens_input = ItemVendaWriteSerializer(many=True, write_only=True)
    cliente_nome = serializers.CharField(source='cliente.nome', read_only=True)
    canal_nome = serializers.CharField(source='canal.nome', read_only=True, default=None)
    competencia_rotulo = serializers.CharField(source='competencia.rotulo', read_only=True)
    recebivel = RecebivelMiniSerializer(read_only=True)

    # Pagamento imediato opcional
    pagar_agora = serializers.BooleanField(write_only=True, default=False)
    forma_pagamento = serializers.ChoiceField(
        choices=FormaPagamento.choices, write_only=True, required=False,
    )
    conta_recebimento = serializers.PrimaryKeyRelatedField(
        queryset=Conta.objects.all(), write_only=True, required=False, allow_null=True,
    )
    data_vencimento = serializers.DateField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Venda
        fields = [
            'id', 'data_venda', 'cliente', 'cliente_nome', 'canal', 'canal_nome',
            'socio_destino', 'valor_total', 'observacoes', 'competencia', 'competencia_rotulo',
            'itens', 'itens_input', 'recebivel', 'criado_em',
            'pagar_agora', 'forma_pagamento', 'conta_recebimento', 'data_vencimento',
        ]
        read_only_fields = ['id', 'valor_total', 'competencia', 'criado_em']

    def validate_itens_input(self, value):
        if not value:
            raise serializers.ValidationError('A venda precisa de ao menos um item.')
        return value

    def _aplicar_itens(self, venda, itens_data):
        for item in itens_data:
            kwargs = {'venda': venda, 'produto': item['produto'], 'quantidade': item.get('quantidade', Decimal('1'))}
            if item.get('preco_unitario') is not None:
                kwargs['preco_unitario'] = item['preco_unitario']
            if item.get('subtotal') is not None:
                kwargs['subtotal'] = item['subtotal']
            ItemVenda(**kwargs).save()

    @transaction.atomic
    def create(self, validated_data):
        itens_data = validated_data.pop('itens_input')
        pagar_agora = validated_data.pop('pagar_agora', False)
        forma = validated_data.pop('forma_pagamento', None)
        conta = validated_data.pop('conta_recebimento', None)
        vencimento = validated_data.pop('data_vencimento', None)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['registrado_por'] = request.user

        venda = Venda.objects.create(**validated_data)
        self._aplicar_itens(venda, itens_data)
        venda.recompute_total()
        receb = venda.sincronizar_recebivel()
        if vencimento:
            receb.data_vencimento = vencimento
            receb.save(update_fields=['data_vencimento'])
        if pagar_agora:
            services.quitar_venda(
                venda=venda, forma_pagamento=forma or FormaPagamento.PIX,
                conta_recebimento=conta,
                registrado_por=validated_data.get('registrado_por'),
            )
        return venda

    @transaction.atomic
    def update(self, instance, validated_data):
        itens_data = validated_data.pop('itens_input', None)
        # Campos de pagamento não se aplicam ao update simples.
        for f in ['pagar_agora', 'forma_pagamento', 'conta_recebimento', 'data_vencimento']:
            validated_data.pop(f, None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if itens_data is not None:
            instance.itens.all().delete()
            self._aplicar_itens(instance, itens_data)
        instance.recompute_total()
        instance.sincronizar_recebivel()
        return instance


# ---------- Pagamento ----------

class PagamentoAlocacaoReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = PagamentoAlocacao
        fields = ['id', 'recebivel', 'valor_aplicado']


class PagamentoSerializer(serializers.ModelSerializer):
    alocacoes = PagamentoAlocacaoReadSerializer(many=True, read_only=True)
    cliente_nome = serializers.CharField(source='cliente.nome', read_only=True)

    class Meta:
        model = Pagamento
        fields = [
            'id', 'cliente', 'cliente_nome', 'competencia', 'data', 'valor',
            'forma_pagamento', 'conta_recebimento', 'observacoes', 'alocacoes', 'criado_em',
        ]
        read_only_fields = ['id', 'competencia', 'alocacoes', 'criado_em']


class AlocacaoInputSerializer(serializers.Serializer):
    recebivel = serializers.PrimaryKeyRelatedField(queryset=Recebivel.objects.all())
    valor = serializers.DecimalField(max_digits=10, decimal_places=2)


class RegistrarPagamentoSerializer(serializers.Serializer):
    """Entrada para registrar um pagamento (parcial ou consolidado)."""
    cliente = serializers.PrimaryKeyRelatedField(queryset=Cliente.objects.all())
    valor = serializers.DecimalField(max_digits=10, decimal_places=2)
    forma_pagamento = serializers.ChoiceField(choices=FormaPagamento.choices, default=FormaPagamento.PIX)
    data = serializers.DateField(required=False)
    conta_recebimento = serializers.PrimaryKeyRelatedField(
        queryset=Conta.objects.all(), required=False, allow_null=True,
    )
    observacoes = serializers.CharField(required=False, allow_blank=True)
    alocacoes = AlocacaoInputSerializer(many=True, required=False)

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        alocacoes = validated_data.get('alocacoes')
        return services.registrar_pagamento(
            cliente=validated_data['cliente'],
            valor=validated_data['valor'],
            forma_pagamento=validated_data['forma_pagamento'],
            data=validated_data.get('data'),
            conta_recebimento=validated_data.get('conta_recebimento'),
            registrado_por=user,
            observacoes=validated_data.get('observacoes', ''),
            alocacoes=alocacoes if alocacoes else None,
        )


class QuitarVendaSerializer(serializers.Serializer):
    forma_pagamento = serializers.ChoiceField(choices=FormaPagamento.choices, default=FormaPagamento.PIX)
    conta_recebimento = serializers.PrimaryKeyRelatedField(
        queryset=Conta.objects.all(), required=False, allow_null=True,
    )
    data = serializers.DateField(required=False)


# ---------- Compra / Produção / Config ----------

class CompraSerializer(serializers.ModelSerializer):
    produto_rateio_nome = serializers.CharField(source='produto_rateio.nome', read_only=True, default='Geral')
    conta_origem_nome = serializers.CharField(source='conta_origem.nome', read_only=True, default=None)
    competencia_rotulo = serializers.CharField(source='competencia.rotulo', read_only=True)

    class Meta:
        model = Compra
        fields = [
            'id', 'data', 'descricao', 'quantidade', 'preco_unitario', 'valor_total',
            'conta_origem', 'conta_origem_nome', 'produto_rateio', 'produto_rateio_nome',
            'situacao', 'competencia', 'competencia_rotulo',
        ]
        read_only_fields = ['id', 'competencia', 'competencia_rotulo', 'produto_rateio_nome', 'conta_origem_nome']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['registrado_por'] = request.user
        return super().create(validated_data)


class ProducaoProdutoSerializer(serializers.ModelSerializer):
    produto_nome = serializers.CharField(source='produto.nome', read_only=True)

    class Meta:
        model = ProducaoProduto
        fields = ['id', 'produto', 'produto_nome', 'competencia', 'quantidade_produzida', 'meta_producao']
        read_only_fields = ['id', 'produto_nome']


class ConfiguracaoFinanceiraSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracaoFinanceira
        fields = ['id', 'dizimo_percentual', 'dizimo_ativo', 'prolabore_percentual', 'prolabore_valor_fixo', 'atualizado_em']
        read_only_fields = ['id', 'atualizado_em']
