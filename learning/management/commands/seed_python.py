"""Seed the Python preparation track for second-year DAM.

The catalogue is a progressive introduction for the 0491 Sistemas de gestión
empresarial module in Navarra. It prepares concepts that students will meet
when working with Odoo, but it is not an Odoo runtime, ORM simulator or
complete accreditation of the module's RA/CE. Python submissions are
inspected as static AST data; this command never executes a solution.
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
    Cohort,
    Course,
    Module,
    TeachingAssignment,
    TestCase,
)

from ._catalog import ensure_cohort_track, get_or_create_catalog_revision_assignment

TRACK_SLUG = "introduccion-python-sge-dam"
CURRICULUM_SOURCE = (
    "https://www.educacion.navarra.es/documents/27590/558252/DF%2B110_2024%2Bmodificacion%2BGS.pdf/"
    "a649cf9e-7adf-3c5d-c5ac-eaa602a553a5?version=1.0"
)
PYTHON_CATALOG_VERSION = 2


def _test(name, test_type, definition, visibility=TestCase.Visibility.PUBLIC):
    return (name, test_type, definition, 1, visibility)


CHALLENGES = [
    {
        # Keep the historical activity slug so an upgrade publishes v2 on the
        # same activity instead of creating a second path.
        "slug": "01-salida-y-variables",
        "title": "01 · Mi primer programa",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 100,
        "theory": "Python es un lenguaje para dar instrucciones al ordenador. Una instrucción sencilla es print, que muestra un mensaje. Los paréntesis y las comillas forman parte de la escritura correcta.",
        "task": "1. En la pestaña `main.py`, cambia el texto que está dentro de `print` por `Hola, equipo`.\n2. Mantén los paréntesis y las comillas.\n3. Pulsa «Comprobar mi archivo» para revisar tu primera instrucción.",
        "hints": [
            "print se escribe con minúsculas y lleva paréntesis.",
            "El texto que se muestra debe estar entre comillas.",
            "Cambia solo las palabras dentro de las comillas.",
        ],
        "objectives": [
            "Escribir una primera instrucción Python",
            "Mantener una llamada print con sintaxis válida",
            "Reconocer que un programa se lee de arriba abajo",
        ],
        "ra": [],
        "ce": [],
        "starter": {"python": 'print("Escribe aquí tu primer mensaje")\n'},
        "solution": {"python": 'print("Hola, equipo")\n'},
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Llamada sencilla", "python.node_kind", {"kind": "call"}),
            _test("Mensaje preparado", "python.call_used", {"name": "print", "args": ["Hola, equipo"]}),
            _test("Salida con print", "python.call_used", {"name": "print"}, TestCase.Visibility.PRIVATE),
        ],
    },
    {
        "slug": "02-tipos-y-cadenas",
        "title": "02 · Datos y tipos",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 110,
        "theory": "Una variable es un nombre que guardamos para volver a usar un dato. Un texto va entre comillas y un número se escribe sin comillas. Una f-string permite mezclar variables dentro de un mensaje.",
        "task": "1. Guarda Cuaderno en la variable producto.\n2. Guarda el número 4 en cantidad.\n3. Crea etiqueta con una f-string que use producto y cantidad y termine en unidades.\n4. Muestra etiqueta con print.",
        "hints": [
            "Una asignación tiene la forma nombre = valor.",
            "Una f-string empieza por f y permite escribir {producto} dentro del texto.",
            "Conserva producto y cantidad en variables separadas antes de crear etiqueta.",
        ],
        "objectives": [
            "Diferenciar un texto de un número",
            "Guardar datos en variables con nombres claros",
            "Construir un mensaje a partir de dos variables",
        ],
        "ra": [],
        "ce": [],
        "starter": {"python": '# Describe un producto del catálogo.\nproducto = "Escribe el nombre del producto"\ncantidad = 0\n\n# Prepara una etiqueta con esos datos.\n'},
        "solution": {"python": 'producto = "Cuaderno"\ncantidad = 4\netiqueta = f"{producto} · {cantidad} unidades"\nprint(etiqueta)\n'},
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Nombre de producto", "python.assignment", {"name": "producto"}),
            _test("Cantidad registrada", "python.assignment", {"name": "cantidad"}),
            _test("Etiqueta creada", "python.assignment", {"name": "etiqueta"}),
            _test("Construcción f-string", "python.node_kind", {"kind": "f_string"}),
            _test("Etiqueta mostrada", "python.call_used", {"name": "print", "arg_names": ["etiqueta"]}),
        ],
    },
    {
        "slug": "03-condicionales-de-stock",
        "title": "03 · Elegir con if",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 120,
        "theory": "Una decisión permite que el programa elija entre dos caminos. if pregunta algo y else indica qué hacer cuando la respuesta es no. Es la base de muchas reglas de una aplicación de gestión.",
        "task": "1. Deja stock con el valor 12.\n2. Si stock es mayor que cero, muestra Disponible.\n3. En caso contrario, muestra Pendiente de reposición.\n4. Mantén las dos partes dentro de if y else.",
        "hints": [
            "La pregunta se puede escribir stock > 0.",
            "El bloque de else empieza alineado con if y termina en dos puntos.",
            "Las instrucciones de cada camino deben quedar indentadas.",
        ],
        "objectives": [
            "Comparar una cantidad con cero",
            "Escribir una decisión con if y else",
            "Dar una respuesta distinta según el stock",
        ],
        "ra": [],
        "ce": [],
        "starter": {"python": "stock = 0\nif stock > 0:\n    # Escribe el mensaje cuando hay unidades.\n    pass\nelse:\n    # Escribe el mensaje cuando no hay unidades.\n    pass\n"},
        "solution": {"python": 'stock = 12\nif stock > 0:\n    print("Disponible")\nelse:\n    print("Pendiente de reposición")\n'},
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Dato stock", "python.assignment", {"name": "stock"}),
            _test("Estructura condicional", "python.node_kind", {"kind": "if"}),
            _test("Condición con alternativa", "python.node_kind", {"kind": "if_else"}),
            _test("Comparación de stock", "python.comparison_used", {"operator": "gt", "left": "stock", "right": 0}),
            _test("Mensajes preparados", "python.call_used", {"name": "print"}, TestCase.Visibility.PRIVATE),
        ],
    },
    {
        "slug": "04-listas-y-bucles",
        "title": "04 · Recorrer una lista",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 130,
        "theory": "Una lista guarda varios datos juntos y for los visita uno a uno. Este patrón sirve para revisar una colección de productos o las líneas de una exportación.",
        "task": "1. Prepara la lista productos con varios nombres.\n2. Escribe for producto in productos.\n3. Dentro del bucle, muestra producto.\n4. Revisa la indentación: print debe estar dentro del bucle.",
        "hints": [
            "Los elementos de una lista van entre corchetes y separados por comas.",
            "La línea del bucle termina en dos puntos.",
            "La instrucción repetida empieza con cuatro espacios.",
        ],
        "objectives": [
            "Guardar varios elementos en una lista",
            "Recorrer una lista con un bucle for",
            "Usar una variable para cada elemento visitado",
        ],
        "ra": [],
        "ce": [],
        "starter": {"python": 'productos = ["Libro", "Teclado"]\n\n# Recorre la lista y muestra cada producto.\n'},
        "solution": {"python": 'productos = ["Libro", "Teclado", "Ratón"]\nfor producto in productos:\n    print(producto)\n'},
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
        "title": "05 · Un registro de producto",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 140,
        "theory": "Un diccionario reúne datos usando una palabra como clave para cada valor. Así podemos representar un registro de producto en memoria y entender mejor los datos que después maneja un ERP.",
        "task": "1. Crea el diccionario producto.\n2. Añade las claves name, price y active.\n3. Usa producto[\"name\"] para consultar el nombre.\n4. Muestra ese nombre.",
        "hints": [
            "Cada clave se escribe entre comillas, seguida de dos puntos.",
            "Las parejas del diccionario van entre llaves y separadas por comas.",
            "active puede guardar el valor booleano True, sin comillas.",
        ],
        "objectives": [
            "Representar un producto como un registro de datos",
            "Distinguir claves y valores de un diccionario",
            "Consultar un dato usando su clave",
        ],
        "ra": [],
        "ce": [],
        "starter": {"python": "# Modela un registro de producto en memoria.\n"},
        "solution": {"python": 'producto = {"name": "Módulo ERP", "price": 49.9, "active": True}\nprint(producto["name"])\n'},
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Registro producto", "python.assignment", {"name": "producto"}),
            _test("Estructura diccionario", "python.node_kind", {"kind": "dict"}),
            _test("Campos del registro", "python.dict_keys", {"name": "producto", "keys": ["name", "price", "active"]}),
            _test("Acceso al nombre", "python.subscript_used", {"name": "producto", "key": "name"}),
            _test("Nombre mostrado", "python.call_used", {"name": "print"}, TestCase.Visibility.PRIVATE),
        ],
    },
    {
        "slug": "06-funciones-reutilizables",
        "title": "06 · Una función para limpiar nombres",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 150,
        "theory": "Una función es un pequeño bloque con nombre que podemos usar varias veces. En este reto prepararás una función que quita espacios sobrantes y presenta un nombre de forma ordenada.",
        "task": "1. Completa normaliza_nombre(valor).\n2. Devuelve valor sin espacios exteriores y con sus palabras en formato título.\n3. Llama a la función con un nombre de ejemplo y guarda el resultado en producto.",
        "hints": [
            "La cabecera se escribe def normaliza_nombre(valor):.",
            "strip quita espacios de los extremos y title pone mayúscula inicial.",
            "Usa return para devolver el resultado de la función.",
        ],
        "objectives": [
            "Declarar una función con un parámetro",
            "Devolver un dato transformado",
            "Reutilizar la función con un registro de ejemplo",
        ],
        "ra": [],
        "ce": [],
        "starter": {"python": "def normaliza_nombre(valor):\n    # Limpia el nombre y devuélvelo.\n    pass\n\n# Prueba la función con una variable.\n"},
        "solution": {"python": 'def normaliza_nombre(valor):\n    return valor.strip().title()\n\nproducto = normaliza_nombre("  teclado  ")\nprint(producto)\n'},
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Función declarada", "python.function_declared", {"name": "normaliza_nombre", "args": ["valor"], "returns": True}),
            _test("Estructura de función", "python.node_kind", {"kind": "function"}),
            _test("Llamada a función", "python.call_used", {"name": "normaliza_nombre"}, TestCase.Visibility.PRIVATE),
        ],
    },
    {
        "slug": "07-excepciones-de-datos",
        "title": "07 · Responder a un dato incorrecto",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 160,
        "theory": "Un dato que llega de una hoja o una exportación puede no tener el formato esperado. try/except permite preparar una respuesta controlada para ese caso, sin esconder todos los errores.",
        "task": "1. Convierte importe_texto a número entero dentro de try.\n2. Si aparece ValueError, guarda 0 en importe.\n3. Muestra importe después del bloque.\n4. Mantén la captura limitada a ValueError.",
        "hints": [
            "La conversión se puede hacer con int(importe_texto).",
            "La línea except ValueError: indica el tipo de dato que esperas corregir.",
            "La asignación de importe debe aparecer tanto en try como en except.",
        ],
        "objectives": [
            "Reconocer que una conversión puede fallar",
            "Escribir un bloque try/except específico",
            "Preparar un valor alternativo para un dato incorrecto",
        ],
        "ra": [],
        "ce": [],
        "starter": {"python": 'importe_texto = "120"\ntry:\n    # Convierte el texto.\n    pass\nexcept ValueError:\n    # Usa un valor seguro si no es un número.\n    pass\n'},
        "solution": {"python": 'importe_texto = "120"\ntry:\n    importe = int(importe_texto)\nexcept ValueError:\n    importe = 0\nprint(importe)\n'},
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Bloque try", "python.node_kind", {"kind": "try"}),
            _test("Manejador de excepción", "python.node_kind", {"kind": "except_handler"}),
            _test("Excepción prevista", "python.exception_handled", {"name": "ValueError"}),
            _test("Conversión int", "python.call_used", {"name": "int"}),
            _test("Importe preparado", "python.assignment", {"name": "importe"}, TestCase.Visibility.PRIVATE),
        ],
    },
    {
        "slug": "08-imports-y-fechas",
        "title": "08 · Traer herramientas con un módulo",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 170,
        "theory": "Un módulo es un archivo con herramientas que podemos importar. La biblioteca estándar de Python ya trae módulos útiles, como datetime para fechas y json para datos de intercambio.",
        "task": "1. Importa date desde datetime e importa json.\n2. Guarda la fecha de hoy en hoy usando date.today().\n3. Muestra su texto con hoy.isoformat().\n4. En este reto solo preparas los imports: no hay ninguna conexión con Odoo.",
        "hints": [
            "Puedes escribir from datetime import date e import json.",
            "date.today() es una llamada que obtiene la fecha actual en un programa real.",
            "isoformat convierte la fecha en un texto ordenado.",
        ],
        "objectives": [
            "Importar herramientas de la biblioteca estándar",
            "Guardar una fecha en una variable",
            "Preparar un formato de fecha para intercambiar datos",
        ],
        "ra": [],
        "ce": [],
        "starter": {"python": "# Importa módulos estándar para preparar datos de gestión.\n"},
        "solution": {"python": 'from datetime import date\nimport json\n\nhoy = date.today()\nprint(hoy.isoformat())\n'},
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
        "title": "09 · Preparar una ruta",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 180,
        "theory": "Una ruta es la dirección de un archivo. pathlib permite escribirla de una forma que se entiende bien y se adapta mejor a distintos sistemas. Aquí solo preparas la dirección: todavía no abres ningún archivo.",
        "task": "1. Importa Path desde pathlib.\n2. Crea la variable fichero con la ruta datos/productos.txt.\n3. Muestra el nombre del archivo con fichero.name.\n4. No necesitas crear la carpeta ni el archivo.",
        "hints": [
            "Usa from pathlib import Path.",
            "Path recibe la ruta como texto.",
            "name es una propiedad de la ruta; print(fichero.name) la muestra.",
        ],
        "objectives": [
            "Distinguir una ruta de un archivo abierto",
            "Crear una ruta con pathlib",
            "Consultar el nombre final de una ruta",
        ],
        "ra": [],
        "ce": [],
        "starter": {"python": 'from pathlib import Path\n\n# Declara la ruta de entrada del ejercicio.\n'},
        "solution": {"python": 'from pathlib import Path\n\nfichero = Path("datos/productos.txt")\nprint(fichero.name)\n'},
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Import de pathlib", "python.import_used", {"module": "pathlib"}),
            _test("Ruta de entrada", "python.assignment", {"name": "fichero"}),
            _test("Constructor Path", "python.call_used", {"name": "Path"}, TestCase.Visibility.PRIVATE),
            _test("Nombre de archivo", "python.attribute_used", {"name": "fichero.name"}),
            _test("Salida del nombre", "python.call_used", {"name": "print", "arg_names": ["fichero.name"]}, TestCase.Visibility.PRIVATE),
        ],
    },
    {
        "slug": "10-lectura-de-texto",
        "title": "10 · Leer líneas de un archivo",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 200,
        "theory": "with open permite trabajar con un archivo y dejarlo cerrado de forma ordenada. El corrector de Programmy4V solo comprueba que has escrito esa estructura; nunca abre la ruta ni lee datos del servidor.",
        "task": "1. Usa with open para abrir datos/productos.txt en modo r y con encoding utf-8.\n2. Guarda las líneas en lineas usando readlines().\n3. Muestra cuántas líneas hay con len(lineas).\n4. La indentación debe dejar la lectura dentro de with.",
        "hints": [
            "La forma base es with open(ruta, \"r\", encoding=\"utf-8\") as archivo:.",
            "readlines() representa la lectura de todas las líneas en un programa real.",
            "Las instrucciones dentro de with llevan cuatro espacios.",
        ],
        "objectives": [
            "Abrir un archivo en modo lectura de forma ordenada",
            "Guardar sus líneas en una variable",
            "Contar elementos sin ejecutar el archivo en la plataforma",
        ],
        "ra": [],
        "ce": [],
        "starter": {"python": 'ruta = "datos/productos.txt"\n\n# Lee las líneas con un gestor de contexto.\n'},
        "solution": {"python": 'ruta = "datos/productos.txt"\nwith open(ruta, "r", encoding="utf-8") as archivo:\n    lineas = archivo.readlines()\nprint(len(lineas))\n'},
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
        "title": "11 · Guardar un catálogo en JSON",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 220,
        "theory": "JSON es un formato de texto habitual para intercambiar registros. json.dump convierte una lista de datos a ese formato. El reto comprueba la estructura escrita y no crea ningún archivo real.",
        "task": "1. Prepara una lista productos con al menos un registro.\n2. Abre resumen.json en modo w y con encoding utf-8 dentro de with.\n3. Usa json.dump para guardar productos en archivo.\n4. La plataforma analiza el código como texto: no escribe en el servidor.",
        "hints": [
            "Importa json antes de usar json.dump.",
            "La forma es with open(\"resumen.json\", \"w\", encoding=\"utf-8\") as archivo:.",
            "json.dump recibe primero los datos y después el archivo.",
        ],
        "objectives": [
            "Preparar una lista de registros para exportar",
            "Abrir una salida de texto con codificación explícita",
            "Escribir la llamada que convierte datos a JSON",
        ],
        "ra": [],
        "ce": [],
        "starter": {"python": "import json\n\nproductos = []\n# Escribe la lista en un archivo JSON.\n"},
        "solution": {"python": 'import json\n\nproductos = [{"name": "Libro", "active": True}]\nwith open("resumen.json", "w", encoding="utf-8") as archivo:\n    json.dump(productos, archivo, ensure_ascii=False, indent=2)\n'},
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Import de JSON", "python.import_used", {"module": "json"}),
            _test("Apertura en escritura", "python.file_opened", {"mode": "w", "context_manager": True, "body_non_empty": True, "encoding": "utf-8"}),
            _test("Serialización JSON", "python.call_used", {"name": "json.dump", "arg_names": ["productos", "archivo"]}, TestCase.Visibility.PRIVATE),
        ],
    },
    {
        "slug": "12-integracion-archivos",
        "title": "12 · Mini flujo de importación",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 240,
        "theory": "Un flujo de datos suele tener tres pasos: leer una entrada, transformar cada registro y guardar una salida. Este pequeño patrón prepara la forma de pensar que se usa al importar datos en un ERP, sin conectarse a Odoo ni simular su ORM.",
        "task": "1. Completa transformar para limpiar y poner en mayúsculas cada línea.\n2. Prepara las rutas entrada.txt y salida.txt con pathlib.\n3. Lee las líneas dentro de with y procesa cada una con un bucle for.\n4. Abre la salida dentro de otro with y escribe los registros transformados.",
        "hints": [
            "Path(...).open también representa una apertura estructurada válida.",
            "La función transformar puede usar strip y upper.",
            "Guarda cada resultado con registros.append y después únelos con saltos de línea.",
        ],
        "objectives": [
            "Separar entrada, transformación y salida",
            "Combinar una función con un bucle",
            "Preparar lectura y escritura de archivos en contextos seguros",
        ],
        "ra": [],
        "ce": [],
        "starter": {"python": 'from pathlib import Path\n\ndef transformar(linea):\n    # Devuelve una línea normalizada.\n    pass\n\n# Lee, procesa y escribe los registros.\n'},
        "solution": {"python": 'from pathlib import Path\n\ndef transformar(linea):\n    return linea.strip().upper()\n\nentrada = Path("entrada.txt")\nsalida = Path("salida.txt")\nregistros = []\nwith entrada.open("r", encoding="utf-8") as origen:\n    for linea in origen:\n        registros.append(transformar(linea))\nwith salida.open("w", encoding="utf-8") as destino:\n    destino.write("\\n".join(registros))\n'},
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Función de transformación", "python.function_declared", {"name": "transformar", "args": ["linea"], "returns": True}),
            _test("Bucle de entrada", "python.node_kind", {"kind": "for", "non_empty": True}),
            _test("Transformación aplicada", "python.call_used", {"name": "transformar"}),
            _test("Acumulación de registros", "python.call_used", {"name": "registros.append"}),
            _test("Lectura en contexto", "python.file_opened", {"mode": "r", "context_manager": True, "body_non_empty": True, "encoding": "utf-8"}, TestCase.Visibility.PRIVATE),
            _test("Escritura en contexto", "python.file_opened", {"mode": "w", "context_manager": True, "body_non_empty": True, "encoding": "utf-8"}, TestCase.Visibility.PRIVATE),
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
            defaults={"active": True, "track": Cohort.Track.PYTHON},
        )
        ensure_cohort_track(cohort, Cohort.Track.PYTHON)
        if owner.role == User.Role.TEACHER and not owner.is_superuser:
            TeachingAssignment.objects.get_or_create(cohort=cohort, teacher=owner, defaults={"active": True})

        course, course_created = Course.objects.get_or_create(
            slug=TRACK_SLUG,
            defaults={
                "title": "Introducción a Python para SGE · DAM",
                "description": "Retos progresivos de Python hasta lectura y escritura de archivos como preparación para trabajar con Odoo en el módulo 0491 Sistemas de gestión empresarial.",
                "created_by": owner,
                "active": True,
            },
        )
        if not course_created:
            course.title = "Introducción a Python para SGE · DAM"
            course.description = "Retos progresivos de Python hasta lectura y escritura de archivos como preparación para trabajar con Odoo en el módulo 0491 Sistemas de gestión empresarial."
            course.save(update_fields=["title", "description", "updated_at"])

        module, module_created = Module.objects.get_or_create(
            course=course,
            position=1,
            defaults={
                "title": "De los primeros datos a los archivos",
                "description": "Transición guiada desde la sintaxis Python hasta la lectura, escritura JSON y un pequeño flujo de importación. Preparación parcial para 0491; no implementa Odoo.",
                "weight": 100,
            },
        )
        if not module_created:
            module.title = "De los primeros datos a los archivos"
            module.description = "Transición guiada desde la sintaxis Python hasta la lectura, escritura JSON y un pequeño flujo de importación. Preparación parcial para 0491; no implementa Odoo."
            module.save(update_fields=["title", "description"])

        created_versions = 0
        existing_versions = 0
        migrated_links = 0
        archived_assignments = 0
        skipped_later_revisions = 0
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
            if activity.versions.filter(version_number__gt=PYTHON_CATALOG_VERSION).exists():
                skipped_later_revisions += 1
                continue
            version, version_created = ActivityVersion.objects.get_or_create(
                activity=activity,
                version_number=PYTHON_CATALOG_VERSION,
                defaults={
                    "language": ActivityVersion.Language.PYTHON,
                    "difficulty": item["difficulty"],
                    "xp_reward": item["xp"],
                    "hints": item["hints"],
                    "instructions": f"## Antes de empezar\nEl editor ya está preparado y solo necesitas trabajar en main.py. No tienes que crear carpetas ni instalar nada.\n\n## La idea\n{item['theory']}\n\n## Pasos\n{item['task']}\n\n> Las comprobaciones leen tu código como texto; la plataforma no lo ejecuta ni abre archivos en el servidor.",
                    "objectives": item["objectives"],
                    "learning_outcomes": item["ra"],
                    "assessment_criteria": item["ce"],
                    "professional_module_code": "0491",
                    "curriculum_scope": "Navarra · preparación DAM",
                    "curriculum_edition": "navarra-2024",
                    "curriculum_unit": "",
                    "curriculum_source": CURRICULUM_SOURCE,
                    "starter_files": item["starter"],
                    "reference_solution": item["solution"],
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

            # Do not point an activity backwards when a teacher has already
            # published a later revision than this built-in catalogue.
            current_version_number = (
                ActivityVersion.objects.filter(pk=activity.current_version_id)
                .values_list("version_number", flat=True)
                .first()
                if activity.current_version_id
                else None
            )
            if (
                current_version_number is None or current_version_number < version.version_number
            ):
                activity.current_version = version
                activity.status = Activity.Status.PUBLISHED
                activity.save(update_fields=["current_version", "status", "updated_at"])

            # Assigned versions are immutable. Complete missing tests only on
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
                            "feedback": "Revisa los pasos y la estructura indicada; la plataforma lee el código sin ejecutarlo.",
                            "position": position,
                        },
                    )
            assignment, assignment_created, upgrade = get_or_create_catalog_revision_assignment(
                activity=activity,
                version=version,
                cohort=cohort,
                defaults={
                    "status": Assignment.Status.PUBLISHED,
                    "created_by": owner,
                    "title_override": item["title"],
                    "attempt_policy": Assignment.AttemptPolicy.BEST,
                    "max_attempts": None,
                    "weight": 100,
                    "allow_late": True,
                    "published_at": timezone.now(),
                },
            )
            # The revision helper preserves an explicit teacher title. A
            # blank legacy title still gets the friendly v2 title.
            if assignment_created and not assignment.title_override:
                assignment.title_override = item["title"]
                assignment.save(update_fields=["title_override"])
            migrated_links += upgrade["migrated_links"]
            archived_assignments += upgrade["archived_assignments"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Itinerario Python v{PYTHON_CATALOG_VERSION} listo: {len(CHALLENGES)} retos, grupo {cohort.name}, "
                f"{created_versions} versiones nuevas y {existing_versions} ya existentes. "
                f"Actualizados {migrated_links} vínculos y archivadas {archived_assignments} asignaciones anteriores. "
                f"Omitidas {skipped_later_revisions} actividades con una revisión posterior."
            )
        )
        self.stdout.write("No se han creado alumnos ni contraseñas; el catálogo es contenido formativo local.")
