from django.urls import path
from .public_v1_views import PublicSystemStatusView

urlpatterns = [
    path('status/', PublicSystemStatusView.as_view(), name='public-status'),
]