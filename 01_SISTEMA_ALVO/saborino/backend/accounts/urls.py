from django.urls import path
from django.conf import settings
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, ActivateAccountView, ThrottledTokenObtainPairView, LogoutView,
)
from .session_views import (
    CsrfBootstrapView, RevokeAllSessionsView, SessionCreateView, SessionDeleteView,
)
from .recovery_views import (
    PasswordResetConfirmationView, PasswordResetExchangeView, PasswordResetRequestView,
)
from .account_views import (
    EmailChangeConfirmationView, EmailChangeRequestView,
    EmailVerificationConfirmationView, EmailVerificationRequestView, PasswordChangeView,
)

urlpatterns = [
    path('csrf/', CsrfBootstrapView.as_view(), name='csrf'),
    path('sessions/', SessionCreateView.as_view(), name='session-create'),
    path('session/', SessionDeleteView.as_view(), name='session-delete'),
    path('sessions/revoke-all/', RevokeAllSessionsView.as_view(), name='session-revoke-all'),
    path('password-reset/requests/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/exchanges/', PasswordResetExchangeView.as_view(), name='password-reset-exchange'),
    path('password-reset/confirmations/', PasswordResetConfirmationView.as_view(), name='password-reset-confirmation'),
    path('password/changes/', PasswordChangeView.as_view(), name='password-change'),
    path('email-verification/requests/', EmailVerificationRequestView.as_view(), name='email-verification-request'),
    path('email-verification/confirmations/', EmailVerificationConfirmationView.as_view(), name='email-verification-confirmation'),
    path('email-change/requests/', EmailChangeRequestView.as_view(), name='email-change-request'),
    path('email-change/confirmations/', EmailChangeConfirmationView.as_view(), name='email-change-confirmation'),
]

if settings.API_JWT_ENABLED:
    urlpatterns += [
        path('token/', ThrottledTokenObtainPairView.as_view(), name='token_obtain_pair'),
        path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
        path('logout/', LogoutView.as_view(), name='logout'),
    ]

if settings.ALLOW_PUBLIC_REGISTRATION:
    urlpatterns += [
        path('register/', RegisterView.as_view(), name='register'),
        path('activate/', ActivateAccountView.as_view(), name='activate'),
    ]
