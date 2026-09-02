# Preparar la primera clase

## Antes de que llegue el alumnado

1. Completa la instalación y accede con la primera cuenta administrativa. El
   arranque de `web` aplica las migraciones y precarga automáticamente los
   catálogos Web · SMR, Bash · ASIR y Python · DAM cuando
   `PRELOAD_CATALOGS=1` (valor predeterminado).
2. Abre **Aulas e itinerarios** (`/admin-ui/classrooms/`) y comprueba que los
   ciclos activos muestran sus retos publicados. Si la instalación se ha
   actualizado desde una versión anterior, puedes repetir el bootstrap:

   ```bash
   docker compose --env-file .env exec web python manage.py bootstrap_catalogs
   ```

3. Abre **Usuarios** (`/admin-ui/users/`) y crea cuentas individuales de
   profesor y alumno; no uses una contraseña compartida por toda la clase. En
   cada cuenta de alumno selecciona **Ciclo e itinerario** (`Web · SMR`,
   `Bash · ASIR` o `Python · DAM`). El alta crea la matrícula activa de forma
   atómica; no hay que asignar los retos uno a uno.
4. Si el centro necesita nombres de grupo distintos, créalos junto con su
   catálogo mediante `seed_web`, `seed_bash` o `seed_python`, pasando el nombre
   deseado en `--cohort`. Por ejemplo:

   ```bash
   docker compose --env-file .env exec web python manage.py seed_web \
     --owner admin --cohort 1SMR-A
   ```

   Sustituye `admin` por una cuenta administrativa o docente existente. El
   comando crea el grupo con el itinerario correcto y enlaza los retos; después
   aparecerá en **Ciclo e itinerario**. Cada alumno solo puede conservar un
   ciclo activo y la matrícula anterior queda inactiva al cambiarlo.
5. Si aún no has cargado los retos en una instalación con el bootstrap
   desactivado, ejecuta dentro de la instalación el seed que corresponda. Para
   preparar ambos grupos en una sola operación:

   ```bash
   docker compose --env-file .env exec web python manage.py bootstrap_catalogs
   ```

   Si solo necesitas Python, usa `seed_python`; si solo necesitas Bash, usa
   `seed_bash`:

   ```bash
   docker compose --env-file .env exec web python manage.py seed_bash --owner admin --cohort 2ASIR
   ```

   Para Python, ejecuta:

   ```bash
   docker compose --env-file .env exec web python manage.py seed_python --owner admin --cohort 2DAM
   ```

   Sustituye `admin` por una cuenta administrativa o docente existente. Estos
   comandos cargan actividades, no crean alumnos ni sus contraseñas, y pueden
   repetirse sin alterar versiones que ya estén asignadas.
6. Comprueba desde un ordenador del aula una cuenta ficticia de estudiante y
   una cuenta de profesor. Usa TLS antes de introducir datos reales.

## En clase

El alumno entra con su cuenta y cambia la contraseña temporal cuando se le
solicita. En su espacio solo aparecen actividades del único ciclo en el que
está matriculado. Si la cuenta se ha creado con `Bash · ASIR`, el dashboard
ofrece directamente **Empezar primer reto** y muestra el primer reto publicado
de ese itinerario; no es necesario abrir una asignación manualmente.

Si aparece el estado vacío, el administrador debe editar la cuenta y elegir un
ciclo e itinerario activo. El cambio se aplica en la siguiente carga del
dashboard y no permite ver actividades de otro itinerario.

En Bash, la dinámica es leer la explicación, editar `script.sh`, consultar
una pista si hace falta, comprobar y entregar. La validación es estática:
no abre una terminal ni ejecuta comandos reales. Las prácticas sobre archivos
se verifican después en la VM de laboratorio indicada por el profesor.

En Python, la dinámica es leer la explicación, editar `main.py`, consultar una
pista si hace falta, comprobar y entregar. El servidor analiza únicamente el
AST en memoria: no ejecuta el programa, no importa módulos y no lee ni escribe
archivos. Los retos de archivos comprueban construcciones como `with open(...)`
solo de forma estructural; la práctica real con datos ficticios se hace en la
VM o entorno de laboratorio que determine el profesor. La ruta prepara
conceptos útiles para Odoo, pero no prueba el ORM ni una integración con Odoo.

Los XP muestran la mejor evidencia automática de cada reto; repetir la misma
entrega no suma la recompensa otra vez. Las insignias no certifican que un
script sea seguro o que una copia se haya restaurado de verdad.

## Revisar y calificar

Desde el panel docente puedes abrir las entregas de tus grupos, leer el código
exacto, añadir feedback y publicar la calificación correspondiente al modo y
pesos de la actividad. La nota publicada y los XP son indicadores distintos.
Exporta el CSV para llevar las calificaciones a tu herramienta habitual.

Para una evaluación reservada, crea tus propios enunciados, tests y rúbricas
en la instalación local. El catálogo incluido es formativo y su código fuente
es público. No subas evidencias reales o soluciones de exámenes a GitHub.

## Al terminar

Comprueba el backup y el espacio disponible. Desactiva las cuentas que ya no
deban acceder, sin borrar silenciosamente las evidencias académicas. Aplica
la política de retención acordada por el centro.
