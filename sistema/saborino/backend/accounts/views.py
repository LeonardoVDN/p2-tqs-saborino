from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import UserSerializer

from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from .serializers import UserRegistrationSerializer

from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes

User = get_user_model()

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        token = default_token_generator.make_token(user)

        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # --- Construção do Link ---
        # Esse link aponta para o SEU FRONTEND (Vue.js)
        # O Vue vai ler esse link e chamar a API de confirmação depois
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173').rstrip('/')
        confirm_link = f"{frontend_url}/confirmar-email/?uid={uid}&token={token}"

        # --- Envio do E-mail ---
        send_mail(
            subject='Confirme sua conta no Sistema',
            message=f'Olá {user.username},\n\nPor favor, clique no link abaixo para ativar sua conta:\n\n{confirm_link}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return Response(
            {"message": "Usuário criado! Verifique seu e-mail para ativar a conta."},
            status=status.HTTP_201_CREATED
        )
    
class ActivateAccountView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')

        if not uid or not token:
            return Response({'error': 'UID e Token são obrigatórios.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 1. Decodifica o ID do usuário (de Base64 para número)
            uid_decoded = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=uid_decoded)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'error': 'Link inválido ou usuário não encontrado.'}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Verifica se o token é válido para esse usuário
        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            return Response({'message': 'Conta ativada com sucesso!'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Link de ativação inválido ou expirado.'}, status=status.HTTP_400_BAD_REQUEST)

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.throttling import ScopedRateThrottle


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """Login com throttle dedicado (defesa contra força bruta)."""
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'


class LogoutView(APIView):
    """Invalida o refresh token (blacklist) no logout."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get('refresh')
        if not refresh:
            return Response({'error': 'Informe o refresh token.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            RefreshToken(refresh).blacklist()
        except Exception:
            return Response({'error': 'Token inválido.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': 'Logout efetuado.'}, status=status.HTTP_205_RESET_CONTENT)
