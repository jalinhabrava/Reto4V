# Itinerario Bash · Programmy4V

## Propósito y límites

Este es un itinerario de iniciación a Bash para 2.º de ASIR. Sirve de apoyo
transversal a scripting, automatización y revisión de registros dentro del
módulo `0378` (Seguridad y alta disponibilidad), pero no acredita resultados
de aprendizaje ni criterios de evaluación. La relación concreta con la
programación didáctica la decide el equipo docente.

Cada reto usa un patrón didáctico breve: explica una idea, presenta un ejemplo
distinto y comentado, y propone un ejercicio pequeño que solo utiliza esa idea
y las anteriores. La plantilla ya contiene el shebang y la mayor parte de la
estructura: el alumno completa unas pocas líneas, sin crear carpetas ni
descargar archivos.

Las órdenes que aparecen son texto para practicar. El corrector analiza la
estructura del archivo con `tree-sitter-bash`; nunca inicia Bash, procesos
hijos, red, ni lectura o escritura en el sistema de archivos. Por tanto, una
prueba superada acredita presencia estructural, no que un script haya sido
ejecutado ni que haya operado sobre un servidor real.

## Crear o actualizar el itinerario

En instalaciones nuevas el catálogo se precarga en **Bash · ASIR** después de
las migraciones cuando `PRELOAD_CATALOGS=1`. Para crear un grupo adicional o
cuando el bootstrap está desactivado:

```bash
python manage.py seed_bash --owner profesor --cohort 2ASIR
```

- `--owner USERNAME` es obligatorio y debe ser profesor o administrador.
- `--cohort NOMBRE` usa `2ASIR` por defecto.
- `--academic-year AAAA-AAAA` es opcional; sin él se calcula según la fecha
  del servidor.

El comando no crea alumnado, contraseñas ni datos personales. Crea o reutiliza
el curso `Laboratorio Bash para Seguridad · ASIR`, un módulo y doce actividades
publicadas. El grupo queda marcado como `track=bash`, necesario para que su
alumnado acceda al itinerario correspondiente.

## Revisión 3: progresión y compatibilidad

La revisión incorporada es la v3. Conserva los doce slugs históricos para que
una instalación existente identifique cada actividad, aunque algunos nombres
antiguos ya no describan el contenido. La progresión real es esta:

| Orden | Slug histórico | Reto v3 | Idea nueva |
|---:|---|---|---|
| 1 | `01-variables-y-salida` | Terminal, shell y primer script | Qué son terminal, shell y script; mostrar texto con `echo`. |
| 2 | `02-condiciones-y-rutas` | Guardar un texto en una variable | Asignación sin espacios y lectura con `$NOMBRE`. |
| 3 | `03-bucle-de-registros` | Proteger texto con comillas | Comillas dobles para texto con espacios y variables. |
| 4 | `04-funciones-reutilizables` | Nombrar una ruta | Rutas absolutas y una variable de ruta. |
| 5 | `05-pipelines-de-registros` | Dar formato con `printf` | Plantilla `%s` y salto de línea `\n`. |
| 6 | `06-parametros-posicionales` | Comprobar un archivo con `if` | `if`, `then`, `fi` y `-f`. |
| 7 | `07-codigos-de-salida` | Elegir un mensaje con `if` y `else` | Segunda rama y comprobación de directorio `-d`. |
| 8 | `08-plan-de-copia` | Repetir nombres con `for` | Lista corta, variable de vuelta, `do` y `done`. |
| 9 | `09-permisos-del-script` | Preguntar a `grep` con `if` | Búsqueda silenciosa `grep -q` como condición. |
| 10 | `10-pipeline-awk-y-orden` | Conectar órdenes con un pipeline | Pasar `grep` a `sort` mediante `|`. |
| 11 | `11-case-de-operacion` | Agrupar un paso en una función | Declarar y llamar una función sencilla. |
| 12 | `12-rutina-integrada` | Repaso: listar rutas preparadas | Reutilizar variables, rutas, `printf` y `for`. |

La primera actividad no introduce `printf`. El último reto no intenta ser una
rutina de copia ni introduce una orden nueva: reúne conceptos ya explicados en
una lista corta de rutas. Las copias y operaciones complejas son una ampliación
posterior, no una promesa que deba encajarse en doce pasos.

Cada solución de referencia supera sus cuatro comprobaciones estáticas. Cada
plantilla inicial queda por debajo de 8/10, el umbral de completado: contiene
la estructura que facilita empezar, pero no todos los elementos evaluados.

### Actualización segura desde v2

Las versiones asignadas son inmutables. Al ejecutar `seed_bash` sobre v2, el
comando publica una v3 nueva, crea su asignación y archiva las asignaciones
anteriores del mismo itinerario. Borradores, entregas, calificaciones y demás
evidencias siguen vinculados a sus versiones y asignaciones originales.

Al migrar el título de una asignación, el título incorporado v2 conocido se
sustituye por el título v3. Un título distinto que haya escrito el docente se
conserva como personalización. Repetir el comando es idempotente: no duplica
el catálogo y no modifica una revisión posterior creada por el centro.

## DSL de pruebas Bash

Las pruebas son declarativas y se validan antes de publicar una actividad. No
aceptan campos desconocidos, expresiones Python, `eval`, regex de corrección ni
órdenes arbitrarias.

| Tipo | Definición | Qué comprueba |
|---|---|---|
| `bash.syntax_valid` | `{}` | Que el árbol Bash no contenga un error sintáctico. |
| `bash.shebang` | `{}`; `{"expected": "/usr/bin/env bash"}` | El shebang inicial; también admite `{"interpreter": "bash"}`. |
| `bash.command_used` | `{"command": "tar"}`; `args` opcional | Presencia de un comando y, opcionalmente, argumentos literales. |
| `bash.variable_assigned` | `{"name": "BACKUP_DIR"}` | Una asignación de variable, incluida una variable de `for`. |
| `bash.node_kind` | `{"kind": "if"}` | Un tipo de nodo. Alias: `if`, `for`, `while`, `function`, `case`, `pipeline`. |

El evaluador analiza cada archivo una vez y reutiliza el árbol. Limita cada
fichero a 256 KiB, el conjunto a 1 MiB, el lote a 200 pruebas, el árbol Bash a
5.000 nodos y la profundidad a 80. Superar un límite o tener sintaxis inválida
produce feedback del corrector; no provoca ejecución de código.

No se comprueba semántica de ejecución, expansión de variables o globs,
permisos efectivos, existencia o contenido real de archivos, ni el resultado
de una copia. El catálogo no presenta estas comprobaciones estructurales como
pruebas de que la operación haya ocurrido.

## XP y calificación

La experiencia se calcula a partir del mejor resultado automático válido de
cada asignación:

```text
earned_xp = floor(xp_reward * best_automatic_score / 10)
```

Una puntuación de al menos 8 completa el reto. XP es feedback formativo y no
una calificación oficial: la nota depende de las políticas publicadas por el
profesor y de la asignación. Reintentos posteriores no añaden XP si no mejoran
el resultado automático.
