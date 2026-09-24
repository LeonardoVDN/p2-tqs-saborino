#!/usr/bin/env bash
# Ambiente de teste do P2 em Linux SEM Docker (usado nas execuções automatizadas).
# PostgreSQL 15 embarcado (pacote npm @embedded-postgres) + Python 3.12 (uv).
# Uso: source p2_linux.sh && p2_pg_start && p2_migrate && p2_seed ... && p2_pg_stop
set -a; source "$(dirname "${BASH_SOURCE[0]}")/env.p2"; set +a
P2_AMB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
P2_BACKEND="$P2_AMB/../saborino/backend"
P2_HOME="${P2_HOME:-$HOME/.p2_saborino}"
P2_PY="${P2_PY:-$P2_HOME/venv/bin/python}"
PG_BIN="$P2_HOME/pg/node_modules/@embedded-postgres/linux-arm64/native"
[ "$(uname -m)" = "x86_64" ] && PG_BIN="$P2_HOME/pg/node_modules/@embedded-postgres/linux-x64/native"
export LD_LIBRARY_PATH="$PG_BIN/lib:${LD_LIBRARY_PATH:-}"

p2_install() {
  mkdir -p "$P2_HOME/pg"
  command -v uv >/dev/null || pip3 install --user -q uv
  export PATH="$HOME/.local/bin:$PATH"
  [ -x "$P2_PY" ] || { uv python install 3.12 && uv venv -q -p 3.12 "$P2_HOME/venv"; }
  VIRTUAL_ENV="$P2_HOME/venv" uv pip install -q -r "$P2_BACKEND/requirements.txt"
  VIRTUAL_ENV="$P2_HOME/venv" uv pip install -q -r "$P2_AMB/requirements-testes.txt"
  local pkg=linux-arm64; [ "$(uname -m)" = "x86_64" ] && pkg=linux-x64
  [ -x "$PG_BIN/bin/postgres" ] || (cd "$P2_HOME/pg" && npm install -s --no-audit --no-fund "@embedded-postgres/$pkg@15.18.0-beta.17")
}
p2_pg_start() {
  if [ ! -d "$P2_HOME/pgdata" ]; then
    echo "$POSTGRES_PASSWORD" > "$P2_HOME/pw"
    "$PG_BIN/bin/initdb" -D "$P2_HOME/pgdata" -U "$POSTGRES_USER" --pwfile="$P2_HOME/pw" -A md5 -E UTF8 >/dev/null
  fi
  "$PG_BIN/bin/pg_ctl" -D "$P2_HOME/pgdata" -o "-p $POSTGRES_PORT -k /tmp" -l "$P2_HOME/pg.log" -w start >/dev/null
  "$P2_PY" - <<PY
import psycopg2
c = psycopg2.connect(host='127.0.0.1', user='$POSTGRES_USER', password='$POSTGRES_PASSWORD', dbname='postgres'); c.autocommit = True
cur = c.cursor(); cur.execute("select 1 from pg_database where datname='$POSTGRES_DB'")
if not cur.fetchone(): cur.execute('CREATE DATABASE $POSTGRES_DB')
PY
}
p2_pg_stop() { "$PG_BIN/bin/pg_ctl" -D "$P2_HOME/pgdata" -m fast stop >/dev/null; }
p2_manage() { (cd "$P2_BACKEND" && "$P2_PY" manage.py "$@"); }
p2_migrate() { p2_manage migrate --noinput; }
p2_seed() { (cd "$P2_BACKEND" && "$P2_PY" "$P2_AMB/seed_ficticio.py"); }
p2_serve() { (cd "$P2_BACKEND" && nohup "$P2_PY" manage.py runserver 127.0.0.1:8010 --noreload > "$P2_HOME/api.log" 2>&1 & echo $! > "$P2_HOME/api.pid"); sleep 4; }
p2_serve_stop() { [ -f "$P2_HOME/api.pid" ] && kill "$(cat "$P2_HOME/api.pid")" 2>/dev/null; rm -f "$P2_HOME/api.pid"; }
