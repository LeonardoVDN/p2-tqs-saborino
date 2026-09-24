from rest_framework import serializers

from .models import Canal, Cliente, Competencia, Conta, Produto


class CompetenciaSerializer(serializers.ModelSerializer):
    rotulo = serializers.CharField(read_only=True)

    class Meta:
        model = Competencia
        fields = ['id', 'ano', 'mes', 'rotulo', 'status', 'data_fechamento', 'observacoes']
        read_only_fields = ['id', 'rotulo']


class CanalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Canal
        fields = ['id', 'nome', 'slug', 'aplica_dizimo', 'ordem', 'ativo']
        read_only_fields = ['id', 'slug']


class ContaSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = Conta
        fields = ['id', 'nome', 'tipo', 'tipo_display', 'titular_nome', 'ativo']
        read_only_fields = ['id', 'tipo_display']


class ProdutoSerializer(serializers.ModelSerializer):
    categoria_display = serializers.CharField(source='get_categoria_display', read_only=True)

    class Meta:
        model = Produto
        fields = [
            'id', 'nome', 'categoria', 'categoria_display', 'unidade',
            'preco_venda', 'custo_estimado_unitario', 'sazonal', 'ativo', 'observacoes',
        ]
        read_only_fields = ['id', 'categoria_display']


class ClienteSerializer(serializers.ModelSerializer):
    canal_nome = serializers.CharField(source='canal.nome', read_only=True, default=None)

    class Meta:
        model = Cliente
        fields = [
            'id', 'nome', 'canal', 'canal_nome', 'contato',
            'forma_pagamento_preferida', 'observacoes', 'ativo',
        ]
        read_only_fields = ['id', 'canal_nome']
