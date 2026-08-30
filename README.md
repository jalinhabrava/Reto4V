# Reto4V

Reto4V es una herramienta de gamificación para el aprendizaje de programación,
pensada para funcionar en la red local de un centro educativo. Ofrece retos,
puntuación, progreso y revisión docente sin depender de servicios externos en
tiempo de uso.

Incluye dos itinerarios que pueden convivir en la misma instalación:

- **Web · FP SMR**: HTML, CSS y JavaScript para el módulo navarro `0228 ·
  Aplicaciones web`.
- **Bash · 2.º ASIR**: scripting de Linux para la asignatura de Seguridad,
  con sintaxis, variables, condiciones, bucles, funciones, filtros y copias
  de seguridad.

La evaluación de Bash es estática: analiza el código con un parser y nunca
ejecuta comandos del alumnado ni abre una shell dentro del servidor. La
puntuación de juego (XP, niveles e insignias) es motivacional y no sustituye a la
calificación académica que decida el profesorado.

![Panel del alumno de Reto4V](docs/images/dashboard.png)

*Vista de ejemplo con datos ficticios; no representa alumnado real.* Consulta
también el [espacio de trabajo Bash](docs/images/bash-workspace.png) y la
[especificación funcional](docs/SPECIFICATIONS.md).

## Arranque rápido en WSL2

Necesitas Docker Engine y Docker Compose v2 dentro de Ubuntu WSL2. Consulta la
[instalación oficial de Docker Engine para Ubuntu](https://docs.docker.com/engine/install/ubuntu/),
el [plugin oficial de Compose](https://docs.docker.com/compose/install/linux/)
y la [documentación de systemd en WSL](https://learn.microsoft.com/windows/wsl/systemd).

En Ubuntu, clona el repositorio dentro del sistema de archivos Linux y ejecuta:

```bash
git clone https://github.com/jalinhabrava/Reto4V.git Reto4V
cd Reto4V
bash scripts/install.sh --host 192.168.20.10 --port 8080
```

El instalador comprueba Docker, crea `.env` sin sobrescribir uno existente,
genera secretos independientes con permisos `600`, construye la imagen,
arranca PostgreSQL y Reto4V, espera al endpoint de salud y ofrece crear la
primera cuenta administradora. Cambia la IP de ejemplo por la del servidor o
por el nombre DNS interno del centro. Para una prueba únicamente local usa
`--host localhost`.

Para cargar los retos de Bash de demostración después de crear la cuenta del
profesor:

```bash
bash scripts/install.sh --no-build --skip-admin --seed-bash \
  --owner profesor --cohort 2ASIR
```

El instalador es idempotente: repetirlo no elimina volúmenes ni usuarios. Las
cuentas se desactivan, no se borran, para conservar la trazabilidad de las
entregas.

## Operación habitual

```bash
bash scripts/healthcheck.sh
docker compose --env-file .env ps
bash scripts/backup.sh
```

La restauración reemplaza los datos actuales y exige una confirmación
explícita:

```bash
RESTORE_CONFIRM=YES bash scripts/restore.sh <postgres.dump.gz> [media.tar.gz]
```

No ejecutes `docker compose down -v` en una instalación con datos: elimina los
volúmenes persistentes.

## Red y seguridad

El modo HTTP directo está limitado a la prueba técnica de Fase 0. Para
credenciales, entregas y notas reales, usa TLS interno con el perfil Caddy:

```bash
bash scripts/install.sh --host reto4v.instituto.lan --port 8443 --tls
```

El certificado interno debe estar confiado en los equipos del aula, o debe
sustituirse por el certificado y proxy del centro. En WSL2 con NAT, configura
el portproxy y el Firewall de Windows siguiendo
[docs/DEPLOY_WSL.md](docs/DEPLOY_WSL.md). No se publica nunca el puerto de
PostgreSQL.

La guía de despliegue cubre además autoarranque con systemd, Windows Server,
modo mirrored, funcionamiento sin Internet y copias de seguridad:
[docs/DEPLOY_WSL.md](docs/DEPLOY_WSL.md).

## Estado curricular

La primera versión trae una actividad web y una ruta inicial de Bash. El seed
de Bash ofrece retos sobre fundamentos de scripting, análisis de logs y
copias de seguridad, orientados a los contenidos prácticos de Seguridad de
2.º ASIR. El banco completo de
actividades y la cobertura de todos los resultados de aprendizaje se ampliarán
por fases.

Consulta el [itinerario Bash](docs/BASH_TRACK.md), la [guía de primera
clase](docs/PRIMERA_CLASE.md) y la documentación técnica para conocer el
alcance y las siguientes iteraciones.

## Desarrollo local

```bash
uv sync --all-groups --frozen
npm ci
npm run build
uv run python manage.py migrate
uv run python manage.py runserver 127.0.0.1:8000
```

Las pruebas backend se ejecutan con `uv run pytest`; las de frontend con
`npm test`. Para un despliegue reproducible, Docker instala las dependencias
Python desde `requirements.lock` con hashes verificados.
