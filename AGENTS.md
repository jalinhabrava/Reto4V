# Programmy4V

Plataforma LAN de retos de programación para FP: web para SMR, scripting Bash
de apoyo a Seguridad y alta disponibilidad de ASIR, y Python introductorio para
Sistemas de gestión empresarial de DAM.

La marca visible es Programmy4V. Los identificadores históricos del repositorio
(incluidos el módulo Django `aulaweb`, los nombres Compose y las rutas/scripts)
se conservan para mantener la compatibilidad de despliegues existentes.

## Reglas del proyecto

- Mantén Django, React y PostgreSQL; SQLite se utiliza para desarrollo y tests.
- Todas las operaciones académicas pasan por permisos y servicios Django.
  No alteres evidencias, versiones asignadas o cálculos mediante SQL directo.
- Nunca ejecutes código del alumno en Python, Bash, Node ni el sistema host.
  Bash utiliza un análisis sintáctico estático, Python utiliza `ast` en memoria
  y la preview web vive aislada.
- No concedas acceso al socket Docker a la aplicación o a estudiantes.
- XP, niveles e insignias son feedback formativo, no calificaciones oficiales.
- No publiques secretos, bases de datos, entregas, capturas con datos reales o
  credenciales en código, ejemplos, historial Git o informes.
- Conserva migrations aditivas y compatibilidad de las actividades web.
- Los contenidos Bash son apoyo transversal a 0378; no inventes equivalencias
  con RA/CE ni presentes los tests estructurales como pruebas de ejecución.
- Los contenidos Python son una preparación parcial para 0491; lee
  `docs/PYTHON_TRACK.md` antes de modificar el corrector o los retos Python.
  No inventes equivalencias con RA/CE ni presentes el análisis estructural
  como ejecución, acceso a Odoo o prueba de lectura/escritura real.
- No fabriques datos de progreso. Verifica cambios con tests y lectura real.
- El catálogo inicial se precarga de forma idempotente al arrancar `web` cuando
  `PRELOAD_CATALOGS=1`; no se crean alumnos ni credenciales de demostración.
  Un alumno debe tener un único ciclo e itinerario activo asignado desde la
  administración local para recibir el primer reto.
- Cambia tanto el contrato backend como la interfaz y su documentación.

## Mapa

| Área | Responsabilidad |
| --- | --- |
| `accounts/` | Identidad local, roles y gestión de usuarios |
| `learning/` | Currículo, actividades versionadas, asignaciones y APIs |
| `grading/` | Parsers, entregas, evaluación, XP y calificaciones |
| `frontend/` y `templates/` | Interfaz, editor y bootstrap seguro |
| `scripts/` y `compose.yaml` | Instalación, operación y recuperación |

Las rutas de sesión y workspace están documentadas en
`docs/BACKEND_API.md` y `frontend/API_CONTRACT.md`. Lee `docs/BASH_TRACK.md`
antes de modificar el corrector o los retos Bash, `docs/PYTHON_TRACK.md`
antes de modificar el corrector o los retos Python, y `SECURITY.md` antes de
cambiar el aislamiento o el despliegue.

## Comprobaciones

```bash
uv sync --all-groups --frozen
uv run pytest -q
uv run python -m unittest discover -s tests -v
uv run ruff check .
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
npm ci
npm test
npm run build
```

Prueba también login, autosave, tests, entrega, progreso y revisión/CSV con
datos ficticios. Comprueba la interfaz en escritorio y móvil. No declares un
despliegue validado sin haberlo arrancado en su entorno objetivo.
