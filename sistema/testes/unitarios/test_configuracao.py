"""Configuração do sistema para o frontend em outro endereço (RF-01).

Teste criado antes da correção do defeito DEF-009.
"""
from core import settings


# RF-01 · DEF-009 (o frontend em :5173 chama a API em :8000 com o cookie de sessão)
def test_cors_aceita_o_cookie_de_sessao_do_frontend():
    assert getattr(settings, 'CORS_ALLOW_CREDENTIALS', False) is True
