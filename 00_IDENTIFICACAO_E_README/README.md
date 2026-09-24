# P2_TQS_2026_CC_GRUPO13_SABORINO

Projeto Integrado P2: Testes e Qualidade de Software. Unisagrado, Ciência da Computação, 2026.
Professor: Prof. Dr. Elvio Gilberto da Silva.

> Estado: **Fase 0 / Marco 1**. O sistema foi escolhido pelo grupo e ainda aguarda aprovação do professor.
> Este README segue a ordem da seção 11.4 do manual e é atualizado a cada fase.

## 1. Identificação dos integrantes

| Integrante | Papel sugerido (seção 4.2) |
|---|---|
| Leonardo Valentim | [a definir pelo grupo] |
| Natasha Teixeira | [a definir pelo grupo] |
| Udymilla Chagas | [a definir pelo grupo] |

Turma: CC. Grupo: 13. A composição é **preliminar**: "por enquanto", conforme informado pelo grupo em 24/09/2026.

## 2. Nome e versão do sistema

- **Sistema Saborino**: sistema web de gestão de uma pequena produção de alimentos. Cobre clientes, produtos, vendas, recebíveis (fiado), pagamentos, compras, produção e fechamento mensal.
- **Versão testada:** release `a63a24f`, com código-fonte congelado em `01_SISTEMA_ALVO/saborino/` em 24/09/2026.
- **Origem:** sistema desenvolvido anteriormente por um integrante (Leonardo Valentim), conforme a seção 5.2.
- Todos os testes rodam numa cópia local com banco próprio e dados fictícios, conforme as seções 5.3 e 15.

## 3. Link do repositório

- GitHub: **[a criar]**. O repositório será aberto pelo grupo, e o link entra aqui.

## 4. Tecnologias

| Camada | Tecnologia | Versão |
|---|---|---|
| Backend / API REST | Python + Django + Django REST Framework | Python 3.12.14, Django 5.2.17, DRF 3.18.1 |
| Banco de dados | PostgreSQL | 15 (15.18 no ambiente de teste) |
| Frontend | Vue 3 + Vite + Pinia + Axios | Node 22, Vite 7 |
| Autenticação | Sessão Django (cookie HttpOnly + CSRF) | — |
| Tarefas assíncronas | Celery + Redis (apenas e-mail; desativado no ambiente de teste) | Celery 5.6 |
| Testes existentes | Django TestCase (backend), Vitest (frontend) | 69 + 1 testes |
| Testes do grupo (planejado) | pytest + pytest-django, Postman/Newman, Selenium, SonarCloud, GitHub Actions | ver `03_PLANO_DE_TESTES` |

## 5. Pré-requisitos

Há duas formas de montar o ambiente.

- **A. Com Docker (forma original do sistema):** Docker Desktop (validado com Docker 28.5.1 e Compose v2.40.3, em macOS 27 arm64), Git, `curl` e `python3` para o smoke test.
- **B. Sem Docker (forma usada nas execuções automatizadas do grupo):** Linux ou macOS, Python 3.12, PostgreSQL 15, Node 22+ e Git. No Linux, o script `01_SISTEMA_ALVO/ambiente_p2/p2_linux.sh` instala sozinho o Python 3.12 (via `uv`) e um PostgreSQL 15 embarcado (via npm).

## 6. Instalação

Forma B, Linux (a mesma usada nas evidências):

```bash
cd 01_SISTEMA_ALVO/ambiente_p2
source p2_linux.sh
p2_install        # Python 3.12 + dependências + PostgreSQL 15 embarcado (em ~/.p2_saborino)
```

Forma A, Docker (macOS com Docker Desktop; validada em 24/09/2026, evidências em `01_SISTEMA_ALVO/evidencias_ambiente/2026-09-24_docker_*`):

```bash
cd 01_SISTEMA_ALVO/saborino
sed -e 's/^POSTGRES_HOST=.*/POSTGRES_HOST=db/' \
    -e 's#^CELERY_BROKER_URL=.*#CELERY_BROKER_URL=redis://redis:6379/0#' \
    ../ambiente_p2/env.p2 > backend/.env
docker compose -p p2tqs-saborino -f docker-compose.yml build api frontend
```

O `-p p2tqs-saborino` dá ao ambiente do P2 um nome de projeto próprio. Sem ele, o Compose usa o nome `sistema-saborino`, e o seed (que apaga os dados operacionais) poderia cair num volume de desenvolvimento com o mesmo nome.

## 7. Configuração

Todas as variáveis ficam em `01_SISTEMA_ALVO/ambiente_p2/env.p2`. Ali estão só valores fictícios: `DEBUG=1`, provedor de e-mail `fake`, envio de e-mail desligado e banco `saborino_p2`.
Nenhum segredo real é versionado.

## 8. Banco e dados

