from django.urls import path
from .webhook import resend_webhook

urlpatterns = [
    path('resend/', resend_webhook, name='resend-webhook'),
]
