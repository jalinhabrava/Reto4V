#!/usr/bin/env bash
# Instala o actualiza una instancia Reto4V en Docker Compose.
#
# El script no instala paquetes del sistema, no necesita sudo y nunca muestra
# el contenido de .env. Es deliberadamente apto para repetirlo después de un
# reinicio o una actualización del código.
set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(cd -- "$SCRIPT_DIR/.." && pwd)
ENV_FILE="$PROJECT_DIR/.env"

HOST=""
PORT=""
USE_PROXY=0
USE_TLS=0
PROXY_EXPLICIT=0
TLS_EXPLICIT=0
NO_BUILD=0
SKIP_ADMIN=0
SEED_BASH=0
SEED_OWNER=""
SEED_COHORT="2ASIR"

usage() {
  cat <<'EOF'
Uso:
  bash scripts/install.sh [opciones]

Opciones:
  --host HOST       IP o nombre DNS usado por el alumnado.
  --port PORT       Puerto publicado en el host (por defecto: 8080).
  --proxy           Publica Caddy en lugar de exponer web directamente.
  --tls             Usa Caddyfile.internal-tls con TLS interno (implica --proxy).
  --direct          Vuelve explícitamente al modo web directo HTTP.
  --seed-bash       Carga la ruta de retos Bash de demostración, si está disponible.
  --owner USERNAME  Usuario propietario de los retos Bash (requiere --seed-bash).
  --cohort NAME     Grupo de los retos Bash (por defecto: 2ASIR).
  --no-build        No reconstruye la imagen; usa la imagen local existente.
  --skip-admin      No abre createsuperuser (útil en automatizaciones).
  -h, --help        Muestra esta ayuda.

Ejemplos:
  bash scripts/install.sh --host 192.168.20.10 --port 8080
  bash scripts/install.sh --host reto4v.instituto.lan --port 8443 --tls
  bash scripts/install.sh --seed-bash --owner profesor
EOF
}

die() {
  echo "Error: $*" >&2
  exit 2
}

is_uint() {
  [[ "$1" =~ ^[0-9]+$ ]] && (( 10#$1 >= 1 && 10#$1 <= 65535 ))
}

is_host() {
  # Deliberadamente no acepta esquema, puerto, barra ni comodines. Django y
  # el proxy reciben un host sin ambigüedad; IPv6 se configura manualmente en
  # .env porque exige corchetes distintos en cada URL.
  [[ "$1" =~ ^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$ ]] || return 1
  [[ "$1" != *..* ]]
}

is_loopback_host() {
  [[ "$1" == "localhost" || "$1" == "127.0.0.1" ]]
}

is_identifier() {
  [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]]
}

random_hex() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 32
  elif command -v python3 >/dev/null 2>&1; then
    python3 -c 'import secrets; print(secrets.token_hex(32))'
  else
    die "Necesito openssl o python3 para generar secretos de .env."
  fi
}

env_line() {
  local key=$1
  [[ -f "$ENV_FILE" ]] || return 1
  awk -v wanted="$key" '
    $0 ~ "^[[:space:]]*" wanted "[[:space:]]*=" {
      sub(/^[^=]*=/, "", $0); sub(/\r$/, "", $0); print; exit
    }
  ' "$ENV_FILE"
}

