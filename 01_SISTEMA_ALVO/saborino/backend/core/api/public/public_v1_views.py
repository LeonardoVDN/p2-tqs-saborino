from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_api_key.permissions import HasAPIKey
from drf_spectacular.utils import extend_schema, OpenApiTypes

class PublicSystemStatusView(APIView):
    permission_classes = [HasAPIKey | IsAuthenticated] 

    @extend_schema(
        summary="Verificar Status do Sistema",
        description="Retorna se a API está online. Requer API Key.",
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request):
        return Response({
            "status": "online",
            "message": "Sistema Operacional",
            "user_type": "Authenticated User" if request.user.is_authenticated else "External API Key",
            "version": "v1"
        })