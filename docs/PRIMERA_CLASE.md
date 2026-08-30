# Preparar la primera clase

## Antes de que llegue el alumnado

1. Completa la instalación y accede con la primera cuenta administrativa.
2. Abre la gestión de usuarios del panel. Crea cuentas individuales de profesor
   y alumno; no uses una contraseña compartida por toda la clase.
3. En la administración (`/admin/`), revisa el año académico y el grupo
   `2ASIR`. Añade sus matrículas (`Enrollment`) y la relación docente
   (`TeachingAssignment`) con el profesor responsable.
4. Si aún no has cargado los retos, ejecuta dentro de la instalación:

   ```bash
   docker compose exec web python manage.py seed_bash --owner admin --cohort 2ASIR
   ```

   Sustituye `admin` por una cuenta administrativa o docente existente. Este
   comando carga actividades, no crea alumnos ni sus contraseñas.
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
