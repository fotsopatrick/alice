#!/bin/sh
# Entrypoint de la Tour (edition Community) pour Cloud Run / ACI / compose.
# L'image officielle Odoo lit HOST / PORT / USER / PASSWORD / DATABASE ; on les
# alimente ici. db_host accepte soit un nom TCP (localhost), soit un chemin de
# socket Cloud SQL (/cloudsql/<connexion>).
set -u

echo "[boot] $(date -Is) — entrypoint, DB_NAME=${DB_NAME:-} HOST=${ODOO_DB_HOST:-} USER=${ODOO_DB_USER:-}"

: "${DB_NAME:=tour_community}"
: "${ODOO_DB_HOST:=localhost}"
: "${ODOO_DB_PORT:=5432}"
: "${ODOO_DB_USER:=odoo}"
: "${ODOO_DB_PASSWORD:=odoo}"
: "${ODOO_ADMIN_PASSWD:=change-me}"

export HOST="$ODOO_DB_HOST"
export PORT="$ODOO_DB_PORT"
export USER="$ODOO_DB_USER"
export PASSWORD="$ODOO_DB_PASSWORD"
export DATABASE="$DB_NAME"

# Attend le PostgreSQL (ACI sidecar / Cloud SQL) avant de creer la base.
if [ "${HOST#/}" = "$HOST" ]; then
  i=0
  while ! pg_isready -h "$HOST" -p "$PORT" -U "$USER" -q 2>/dev/null; do
    i=$((i + 2))
    [ "$i" -ge 180 ] && break
    sleep 2
  done
  echo "[boot] $(date -Is) — postgres prêt après ~${i}s"
fi

# Fichiers construits par Chloe : /tmp est le seul repertoire inscriptible
# sur Cloud Run. On le rend parametrable.
export TOUR_APPS_DIR="${TOUR_APPS_DIR:-/var/lib/odoo/community-apps}"
if [ "${TOUR_APPS_DIR}" != "/var/lib/odoo/community-apps" ]; then
  mkdir -p "$TOUR_APPS_DIR"
fi

# Cree la base au premier demarrage (best effort, idempotent).
if [ "${CREATE_DB:-1}" = "1" ]; then
  if [ "${HOST#/}" != "$HOST" ]; then
    # socket Cloud SQL : on cible la base 'postgres' du meme cluster
    PGPASSWORD="$PASSWORD" psql -h "$HOST" -U "$USER" -d postgres \
      -tc "SELECT 1 FROM pg_database WHERE datname='$DATABASE'" | grep -q 1 || \
      PGPASSWORD="$PASSWORD" psql -h "$HOST" -U "$USER" -d postgres -c \
      "CREATE DATABASE \"$DATABASE\";" || true
  else
    PGPASSWORD="$PASSWORD" psql -h "$HOST" -p "$PORT" -U "$USER" -d postgres \
      -tc "SELECT 1 FROM pg_database WHERE datname='$DATABASE'" | grep -q 1 || \
      PGPASSWORD="$PASSWORD" createdb -h "$HOST" -p "$PORT" -U "$USER" "$DATABASE" || true
  fi
fi
echo "[boot] $(date -Is) — base OK (ou créée), lancement d'odoo…"

# On garde la main en cas d'echec (diagnostic ACI : logs visibles, exec possible).
set +e
odoo --http-interface 0.0.0.0 --http-port 8069 \
  -w "$ODOO_ADMIN_PASSWD" \
  --db-filter "^$DATABASE$" 2>&1
RC=$?
echo "[boot] $(date -Is) — odoo EXITED rc=$RC (maintenu allumé pour diagnostic)"
sleep 86400