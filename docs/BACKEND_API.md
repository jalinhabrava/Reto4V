# Backend Django de Programmy4V

## Desarrollo y despliegue

```bash
python manage.py migrate
python manage.py bootstrap_catalogs
python manage.py runserver 0.0.0.0:8000
```

La configuración local usa SQLite (`data/db.sqlite3`). En WSL/Compose se
configura PostgreSQL mediante `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` y
`DB_PORT` (o `DATABASE_URL`).

`seed_demo` es un comando opcional para un entorno de desarrollo. Cuando crea cuentas genera contraseñas aleatorias,
las muestra una sola vez y solo guarda el hash Argon2id. Se pueden proporcionar
contraseñas explícitas con `--admin-password`, `--teacher-password` y
`--student-password`; nunca se escriben en exportaciones ni logs.

En una instalación del centro, `bootstrap_catalogs` se ejecuta automáticamente
al arrancar el servicio `web` cuando `PRELOAD_CATALOGS=1` (predeterminado),
después de aplicar las migraciones. Es idempotente, no crea alumnos ni
contraseñas de demostración y precarga los itinerarios Web · SMR, Bash · ASIR
y Python · DAM. Se puede repetir de forma segura tras una actualización:

```bash
docker compose --env-file .env exec web python manage.py bootstrap_catalogs
```

`PRELOAD_CATALOGS=0` desactiva el paso automático para una instalación que
necesite gestionar su catálogo manualmente. Los seeds de cada itinerario
siguen disponibles para ampliaciones controladas. Los tres catálogos
incorporados se sirven en revisión v2: si el grupo tiene enlaces a v1, el
bootstrap crea la versión v2, migra los enlaces del grupo a una asignación v2
y archiva la asignación v1. Los borradores, entregas, calificaciones y demás
evidencias v1 se conservan internamente ligadas a su asignación/version para
mantener la integridad histórica; no se trasladan XP ni progreso a v2.
Una revisión posterior creada por el centro no se degrada ni se reemplaza.

## Contrato del workspace

Todas las rutas mutables requieren sesión autenticada, rol de alumno y CSRF.
El servidor comprueba además matrícula, ventana de entrega y versión de la
actividad; no confía en el cliente para permisos ni para notas oficiales.

`Cohort.track` identifica el itinerario (`web`, `bash` o `python`). El panel
local `/admin-ui/classrooms/` muestra ciclos activos y `/admin-ui/users/`
permite elegir el campo `cohort` al crear o editar un alumno. El servicio de
matrículas garantiza una sola `Enrollment(active=True)` por alumno, desactiva
la anterior al cambiar de ciclo y conserva las evidencias. Un alumno recién
creado con ciclo asignado recibe automáticamente todos los retos publicados
de su grupo y puede abrir el primero en cuanto inicia sesión.

| Método | Ruta | Uso |
|---|---|---|
| GET | `/assignments/<uuid>/` | Pantalla HTML del workspace; el bootstrap no incluye tests privados. |
| GET | `/api/assignments/<uuid>/` | Actividad, versión, archivos iniciales, borrador y entregas propias. |
| GET | `/api/assignments/<uuid>/draft/` | Borrador actual y su `revision`; también entrega la cookie CSRF. |
| POST | `/api/assignments/<uuid>/draft/` | Autosave web `{html, css, javascript, revision}`, Bash `{bash, revision}` o Python `{python, revision}`. Devuelve la revisión nueva; ante conflicto responde `409` con `current`. |
| POST | `/api/assignments/<uuid>/tests/` | Ejecuta únicamente tests públicos declarativos; no consume intento. |
| POST | `/api/assignments/<uuid>/submit/` | Crea una evidencia inmutable y asigna el siguiente intento dentro de una transacción. |

La respuesta `201` de entrega incluye además `gamification` con la fila del
reto recién recalculada (`earned_xp`, `best_score`, `completed` y `progress`),
para actualizar el workspace al instante. El valor se deriva del mejor
resultado automático persistido del alumno; no procede del cliente.

Las respuestas de tests formativos contienen `score`, `passed_points`,
`total_points` y `results`, siempre limitados a tests públicos. Al entregar,
el servidor puede utilizar también tests privados para el cálculo oficial,
pero no devuelve al alumno su nombre, definición, feedback ni detalle. La
puntuación enviada al navegador es feedback; la nota oficial se calcula al
crear la entrega con el evaluador estático del servidor.

## Rutas de lenguaje y gamificación

Una `ActivityVersion` puede declarar `language: "web"`, `language: "bash"` o
`language: "python"`. Los puntos de partida son diferentes: Web corresponde
a 1.º de SMR y parte de cero informático; Bash corresponde a 2.º de ASIR,
parte de una base de Linux y empieza desde cero en Bash; Python corresponde a
2.º de DAM y enlaza la base de programación con datos y archivos para preparar
el trabajo posterior con Odoo.
`difficulty: "beginner" | "intermediate" | "advanced"`, `xp_reward` (0–1000)
y una lista de `hints`. Las versiones web solo aceptan `html`, `css` y
`javascript`; las versiones Bash solo aceptan `bash`; las versiones Python
solo aceptan `python` (el editor lo presenta como `main.py`). La respuesta
`version.files` devuelve exclusivamente las claves del lenguaje de la
actividad. `version.editor_files` indica qué pestañas debe enseñar el editor;
en Web permite introducir primero solo HTML, después CSS y finalmente
JavaScript sin mostrar archivos que aún no se han explicado. El frontend las
presenta como `index.html`, `styles.css` y `script.js`; en el recorrido Web las
pestañas del workspace son **Pasos**, **Editor** y **Resultado**, y los paneles
inferiores se llaman **Comprobaciones** y **Entregas**.

