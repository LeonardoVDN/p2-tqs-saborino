from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from cadastros.models import Competencia
from . import reports
from .models import (
    Compra, ConfiguracaoFinanceira, Pagamento, ProducaoProduto, Recebivel, Venda,
)
from .serializers import (
    CompraSerializer, ConfiguracaoFinanceiraSerializer, PagamentoSerializer,
    ProducaoProdutoSerializer, QuitarVendaSerializer, RecebivelSerializer,
    RegistrarPagamentoSerializer, VendaSerializer,
)


def resolver_competencia(request, criar=False):
    """Resolve a competência a partir de ?competencia=<id> ou ?ano=&mes=.
    Sem parâmetros, usa o mês corrente."""
    p = request.query_params
    comp_id = p.get('competencia')
    if comp_id:
        return Competencia.objects.filter(pk=comp_id).first()
    ano, mes = p.get('ano'), p.get('mes')
    if ano and mes:
        if criar:
            return Competencia.objects.get_or_create(ano=int(ano), mes=int(mes))[0]
        return Competencia.objects.filter(ano=int(ano), mes=int(mes)).first()
    return Competencia.para_data(timezone.localdate())


class VendaViewSet(viewsets.ModelViewSet):
    queryset = Venda.objects.select_related('cliente', 'canal', 'competencia', 'recebivel').prefetch_related('itens__produto')
    serializer_class = VendaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        comp_id = p.get('competencia')
        if comp_id:
            qs = qs.filter(competencia_id=comp_id)
        cliente = p.get('cliente')
        if cliente:
            qs = qs.filter(cliente_id=cliente)
        return qs

    @action(detail=False, methods=['get'], url_path=r'repetir-ultimo/(?P<cliente_id>\d+)')
    def repetir_ultimo(self, request, cliente_id=None):
        """Devolve os itens da última venda do cliente, para pré-preencher."""
        ultima = (
            Venda.objects.filter(cliente_id=cliente_id)
            .prefetch_related('itens__produto').order_by('-data_venda', '-id').first()
        )
        if not ultima:
            return Response({'itens': []})
        itens = [
            {'produto': i.produto_id, 'produto_nome': i.produto.nome,
             'quantidade': i.quantidade, 'preco_unitario': i.preco_unitario}
            for i in ultima.itens.all()
        ]
        return Response({'venda': ultima.id, 'itens': itens})

    @action(detail=True, methods=['post'], url_path='quitar')
    def quitar(self, request, pk=None):
        """Baixa rápida: quita todo o saldo em aberto da venda."""
        from . import services
        venda = self.get_object()
        ser = QuitarVendaSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        pagamento = services.quitar_venda(
            venda=venda,
            forma_pagamento=ser.validated_data['forma_pagamento'],
            conta_recebimento=ser.validated_data.get('conta_recebimento'),
            data=ser.validated_data.get('data'),
            registrado_por=request.user if request.user.is_authenticated else None,
        )
        if pagamento is None:
            return Response({'detail': 'Venda já está quitada.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PagamentoSerializer(pagamento).data, status=status.HTTP_201_CREATED)


class RecebivelViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Recebivel.objects.select_related('cliente', 'venda').all()
    serializer_class = RecebivelSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        comp_id = p.get('competencia')
        if comp_id:
            qs = qs.filter(venda__competencia_id=comp_id)
        cliente = p.get('cliente')
        if cliente:
            qs = qs.filter(cliente_id=cliente)
        return qs

    @action(detail=False, methods=['get'])
    def em_aberto(self, request):
        """Recebíveis com saldo, ordenados por data da venda (mais antigos primeiro)."""
        qs = self.get_queryset().order_by('venda__data_venda', 'id')
        abertos = [r for r in qs if r.a_receber > 0]
        return Response(self.get_serializer(abertos, many=True).data)


class PagamentoViewSet(viewsets.ModelViewSet):
    queryset = Pagamento.objects.select_related('cliente', 'conta_recebimento').prefetch_related('alocacoes').all()
    serializer_class = PagamentoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        comp_id = self.request.query_params.get('competencia')
        if comp_id:
            qs = qs.filter(competencia_id=comp_id)
        cliente = self.request.query_params.get('cliente')
        if cliente:
            qs = qs.filter(cliente_id=cliente)
        return qs

    def create(self, request, *args, **kwargs):
        ser = RegistrarPagamentoSerializer(data=request.data, context={'request': request})
        ser.is_valid(raise_exception=True)
        pagamento = ser.save()
        return Response(PagamentoSerializer(pagamento).data, status=status.HTTP_201_CREATED)


class CompraViewSet(viewsets.ModelViewSet):
    queryset = Compra.objects.select_related('conta_origem', 'produto_rateio', 'competencia').all()
    serializer_class = CompraSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        comp_id = self.request.query_params.get('competencia')
        if comp_id:
            qs = qs.filter(competencia_id=comp_id)
        return qs


class ProducaoProdutoViewSet(viewsets.ModelViewSet):
    queryset = ProducaoProduto.objects.select_related('produto', 'competencia').all()
    serializer_class = ProducaoProdutoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        comp_id = self.request.query_params.get('competencia')
        if comp_id:
            qs = qs.filter(competencia_id=comp_id)
        return qs


class ConfiguracaoFinanceiraView(APIView):
    def get(self, request):
        config = ConfiguracaoFinanceira.get_solo()
        return Response(ConfiguracaoFinanceiraSerializer(config).data)

    def put(self, request):
        config = ConfiguracaoFinanceira.get_solo()
        ser = ConfiguracaoFinanceiraSerializer(config, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


# ---------- Relatórios ----------

class DashboardView(APIView):
    def get(self, request):
        comp = resolver_competencia(request)
        if not comp:
            return Response({'detail': 'Competência não encontrada.'}, status=404)
        return Response(reports.build_dashboard(comp))


class CustoPorProdutoView(APIView):
    def get(self, request):
        comp = resolver_competencia(request)
        if not comp:
            return Response({'detail': 'Competência não encontrada.'}, status=404)
        return Response(reports.custo_por_produto(comp))


class RelatorioPorProdutoView(APIView):
    def get(self, request):
        comp = resolver_competencia(request)
        if not comp:
            return Response({'detail': 'Competência não encontrada.'}, status=404)
        return Response(reports.relatorio_por_produto(comp))


class FechamentoView(APIView):
    def get(self, request):
        comp = resolver_competencia(request)
        if not comp:
            return Response({'detail': 'Competência não encontrada.'}, status=404)
        return Response(reports.build_fechamento(comp))
