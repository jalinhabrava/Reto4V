# Contrato de integración de Reto4V

El bundle React se sirve desde las plantillas Django y usa únicamente rutas relativas del mismo origen. La sesión se entrega en `user-data` (o en `aulaweb-bootstrap`) mediante `json_script`; nunca se persiste en `localStorage`.

## Conceptos compartidos

Cada actividad publicada pertenece a un itinerario:

- `language: "web"`: editor de `html`, `css` y `javascript` para el módulo de Aplicaciones web de SMR.
- `language: "bash"`: editor de un único archivo `bash` (`script.sh`) para scripting y seguridad de ASIR. El navegador no ejecuta este archivo.

La versión puede incluir `difficulty` (`beginner`, `intermediate`, `advanced`), `xp_reward` (entero no negativo) y `hints` (lista de textos u objetos). El cliente no inventa puntos, insignias ni progreso en producción: si un dato no llega, muestra un estado vacío o cero.

## Bootstrap de Django

En las plantillas de dashboard y workspace:

```django
{{ user_payload|json_script:"user-data" }}
{{ workspace|json_script:"workspace-data" }}
```

El usuario necesita, como mínimo, `id`, `username`, `display_name`, `role` (`student`, `teacher` o `admin`) y `groups` (lista).

## Sesión

- `POST /login/`: formulario URL-encoded `{username, password}` y cabecera `X-CSRFToken`. En éxito Django redirige a `/student/dashboard/` o `/teacher/dashboard/`.
- `POST /logout/`: requiere sesión y CSRF. La respuesta puede redirigir a `/login/`.

## Dashboard del alumno

`GET /api/student/dashboard/` con `Accept: application/json` devuelve:

```json
{
  "assignments": [
    {
      "id": "uuid",
      "title": "Copia segura con Bash",
      "status": "in_progress",
      "due_at": null,
      "module": "Seguridad",
      "language": "bash",
      "difficulty": "intermediate",
      "xp_reward": 90,
      "earned_xp": 40,
      "completed": false,
      "progress": 45
    }
  ],
  "gamification": {
    "total_xp": 420,
    "level": 1,
    "level_progress": 84,
    "xp_to_next_level": 80,
    "completed_challenges": 7,
    "badges": [
      {"id": "first-script", "title": "Primer script", "description": "…"}
    ]
  }
}
```

`completed` debe significar dominio según la política académica del servidor; una entrega corregida no equivale automáticamente a reto completado. `earned_xp` y `progress` son independientes de la nota publicada.

El filtro `Todos`, `Web · SMR`, `Bash · ASIR` se aplica sobre `language` y no altera los datos del servidor.

## Navegación cliente

El editor se abre en `/assignments/<uuid>/` mediante `history.pushState`, sin desmontar la shell React ni perder el borrador local. La ruta Django también sirve esa URL para que una recarga reconstruya el workspace desde `workspace-data`. El botón de vuelta y el botón atrás del navegador restauran el dashboard; al volver, el cliente solicita de nuevo `/api/student/dashboard/` para actualizar XP, progreso y entregas.

## Dashboard docente

- `GET /teacher/dashboard/` con `Accept: application/json` → `{ "assignments": [{ "id", "title", "submissions", "graded", "language", "difficulty", "xp_reward" }], "reviews": [], "pending_reviews": 0 }`.
- `GET /teacher/exports/?format=long|wide` → CSV UTF-8 con BOM y separador `;`. El cliente conserva este enlace y no reinterpreta ni recalcula las notas.

## Workspace

`GET /api/assignments/<uuid>/` → detalle público de la asignación:

```json
{
  "id": "uuid",
  "title": "Copia segura con Bash",
  "max_attempts": 3,
  "activity": {"title": "Copia segura con Bash", "module": "Seguridad"},
  "version": {
    "language": "bash",
    "difficulty": "intermediate",
    "xp_reward": 90,
    "instructions": "Texto sanitizado de la actividad",
    "objectives": ["…"],
    "hints": ["…"],
    "files": {"bash": "#!/usr/bin/env bash\n"},
    "public_tests": [{"id": "uuid", "name": "Declara Bash", "points": "2"}]
  },
  "draft": {"files": {"bash": "…"}, "revision": 4},
  "gamification": {"assignment_id": "uuid", "language": "bash", "difficulty": "intermediate", "xp_reward": 90, "earned_xp": 40, "best_score": "8.50", "completed": false, "progress": 45},
  "submissions": [{"id": "uuid", "attempt_number": 1, "submitted_at": "…", "published_score": "8.50"}]
}
```

Para `language: "web"`, `files` conserva las claves `{html, css, javascript}` y el editor mantiene la preview aislada.

En el workspace, `gamification` es el resumen del reto actual (no el total del alumno); el total, nivel e insignias globales solo aparecen en el dashboard.

- `POST /api/assignments/<uuid>/draft/`: web `{html, css, javascript, revision}`; Bash `{bash, revision}`. El servidor valida tamaño, compara `revision`/`If-Match` y devuelve `{revision, saved_at}`. En conflicto responde HTTP `409` con `{detail, revision, current:{files, updated_at}}`.
- `POST /api/assignments/<uuid>/tests/`: recibe las mismas claves de archivos según `language` y devuelve `{score, passed_points, total_points, results}`. Para Bash la validación es estática y nunca ejecuta el script.
- `POST /api/assignments/<uuid>/submit/`: recibe las mismas claves. Devuelve HTTP `201` con `{submission:{id, attempt_number, submitted_at, status, is_late}, report:{score, results}, gamification?}`. La evidencia es inmutable.

Todas las mutaciones incluyen la cookie CSRF mediante `X-CSRFToken`. El cliente no muestra nunca tests privados.

## Preview y seguridad

Solo las actividades web se escriben en `iframe[srcDoc]` con `sandbox="allow-scripts"`, sin `allow-same-origin`, y con CSP interna sin red (`connect-src 'none'`). El puente de consola envía mensajes `postMessage` con canal `aulaweb-preview`; la aplicación acepta únicamente mensajes cuya ventana emisora sea el iframe actual, limita el tamaño y trata todos los valores como texto no fiable.

Las actividades Bash muestran una revisión estática local (líneas, variables y patrones orientativos) claramente marcada como no ejecución. La validación oficial y la calificación proceden del servidor.
