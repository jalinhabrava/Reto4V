#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat >&2 <<'EOF'
Uso: RESTORE_CONFIRM=YES scripts/restore.sh <postgres.dump.gz|postgres.dump> [media.tar.gz]

La restauración detiene el servicio web y reemplaza los datos del destino.
Es destructiva para la base de datos actual; exporta un backup nuevo antes.
EOF
}

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage
  exit 2
fi
if [[ "${RESTORE_CONFIRM:-}" != "YES" ]]; then
  echo "Esta operación reemplaza datos. Repite con RESTORE_CONFIRM=YES." >&2
  exit 2
fi

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PROJECT_DIR=$(cd -- "${SCRIPT_DIR}/.." && pwd)
cd "${PROJECT_DIR}"
[[ -f .env ]] || { echo "Falta ${PROJECT_DIR}/.env." >&2; exit 2; }

env_value() {
  local key=$1 value
  value=$(awk -v wanted="$key" '
    $0 ~ "^[[:space:]]*" wanted "[[:space:]]*=" {
      sub(/^[^=]*=/, "", $0); sub(/\r$/, ""); print; exit
    }
  ' .env)
  value=$(printf '%s\n' "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
  printf '%s' "$value"
}

dump_file=$(realpath -- "$1")
[[ -f "${dump_file}" ]] || { echo "No existe el dump: ${dump_file}" >&2; exit 2; }
media_file=""
if [[ $# -eq 2 ]]; then
  media_file=$(realpath -- "$2")
  [[ -f "${media_file}" ]] || { echo "No existe el archivo media: ${media_file}" >&2; exit 2; }
fi

compose=(docker compose --project-directory "${PROJECT_DIR}" --env-file "${PROJECT_DIR}/.env")
compose_profile=()
if [[ "$(env_value COMPOSE_PROFILES)" == *proxy* ]] || {
  [[ "$(env_value APP_PORT)" == "8000" ]] && [[ -n "$(env_value CADDY_HTTP_PORT)" ]]
}; then
  compose_profile+=(--profile proxy)
fi
echo "Deteniendo web y proxy…"
"${compose[@]}" "${compose_profile[@]}" stop web caddy >/dev/null 2>&1 || true
"${compose[@]}" up -d db >/dev/null

echo "Restaurando PostgreSQL desde ${dump_file}…"
if [[ "${dump_file}" == *.gz ]]; then
  gzip -cd -- "${dump_file}"
else
  cat -- "${dump_file}"
fi | "${compose[@]}" exec -T db sh -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" exec pg_restore --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges'

if [[ -n "${media_file}" ]]; then
  echo "Restaurando media local…"
  "${compose[@]}" run --rm --no-deps -T --entrypoint /bin/sh web \
    -c 'tar -xzf - -C /app/media' < "${media_file}"
fi

echo "Arrancando web…"
"${compose[@]}" up -d web >/dev/null
if ((${#compose_profile[@]})); then
  echo "Arrancando proxy…"
  "${compose[@]}" "${compose_profile[@]}" up -d caddy >/dev/null
fi
echo "Restauración terminada. Comprueba la aplicación y conserva el backup anterior hasta validar el resultado."
