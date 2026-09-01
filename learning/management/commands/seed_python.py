"""Seed the Python preparation track for second-year DAM.

The catalogue is a progressive introduction for ``0491 Sistemas de gestión
empresarial`` in Navarra.  It prepares concepts that students will meet when
working with Odoo, but it is not an Odoo runtime, ORM simulator or complete
accreditation of the module's RA/CE.  Python submissions are inspected as
static AST data; this command never executes a solution.
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

TRACK_SLUG = "introduccion-python-sge-dam"
CURRICULUM_SOURCE = (
    "https://www.educacion.navarra.es/documents/27590/558252/DF%2B110_2024%2Bmodificacion%2BGS.pdf/"
    "a649cf9e-7adf-3c5d-c5ac-eaa602a553a5?version=1.0"
)


def _test(name, test_type, definition, visibility=TestCase.Visibility.PUBLIC):
    return (name, test_type, definition, 1, visibility)


CHALLENGES = [
    {
        "slug": "01-salida-y-variables",
        "title": "01 · Salida y variables",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 100,
        "theory": "Una variable asocia un nombre a un dato y print permite mostrar información. Empieza separando los datos del mensaje para que el programa sea fácil de leer.",
        "task": "Crea la variable mensaje con un texto de bienvenida y muéstrala con print. El laboratorio analiza el código; nunca ejecuta el programa del alumnado.",
        "hints": [
            "Los nombres de variable se escriben en minúsculas con guion bajo si hace falta.",
            "Una asignación tiene la forma nombre = valor.",
            "print(mensaje) es suficiente para mostrar el dato.",
        ],
        "starter": "# Prepara un mensaje para el equipo de Odoo.\n",
        "solution": 'mensaje = "Bienvenido al laboratorio de Odoo"\nprint(mensaje)\n',
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Variable mensaje", "python.assignment", {"name": "mensaje"}),
            _test("Salida con print", "python.call_used", {"name": "print"}, TestCase.Visibility.PRIVATE),
            _test("Estructura de asignación", "python.node_kind", {"kind": "assignment"}),
        ],
    },
    {
        "slug": "02-tipos-y-cadenas",
        "title": "02 · Tipos y cadenas de texto",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 110,
        "theory": "Python distingue textos, números y valores booleanos. Las f-strings permiten construir mensajes legibles sin concatenaciones difíciles de mantener.",
        "task": "Guarda un nombre de producto en producto, su cantidad en cantidad y crea una etiqueta con una f-string. Muestra la etiqueta al final.",
        "hints": [
            "Usa comillas para el texto y un entero para cantidad.",
            "Una f-string comienza por f y puede insertar {producto}.",
            "Conserva los datos en variables separadas antes de crear la etiqueta.",
        ],
        "starter": "# Describe un producto del catálogo.\n",
        "solution": 'producto = "Módulo ERP"\ncantidad = 3\netiqueta = f"{producto} · {cantidad} unidades"\nprint(etiqueta)\n',
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Nombre de producto", "python.assignment", {"name": "producto"}),
            _test("Cantidad registrada", "python.assignment", {"name": "cantidad"}),
            _test("Etiqueta f-string", "python.assignment", {"name": "etiqueta"}),
            _test("Construcción f-string", "python.node_kind", {"kind": "f_string"}),
            _test(
                "Salida de etiqueta",
                "python.call_used",
                {"name": "print", "arg_names": ["etiqueta"]},
                TestCase.Visibility.PRIVATE,
            ),
        ],
    },
    {
        "slug": "03-condicionales-de-stock",
        "title": "03 · Condicionales de stock",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 120,
        "theory": "Las decisiones if/else permiten expresar reglas de negocio. En un ERP es habitual informar de un producto disponible o pendiente de reposición.",
        "task": "Define stock y usa if/else para mostrar si hay unidades disponibles. El corrector comprueba la estructura, no el resultado de ejecución.",
        "hints": [
            "Compara stock con cero dentro de la condición.",
            "La rama else cubre el caso de inventario agotado.",
            "Usa print para que cada rama tenga un mensaje claro.",
        ],
        "starter": "stock = 0\n# Decide qué mensaje corresponde al inventario.\n",
        "solution": 'stock = 12\nif stock > 0:\n    print("Disponible")\nelse:\n    print("Pendiente de reposición")\n',
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Dato stock", "python.assignment", {"name": "stock"}),
            _test("Estructura condicional", "python.node_kind", {"kind": "if"}),
            _test("Condición con alternativa", "python.node_kind", {"kind": "if_else"}),
            _test(
                "Comparación de stock",
                "python.comparison_used",
                {"operator": "gt", "left": "stock", "right": 0},
            ),
            _test("Mensaje de negocio", "python.call_used", {"name": "print"}, TestCase.Visibility.PRIVATE),
        ],
    },
    {
        "slug": "04-listas-y-bucles",
        "title": "04 · Listas y bucles",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 130,
        "theory": "Una lista agrupa registros y for permite recorrerlos. Este patrón aparece al procesar líneas, productos o documentos de una exportación.",
        "task": "Crea la lista productos, recórrela con for usando la variable producto y muestra cada elemento.",
        "hints": [
            "Los elementos de una lista se escriben entre corchetes.",
            "El bucle comienza con for producto in productos:.",
            "Indenta el print dentro del bucle.",
        ],
        "starter": "productos = [\"Libro\", \"Teclado\"]\n# Recorre la lista y muestra sus elementos.\n",
        "solution": 'productos = ["Libro", "Teclado", "Ratón"]\nfor producto in productos:\n    print(producto)\n',
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Lista de productos", "python.assignment", {"name": "productos"}),
            _test("Estructura de lista", "python.node_kind", {"kind": "list"}),
            _test("Bucle de registros", "python.node_kind", {"kind": "for"}),
            _test("Variable del bucle", "python.loop_target", {"name": "producto", "iterable": "productos"}),
            _test("Elemento mostrado", "python.call_used", {"name": "print", "arg_names": ["producto"]}),
            _test("Salida de cada producto", "python.call_used", {"name": "print"}, TestCase.Visibility.PRIVATE),
        ],
    },
    {
        "slug": "05-diccionarios-de-registro",
        "title": "05 · Diccionarios como registros ERP",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 140,
        "theory": "Los diccionarios representan registros con claves y valores. El patrón ayuda a entender los datos que una aplicación de gestión intercambia, aunque aquí no se conecta con el ORM de Odoo.",
        "task": "Representa un producto mediante un diccionario producto con name, price y active. Accede a una clave y muestra el nombre.",
        "hints": [
            "Escribe cada clave entre comillas y sepárala de su valor con dos puntos.",
            "Las claves se consultan con producto[\"name\"].",
            "active puede ser un valor booleano True.",
        ],
        "starter": "# Modela un registro de producto en memoria.\n",
        "solution": 'producto = {"name": "Módulo ERP", "price": 49.9, "active": True}\nprint(producto["name"])\n',
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Registro producto", "python.assignment", {"name": "producto"}),
            _test("Estructura diccionario", "python.node_kind", {"kind": "dict"}),
            _test("Campos del registro", "python.dict_keys", {"name": "producto", "keys": ["name", "price", "active"]}),
            _test("Acceso al nombre", "python.subscript_used", {"name": "producto", "key": "name"}),
            _test("Lectura del registro", "python.call_used", {"name": "print"}, TestCase.Visibility.PRIVATE),
        ],
    },
    {
        "slug": "06-funciones-reutilizables",
        "title": "06 · Funciones reutilizables",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 150,
        "theory": "Las funciones encapsulan una transformación y permiten reutilizarla con muchos registros. En integraciones reales se combinan con las APIs del sistema, que quedan fuera de este itinerario introductorio.",
        "task": "Declara normaliza_nombre(valor) para limpiar un nombre y devuelve el resultado. Después llama a la función con un dato de ejemplo.",
        "hints": [
            "Usa def normaliza_nombre(valor): y devuelve una expresión.",
            "strip elimina espacios exteriores y title mejora la presentación.",
            "La llamada a la función debe estar fuera de su bloque indentado.",
        ],
        "starter": "def normaliza_nombre(valor):\n    # Limpia el nombre y devuélvelo.\n    pass\n\n# Prueba la función con una variable.\n",
        "solution": 'def normaliza_nombre(valor):\n    return valor.strip().title()\n\nproducto = normaliza_nombre("  teclado  ")\nprint(producto)\n',
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test(
                "Función declarada",
                "python.function_declared",
                {"name": "normaliza_nombre", "args": ["valor"], "returns": True},
            ),
            _test("Estructura de función", "python.node_kind", {"kind": "function"}),
            _test("Llamada a función", "python.call_used", {"name": "normaliza_nombre"}, TestCase.Visibility.PRIVATE),
        ],
    },
    {
        "slug": "07-excepciones-de-datos",
        "title": "07 · Excepciones y datos inválidos",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 160,
        "theory": "Los datos importados pueden no tener el formato esperado. try/except permite expresar una respuesta controlada sin ocultar todos los errores ni detener el tratamiento de los demás registros.",
        "task": "Convierte un importe de texto a entero dentro de try y asigna un valor alternativo en except ValueError.",
        "hints": [
            "La conversión se puede hacer con int(importe_texto).",
            "Captura únicamente ValueError para este caso.",
            "Deja el resultado en la variable importe.",
        ],
        "starter": 'importe_texto = "120"\n# Convierte el texto y trata un formato inválido.\n',
        "solution": 'importe_texto = "120"\ntry:\n    importe = int(importe_texto)\nexcept ValueError:\n    importe = 0\nprint(importe)\n',
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Bloque try", "python.node_kind", {"kind": "try"}),
            _test("Manejador de excepción", "python.node_kind", {"kind": "except_handler"}),
            _test("Excepción prevista", "python.exception_handled", {"name": "ValueError"}),
            _test("Conversión int", "python.call_used", {"name": "int"}),
            _test("Importe normalizado", "python.assignment", {"name": "importe"}, TestCase.Visibility.PRIVATE),
        ],
    },
    {
        "slug": "08-imports-y-fechas",
        "title": "08 · Imports y fechas",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 170,
        "theory": "Los módulos de la biblioteca estándar aportan capacidades reutilizables. El corrector reconoce la sentencia import sin cargar módulos; aquí se practica la organización del programa y no se invoca ninguna API de Odoo.",
        "task": "Importa datetime y json, obtén una fecha con date.today() y muestra su representación. El JSON se prepara para próximos ejercicios de intercambio de datos.",
        "hints": [
            "Puedes usar from datetime import date e import json.",
            "date.today() es una llamada con nombre cualificado.",
            "Guarda la fecha antes de pasársela a print.",
        ],
        "starter": "# Importa módulos estándar para preparar datos de gestión.\n",
        "solution": 'from datetime import date\nimport json\n\nhoy = date.today()\nprint(hoy.isoformat())\n',
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Import de fechas", "python.import_used", {"module": "datetime"}),
            _test("Import de JSON", "python.import_used", {"module": "json"}),
            _test("Fecha actual", "python.call_used", {"name": "date.today"}, TestCase.Visibility.PRIVATE),
            _test("Formato de fecha", "python.call_used", {"name": "hoy.isoformat"}),
        ],
    },
    {
        "slug": "09-rutas-con-pathlib",
        "title": "09 · Rutas con pathlib",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 180,
        "theory": "pathlib representa rutas de forma portable y legible. Antes de abrir un archivo conviene separar la ruta del código que lo procesa.",
        "task": "Importa Path desde pathlib, crea la ruta fichero y muestra su nombre con la propiedad name. Todavía no se abre ningún archivo.",
        "hints": [
            "Usa from pathlib import Path.",
            "Path recibe la ruta como texto.",
            "fichero.name es una propiedad; print(fichero.name) la muestra.",
        ],
        "starter": 'from pathlib import Path\n\n# Declara la ruta de entrada del ejercicio.\n',
        "solution": 'from pathlib import Path\n\nfichero = Path("datos/productos.txt")\nprint(fichero.name)\n',
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Import de pathlib", "python.import_used", {"module": "pathlib"}),
            _test("Ruta de entrada", "python.assignment", {"name": "fichero"}),
            _test("Constructor Path", "python.call_used", {"name": "Path"}, TestCase.Visibility.PRIVATE),
            _test("Nombre de archivo", "python.attribute_used", {"name": "fichero.name"}),
            _test(
                "Salida del nombre",
                "python.call_used",
                {"name": "print", "arg_names": ["fichero.name"]},
                TestCase.Visibility.PRIVATE,
            ),
        ],
    },
    {
        "slug": "10-lectura-de-texto",
        "title": "10 · Leer un archivo de texto",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 200,
        "theory": "with open garantiza un cierre ordenado del recurso en un programa real. El reto comprueba la intención estructural y nunca abre la ruta ni lee datos en el servidor de Reto4V.",
        "task": "Usa with open para leer productos.txt en modo r y con encoding utf-8. Guarda las líneas y muestra el número obtenido.",
        "hints": [
            "La forma base es with open(ruta, \"r\", encoding=\"utf-8\") as archivo:.",
            "readlines() devuelve una colección de líneas en un programa real.",
            "La indentación debe incluir la lectura dentro del with.",
        ],
        "starter": 'ruta = "datos/productos.txt"\n# Lee las líneas con un gestor de contexto.\n',
        "solution": 'ruta = "datos/productos.txt"\nwith open(ruta, "r", encoding="utf-8") as archivo:\n    lineas = archivo.readlines()\nprint(len(lineas))\n',
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Apertura en lectura", "python.file_opened", {"mode": "r", "context_manager": True, "body_non_empty": True}),
            _test("Codificación UTF-8", "python.file_opened", {"encoding": "utf-8"}, TestCase.Visibility.PRIVATE),
            _test("Lectura de líneas", "python.call_used", {"name": "archivo.readlines"}),
            _test("Conteo de líneas", "python.call_used", {"name": "len", "arg_names": ["lineas"]}),
        ],
    },
    {
        "slug": "11-escritura-json",
        "title": "11 · Escribir datos JSON",
        "difficulty": ActivityVersion.Difficulty.ADVANCED,
        "xp": 220,
        "theory": "JSON es un formato habitual para intercambiar registros. El uso de with y una codificación explícita reduce errores de recursos y de representación de texto.",
        "task": "Prepara una lista de productos, abre resumen.json en modo w con UTF-8 y usa json.dump para escribirla. El servidor solo analiza el AST.",
        "hints": [
            "Importa json antes de usar json.dump.",
            "Escribe con with open(\"resumen.json\", \"w\", encoding=\"utf-8\") as archivo:.",
            "json.dump recibe primero los datos y luego el archivo.",
        ],
        "starter": "import json\n\nproductos = []\n# Escribe la lista en un archivo JSON.\n",
        "solution": 'import json\n\nproductos = [{"name": "Libro", "active": True}]\nwith open("resumen.json", "w", encoding="utf-8") as archivo:\n    json.dump(productos, archivo, ensure_ascii=False, indent=2)\n',
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Import de JSON", "python.import_used", {"module": "json"}),
            _test(
                "Apertura en escritura",
                "python.file_opened",
                {"mode": "w", "context_manager": True, "body_non_empty": True, "encoding": "utf-8"},
            ),
            _test(
                "Serialización JSON",
                "python.call_used",
                {"name": "json.dump", "arg_names": ["productos", "archivo"]},
                TestCase.Visibility.PRIVATE,
            ),
        ],
    },
    {
        "slug": "12-integracion-archivos",
        "title": "12 · Leer, procesar y escribir",
        "difficulty": ActivityVersion.Difficulty.ADVANCED,
        "xp": 240,
        "theory": "Una integración sencilla separa entrada, transformación y salida. Este patrón prepara la lectura de exportaciones para futuras integraciones con un ERP, sin conectarse a Odoo ni simular su ORM.",
        "task": "Declara transformar, lee líneas de entrada.txt con pathlib en modo r, procesa cada línea y escribe el resultado en salida.txt en modo w. Mantén ambos archivos dentro de with.",
        "hints": [
            "Path(...).open también representa una apertura estática válida.",
            "La función transformar puede usar strip y upper para normalizar una línea.",
            "Un for dentro del primer with permite acumular resultados antes de escribirlos.",
        ],
        "starter": 'from pathlib import Path\n\ndef transformar(linea):\n    # Devuelve una línea normalizada.\n    pass\n\n# Lee, procesa y escribe los registros.\n',
        "solution": 'from pathlib import Path\n\ndef transformar(linea):\n    return linea.strip().upper()\n\nentrada = Path("entrada.txt")\nsalida = Path("salida.txt")\nregistros = []\nwith entrada.open("r", encoding="utf-8") as origen:\n    for linea in origen:\n        registros.append(transformar(linea))\nwith salida.open("w", encoding="utf-8") as destino:\n    destino.write("\\n".join(registros))\n',
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test(
                "Función de transformación",
                "python.function_declared",
                {"name": "transformar", "args": ["linea"], "returns": True},
            ),
            _test("Bucle de entrada", "python.node_kind", {"kind": "for", "non_empty": True}),
            _test("Transformación aplicada", "python.call_used", {"name": "transformar"}),
            _test("Acumulación de registros", "python.call_used", {"name": "registros.append"}),
            _test(
                "Lectura en contexto",
                "python.file_opened",
                {"mode": "r", "context_manager": True, "body_non_empty": True, "encoding": "utf-8"},
                TestCase.Visibility.PRIVATE,
            ),
            _test(
                "Escritura en contexto",
                "python.file_opened",
                {"mode": "w", "context_manager": True, "body_non_empty": True, "encoding": "utf-8"},
                TestCase.Visibility.PRIVATE,
            ),
            _test("Salida transformada", "python.call_used", {"name": "destino.write"}),
        ],
    },
]


class Command(BaseCommand):
    help = "Crea el itinerario local de 12 retos Python para SGE de segundo de DAM."

    def add_arguments(self, parser):
        parser.add_argument("--owner", required=True, help="Usuario profesor o administrador propietario del contenido.")
        parser.add_argument("--cohort", default="2DAM", help="Grupo al que se asignan los retos (por defecto: 2DAM).")
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
            defaults={"active": True},
        )
        if owner.role == User.Role.TEACHER and not owner.is_superuser:
            TeachingAssignment.objects.get_or_create(cohort=cohort, teacher=owner, defaults={"active": True})

        course, _ = Course.objects.get_or_create(
            slug=TRACK_SLUG,
            defaults={
                "title": "Introducción a Python para SGE · DAM",
                "description": "Retos progresivos de Python hasta lectura y escritura de archivos como preparación para trabajar con Odoo en el módulo 0491 Sistemas de gestión empresarial.",
                "created_by": owner,
                "active": True,
            },
        )
        module, _ = Module.objects.get_or_create(
            course=course,
            position=1,
            defaults={
                "title": "Python aplicado a datos · /python",
                "description": "Fundamentos de Python, estructuras y archivos. Alineamiento parcial y preparatorio: no sustituye el módulo 0491 ni implementa Odoo.",
                "weight": 100,
            },
        )

        created_versions = 0
        existing_versions = 0
        for item in CHALLENGES:
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
            version, version_created = ActivityVersion.objects.get_or_create(
                activity=activity,
                version_number=1,
                defaults={
                    "language": ActivityVersion.Language.PYTHON,
                    "difficulty": item["difficulty"],
                    "xp_reward": item["xp"],
                    "hints": item["hints"],
                    "instructions": f"## Teoría\n{item['theory']}\n\n## Reto\n{item['task']}\n\n> El corrector analiza el AST de Python de forma estática; no ejecutes este código en el servidor ni lo confundas con una integración real de Odoo.",
                    "objectives": [
                        "Escribir Python legible para representar y transformar datos",
                        "Aplicar estructuras de control, funciones y manejo de errores",
                        "Preparar lectura y escritura de archivos para flujos de datos de SGE",
                    ],
                    "learning_outcomes": [],
                    "assessment_criteria": [],
                    "professional_module_code": "0491",
                    "curriculum_scope": "Navarra · preparación DAM",
                    "curriculum_edition": "navarra-2024",
                    "curriculum_unit": "",
                    "curriculum_source": CURRICULUM_SOURCE,
                    "starter_files": {"python": item["starter"]},
                    "reference_solution": {"python": item["solution"]},
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

            # Assigned versions are immutable.  Complete missing tests only on
            # a new/unassigned version; never alter an existing assigned one.
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
                            "feedback": "Revisa la estructura indicada en el enunciado; el corrector no ejecuta el código.",
                            "position": position,
                        },
                    )
            assignment, _ = Assignment.objects.get_or_create(
                activity=activity,
                activity_version=version,
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
                f"Itinerario Python listo: {len(CHALLENGES)} retos, grupo {cohort.name}, "
                f"{created_versions} versiones nuevas y {existing_versions} ya existentes."
            )
        )
        self.stdout.write("No se han creado alumnos ni contraseñas; el catálogo es contenido formativo local.")
