from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_api_key.permissions import HasAPIKey
from accounts.tasks import tarefa_pesada_simulada 


class TriggerTaskView(APIView):
    permission_classes = [HasAPIKey] 

    def post(self, request):
        nome = request.data.get('nome', 'Visitante')
        
        tarefa_pesada_simulada.delay(nome) 
        
        return Response({
            "message": "Tarefa enviada para a fila! Pode continuar navegando.",
            "status": "processing"
        })