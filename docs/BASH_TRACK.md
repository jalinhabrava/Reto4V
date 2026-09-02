# Itinerario Bash · Programmy4V

## Propósito

Este itinerario añade una ruta de aprendizaje de Bash para 2.º de ASIR,
especialmente útil como apoyo a scripting, automatización, comprobación de
registros y planificación de copias de seguridad. Está pensado para una
instalación LAN y no necesita Internet para que el alumnado trabaje.

El nivel de entrada previsto es alumnado de 2.º de ASIR que parte de cero en
Bash, aunque ya tenga una base de informática. La progresión comienza con un
primer archivo de texto y mensajes sencillos, y añade una sola idea principal
en cada reto antes de llegar a las rutinas de copias. Las instrucciones son
directas, incluyen pasos numerados, pistas progresivas y un archivo inicial
preparado para completar.

El contenido se marca con el código de módulo profesional `0378` (Seguridad y
alta disponibilidad), pero es **apoyo transversal sin acreditación de RA/CE**:
no declara una cobertura completa de resultados de aprendizaje ni inventa
criterios de evaluación. La referencia de base del currículo navarro de grado
superior es el [Decreto Foral 50/2010](https://www.lexnavarra.navarra.es/detalle.asp?r=9158),
con la modificación vigente publicada en el [Decreto Foral
110/2024](https://www.educacion.navarra.es/documents/27590/558252/DF%2B110_2024%2Bmodificacion%2BGS.pdf/a649cf9e-7adf-3c5d-c5ac-eaa602a553a5?version=1.0).
La relación concreta entre scripting, automatización, seguridad y la
programación didáctica del centro debe decidirla el equipo docente. Como
contexto opcional, el scripting puede conectarse con contenidos de
automatización de ASO0374, sin trasladar aquí una supuesta equivalencia de
RA/CE.

## Crear el itinerario

En una instalación nueva, el catálogo Bash se precarga automáticamente en el
grupo base **Bash · ASIR** después de las migraciones (`PRELOAD_CATALOGS=1`).
Para una instalación con el bootstrap desactivado o para un grupo adicional,
crea el itinerario después de tener una cuenta de profesor o administrador:

```bash
python manage.py seed_bash --owner profesor --cohort 2ASIR
```

Opciones disponibles:

- `--owner USERNAME` (obligatoria): cuenta existente de profesor o administrador.
- `--cohort NOMBRE`: grupo destinatario; por defecto `2ASIR`.
- `--academic-year AAAA-AAAA`: curso académico; si se omite se calcula según la fecha del servidor.

El comando crea el curso `Laboratorio Bash para Seguridad · ASIR`, el módulo
`De cero a tus primeras automatizaciones`, doce actividades publicadas y sus asignaciones al
grupo indicado. El grupo queda marcado con `track=bash`, que permite que el
panel admin lo muestre como **Bash · ASIR** y que las cuentas de alumno lo
seleccionen. No crea alumnos, contraseñas ni datos personales. Es idempotente:
reutiliza actividades y registros compatibles; si encuentra el catálogo v1,
añade la revisión v2 y una asignación nueva sin mutar ninguna versión ya
asignada.

Al crear o editar un alumno en `/admin-ui/users/`, selecciona su ciclo e
itinerario. Esa selección activa su única matrícula; no hay que asignar cada
reto por separado. Si cambias a otro ciclo, la matrícula anterior se conserva
como historial pero deja de dar acceso.

El catálogo contiene teoría, reto, pistas, una plantilla Bash y una solución
de referencia para que el docente pueda revisar el diseño. Como el repositorio
es público, esas soluciones **no deben considerarse respuestas secretas** ni
usarse como banco de exámenes. Para una evaluación con secreto real, crea una
nueva versión/actividad y tests privados directamente en la base de datos del
centro; la API oculta los tests privados al alumno, pero ningún secreto
commiteado en un repositorio público puede permanecer secreto.

## Progresión del catálogo Bash v2

La revisión incorporada por `seed_bash` es la v2. Conserva los slugs de las
instalaciones anteriores para que cada actividad siga siendo identificable,
pero reordena la dificultad y simplifica el lenguaje para acompañar a quien
está empezando:

| Orden | Reto | Idea principal |
|---:|---|---|
| 1 | Mi primer script | Shebang, `echo` y `printf` para mostrar mensajes. |
| 2 | Guardar un dato en una variable | Crear `NOMBRE` y usar su contenido. |
| 3 | Guardar una carpeta y un archivo | Preparar `CARPETA` y `ARCHIVO` para formar una ruta. |
| 4 | Recibir un dato | Leer `$1` y usar `alumno` como valor de reserva. |
| 5 | Tomar una decisión con `if` | Comprobar si existe un archivo. |
| 6 | Repetir una tarea con `for` | Recorrer nombres de archivos. |
| 7 | Repetir hasta terminar con `while` | Avanzar con un contador y detener el bucle. |
| 8 | Crear una función sencilla | Agrupar y llamar una tarea reutilizable. |
| 9 | Filtrar información con un pipeline | Pasar resultados de `grep` a `sort` mediante `|`. |
| 10 | Preparar una carpeta de copias | Comprobar y crear una ruta con `mkdir -p`. |
| 11 | Preparar una copia con `tar` | Revisar la fuente y expresar una copia comprimida. |
| 12 | Crear y verificar una copia | Combinar función, condición, `tar` y `sha256sum`. |

Las doce soluciones de referencia pasan las cuatro comprobaciones estáticas
de su reto. Esto acredita que la estructura escrita contiene los elementos
que se practican; no significa que el script se haya ejecutado ni que se haya
leído, creado o verificado un archivo real.

### Actualización segura desde v1

Al arrancar una instalación existente con el catálogo precargado, o al volver
a ejecutar `seed_bash`, la actividad conserva su slug y recibe una versión v2
inmutable. La asignación nueva se vincula al grupo y las asignaciones
anteriores se archivan solo para ese mismo itinerario. Las entregas,
borradores, cálculos de nota y demás evidencias siguen ligados a su asignación
y a su versión originales; no se borran ni se recalculan por la actualización.

El proceso es idempotente: repetirlo no crea un segundo conjunto de doce
retos ni sustituye una solución personalizada por el centro. Si una actividad
ya tiene una versión posterior creada por el centro, el catálogo incorporado
no la degrada ni la reemplaza. Los slugs históricos se mantienen precisamente
para que esta actualización sea reconocible en instalaciones ya utilizadas.

## DSL de tests Bash

Las definiciones son declarativas y se validan antes de guardar/publicar una
actividad. Los tests no aceptan campos desconocidos ni expresiones Python,
regex de corrección, `eval` ni órdenes arbitrarias:

| Tipo | Definición | Comportamiento |
|---|---|---|
| `bash.syntax_valid` | `{}` | El árbol Bash no contiene errores sintácticos. |
| `bash.shebang` | `{}` o `{"expected": "/usr/bin/env bash"}` | Comprueba el shebang inicial; también admite `{"interpreter": "bash"}`. |
| `bash.command_used` | `{"command": "tar"}`; opcional `args: ["-czf", "$ARCHIVE"]` | Busca un nodo `command` con nombre y argumentos literales. No expande variables ni ejecuta la orden. |
| `bash.variable_assigned` | `{"name": "BACKUP_DIR"}` | Comprueba una asignación de variable, incluida la variable de control de un `for`. |
| `bash.node_kind` | `{"kind": "if_statement"}` | Busca un tipo de nodo de la gramática Bash. Alias pedagógicos: `if`, `for`, `while`, `function`, `case`, `pipeline`. |

El parser es `tree-sitter-bash`. Cada evaluación analiza el fichero una sola
vez y reutiliza el árbol para todos los tests. Se limita el fichero a 256 KiB,
el conjunto de archivos a 1 MiB, el lote a 200 tests, el árbol Bash a 5.000
nodos y la profundidad a 80 niveles. Un árbol con error sintáctico produce
feedback de fallo; superar un límite rechaza la evaluación como entrada no
válida. En ningún caso se inicia `/bin/bash`, un proceso hijo, una red o una
lectura/escritura del sistema de archivos.

La cobertura está orientada a fundamentos y estructuras frecuentes: comandos,
variables, asignaciones, `if`, `for`, `while`, funciones, pipelines,
redirecciones y `case`. No se promete semántica de ejecución, expansión de
globs, permisos efectivos, estado del sistema, contenido de archivos ni
resultado real de una copia. Construcciones que el árbol marque con error no
pueden obtener puntuación de sintaxis hasta que se escriban de una forma
compatible con el reto.

## XP, niveles y calificación

La experiencia se calcula en el servidor a partir del mejor resultado
automático válido de cada asignación:

```text
earned_xp = floor(xp_reward * best_automatic_score / 10)
```

El valor máximo de `xp_reward` es 1.000. La puntuación automática está entre 0
y 10; un resultado de al menos 8 completa el reto. Cada 500 XP comienza un
nivel nuevo. Los intentos repetidos no generan XP adicional: solo el máximo
automático por asignación cuenta, y los resultados con error del corrector o
sin calificación automática se ignoran.

XP y calificación son conceptos separados. La nota oficial sigue siendo el
cálculo publicado por el profesor y las políticas de intentos de la
asignación; XP no se exporta como nota, no modifica rúbricas y no crea una
clasificación pública. Las insignias se derivan de forma determinista de los
retos completados y del XP de ese alumno, sin ranking entre compañeros.

El dashboard del alumno expone por asignación `language`, `difficulty`,
`xp_reward`, `earned_xp`, `completed` y `progress` (porcentaje basado en la
mejor puntuación automática). En `gamification` expone `total_xp`, `level`,
`level_progress` (porcentaje dentro del nivel), `xp_to_next_level`,
`completed_challenges` y las insignias `{id, title, description}`.
