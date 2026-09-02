#!/usr/bin/env bash
set -Eeuo pipefail

umask 077
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PROJECT_DIR=$(cd -- "${SCRIPT_DIR}/.." && pwd)
cd "${PROJECT_DIR}"

if [[ ! -f .env ]]; then
  echo "Falta ${PROJECT_DIR}/.env. Ejecuta scripts/install.sh." >&2
  exit 2
fi

BACKUP_ROOT=${BACKUP_DIR:-"${PROJECT_DIR}/backups"}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
TMP_DIR="${BACKUP_ROOT}/.reto4v-${STAMP}.tmp"
FINAL_DIR="${BACKUP_ROOT}/${STAMP}"
mkdir -p "${BACKUP_ROOT}"
if [[ -e "${TMP_DIR}" || -e "${FINAL_DIR}" ]]; then
  echo "Ya existe un backup con la marca ${STAMP}; reintenta." >&2
  exit 2
fi
mkdir "${TMP_DIR}"

compose=(docker compose --project-directory "${PROJECT_DIR}" --env-file "${PROJECT_DIR}/.env")

echo "Iniciando los servicios necesarios para el backup…"
"${compose[@]}" up -d db web >/dev/null

echo "Guardando PostgreSQL…"
"${compose[@]}" exec -T db sh -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" exec pg_dump --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --format=custom --no-owner --no-privileges' \
  | gzip -9 > "${TMP_DIR}/postgres.dump.gz"

echo "Guardando media local…"
"${compose[@]}" exec -T web sh -c 'tar -czf - -C /app/media .' > "${TMP_DIR}/media.tar.gz"

{
  echo "Programmy4V backup"
  echo "created_at_utc=${STAMP}"
  echo "project_dir=${PROJECT_DIR}"
  echo "compose_project=${COMPOSE_PROJECT_NAME:-reto4v}"
  echo "media_archive=media.tar.gz"
  echo "database_archive=postgres.dump.gz"
} > "${TMP_DIR}/manifest.txt"

(cd "${TMP_DIR}" && sha256sum postgres.dump.gz media.tar.gz manifest.txt) > "${TMP_DIR}/SHA256SUMS"
mv -- "${TMP_DIR}" "${FINAL_DIR}"
chmod 0700 "${FINAL_DIR}"

echo "Backup completo: ${FINAL_DIR}"
  echo "Comprueba SHA256SUMS y cifra/copia esta carpeta a una ubicación protegida del centro."
