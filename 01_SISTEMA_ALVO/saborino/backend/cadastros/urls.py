from rest_framework.routers import DefaultRouter

from .views import (
    CanalViewSet, ClienteViewSet, CompetenciaViewSet, ContaViewSet, ProdutoViewSet,
)

router = DefaultRouter()
router.register('competencias', CompetenciaViewSet)
router.register('canais', CanalViewSet)
router.register('contas', ContaViewSet)
router.register('produtos', ProdutoViewSet)
router.register('clientes', ClienteViewSet)

urlpatterns = router.urls
