#!/bin/sh
set -eu

cd /app

# Compose's database healthcheck is the first gate.  A short retry here also
# covers a systemd restart where the web container is recreated at the same
# time as PostgreSQL.
if [ "${WAIT_FOR_DATABASE:-1}" = "1" ] && [ -n "${DB_NAME:-}" ]; then
  attempt=1
  while [ "$attempt" -le "${DB_WAIT_RETRIES:-30}" ]; do
    if python manage.py check --database default >/dev/null 2>&1; then
      break
    fi
    if [ "$attempt" -eq "${DB_WAIT_RETRIES:-30}" ]; then
      echo "La base de datos no estuvo disponible a tiempo" >&2
      exit 1
    fi
    attempt=$((attempt + 1))
    sleep 2
  done
fi

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  python manage.py migrate --noinput
fi

if [ "${RUN_COLLECTSTATIC:-1}" = "1" ]; then
  python manage.py collectstatic --noinput --clear
fi

exec "$@"
