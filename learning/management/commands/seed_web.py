"""Seed the local HTML/CSS/JavaScript catalogue for first-year SMR.

The catalogue is a practical, partial introduction to the code-related part
of the Navarra web applications module (0228).  It deliberately does not
claim to cover the module's CMS, LMS or deployment outcomes.  Evaluation is
static and declarative: no student preview or submission is executed here.
"""

from __future__ import annotations

from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from learning.models import (
    AcademicYear,
    Activity,
    ActivityVersion,
    Assignment,
    AssignmentCohort,
    Cohort,
    Course,
    Module,
    TeachingAssignment,
    TestCase,
)

from ._catalog import ensure_cohort_track, get_or_create_catalog_assignment

TRACK_SLUG = "fundamentos-web-smr"
CURRICULUM_SOURCE = "https://www.lexnavarra.navarra.es/detalle.asp?r=9129"


def _test(name, test_type, definition, points=1, visibility=TestCase.Visibility.PUBLIC):
    return (name, test_type, definition, points, visibility)


_WEB_STARTER = {
    "html": "<!doctype html>\n<html lang=\"es\">\n  <head><meta charset=\"utf-8\"><title>Mi práctica</title></head>\n  <body>\n    <!-- Completa la estructura HTML. -->\n  </body>\n</html>\n",
    "css": "/* Añade los estilos del reto. */\n",
    "javascript": "// Añade el comportamiento del reto.\n",
}


