# Programmy4V

Programmy4V es una herramienta de gamificación para el aprendizaje de programación,
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

![Panel del alumno de Programmy4V](docs/images/dashboard.png)

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

La marca que verá el alumnado es **Programmy4V**. Se conserva `Reto4V` en la
URL del repositorio y en el nombre de la carpeta del ejemplo para que las
actualizaciones de instalaciones existentes sigan funcionando; también se
mantienen los nombres internos de Django, Compose y los scripts por la misma
razón.

El instalador comprueba Docker, crea `.env` sin sobrescribir uno existente,
genera secretos independientes con permisos `600`, construye la imagen,
arranca PostgreSQL y Programmy4V, espera al endpoint de salud y ofrece crear la
primera cuenta administradora. Cambia la IP de ejemplo por la del servidor o
por el nombre DNS interno del centro. Para una prueba únicamente local usa
`--host localhost`.

La imagen precarga automáticamente, al arrancar por primera vez, los tres
catálogos formativos y sus grupos base: Web · SMR, Bash · ASIR y Python · DAM.
No crea alumnos ni contraseñas de demostración. El proceso es idempotente y
puede repetirse al actualizar la instalación. La opción está controlada por
`PRELOAD_CATALOGS=1` (valor predeterminado); para una instalación que deba
arrancar sin tocar el catálogo, establece `PRELOAD_CATALOGS=0` en `.env`.

Después de iniciar sesión como administrador, crea cada alumno desde
`/admin-ui/users/` y selecciona su ciclo e itinerario en el campo **Ciclo e
itinerario**. Esa acción crea la matrícula activa automáticamente; el alumno
verá su primer reto en cuanto entre. Cada alumno puede tener un único ciclo e
itinerario activo. Para cambiarlo, edita la cuenta y selecciona el nuevo grupo;
la matrícula anterior queda inactiva para conservar la trazabilidad.

Si necesitas volver a cargar o reparar el catálogo de forma manual, ejecuta:

```bash
docker compose --env-file .env exec web python manage.py bootstrap_catalogs
```

### Actualizar una instalación existente

Haz primero una copia de seguridad y, desde la carpeta clonada dentro de WSL,
aplica la nueva versión con:

```bash
bash scripts/backup.sh
git pull --ff-only
bash scripts/install.sh --skip-admin
```

El último paso conserva `.env` y los volúmenes, reconstruye la aplicación,
aplica las migraciones y precarga de forma idempotente los 36 retos. No uses
`docker compose down -v`: ese modificador sí elimina los datos persistentes.

También puedes cargar un itinerario concreto, manteniendo el propietario y el
grupo que el centro haya elegido:

```bash
docker compose --env-file .env exec web python manage.py seed_bash \
  --owner profesor --cohort 2ASIR
docker compose --env-file .env exec web python manage.py seed_python \
  --owner profesor --cohort 2DAM
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

El catálogo inicial trae doce retos por itinerario (36 en total): Web para
Aplicaciones web de SMR, Bash para los fundamentos prácticos de Seguridad de
2.º ASIR y Python para preparar el trabajo posterior con Odoo en Sistemas de
gestión empresarial de 2.º DAM. El banco completo de actividades y la
cobertura de todos los resultados de aprendizaje se ampliarán por fases.

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
uv run python manage.py bootstrap_catalogs
uv run python manage.py runserver 127.0.0.1:8000
```

Las pruebas backend se ejecutan con `uv run pytest`; las de frontend con
`npm test`. Para un despliegue reproducible, Docker instala las dependencias
Python desde `requirements.lock` con hashes verificados.
