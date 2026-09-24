from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from .models import Canal, Cliente, Competencia, Conta, Produto
from .serializers import (
    CanalSerializer, ClienteSerializer, CompetenciaSerializer,
    ContaSerializer, ProdutoSerializer,
)


class CompetenciaViewSet(viewsets.ModelViewSet):
    queryset = Competencia.objects.all()
    serializer_class = CompetenciaSerializer

    @action(detail=False, methods=['get'])
    def atual(self, request):
        """Competência do mês corrente (criando se necessário)."""
        comp = Competencia.para_data(timezone.localdate())
        return Response(self.get_serializer(comp).data)


class CanalViewSet(viewsets.ModelViewSet):
    queryset = Canal.objects.all()
    serializer_class = CanalSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('ativo') == 'true':
            qs = qs.filter(ativo=True)
        return qs


class ContaViewSet(viewsets.ModelViewSet):
    queryset = Conta.objects.all()
    serializer_class = ContaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('ativo') == 'true':
            qs = qs.filter(ativo=True)
        return qs


class ProdutoViewSet(viewsets.ModelViewSet):
    queryset = Produto.objects.all()
    serializer_class = ProdutoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get('ativo') == 'true':
            qs = qs.filter(ativo=True)
        if p.get('sazonal') == 'true':
            qs = qs.filter(sazonal=True)
        busca = p.get('q')
        if busca:
            qs = qs.filter(nome__icontains=busca)
        return qs


class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.select_related('canal').all()
    serializer_class = ClienteSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get('ativo') == 'true':
            qs = qs.filter(ativo=True)
        busca = p.get('q')
        if busca:
            qs = qs.filter(nome__icontains=busca)
        return qs