CHALLENGES = [
    {
        "slug": "01-estructura-semantica",
        "title": "01 · Estructura semántica",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 100,
        "theory": "Las etiquetas semánticas describen el papel de cada bloque y ayudan a mantener una página comprensible.",
        "task": "Crea una cabecera con un título y un elemento main para el panel de inventario.",
        "ra": ["RA1"],
        "ce": ["RA1.b", "RA1.d"],
        "html": "<!doctype html>\n<html lang=\"es\">\n  <head><meta charset=\"utf-8\"><title>Inventario</title></head>\n  <body>\n    <header><h1>Panel de inventario</h1></header>\n    <main><p>Consulta los productos disponibles.</p></main>\n  </body>\n</html>\n",
        "css": "body { font-family: sans-serif; }\n",
        "javascript": "",
        "tests": [
            _test("Elemento main", "html.selector_exists", {"selector": "main"}),
            _test("Título del panel", "html.text_contains", {"selector": "h1", "expected": "Panel de inventario"}),
            _test("Idioma declarado", "html.attribute_equals", {"selector": "html", "attribute": "lang", "expected": "es"}),
            _test("Orden semántico", "html.element_order", {"first": "header", "second": "main"}),
        ],
    },
    {
        "slug": "enlaces-y-atributos",
        "title": "02 · Enlaces y atributos",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 110,
        "theory": "Los atributos aportan información adicional a los elementos. Un enlace debe indicar con claridad el destino que abrirá.",
        "task": "Construye una navegación con dos enlaces y etiqueta su propósito mediante aria-label.",
        "ra": ["RA1"],
        "ce": ["RA1.b", "RA1.d"],
        "html": "<nav aria-label=\"Principal\">\n  <a href=\"/inicio\">Inicio</a>\n  <a href=\"/productos\">Productos</a>\n</nav>\n",
        "css": "nav { display: flex; gap: 1rem; }\n",
        "javascript": "",
        "tests": [
            _test("Dos enlaces", "html.selector_count", {"selector": "nav a", "expected": 2}),
            _test("Etiqueta de navegación", "html.attribute_equals", {"selector": "nav", "attribute": "aria-label", "expected": "Principal"}),
            _test("Destino de productos", "html.attribute_equals", {"selector": "a[href='/productos']", "attribute": "href", "expected": "/productos"}),
            _test("Enlace de inicio", "html.attribute_equals", {"selector": "a[href='/inicio']", "attribute": "href", "expected": "/inicio"}),
        ],
    },
    {
        "slug": "listas-y-tablas",
        "title": "03 · Listas y tablas de datos",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 120,
        "theory": "Las listas sirven para colecciones y las tablas para datos relacionados por filas y columnas.",
        "task": "Muestra tres productos en una lista y prepara una tabla para sus existencias.",
        "ra": ["RA1"],
        "ce": ["RA1.b", "RA1.d"],
        "html": "<section id=\"productos\">\n  <h2>Productos</h2>\n  <ul><li>Teclado</li><li>Ratón</li><li>Monitor</li></ul>\n  <table><thead><tr><th>Producto</th><th>Stock</th></tr></thead><tbody><tr><td>Teclado</td><td>8</td></tr></tbody></table>\n</section>\n",
        "css": "#productos { padding: 1rem; }\ntable { border-collapse: collapse; }\n",
        "javascript": "",
        "tests": [
            _test("Tres productos", "html.selector_count", {"selector": "#productos li", "expected": 3}),
            _test("Tabla de existencias", "html.selector_exists", {"selector": "#productos table"}),
            _test("Encabezado de sección", "html.text_contains", {"selector": "#productos h2", "expected": "Productos"}),
            _test("Tabla después del listado", "html.element_order", {"first": "ul", "second": "table"}),
        ],
    },
    {
        "slug": "formularios-accesibles",
        "title": "04 · Formularios accesibles",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 130,
        "theory": "Un formulario usable relaciona cada control con su etiqueta y ofrece un tipo de dato apropiado.",
        "task": "Crea un formulario de alta de producto con un campo de correo obligatorio y un botón de envío.",
        "ra": ["RA1"],
        "ce": ["RA1.b", "RA1.d"],
        "html": "<form action=\"/guardar\" method=\"post\">\n  <label for=\"email\">Correo del responsable</label>\n  <input id=\"email\" name=\"email\" type=\"email\" required>\n  <button type=\"submit\">Guardar</button>\n</form>\n",
        "css": "form { display: grid; gap: .75rem; max-width: 28rem; }\n",
        "javascript": "",
        "tests": [
            _test("Etiqueta asociada", "html.attribute_equals", {"selector": "label", "attribute": "for", "expected": "email"}),
            _test("Entrada de correo", "html.attribute_equals", {"selector": "#email", "attribute": "type", "expected": "email"}),
            _test("Campo obligatorio", "html.selector_exists", {"selector": "input[required]"}),
            _test("Destino del formulario", "html.attribute_equals", {"selector": "form", "attribute": "action", "expected": "/guardar"}),
        ],
    },
    {
        "slug": "multimedia-responsiva",
        "title": "05 · Multimedia y alternativas",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 140,
        "theory": "Las imágenes y los recursos multimedia deben incluir alternativas o controles para que la información no dependa de un único sentido.",
        "task": "Añade una imagen con texto alternativo y un audio con controles dentro de una figura explicativa.",
        "ra": ["RA1"],
        "ce": ["RA1.e"],
        "html": "<figure>\n  <img src=\"producto.webp\" alt=\"Captura del producto\">\n  <figcaption>Vista previa del producto.</figcaption>\n</figure>\n<audio controls src=\"explicacion.mp3\">Descripción de audio</audio>\n",
        "css": "img { max-width: 100%; height: auto; }\n",
        "javascript": "",
        "tests": [
            _test("Imagen", "html.selector_exists", {"selector": "figure img"}),
            _test("Texto alternativo", "html.attribute_equals", {"selector": "figure img", "attribute": "alt", "expected": "Captura del producto"}),
            _test("Controles de audio", "html.selector_exists", {"selector": "audio[controls]"}),
            _test("Pie de figura", "html.text_contains", {"selector": "figcaption", "expected": "Vista previa"}),
        ],
    },
    {
        "slug": "html-limpio-y-valido",
        "title": "06 · HTML limpio y mantenible",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 150,
        "theory": "Una estructura limpia favorece la interoperabilidad y permite separar contenido, presentación y comportamiento.",
        "task": "Presenta una noticia con article, título, párrafo y fecha mediante time. Evita etiquetas de presentación obsoletas.",
        "ra": ["RA1"],
        "ce": ["RA1.c", "RA1.d"],
        "html": "<article>\n  <h2>Nuevo catálogo</h2>\n  <p>El equipo ha actualizado los datos de productos.</p>\n  <time datetime=\"2026-09-01\">1 de septiembre de 2026</time>\n</article>\n",
        "css": "article { line-height: 1.6; }\n",
        "javascript": "",
        "tests": [
            _test("Artículo", "html.selector_exists", {"selector": "article"}),
            _test("Fecha ISO", "html.attribute_equals", {"selector": "time", "attribute": "datetime", "expected": "2026-09-01"}),
            _test("Sin font obsoleto", "html.forbidden_element_absent", {"selector": "font"}),
            _test("Título antes del texto", "html.element_order", {"first": "article h2", "second": "article p"}),
        ],
    },
    {
        "slug": "css-selectores-y-color",
        "title": "07 · Selectores y color",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 160,
        "theory": "Los selectores conectan reglas CSS con elementos HTML. Las declaraciones deben expresar una decisión visual concreta.",
        "task": "Diseña la tarjeta de un producto con una paleta legible y un fondo suave.",
        "ra": ["RA1"],
        "ce": ["RA1.f", "RA1.g"],
        "html": "<article class=\"card\"><h2>Producto</h2><p>Descripción breve.</p></article>\n",
        "css": ".card { color: #16324f; background-color: #f7f9fc; }\n",
        "javascript": "",
        "tests": [
            _test("Selector de tarjeta", "css.selector_exists", {"selector": ".card"}),
            _test("Color de texto", "css.declaration_equals", {"selector": ".card", "property": "color", "expected": "#16324f"}),
            _test("Fondo suave", "css.declaration_equals", {"selector": ".card", "property": "background-color", "expected": "#f7f9fc"}),
            _test("Contenido de tarjeta", "html.selector_exists", {"selector": ".card h2"}),
        ],
    },
    {
        "slug": "css-modelo-de-caja",
        "title": "08 · Modelo de caja y layout",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 170,
        "theory": "El modelo de caja combina espacio interior, borde y separación exterior. Flex y grid permiten organizar interfaces sin recurrir a posiciones frágiles.",
        "task": "Construye una cuadrícula de dos columnas con separación y una tarjeta con espacio interior.",
        "ra": ["RA1"],
        "ce": ["RA1.f", "RA1.g"],
        "html": "<div class=\"layout\"><aside>Filtros</aside><main><section class=\"panel\">Resultados</section></main></div>\n",
        "css": ".layout { display: grid; grid-template-columns: 1fr 2fr; gap: 1rem; }\n.panel { padding: 1.5rem; border-radius: .75rem; }\n",
        "javascript": "",
        "tests": [
            _test("Layout grid", "css.declaration_equals", {"selector": ".layout", "property": "display", "expected": "grid"}),
            _test("Columnas proporcionadas", "css.declaration_equals", {"selector": ".layout", "property": "grid-template-columns", "expected": "1fr 2fr"}),
            _test("Separación de columnas", "css.declaration_equals", {"selector": ".layout", "property": "gap", "expected": "1rem"}),
            _test("Espacio de panel", "css.declaration_equals", {"selector": ".panel", "property": "padding", "expected": "1.5rem"}),
        ],
    },
    {
        "slug": "css-responsive",
        "title": "09 · Diseño responsive",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 180,
        "theory": "Una interfaz debe adaptarse a distintas anchuras. Las media queries permiten cambiar la composición sin duplicar el contenido.",
        "task": "Añade una media query para convertir el layout en una columna en pantallas estrechas y define un estado hover para el botón.",
        "ra": ["RA1"],
        "ce": ["RA1.f", "RA1.g"],
        "html": "<div class=\"layout\"><main>Contenido</main><aside><button class=\"button\">Guardar</button></aside></div>\n",
        "css": "@media (max-width: 720px) { .layout { grid-template-columns: 1fr; } }\n.button:hover { background-color: #0f766e; }\n",
        "javascript": "",
        "tests": [
            _test("Media query móvil", "css.media_query_exists", {"query": "(max-width: 720px)"}),
            _test("Estado hover", "css.selector_exists", {"selector": ".button:hover"}),
            _test("Color interactivo", "css.declaration_equals", {"selector": ".button:hover", "property": "background-color", "expected": "#0f766e"}),
            _test("Botón del panel", "html.selector_exists", {"selector": ".button"}),
        ],
    },
    {
        "slug": "javascript-funciones-y-datos",
        "title": "10 · Variables y funciones JavaScript",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 190,
        "theory": "Las variables guardan el estado y las funciones encapsulan operaciones reutilizables de la interfaz.",
        "task": "Declara un total inicial y una función calcularTotal que reciba precio y cantidad.",
        "ra": ["RA1"],
        "ce": ["RA1.h"],
        "html": "<main><h1>Carrito</h1></main>\n",
        "css": "main { max-width: 40rem; }\n",
        "javascript": "const total = 0;\nfunction calcularTotal(precio, cantidad) {\n  return precio * cantidad;\n}\n",
        "tests": [
            _test("JavaScript válido", "js.syntax_valid", {}),
            _test("Variable total", "js.variable_declared", {"name": "total"}),
            _test("Función de cálculo", "js.function_declared", {"name": "calcularTotal"}),
            _test("Sin ejecución dinámica", "js.forbidden_api_absent", {"api": "eval"}),
        ],
    },
    {
        "slug": "javascript-eventos-dom",
        "title": "11 · Eventos del DOM",
        "difficulty": ActivityVersion.Difficulty.ADVANCED,
        "xp": 210,
        "theory": "Los eventos conectan las acciones de la persona con el comportamiento de la página. Un listener explícito facilita revisar esa relación.",
        "task": "Selecciona el botón guardar y registra un listener click que actualice la interfaz.",
        "ra": ["RA1"],
        "ce": ["RA1.h"],
        "html": "<button id=\"guardar\" type=\"button\">Guardar</button><p id=\"estado\"></p>\n",
        "css": "button { cursor: pointer; }\n",
        "javascript": "const boton = document.querySelector('#guardar');\nconst estado = document.querySelector('#estado');\nboton.addEventListener('click', () => {\n  estado.textContent = 'Guardado';\n});\n",
        "tests": [
            _test("JavaScript válido", "js.syntax_valid", {}),
            _test("Botón seleccionado", "js.variable_declared", {"name": "boton"}),
            _test("Evento click", "js.event_listener_registered", {"event": "click"}),
            _test("Sin API peligrosa", "js.forbidden_api_absent", {"api": "document.write"}),
        ],
    },
    {
        "slug": "panel-integrado-web",
        "title": "12 · Panel web integrado",
        "difficulty": ActivityVersion.Difficulty.ADVANCED,
        "xp": 240,
        "theory": "Una interfaz completa combina estructura semántica, decisiones visuales y comportamiento pequeño pero claro.",
        "task": "Integra una tarjeta de estado con un botón que muestre un mensaje al pulsarlo. Mantén separadas las tres capas.",
        "ra": ["RA1"],
        "ce": ["RA1.b", "RA1.f", "RA1.g", "RA1.h"],
        "html": "<!doctype html>\n<html lang=\"es\"><body>\n  <main class=\"app\"><article class=\"status-card\"><h1>Estado del sistema</h1><p id=\"mensaje\">Pendiente</p><button id=\"comprobar\" type=\"button\">Comprobar</button></article></main>\n</body></html>\n",
        "css": ".app { min-height: 100vh; display: grid; place-items: center; }\n.status-card { padding: 2rem; background: #ffffff; }\n",
        "javascript": "function actualizarEstado() {\n  document.querySelector('#mensaje').textContent = 'Todo correcto';\n}\nconst comprobar = document.querySelector('#comprobar');\ncomprobar.addEventListener('click', actualizarEstado);\n",
        "tests": [
            _test("Contenedor principal", "html.selector_exists", {"selector": "main.app"}),
            _test("Tarjeta de estado", "html.selector_exists", {"selector": ".status-card"}),
            _test("Layout centrado", "css.declaration_equals", {"selector": ".app", "property": "place-items", "expected": "center"}),
            _test("Función de estado", "js.function_declared", {"name": "actualizarEstado"}),
            _test("Evento de comprobación", "js.event_listener_registered", {"event": "click"}),
        ],
    },
]