El comando `python manage.py seed_web --owner PROFESOR --cohort 1SMR`
crea el itinerario local v2 de doce retos de entrada para `0228 Aplicaciones
web`. El comando `python manage.py seed_bash --owner PROFESOR --cohort 2ASIR`
crea el itinerario local v2 de doce retos de apoyo transversal para el módulo
0378. No crea alumnos y no asigna RA/CE. Véase
[`docs/BASH_TRACK.md`](BASH_TRACK.md) para el catálogo, la DSL y sus límites.

El comando `python manage.py seed_python --owner PROFESOR --cohort 2DAM`
crea el itinerario local v2 de doce retos progresivos de preparación para `0491 Sistemas de gestión
empresarial` de segundo de DAM, desde variables hasta lectura y escritura de
archivos. Es un alineamiento parcial del currículo navarro y no una cobertura
completa de RA/CE ni una integración con Odoo. Véase
[`docs/PYTHON_TRACK.md`](PYTHON_TRACK.md) para el catálogo, la DSL y sus límites.

El detalle de workspace añade a `version` `language`, `difficulty`, `xp_reward`
e `hints`, y un objeto superior `gamification`. El dashboard del alumno añade
en cada asignación `language`, `difficulty`, `xp_reward`, `earned_xp`,
`completed` y `progress`, además de:

```json
{
  "gamification": {
    "total_xp": 0,
    "level": 1,
    "level_progress": 0,
    "xp_to_next_level": 500,
    "completed_challenges": 0,
    "badges": []
  }
}
```

El XP lo calcula el servidor con el mejor resultado automático válido de cada
asignación (`floor(xp_reward * score / 10)`), por lo que repetir entregas en
esa asignación no lo aumenta. Un reto se considera completado desde 8/10. Esta métrica es
independiente de las calificaciones oficiales publicadas y no genera rankings.
Las insignias `web-path`, `bash-path` y `python-path` indican itinerarios
completados; `cross-path` se obtiene con al menos dos y `triple-path` con los
tres.

## Operación administrativa

La primera cuenta se crea con `python manage.py createsuperuser`. Después, la
interfaz `/admin-ui/users/` permite alta, edición, desactivación y reset de
contraseña temporal. La contraseña temporal obliga a pasar por el cambio de
contraseña antes de poder usar el resto de la aplicación. En Django Admin,
usuarios, matrículas, enlaces entre grupos y retos, evidencias de entrega,
resultados y cálculos de nota quedan como consulta: las mutaciones académicas
se realizan desde el panel local o los comandos de catálogo, que sí aplican
los servicios y sus validaciones.
Desde el alta o edición, el administrador debe elegir el ciclo e itinerario de
cada alumno; no se crean matrículas implícitas por pertenecer a la instalación.

## Evaluador estático

HTML se analiza con BeautifulSoup/html5lib, CSS con tinycss2, JavaScript con
el AST de esprima, Bash con `tree-sitter-bash` y Python con el módulo estándar
`ast`. No se evalúa ni ejecuta el árbol Python, no se genera bytecode y no se
usa `eval`, `exec`, `vm`, una plantilla Django ni un proceso del sistema para
ejecutar código del alumno. La DSL valida tipos y
campos desconocidos antes de evaluar y limita cada archivo a 256 KiB, el
conjunto a 1 MiB y una versión a 200 tests. Los parsers Bash y Python se
ejecutan en memoria, una vez por lote, con límites adicionales de 5.000 nodos
y 80 niveles de profundidad; no abren shell, red, archivos ni subprocesos.
Los tests Python de `file_opened` solo reconocen el `open` incorporado (si no
está sombreado) o `.open()` sobre una instancia estructuralmente reconocible
de `pathlib.Path`/`PurePath`, además de su modo, codificación y contexto
`with`: nunca abren las rutas ni leen o escriben su contenido. Los predicados
adicionales de la DSL (`function_declared`, `node_kind`, `call_used`,
`attribute_used`, `subscript_used`, `dict_keys`, `loop_target`,
`exception_handled` y `comparison_used`) solo inspeccionan nodos AST y no
convierten el análisis en una ejecución del programa.

La evaluación de comportamiento DOM queda fuera de esta fase. Los proyectos
que la necesiten deben usar rúbrica/manual hasta incorporar un runner aislado
revisado.

## Trazabilidad curricular

`ActivityVersion` conserva `professional_module_code` (por ejemplo 0228 para
Web, 0378 para el apoyo Bash o 0491 para la preparación Python),
`curriculum_scope`, `curriculum_edition`, `curriculum_source`,
`learning_outcomes` y `assessment_criteria`. El contenido de demo declara solo
`RA1.b`, `RA1.d` y `RA1.g` del marco navarro, porque los archivos iniciales de
la prueba vertical no evidencian el resto del RA1. La fuente se deja versionada
para poder distinguir modificaciones futuras del currículo.
