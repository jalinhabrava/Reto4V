#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PROJECT_DIR=$(cd -- "${SCRIPT_DIR}/.." && pwd)
cd "${PROJECT_DIR}"

[[ -f "${PROJECT_DIR}/.env" ]] || {
  echo "No existe ${PROJECT_DIR}/.env. Ejecuta bash scripts/install.sh primero." >&2
  exit 2
}

env_value() {
  local key=$1 value
  value=$(awk -v wanted="$key" '
    $0 ~ "^[[:space:]]*" wanted "[[:space:]]*=" {
      sub(/^[^=]*=/, "", $0); sub(/\r$/, ""); print; exit
    }
  ' .env 2>/dev/null || true)
  value=$(printf '%s\n' "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
  printf '%s' "$value"
}

port=$(env_value APP_PORT)
[[ -n "$port" ]] || port=8080
path=$(env_value HEALTHCHECK_PATH)
[[ -n "$path" ]] || path=/health/
url=$(env_value APP_URL)
[[ -n "$url" ]] || url="http://127.0.0.1:${port}${path}"

if command -v curl >/dev/null 2>&1; then
  curl_args=(--fail --silent --show-error --location --max-time 10)
  if [[ "$url" == https://* ]]; then
    curl_args+=(--insecure)
  fi
  curl "${curl_args[@]}" "$url" >/dev/null
elif command -v wget >/dev/null 2>&1; then
  wget_args=(--quiet --output-document=/dev/null --timeout=10)
  if [[ "$url" == https://* ]]; then
    wget_args+=(--no-check-certificate)
  fi
  wget "${wget_args[@]}" "$url"
else
  echo "Instala curl o wget para comprobar $url." >&2
  exit 2
fi

echo "Programmy4V responde en $url"
docker compose --project-directory "${PROJECT_DIR}" --env-file "${PROJECT_DIR}/.env" ps
