#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PROJECT_DIR=$(cd -- "${SCRIPT_DIR}/.." && pwd)
ENABLE_BACKUP=${ENABLE_BACKUP:-0}

if [[ "$(id -u)" -ne 0 ]]; then
  exec sudo --preserve-env=ENABLE_BACKUP "${BASH_SOURCE[0]}" "$@"
fi

command -v systemctl >/dev/null 2>&1 || {
  echo "systemctl no está disponible. Activa systemd en /etc/wsl.conf y ejecuta wsl.exe --shutdown." >&2
  exit 2
}
systemctl is-system-running >/dev/null 2>&1 || {
  echo "systemd no está en ejecución en esta sesión WSL." >&2
  exit 2
}
command -v docker >/dev/null 2>&1 || {
  echo "Docker Engine no está instalado o no está en PATH." >&2
  exit 2
}
docker compose version >/dev/null 2>&1 || {
  echo "Falta el plugin Docker Compose v2." >&2
  exit 2
}

install_unit() {
  local source_file=$1
  local unit_name=$2
  local escaped_dir
  escaped_dir=$(printf '%s' "${PROJECT_DIR}" | sed 's/[&|]/\\&/g')
  sed "s|@APP_DIR@|${escaped_dir}|g" "${source_file}" > "/etc/systemd/system/${unit_name}"
  chmod 0644 "/etc/systemd/system/${unit_name}"
}

install_unit "${SCRIPT_DIR}/reto4v-compose.service" reto4v-compose.service
if [[ "${ENABLE_BACKUP}" == "1" ]]; then
  install_unit "${SCRIPT_DIR}/reto4v-backup.service" reto4v-backup.service
  install_unit "${SCRIPT_DIR}/reto4v-backup.timer" reto4v-backup.timer
fi

systemctl daemon-reload
systemctl enable --now reto4v-compose.service
if [[ "${ENABLE_BACKUP}" == "1" ]]; then
  systemctl enable --now reto4v-backup.timer
fi

echo "Servicio instalado: systemctl status reto4v-compose.service"
if [[ "${ENABLE_BACKUP}" == "1" ]]; then
  echo "Backup programado: systemctl list-timers reto4v-backup.timer"
fi
