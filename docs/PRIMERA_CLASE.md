# Preparar la primera clase

## Antes de que llegue el alumnado

1. Completa la instalación y accede con la primera cuenta administrativa.
2. Abre la gestión de usuarios del panel. Crea cuentas individuales de profesor
   y alumno; no uses una contraseña compartida por toda la clase.
3. En la administración (`/admin/`), revisa el año académico y crea o valida
   los grupos `2ASIR` y `2DAM` que vayas a usar. Añade las matrículas
   (`Enrollment`) y la relación docente (`TeachingAssignment`) con el profesor
   responsable.
4. Si aún no has cargado los retos, ejecuta dentro de la instalación el seed
   que corresponda. Para preparar ambos grupos en una sola operación:

   ```bash
   bash scripts/install.sh --no-build --skip-admin \
     --seed-bash --seed-python --owner admin \
     --cohort 2ASIR --python-cohort 2DAM
   ```

   Si solo necesitas Python, usa `--seed-python --python-cohort 2DAM`; si solo
   necesitas Bash, conserva el comando directo:

   ```bash
   docker compose exec web python manage.py seed_bash --owner admin --cohort 2ASIR
   ```

   Sustituye `admin` por una cuenta administrativa o docente existente. Estos
   comandos cargan actividades, no crean alumnos ni sus contraseñas, y pueden
   repetirse sin alterar versiones que ya estén asignadas.
5. Comprueba desde un ordenador del aula una cuenta ficticia de estudiante y
   una cuenta de profesor. Usa TLS antes de introducir datos reales.

## En clase

El alumno entra con su cuenta y cambia la contraseña temporal cuando se le
solicita. En su espacio solo aparecen actividades de los grupos en los que
está matriculado.

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
