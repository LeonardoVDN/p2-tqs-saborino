# P2 · Testes e Qualidade de Software · Grupo 13 (CC)

Projeto da disciplina de Testes e Qualidade de Software da Unisagrado (2026), com o Prof. Dr. Elvio Gilberto da Silva.
Integrantes: Leonardo Valentim, Natasha Teixeira e Udymilla Chagas.

O sistema testado é o **Saborino**, um sistema web de gestão de uma pequena produção de alimentos
(Django REST Framework, PostgreSQL 15 e Vue 3). O código está em `sistema/saborino`.
Os arquivos de implantação foram retirados e os cadastros padrão usam nomes genéricos.

## Como rodar (Docker)

```bash
cd sistema/saborino
cp ../ambiente/env.teste backend/.env
sed -i '' 's/^POSTGRES_HOST=.*/POSTGRES_HOST=db/; s#^CELERY_BROKER_URL=.*#CELERY_BROKER_URL=redis://redis:6379/0#' backend/.env

docker compose -p p2tqs-saborino -f docker-compose.yml up -d db redis
docker compose -p p2tqs-saborino -f docker-compose.yml run --rm api python manage.py migrate
docker compose -p p2tqs-saborino -f docker-compose.yml run --rm -v "$PWD/../ambiente:/p2:ro" api python /p2/seed.py
docker compose -p p2tqs-saborino -f docker-compose.yml -f ../ambiente/docker-compose.teste.yml up -d api frontend
```

O arquivo `docker-compose.teste.yml` liga o `CORS_ALLOW_CREDENTIALS` só no ambiente de teste. Sem ele, o frontend abre em branco porque o navegador bloqueia as chamadas à API.

- Frontend: http://localhost:5173
- API: http://localhost:8000/api/v1
- Usuário de teste (fictício): `tester@saborino.test` / `SenhaFicticia-P2-2026`

O seed apaga os dados de teste e recria sempre o mesmo estado inicial. Para parar: `docker compose -p p2tqs-saborino -f docker-compose.yml down`.

## Testes

```bash
docker compose -p p2tqs-saborino -f docker-compose.yml run --rm api python manage.py test   # suíte existente do backend
bash ../ambiente/smoke.sh                                                            # verificação rápida da API
```

Os testes do grupo (unitários, API com Postman e interface com Selenium) entram nas próximas etapas.