class Command(BaseCommand):
    help = "Crea el itinerario local de 12 retos HTML/CSS/JavaScript para SMR (módulo 0228)."

    def add_arguments(self, parser):
        parser.add_argument("--owner", required=True, help="Usuario profesor o administrador propietario del contenido.")
        parser.add_argument("--cohort", default="1SMR", help="Grupo al que se asignan los retos (por defecto: 1SMR).")
        parser.add_argument("--academic-year", default=None, help="Curso académico; si se omite se calcula desde la fecha actual.")

    def _academic_year_name(self, value):
        if value:
            return value
        today = date.today()
        start = today.year if today.month >= 9 else today.year - 1
        return f"{start}-{start + 1}"

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            owner = User.objects.get(username=options["owner"])
        except User.DoesNotExist as exc:
            raise CommandError(f"No existe la cuenta propietaria {options['owner']!r}.") from exc
        if not (owner.is_superuser or owner.role in {User.Role.ADMIN, User.Role.TEACHER}):
            raise CommandError("--owner debe ser una cuenta de profesor o administrador.")

        year, _ = AcademicYear.objects.get_or_create(
            name=self._academic_year_name(options.get("academic_year")),
            defaults={"active": True},
        )
        cohort, _ = Cohort.objects.get_or_create(
            name=options["cohort"],
            academic_year=year,
            defaults={"active": True, "track": Cohort.Track.WEB},
        )
        ensure_cohort_track(cohort, Cohort.Track.WEB)
        if owner.role == User.Role.TEACHER and not owner.is_superuser:
            TeachingAssignment.objects.get_or_create(cohort=cohort, teacher=owner, defaults={"active": True})

        course, _ = Course.objects.get_or_create(
            slug=TRACK_SLUG,
            defaults={
                "title": "Aplicaciones web · SMR",
                "description": "Retos progresivos de HTML, CSS y JavaScript para el módulo 0228 Aplicaciones web.",
                "created_by": owner,
                "active": True,
            },
        )
        module, _ = Module.objects.get_or_create(
            course=course,
            position=1,
            defaults={
                "title": "Fundamentos de interfaz web",
                "description": "Estructura, presentación y comportamiento web; cobertura parcial del código del RA1.",
                "weight": 100,
            },
        )

        created_versions = 0
        existing_versions = 0
        for index, item in enumerate(CHALLENGES, start=1):
            activity, _ = Activity.objects.get_or_create(
                module=module,
                slug=item["slug"],
                defaults={
                    "title": item["title"],
                    "kind": Activity.Kind.CODE,
                    "status": Activity.Status.PUBLISHED,
                    "created_by": owner,
                },
            )
            if index <= 6:
                starter_files = dict(_WEB_STARTER)
            elif index <= 9:
                starter_files = {"html": item["html"], "css": "", "javascript": ""}
            else:
                starter_files = {"html": item["html"], "css": item["css"], "javascript": ""}
            version, version_created = ActivityVersion.objects.get_or_create(
                activity=activity,
                version_number=1,
                defaults={
                    "language": ActivityVersion.Language.WEB,
                    "difficulty": item["difficulty"],
                    "xp_reward": item["xp"],
                    "hints": [
                        "Separa HTML, CSS y JavaScript en sus archivos correspondientes.",
                        "Comprueba primero que exista el elemento o selector pedido.",
                        "El corrector inspecciona la estructura y no ejecuta tu código.",
                    ],
                    "instructions": f"## Teoría\n{item['theory']}\n\n## Reto\n{item['task']}\n\n> El corrector analiza los archivos de forma estática; no se ejecuta código del alumnado.",
                    "objectives": [
                        "Separar estructura HTML, presentación CSS y comportamiento JavaScript",
                        "Aplicar patrones de interfaz accesibles y responsive",
                        "Leer un corrector declarativo como una lista de requisitos verificables",
                    ],
                    "learning_outcomes": item["ra"],
                    "assessment_criteria": item["ce"],
                    "professional_module_code": "0228",
                    "curriculum_scope": "Navarra · cobertura parcial",
                    "curriculum_edition": "navarra-2025",
                    "curriculum_unit": "",
                    "curriculum_source": CURRICULUM_SOURCE,
                    "starter_files": starter_files,
                    "reference_solution": {"html": item["html"], "css": item["css"], "javascript": item["javascript"]},
                    "grading_mode": ActivityVersion.GradingMode.AUTOMATIC_STATIC,
                    "auto_weight": "1.0000",
                    "manual_weight": "0.0000",
                    "created_by": owner,
                },
            )
            if version_created:
                created_versions += 1
            else:
                existing_versions += 1
            if activity.current_version_id is None:
                activity.current_version = version
                activity.status = Activity.Status.PUBLISHED
                activity.save(update_fields=["current_version", "status", "updated_at"])

            # Assigned versions are immutable.  Fill tests only while a
            # version is still unassigned; this keeps an existing installation
            # safe when the bootstrap command is run on every restart.
            if not version.assignments.exists():
                for position, (name, test_type, definition, points, visibility) in enumerate(item["tests"]):
                    TestCase.objects.get_or_create(
                        activity_version=version,
                        name=name,
                        defaults={
                            "type": test_type,
                            "definition": definition,
                            "points": points,
                            "visibility": visibility,
                            "feedback": "Revisa la estructura indicada en el enunciado.",
                            "position": position,
                        },
                    )
            assignment, _ = get_or_create_catalog_assignment(
                activity=activity,
                version=version,
                defaults={
                    "status": Assignment.Status.PUBLISHED,
                    "created_by": owner,
                    "attempt_policy": Assignment.AttemptPolicy.BEST,
                    "max_attempts": None,
                    "weight": 100,
                    "allow_late": True,
                    "published_at": timezone.now(),
                },
            )
            AssignmentCohort.objects.get_or_create(assignment=assignment, cohort=cohort)

        self.stdout.write(
            self.style.SUCCESS(
                f"Itinerario Web listo: {len(CHALLENGES)} retos, grupo {cohort.name}, "
                f"{created_versions} versiones nuevas y {existing_versions} ya existentes."
            )
        )
        self.stdout.write("No se han creado alumnos ni contraseñas; el catálogo es contenido formativo local.")
