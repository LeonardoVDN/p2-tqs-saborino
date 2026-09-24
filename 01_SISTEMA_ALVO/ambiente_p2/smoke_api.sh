#!/usr/bin/env bash
# Smoke test da API do Saborino no ambiente P2 (TQS 2026). Só leituras e um cadastro fictício.
# Uso: bash smoke_api.sh [URL_BASE]   (padrão: http://localhost:8000/api/v1, forma A com Docker)
# Na forma B (Linux sem Docker), use http://127.0.0.1:8010/api/v1. Requer curl e python3.
# Compatível com o bash 3.2 do macOS: nada de aspas escapadas dentro de $(...).
set -u
BASE="${1:-http://localhost:8000/api/v1}"
JAR="$(mktemp)"; BODY_FILE="$(mktemp)"; trap 'rm -f "$JAR" "$BODY_FILE"' EXIT
EMAIL='tester@saborino.test'; SENHA='SenhaFicticia-P2-2026'
LOGIN_ERRADO="$(printf '{"email":"%s","password":"%s"}' "$EMAIL" 'senha-errada')"
LOGIN_VALIDO="$(printf '{"email":"%s","password":"%s"}' "$EMAIL" "$SENHA")"
CLIENTE_VALIDO='{"nome":"Cliente Fictício Smoke"}'
CLIENTE_VAZIO='{"nome":""}'

csrf() { awk '$6 ~ /csrf/ {v=$7} END {print v}' "$JAR"; }

# passo RÓTULO MÉTODO CAMINHO [JSON] [corpo|itens]: faz a requisição e imprime uma linha de resultado
passo() {
  local rotulo="$1" metodo="$2" caminho="$3" dados="${4:-}" extra="${5:-}" codigo detalhe=''
  if [ -n "$dados" ]; then
    codigo="$(curl -s -o "$BODY_FILE" -w '%{http_code}' -b "$JAR" -c "$JAR" -X "$metodo" \
      -H 'Content-Type: application/json' -H "X-CSRFToken: $(csrf)" --data "$dados" "$BASE$caminho")"
  else
    codigo="$(curl -s -o "$BODY_FILE" -w '%{http_code}' -b "$JAR" -c "$JAR" -X "$metodo" "$BASE$caminho")"
  fi
  case "$extra" in
    corpo) detalhe=" $(head -c 160 "$BODY_FILE")" ;;
    itens) detalhe=" itens: $(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(len(d["results"]) if isinstance(d, dict) and "results" in d else len(d) if isinstance(d, list) else "?")' "$BODY_FILE")" ;;
  esac
  echo "$rotulo -> $codigo$detalhe"
}

echo "# Smoke test da API do Saborino no ambiente P2 — $(date -Iseconds) — $BASE"
passo 'GET /auth/csrf/'                     GET  /auth/csrf/
passo 'POST /auth/sessions/ (senha errada)' POST /auth/sessions/ "$LOGIN_ERRADO"
passo 'POST /auth/sessions/ (válida)'       POST /auth/sessions/ "$LOGIN_VALIDO"
passo 'GET /me/'                            GET  /me/ '' corpo
passo 'GET /clientes/'                      GET  /clientes/ '' itens
passo 'POST /clientes/ válido'              POST /clientes/ "$CLIENTE_VALIDO"
passo 'POST /clientes/ nome vazio'          POST /clientes/ "$CLIENTE_VAZIO" corpo
passo 'GET /relatorios/dashboard/'          GET  /relatorios/dashboard/
: > "$JAR"
passo 'GET /clientes/ sem login'            GET  /clientes/
