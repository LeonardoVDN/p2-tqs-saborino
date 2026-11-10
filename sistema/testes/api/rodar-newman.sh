#!/usr/bin/env bash
# Roda a coleção com o Newman: restaura os dados fictícios, executa e restaura de novo.
# Uso: bash rodar-newman.sh [pasta-de-saida]   (precisa do sistema no ar e do Newman instalado)
set -u
AQUI="$(cd "$(dirname "$0")" && pwd)"
SAIDA="${1:-$AQUI/resultado}"; mkdir -p "$SAIDA"
NEWMAN="${NEWMAN:-newman}"
DIA="$(date +%Y-%m-%d)"
seed() { docker exec p2tqs-saborino-api-1 python /p2/seed.py > /dev/null; }
seed
"$NEWMAN" run "$AQUI/saborino-api.postman_collection.json" -e "$AQUI/saborino-local.postman_environment.json" \
  --reporters cli,junit,htmlextra --reporter-junit-export "$SAIDA/$DIA-newman.xml" \
  --reporter-htmlextra-export "$SAIDA/$DIA-newman.html" --reporter-htmlextra-title "Saborino · Testes de API" --color off
CODIGO=$?
seed
exit $CODIGO
