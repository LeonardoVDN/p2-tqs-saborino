# Ajuste do ambiente de teste do P2, sem alterar o código do sistema.
# O frontend (localhost:5173) chama a API (localhost:8000) com cookie de sessão,
# e sem esta opção o navegador bloqueia as requisições por CORS.
from core.settings import *  # noqa: F401,F403

CORS_ALLOW_CREDENTIALS = True
