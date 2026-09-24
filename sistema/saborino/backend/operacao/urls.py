from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CompraViewSet, ConfiguracaoFinanceiraView, CustoPorProdutoView, DashboardView,
    FechamentoView, PagamentoViewSet, ProducaoProdutoViewSet, RecebivelViewSet,
    RelatorioPorProdutoView, VendaViewSet,
)

router = DefaultRouter()
router.register('vendas', VendaViewSet)
router.register('recebiveis', RecebivelViewSet)
router.register('pagamentos', PagamentoViewSet)
router.register('compras', CompraViewSet)
router.register('producoes', ProducaoProdutoViewSet)

urlpatterns = [
    path('config-financeira/', ConfiguracaoFinanceiraView.as_view(), name='config-financeira'),
    path('relatorios/dashboard/', DashboardView.as_view(), name='rel-dashboard'),
    path('relatorios/custo-por-produto/', CustoPorProdutoView.as_view(), name='rel-custo-produto'),
    path('relatorios/por-produto/', RelatorioPorProdutoView.as_view(), name='rel-por-produto'),
    path('relatorios/fechamento/', FechamentoView.as_view(), name='rel-fechamento'),
]
urlpatterns += router.urls
