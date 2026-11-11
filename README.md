# P2 · Testes e Qualidade de Software · Grupo 13 (CC)

Projeto da disciplina de Testes e Qualidade de Software da Unisagrado (2026), com o Prof. Dr. Elvio Gilberto da Silva.
Integrantes: Leonardo Valentim, Natasha Teixeira, Udymilla Chagas, Karina Zaniti Sanches e Lucas Leão Franco.

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

### Testes unitários do grupo (pytest)

Ficam em `sistema/testes/unitarios`. Rodam dentro do container da API, sem banco (as dependências de teste ficam numa pasta fora do projeto):

```bash
docker run --rm -v ~/.p2_saborino/pydeps:/deps python:3.12-slim-bookworm pip install -q --target /deps pytest==8.4.2 pytest-django==4.11.1 pytest-cov
docker compose -p p2tqs-saborino -f docker-compose.yml -f ../ambiente/docker-compose.teste.yml run --rm --no-deps \
  -v ~/.p2_saborino/pydeps:/deps -v "$PWD/../testes:/testes" -e PYTHONPATH=/deps:/app:/p2 -w /testes api python -m pytest -v
```

### Testes de API (Postman e Newman)

A coleção e o ambiente ficam em `sistema/testes/api` e podem ser importados no Postman. Para rodar pelo terminal com o Newman (`npm install -g newman newman-reporter-htmlextra`), com o sistema no ar:

```bash
bash sistema/testes/api/rodar-newman.sh
```

O script restaura os dados fictícios antes e depois e grava os relatórios em `sistema/testes/api/resultado/`. Duas verificações falham de propósito enquanto os defeitos DEF-004 e DEF-008 (issues #4 e #8) não forem corrigidos.

### Testes de interface (Selenium)

Ficam em `sistema/testes/interface` e rodam no Chrome do computador (sem janela), com o sistema no ar. Cada teste restaura os dados fictícios antes de começar e salva um print no final:

```bash
pip install pytest==8.4.2 selenium==4.35.0 pytest-html
cd sistema/testes/interface && python -m pytest -v
```

Os prints ficam em `sistema/testes/interface/resultado/`. Para ver o navegador abrindo, use `MOSTRAR_NAVEGADOR=1`. O teste do nome de produto repetido falha enquanto o DEF-001 (issue #1) não for corrigido.

### Testes não funcionais

Ficam em `sistema/testes/nao-funcionais`, com o sistema no ar. `nf_api.py` mede desempenho, segurança básica e confiabilidade pela API (só precisa do Python). `nf_interface.py` mede o tempo das telas e a compatibilidade (Chrome em duas resoluções e Safari), com o Selenium:

```bash
cd sistema/testes/nao-funcionais
python3 nf_api.py resultado
python nf_interface.py resultado
```

### Pipeline (GitHub Actions)

O arquivo `.github/workflows/testes.yml` roda a cada envio para a `main` e a cada pull request. Ele instala as dependências, executa os testes unitários do grupo e a suíte do sistema (com um PostgreSQL 15 de serviço) e publica o resultado como artefato. As execuções ficam na aba Actions.
