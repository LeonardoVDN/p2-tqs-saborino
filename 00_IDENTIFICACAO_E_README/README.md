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

- **A. Com Docker (forma original do sistema):** Docker Desktop e Git.
- **B. Sem Docker (forma usada nas execuções automatizadas do grupo):** Linux ou macOS, Python 3.12, PostgreSQL 15, Node 22+ e Git. No Linux, o script `01_SISTEMA_ALVO/ambiente_p2/p2_linux.sh` instala sozinho o Python 3.12 (via `uv`) e um PostgreSQL 15 embarcado (via npm).

## 6. Instalação

Forma B, Linux (a mesma usada nas evidências):

```bash
cd 01_SISTEMA_ALVO/ambiente_p2
source p2_linux.sh
p2_install        # Python 3.12 + dependências + PostgreSQL 15 embarcado (em ~/.p2_saborino)
```

Forma A, Docker (macOS com Docker Desktop; ainda não executada pelo grupo):

```bash
cd 01_SISTEMA_ALVO/saborino
cp ../ambiente_p2/env.p2 backend/.env
# no backend/.env: POSTGRES_HOST=db e CELERY_BROKER_URL=redis://redis:6379/0
docker compose -f docker-compose.yml up --build
```

## 7. Configuração

Todas as variáveis ficam em `01_SISTEMA_ALVO/ambiente_p2/env.p2`. Ali estão só valores fictícios: `DEBUG=1`, provedor de e-mail `fake`, envio de e-mail desligado e banco `saborino_p2`.
Nenhum segredo real é versionado.

## 8. Banco e dados

- Banco de teste: `saborino_p2`, em PostgreSQL local. A suíte automatizada cria e destrói o próprio `test_saborino_p2`.
- A massa de dados fictícia está em `01_SISTEMA_ALVO/ambiente_p2/seed_ficticio.py`. Ela é **idempotente**: apaga os dados operacionais e recria sempre o mesmo estado, com 3 clientes, 3 produtos, 2 vendas, 2 recebíveis, 1 pagamento parcial, 1 compra e 1 registro de produção, todos em setembro de 2026.
- Para restaurar o ambiente entre execuções, rode `p2_seed` de novo (seção 9.1, item 6).

## 9. Execução

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

## 15. Contato do grupo

Leonardo Valentim: [e-mail institucional a preencher]. Natasha Teixeira: [a preencher]. Udymilla Chagas: [a preencher].
