from django.urls import path, include
from accounts.views import MeView
from rest_framework.views import APIView
from rest_framework.response import Response
from .internal_view import TriggerTaskView

urlpatterns = [

    path('auth/', include('rest_framework.urls')),

    path('me/', MeView.as_view(), name='internal-me'),
    
    path('test-celery/', TriggerTaskView.as_view()),
    
]