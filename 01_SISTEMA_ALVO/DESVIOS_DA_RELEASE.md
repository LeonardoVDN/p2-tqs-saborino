# Desvios da cópia testada em relação à release `a63a24f`

A cópia em `saborino/` foi tirada da release `a63a24f` em 24/09/2026. Antes da publicação do repositório,
o grupo a anonimizou para expor só o código, sem nenhuma informação sobre o uso real do sistema.
Nenhuma regra de negócio, validação ou cálculo foi alterada. A tabela abaixo lista tudo o que mudou.

| Onde | O que mudou | Efeito no comportamento |
|---|---|---|
| `deploy/`, `docs/`, `compose.yaml`, os `.env` de exemplo de produção, `backend/Dockerfile.prod`, `backend/Dockerfile.lock`, `backend/docker/`, `ui/Dockerfile.prod`, `ui/nginx.spa.conf` | Removidos. São arquivos de implantação, operação e planejamento de ambientes reais. | Nenhum na aplicação. O ambiente de desenvolvimento (`docker-compose.yml` e os `Dockerfile` de desenvolvimento) continua igual. |
| `README.md` do sistema | Trocado por um README curto de desenvolvimento. | Nenhum. |
| `.gitignore` do sistema | Removido o bloco de segredos e certificados de produção. | Nenhum. |
| `backend/cadastros/migrations/0002_seed_inicial.py` | Canais padrão viraram "Canal A", "Canal B" (com dízimo) e "Canal C". Contas padrão viraram "Conta Corrente", "Caixa", "Cartão de Crédito" e "Cartão de Terceiro". | Só os nomes dos cadastros iniciais. A regra de dízimo continua no Canal B. |
| `backend/cadastros/models.py`, `backend/cadastros/migrations/0001_initial.py` | Textos de ajuda e docstrings com os novos nomes. | Nenhum. |
| `backend/accounts/migrations/0003_seed_socios.py`, `backend/accounts/models.py` | Sócios padrão viraram "Nós", "Sócio 1" e "Sócio 2". | Só os nomes dos cadastros iniciais. |
| `backend/operacao/models.py`, `backend/operacao/migrations/0001_initial.py`, `ui/src/views/FechamentoView.vue`, `backend/operacao/management/commands/importar_saborino.py` | Valores do enum `SocioDestino` viraram `NOS`, `S1` e `S2`, com os rótulos correspondentes. As expressões reconhecidas pelo importador de planilha foram atualizadas. | O comportamento é o mesmo; mudaram só os códigos e rótulos. |
| `backend/operacao/tests.py`, `backend/accounts/tests.py` | Canal, cliente e usuário de teste receberam nomes neutros. | Nenhum. Os 69 testes continuam passando. |
| `backend/core/settings.py` | Remetente e resposta padrão de e-mail passaram a usar `example.com`. | Nenhum no ambiente de teste (o envio de e-mail está desligado). |

Evidência da revalidação: `evidencias_ambiente/2026-09-24_docker_validacao_codigo_anonimizado.txt`
(`makemigrations --check` sem mudanças, 69 testes OK, migrate e seed num banco novo, smoke da API, Vitest e build do frontend).