env_value() {
  local key=$1
  local value
  value=$(env_line "$key" || true)
  # Compose env files use unquoted simple values here. Trim only surrounding
  # whitespace, never shell-evaluate the result.
  value=$(printf '%s\n' "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
  printf '%s' "$value"
}

set_env_key() {
  local key=$1
  local value=$2
  local tmp
  [[ -f "$ENV_FILE" ]] || die "No existe $ENV_FILE para actualizarlo."
  [[ "$value" != *$'\n'* && "$value" != *$'\r'* ]] || die "Valor inválido para $key."
  tmp=$(mktemp "$ENV_FILE.tmp.XXXXXX")
  chmod 600 "$tmp"
  awk -v wanted="$key" -v replacement="$value" '
    BEGIN { replaced = 0 }
    {
      sub(/\r$/, "")
      if ($0 ~ "^[[:space:]]*" wanted "[[:space:]]*=" && replaced == 0) {
        print wanted "=" replacement
        replaced = 1
      } else {
        print
      }
    }
    END {
      if (replaced == 0) print wanted "=" replacement
    }
  ' "$ENV_FILE" > "$tmp"
  chmod 600 "$tmp"
  mv -f -- "$tmp" "$ENV_FILE"
}

ensure_env() {
  if [[ ! -e "$ENV_FILE" ]]; then
    [[ -f "$PROJECT_DIR/.env.example" ]] || die "Falta .env.example."
    (umask 077 && cp -- "$PROJECT_DIR/.env.example" "$ENV_FILE")
    echo "Creado .env con permisos privados."
  elif [[ ! -f "$ENV_FILE" ]]; then
    die "$ENV_FILE existe pero no es un archivo regular."
  else
    chmod 600 "$ENV_FILE"
    echo "Se conserva la configuración existente en .env."
  fi

  local password secret
  password=$(env_value POSTGRES_PASSWORD)
  if [[ -z "$password" || "$password" == CHANGE_ME* ]]; then
    password=$(random_hex)
    set_env_key POSTGRES_PASSWORD "$password"
  fi
  secret=$(env_value DJANGO_SECRET_KEY)
  if [[ -z "$secret" || "$secret" == CHANGE_ME* ]]; then
    secret=$(random_hex)
    set_env_key DJANGO_SECRET_KEY "$secret"
  fi

  unset password secret
}

compose_base() {
  printf 'docker compose --project-directory %q --env-file %q' "$PROJECT_DIR" "$ENV_FILE"
}

compose_run() {
  local -a command=(docker compose --project-directory "$PROJECT_DIR" --env-file "$ENV_FILE")
  if (( USE_PROXY )); then
    command+=(--profile proxy)
  fi
  "${command[@]}" "$@"
}

configure_requested_values() {
  local current_port current_host scheme bind_ip csrf_origin
  current_port=$(env_value APP_PORT)
  [[ -n "$current_port" ]] || current_port=8080
  if [[ -n "$PORT" ]]; then
    current_port=$PORT
  fi
  is_uint "$current_port" || die "APP_PORT no es un puerto válido: $current_port"

  if [[ -n "$HOST" ]]; then
    is_host "$HOST" || die "--host debe ser una IP o nombre DNS sin esquema ni puerto: $HOST"
    if is_loopback_host "$HOST"; then
      bind_ip=127.0.0.1
    else
      bind_ip=0.0.0.0
    fi
    set_env_key DJANGO_ALLOWED_HOSTS "$HOST,localhost,127.0.0.1"
    set_env_key APP_BIND_IP "$bind_ip"
    if (( ! USE_PROXY )); then
      scheme=http
      if (( USE_TLS )); then scheme=https; fi
      csrf_origin="$scheme://$HOST:$current_port"
      set_env_key DJANGO_CSRF_TRUSTED_ORIGINS "$csrf_origin"
      set_env_key APP_URL "$csrf_origin/health/"
    fi
  fi

  if (( USE_PROXY )); then
    # web queda accesible solo dentro de WSL; Caddy es la única entrada LAN.
    if [[ -z "$PORT" ]]; then
      current_port=$(env_value CADDY_HTTP_PORT)
      [[ -n "$current_port" ]] || current_port=8081
      is_uint "$current_port" || die "CADDY_HTTP_PORT no es un puerto válido: $current_port"
    fi
    set_env_key APP_BIND_IP 127.0.0.1
    set_env_key APP_PORT 8000
    set_env_key CADDY_HTTP_PORT "$current_port"
    set_env_key COMPOSE_PROFILES proxy
    if [[ -n "$HOST" ]]; then
      scheme=http
      if (( USE_TLS )); then scheme=https; fi
      csrf_origin="$scheme://$HOST:$current_port"
      set_env_key DJANGO_CSRF_TRUSTED_ORIGINS "$csrf_origin"
      set_env_key APP_URL "$csrf_origin/health/"
    fi
    if (( USE_TLS )); then
      if (( TLS_EXPLICIT )) && [[ -z "$HOST" ]]; then
        die "--tls requiere --host para generar un certificado interno útil."
      fi
      set_env_key CADDYFILE ./Caddyfile.internal-tls
      # Caddy escucha en :8080 dentro del contenedor y usa el nombre para
      # generar el certificado interno; el puerto exterior puede variar.
      # En una repetición sin --host se conserva el nombre y las URL ya
      # configurados; cambiarlo a :8080 rompería el certificado y los
      # orígenes de Django.
      if [[ -n "$HOST" ]]; then
        set_env_key CADDY_SITE_ADDRESS "$HOST:8080"
        set_env_key DJANGO_SESSION_COOKIE_SECURE 1
        set_env_key DJANGO_CSRF_COOKIE_SECURE 1
      fi
    elif [[ -n "$HOST" ]] || (( PROXY_EXPLICIT )); then
        set_env_key CADDYFILE ./Caddyfile
        set_env_key CADDY_SITE_ADDRESS :8080
        set_env_key DJANGO_SESSION_COOKIE_SECURE 0
        set_env_key DJANGO_CSRF_COOKIE_SECURE 0
        if [[ -z "$HOST" ]]; then
          set_env_key APP_URL "http://127.0.0.1:$current_port/health/"
        fi
    fi
  else
    set_env_key APP_PORT "$current_port"
    # Clear the proxy marker when switching back to direct mode.  Otherwise a
    # later invocation without flags would infer the old Caddy profile from
    # APP_PORT=8000 and start it again unexpectedly.
    set_env_key COMPOSE_PROFILES ""
    set_env_key CADDY_HTTP_PORT ""
    set_env_key CADDYFILE ./Caddyfile
    set_env_key DJANGO_SESSION_COOKIE_SECURE 0
    set_env_key DJANGO_CSRF_COOKIE_SECURE 0
    if [[ -z "$HOST" && -n "$PORT" ]]; then
      set_env_key DJANGO_CSRF_TRUSTED_ORIGINS "http://localhost:$current_port,http://127.0.0.1:$current_port"
    fi
    if [[ -z "$HOST" ]]; then
      set_env_key APP_URL "http://127.0.0.1:$current_port/health/"
    fi
  fi

  current_host=$(env_value DJANGO_ALLOWED_HOSTS)
  [[ -n "$current_host" ]] || die "DJANGO_ALLOWED_HOSTS está vacío; usa --host o completa .env."
  if [[ "$(env_value DJANGO_DEBUG)" == "1" || "$(env_value DJANGO_DEBUG)" == "true" ]]; then
    echo "Aviso: DJANGO_DEBUG está activo; no lo uses con datos reales." >&2
  fi
}

preflight() {
  [[ -f "$PROJECT_DIR/compose.yaml" ]] || die "No encuentro compose.yaml en $PROJECT_DIR."
  command -v docker >/dev/null 2>&1 || die "Docker Engine no está instalado o no está en PATH."
  docker info >/dev/null 2>&1 || die "No se puede acceder al daemon Docker. Inicia Docker Engine y vuelve a intentarlo."
  docker compose version >/dev/null 2>&1 || die "Falta Docker Compose v2 (plugin docker-compose-plugin)."
  [[ -r "$ENV_FILE" && -w "$ENV_FILE" ]] || die ".env no es legible y escribible por el usuario actual."
  compose_run config --quiet
}

wait_and_check() {
  local port path url scheme tls_host
  if (( USE_PROXY )); then
    port=$(env_value CADDY_HTTP_PORT)
  else
    port=$(env_value APP_PORT)
  fi
  path=$(env_value HEALTHCHECK_PATH)
  [[ -n "$path" ]] || path=/health/
  scheme=http
  if (( USE_TLS )); then scheme=https; fi
  if (( USE_TLS )); then
    tls_host=$HOST
    if [[ -z "$tls_host" ]]; then
      tls_host=$(env_value DJANGO_ALLOWED_HOSTS | cut -d, -f1)
    fi
    [[ -n "$tls_host" ]] || die "No se puede determinar el nombre TLS desde DJANGO_ALLOWED_HOSTS."
    url="$scheme://$tls_host:$port$path"
  else
    url="$scheme://127.0.0.1:$port$path"
  fi
  echo "Comprobando $url …"
  if command -v curl >/dev/null 2>&1; then
    if (( USE_TLS )); then
      curl --fail --silent --show-error --insecure --resolve "$tls_host:$port:127.0.0.1" --max-time 15 "$url" >/dev/null
    else
      curl --fail --silent --show-error --max-time 15 "$url" >/dev/null
    fi
  elif command -v wget >/dev/null 2>&1; then
    if (( USE_TLS )); then
      die "Para comprobar TLS con el nombre correcto necesito curl (incluye --resolve); instala curl y repite."
    else
      wget --quiet --timeout=15 --output-document=/dev/null "$url"
    fi
  else
    die "Necesito curl o wget para verificar la instalación."
  fi
  echo "Reto4V responde correctamente."
}

first_admin() {
  (( SKIP_ADMIN )) && return 0
  local existing
  existing=$(compose_run exec -T web python manage.py shell -c \
    'from django.contrib.auth import get_user_model; print(get_user_model().objects.filter(is_superuser=True).exists())' \
    2>/dev/null | tail -n 1 || true)
  if [[ "$existing" == "True" ]]; then
    echo "Ya existe una cuenta administradora; se omite createsuperuser."
    return 0
  fi
  if [[ ! -t 0 || ! -t 1 ]]; then
    echo "Instalación no interactiva. Crea el primer administrador con:"
    echo "  $(compose_base) exec web python manage.py createsuperuser"
    return 0
  fi
  local answer
  read -r -p "¿Crear ahora la primera cuenta administradora? [S/n] " answer
  if [[ -z "$answer" ]]; then answer=S; fi
  if [[ "$answer" =~ ^[SsYy]$ ]]; then
    compose_run exec web python manage.py createsuperuser
  else
    echo "Omitido. Puedes crearla más tarde con:"
    echo "  $(compose_base) exec web python manage.py createsuperuser"
  fi
}

seed_bash_if_requested() {
  (( SEED_BASH )) || return 0
  [[ -n "$SEED_OWNER" ]] || die "--seed-bash requiere --owner USERNAME."
  is_identifier "$SEED_OWNER" || die "--owner solo puede contener letras, números, punto, guion o guion bajo."
  echo "Cargando retos Bash para $SEED_OWNER ($SEED_COHORT) …"
  if ! compose_run exec -T web python manage.py seed_bash --owner "$SEED_OWNER" --cohort "$SEED_COHORT"; then
    echo "No se pudo ejecutar seed_bash. Comprueba que el usuario y el comando estén disponibles." >&2
    return 1
  fi
}

while (($#)); do
  case "$1" in
    --host)
      (($# >= 2)) || die "Falta el valor de --host."
      HOST=$2; shift 2 ;;
    --port)
      (($# >= 2)) || die "Falta el valor de --port."
      PORT=$2; shift 2 ;;
    --proxy) USE_PROXY=1; PROXY_EXPLICIT=1; shift ;;
    --tls) USE_TLS=1; USE_PROXY=1; TLS_EXPLICIT=1; PROXY_EXPLICIT=1; shift ;;
    --direct) USE_PROXY=0; USE_TLS=0; TLS_EXPLICIT=1; PROXY_EXPLICIT=1; shift ;;
    --seed-bash) SEED_BASH=1; shift ;;
    --owner)
      (($# >= 2)) || die "Falta el valor de --owner."
      SEED_OWNER=$2; shift 2 ;;
    --cohort)
      (($# >= 2)) || die "Falta el valor de --cohort."
      SEED_COHORT=$2; shift 2 ;;
    --no-build) NO_BUILD=1; shift ;;
    --skip-admin) SKIP_ADMIN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Opción desconocida: $1 (usa --help)." ;;
  esac
done

if [[ -n "$PORT" ]]; then is_uint "$PORT" || die "--port debe estar entre 1 y 65535."; fi
if [[ -n "$HOST" ]]; then is_host "$HOST" || die "--host debe ser una IP o nombre DNS sin esquema ni puerto."; fi
if (( USE_TLS && ! USE_PROXY )); then die "--tls requiere --proxy."; fi
if (( USE_TLS && TLS_EXPLICIT )) && [[ -z "$HOST" ]]; then die "--tls requiere --host para generar un certificado interno útil."; fi

cd "$PROJECT_DIR"
ensure_env
# Al repetir el instalador sin banderas, conserva el modo previamente elegido.
# Solo --proxy/--tls (o la futura opción --direct) cambia ese estado de forma
# explícita, para no apagar Caddy ni resetear un puerto TLS accidentalmente.
if (( PROXY_EXPLICIT == 0 )); then
  if [[ "$(env_value APP_PORT)" == 8000 && -n "$(env_value CADDY_HTTP_PORT)" ]]; then
    USE_PROXY=1
  fi
fi
if (( TLS_EXPLICIT == 0 && USE_PROXY )) && [[ "$(env_value CADDYFILE)" == *internal-tls* ]]; then
  USE_TLS=1
fi
configure_requested_values
preflight

if (( NO_BUILD == 0 )); then
  echo "Construyendo la imagen de Reto4V (la primera vez necesita Internet) …"
  compose_run build --pull
else
  echo "Se omite la reconstrucción; se usará la imagen existente."
fi

echo "Arrancando PostgreSQL y Reto4V …"
if compose_run up --help 2>&1 | grep -q -- '--wait'; then
  compose_run up -d --wait
else
  compose_run up -d
fi
wait_and_check
first_admin
seed_bash_if_requested

echo
echo "Instalación terminada."
echo "Configuración: $ENV_FILE (permisos 600; no la publiques)."
if (( USE_PROXY )); then
  if (( USE_TLS )); then
    echo "Entrada local: https://127.0.0.1:$(env_value CADDY_HTTP_PORT) (certificado interno; el navegador puede pedir confianza inicial)"
  else
    echo "Entrada local: http://127.0.0.1:$(env_value CADDY_HTTP_PORT)"
  fi
else
  echo "Entrada local: http://127.0.0.1:$(env_value APP_PORT)"
fi
echo "Para comprobar estado: bash scripts/healthcheck.sh"
