# Reto4V

Reto4V es una herramienta de gamificación para el aprendizaje de programación,
pensada para funcionar en la red local de un centro educativo. Ofrece retos,
puntuación, progreso y revisión docente sin depender de servicios externos en
tiempo de uso.

Incluye tres itinerarios que pueden convivir en la misma instalación:

- **Web · FP SMR**: HTML, CSS y JavaScript para el módulo navarro `0228 ·
  Aplicaciones web`.
- **Bash · 2.º ASIR**: scripting de Linux para la asignatura de Seguridad,
  con sintaxis, variables, condiciones, bucles, funciones, filtros y copias
  de seguridad.
- **Python · 2.º DAM**: fundamentos hasta lectura y escritura de archivos,
  orientados al módulo `0491 · Sistemas de gestión empresarial` y como base
  para trabajar posteriormente con Odoo.

La evaluación de Bash es estática: analiza el código con un parser y nunca
ejecuta comandos del alumnado ni abre una shell dentro del servidor. Python se
analiza con el módulo `ast`: tampoco se ejecuta, importa módulos ni abre
archivos; los retos de lectura y escritura solo comprueban la estructura del
código. La puntuación de juego (XP, niveles e insignias) es motivacional y no
sustituye a la calificación académica que decida el profesorado.

![Panel del alumno de Reto4V](docs/images/dashboard.png)

*Vista de ejemplo con datos ficticios; no representa alumnado real.* Consulta
también los espacios de trabajo [Bash](docs/images/bash-workspace.png) y
[Python](docs/images/python-workspace.png), además de la
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

Para cargar también Python para el grupo de 2.º DAM:

```bash
bash scripts/install.sh --no-build --skip-admin --seed-python \
  --owner profesor --python-cohort 2DAM
```

También puedes cargar ambos itinerarios en una sola ejecución. `--cohort` es
el nombre histórico del grupo Bash; `--bash-cohort` es su forma explícita y
`--python-cohort` mantiene por defecto `2DAM`:

```bash
bash scripts/install.sh --no-build --skip-admin \
  --seed-bash --seed-python --owner profesor \
  --cohort 2ASIR --python-cohort 2DAM
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

La versión 0.3 trae una actividad web y dos rutas iniciales de doce retos:
Bash para los fundamentos prácticos de Seguridad de 2.º ASIR y Python para
preparar el trabajo posterior con Odoo en Sistemas de gestión empresarial de
2.º DAM. El banco completo de actividades y la cobertura de todos los
resultados de aprendizaje se ampliarán por fases.

La ruta Python es una preparación parcial, no una implementación de Odoo ni
una acreditación del módulo. El currículo navarro vigente sitúa `0491 ·
Sistemas de gestión empresarial` en 160 horas, 5 horas semanales y 2.º curso;
consulta el [Decreto Foral 110/2024](https://www.educacion.navarra.es/documents/27590/558252/DF%2B110_2024%2Bmodificacion%2BGS.pdf/a649cf9e-7adf-3c5d-c5ac-eaa602a553a5?version=1.0),
el [itinerario Bash](docs/BASH_TRACK.md), el [itinerario Python](docs/PYTHON_TRACK.md),
la [guía de primera clase](docs/PRIMERA_CLASE.md) y la documentación técnica
para conocer el alcance y las siguientes iteraciones. La referencia de
desarrollo de Odoo se encuentra en su [tutorial oficial del framework de servidor](https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101.html).

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
