from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from accounts.views import MeView

public_urls = path('api/v1/public/', include('core.api.public.public_v1_urls'))
internal_urls = path('api/internal/', include('core.api.internal.internal_urls'))

urlpatterns = [
    path('api/v1/auth/', include('accounts.urls')),
    path('api/v1/webhooks/email/', include('notifications.urls')),
    path('api/v1/me/', MeView.as_view(), name='me'),

    path('api/v1/', include('cadastros.urls')),
    path('api/v1/', include('operacao.urls')),

    public_urls,
]

if settings.PUBLIC_ADMIN_ENABLED:
    urlpatterns.append(path('admin/', admin.site.urls))

if settings.ENABLE_INTERNAL_API:
    urlpatterns.append(internal_urls)

if settings.ENABLE_API_DOCS:
    urlpatterns += [
        path('api/schema/public/', SpectacularAPIView.as_view(
            patterns=[public_urls],
            custom_settings={
                'TITLE': 'API Pública Sistema Saborino (v1)',
                'VERSION': 'v1',
            }
        ), name='schema-public'),
        path('docs/public/', SpectacularSwaggerView.as_view(
            url_name='schema-public'
        ), name='swagger-public'),
        path('api/schema/internal/', SpectacularAPIView.as_view(
            patterns=[internal_urls],
            custom_settings={
                'TITLE': 'API Interna Sistema Saborino (Frontend)',
                'VERSION': 'dev',
            }
        ), name='schema-internal'),
        path('docs/internal/', SpectacularSwaggerView.as_view(
            url_name='schema-internal'
        ), name='swagger-internal'),
    ]
