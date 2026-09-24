# Sistema Saborino

Sistema web de gestão de uma pequena produção de alimentos: clientes, produtos, vendas, recebíveis,
pagamentos, compras, produção e fechamento mensal.

Esta é a cópia usada como objeto de teste no Projeto P2 de Testes e Qualidade de Software. Os arquivos
de implantação e operação de ambientes reais foram retirados, e os dados padrão das migrações foram
trocados por valores neutros. As instruções completas de instalação, execução e teste do ambiente
do P2 estão em `00_IDENTIFICACAO_E_README/README.md`.

## Tecnologias

- Backend: Python 3.12, Django 5.2, Django REST Framework, drf-spectacular (OpenAPI)
- Banco de dados: PostgreSQL 15
- Frontend: Vue 3, Vite, Pinia, Axios
- Tarefas assíncronas: Celery e Redis (usados só no envio de e-mail)
- Desenvolvimento: Docker e Docker Compose (`docker-compose.yml`)

## Estrutura

```
saborino/
├── backend/            # API Django (apps accounts, cadastros, operacao, notifications, core)
├── ui/                 # Frontend Vue 3
├── docker-compose.yml  # Ambiente de desenvolvimento local
└── .env.example        # Portas e URL da API usadas pelo Compose
```

## Execução local (resumo)

```bash
cp backend/.env.example backend/.env    # ajuste os valores; nunca versione o .env
docker compose -f docker-compose.yml build
docker compose -f docker-compose.yml run --rm api python manage.py migrate
docker compose -f docker-compose.yml up
```

- API: http://localhost:8000/api/v1
- Documentação da API (com `DEBUG=1`): http://localhost:8000/docs/public/
- Frontend: http://localhost:5173

## Testes existentes

```bash
docker compose -f docker-compose.yml run --rm api python manage.py test   # backend (Django TestCase)
cd ui && npx vitest run                                                   # frontend (Vitest)
```