- Banco de teste: `saborino_p2`, em PostgreSQL local. A suíte automatizada cria e destrói o próprio `test_saborino_p2`.
- A massa de dados fictícia está em `01_SISTEMA_ALVO/ambiente_p2/seed_ficticio.py`. Ela é **idempotente**: apaga os dados operacionais e recria sempre o mesmo estado, com 3 clientes, 3 produtos, 2 vendas, 2 recebíveis, 1 pagamento parcial, 1 compra e 1 registro de produção, todos em setembro de 2026.
- Para restaurar o ambiente entre execuções, rode `p2_seed` de novo (seção 9.1, item 6).

## 9. Execução

Forma A, Docker (a partir de `01_SISTEMA_ALVO/saborino`):

```bash
docker compose -p p2tqs-saborino -f docker-compose.yml up -d db redis
docker compose -p p2tqs-saborino -f docker-compose.yml run --rm api python manage.py migrate --noinput
docker compose -p p2tqs-saborino -f docker-compose.yml run --rm -v "$PWD/../ambiente_p2:/p2:ro" api python /p2/seed_ficticio.py
docker compose -p p2tqs-saborino -f docker-compose.yml up -d api frontend   # API em :8000, frontend em :5173
bash ../ambiente_p2/smoke_api.sh http://localhost:8000/api/v1                # smoke da API
# encerrar (nunca com -v; o volume guarda só dados fictícios, e o seed o restaura):
docker compose -p p2tqs-saborino -f docker-compose.yml down
```

Os serviços `celery` e `dashboard` (Flower) não são iniciados, porque o envio de e-mail está fora do escopo (seção 14).

Forma B, Linux sem Docker:

```bash
source 01_SISTEMA_ALVO/ambiente_p2/p2_linux.sh
p2_pg_start && p2_migrate && p2_seed
p2_serve                         # API em http://127.0.0.1:8010/api/v1
# frontend (outro terminal):
cd 01_SISTEMA_ALVO/saborino/ui && npm ci && VITE_API_URL=http://localhost:8010/api/v1 npm run dev   # http://localhost:5173
# encerrar:
p2_serve_stop && p2_pg_stop
```


## 10. Execução dos testes

| Nível | Comando | Estado |
|---|---|---|
| Suíte existente do backend | `p2_manage test` | Executada em 24/09/2026: 69 testes, OK |
| Suíte existente do frontend | `cd saborino/ui && npx vitest run` | Executada em 24/09/2026: 1 teste, OK |
| Unitários do grupo (pytest) | a definir, pasta 07 | Fase 5 |
| Integração/API (Postman + Newman) | a definir, pasta 08 | Fase 6 |
| Sistema/interface (Selenium) | a definir, pasta 09 | Fase 6 |

## 11. Acesso ao pipeline

GitHub Actions: **[a configurar na Fase 9]**.

## 12. Localização dos documentos

| Pasta | Conteúdo |
|---|---|
| 00_IDENTIFICACAO_E_README | Este README, a Ficha do Apêndice A (P01) e o resumo de andamento |
| 01_SISTEMA_ALVO | Código do Saborino, o ambiente P2 (`ambiente_p2/`) e as evidências de que o ambiente sobe |
| 02 a 16 | Seguem a seção 11.3 do manual e são preenchidas conforme cada marco |

## 13. Credenciais fictícias

| Uso | Usuário | Senha |
|---|---|---|
| Login no sistema (teste) | `tester@saborino.test` | `SenhaFicticia-P2-2026` |
| PostgreSQL local | `postgres` | `postgres` |

## 14. Problemas conhecidos

- O Celery e o Redis não sobem no ambiente de teste. Por isso, os fluxos de e-mail (verificação, recuperação e troca de e-mail) ficam **fora do escopo**.
- A pasta `Documentos` do Mac está sincronizada com o iCloud. Arquivos que ficam só na nuvem precisam ser baixados antes de rodar. Recomenda-se não instalar `node_modules` nem venv dentro dela.
- Os arquivos de implantação e operação de ambientes reais foram retirados da cópia e ficam fora do escopo dos testes.
- **Docker no Mac, erro `docker-credential-desktop: executable file not found`:** o link `/usr/local/bin/docker-credential-desktop` pode apontar para `/Volumes/Docker/...`, que é a imagem de instalação e deixa de existir depois que ela é desmontada. Solução sem mexer no sistema: `export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"` antes dos comandos `docker compose`.
- **Smoke test no macOS:** o `bash` padrão é o 3.2. O `smoke_api.sh` foi escrito para funcionar nele. Ao adaptar o script, não coloque aspas escapadas dentro de `$(...)`, porque isso corrompe o JSON enviado.
- A forma A usa PostgreSQL 15.19 (imagem `postgres:15-alpine`), e a forma B usa o 15.18 embarcado. As duas são da mesma versão principal.
- As migrações `accounts.0003_seed_socios` e `cadastros.0002_seed_inicial` fazem parte do código original e criam sócios e contas padrão. O seed fictício substitui as contas e os canais, mas os três sócios padrão continuam no banco.

## 15. Contato do grupo

Leonardo Valentim: [e-mail institucional a preencher]. Natasha Teixeira: [a preencher]. Udymilla Chagas: [a preencher].
