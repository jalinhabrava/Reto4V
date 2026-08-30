# Backend Django de Reto4V

## Desarrollo y despliegue

```bash
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 0.0.0.0:8000
```

La configuración local usa SQLite (`data/db.sqlite3`). En WSL/Compose se
configura PostgreSQL mediante `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` y
`DB_PORT` (o `DATABASE_URL`).

`seed_demo` es idempotente. Cuando crea cuentas genera contraseñas aleatorias,
las muestra una sola vez y solo guarda el hash Argon2id. Se pueden proporcionar
contraseñas explícitas con `--admin-password`, `--teacher-password` y
`--student-password`; nunca se escriben en exportaciones ni logs.

## Contrato del workspace

Todas las rutas mutables requieren sesión autenticada, rol de alumno y CSRF.
El servidor comprueba además matrícula, ventana de entrega y versión de la
actividad; no confía en el cliente para permisos ni para notas oficiales.

| Método | Ruta | Uso |
|---|---|---|
| GET | `/assignments/<uuid>/` | Pantalla HTML del workspace; el bootstrap no incluye tests privados. |
| GET | `/api/assignments/<uuid>/` | Actividad, versión, archivos iniciales, borrador y entregas propias. |
| GET | `/api/assignments/<uuid>/draft/` | Borrador actual y su `revision`; también entrega la cookie CSRF. |
| POST | `/api/assignments/<uuid>/draft/` | Autosave `{html, css, javascript, revision}`. Devuelve la revisión nueva; ante conflicto responde `409` con `current`. |
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

Una `ActivityVersion` puede declarar `language: "web"` o `language: "bash"`,
`difficulty: "beginner" | "intermediate" | "advanced"`, `xp_reward` (0–1000)
y una lista de `hints`. Las versiones web solo aceptan `html`, `css` y
`javascript`; las versiones Bash solo aceptan `bash`. La respuesta
`version.files` devuelve exclusivamente las claves del lenguaje de la
actividad.

El comando opcional `python manage.py seed_bash --owner PROFESOR --cohort 2ASIR`
crea el itinerario local de doce retos de apoyo transversal para el módulo
0378. No crea alumnos y no asigna RA/CE. Véase
[`docs/BASH_TRACK.md`](BASH_TRACK.md) para el catálogo, la DSL y sus límites.

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
asignación (`floor(xp_reward * score / 10)`), por lo que repetir entregas no
lo aumenta. Un reto se considera completado desde 8/10. Esta métrica es
independiente de las calificaciones oficiales publicadas y no genera rankings.

## Operación administrativa

La primera cuenta se crea con `python manage.py createsuperuser`. Después, la
interfaz `/admin-ui/users/` permite alta, edición, desactivación y reset de
contraseña temporal. La contraseña temporal obliga a pasar por el cambio de
contraseña antes de poder usar el resto de la aplicación. Las evidencias de
entrega, resultados y cálculos de nota son de solo lectura en Django Admin.

## Evaluador estático

HTML se analiza con BeautifulSoup/html5lib, CSS con tinycss2, JavaScript con
el AST de esprima y Bash con `tree-sitter-bash`. No se usa `eval`, `exec`,
`vm`, una plantilla Django ni un proceso del sistema para ejecutar código del
alumno. La DSL valida tipos y campos desconocidos antes de evaluar y limita
cada archivo a 256 KiB, el conjunto a 1 MiB y una versión a 200 tests. El
parser Bash se ejecuta en memoria, una vez por lote, con límites adicionales
de 5.000 nodos y 80 niveles de profundidad; no abre shell, red, archivos ni
subprocesos.

La evaluación de comportamiento DOM queda fuera de esta fase. Los proyectos
que la necesiten deben usar rúbrica/manual hasta incorporar un runner aislado
revisado.

## Trazabilidad curricular

`ActivityVersion` conserva `professional_module_code` (0228),
`curriculum_scope`, `curriculum_edition`, `curriculum_source`,
`learning_outcomes` y `assessment_criteria`. El contenido de demo declara solo
`RA1.b`, `RA1.d` y `RA1.g` del marco navarro, porque los archivos iniciales de
la prueba vertical no evidencian el resto del RA1. La fuente se deja versionada
para poder distinguir modificaciones futuras del currículo.
