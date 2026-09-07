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
PYTHON_CATALOG_VERSION = 3
V2_TITLES = {
    "01-salida-y-variables": "01 · Mi primer programa",
    "02-tipos-y-cadenas": "02 · Datos y tipos",
    "03-condicionales-de-stock": "03 · Elegir con if",
    "04-listas-y-bucles": "04 · Recorrer una lista",
    "05-diccionarios-de-registro": "05 · Un registro de producto",
    "06-funciones-reutilizables": "06 · Una función para limpiar nombres",
    "07-excepciones-de-datos": "07 · Responder a un dato incorrecto",
    "08-imports-y-fechas": "08 · Traer herramientas con un módulo",
    "09-rutas-con-pathlib": "09 · Preparar una ruta",
    "10-lectura-de-texto": "10 · Leer líneas de un archivo",
    "11-escritura-json": "11 · Guardar un catálogo en JSON",
    "12-integracion-archivos": "12 · Mini flujo de importación",
}


def _test(name, test_type, definition, visibility=TestCase.Visibility.PUBLIC, points=1):
    return (name, test_type, definition, points, visibility)


CHALLENGES = [
    {
        # Los slugs son parte de la identidad histórica de las actividades.
        "slug": "01-salida-y-variables",
        "title": "01 · Mostrar un mensaje",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 100,
        "theory": """### Concepto\nPython es un lenguaje para escribir instrucciones que el ordenador puede seguir. `print()` muestra un texto en la pantalla. El nombre de la instrucción, los paréntesis y las comillas tienen que quedarse como están. Una línea que empieza por `#` es un comentario: sirve para explicar el código y Python la ignora.\n\n### Ejemplo\n```python\n# El texto entre comillas es el mensaje que se mostrará.\nprint("Bienvenida")\n```\nLa palabra `Bienvenida` es distinta de la del ejercicio: el ejemplo solo enseña dónde va el texto.""",
        "task": "Cambia únicamente el texto de la línea preparada para que `print()` muestre `Hola, Python`.",
        "hints": ["Escribe `print` en minúsculas.", "Conserva los paréntesis y las comillas.", "Solo hay que cambiar el mensaje preparado."],
        "objectives": ["Mostrar texto con print", "Reconocer la sintaxis de una llamada sencilla"],
        "ra": [], "ce": [],
        "starter": {"python": 'print("Cambia este mensaje")\n'},
        "solution": {"python": 'print("Hola, Python")\n'},
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Mensaje solicitado", "python.call_used", {"name": "print", "args": ["Hola, Python"]}),
            _test("Uso de print", "python.call_used", {"name": "print"}, TestCase.Visibility.PRIVATE),
        ],
    },
    {
        "slug": "02-tipos-y-cadenas",
        "title": "02 · Guardar un dato en una variable",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 110,
        "theory": """### Concepto\nUna variable da un nombre a un dato para poder usarlo después. Se crea con `nombre = valor`. En este reto el valor es un texto, por eso va entre comillas.\n\n### Ejemplo\n```python\n# ciudad guarda el texto de la derecha.\nciudad = "Pamplona"\nprint(ciudad)  # print usa el valor guardado, sin comillas.\n```\nUna variable no es el texto que escribe el programa: es la etiqueta que apunta al dato.""",
        "task": "En la línea preparada, cambia el texto para que la variable `producto` guarde `Cuaderno`. Después añade `print(producto)`.",
        "hints": ["No borres `producto =`.", "Cuaderno es texto y necesita comillas.", "En `print(producto)`, producto no lleva comillas."],
        "objectives": ["Asignar un texto a una variable", "Mostrar el valor guardado"],
        "ra": [], "ce": [],
        "starter": {"python": 'producto = "Cambia este texto"\n# Muestra la variable debajo.\n'},
        "solution": {"python": 'producto = "Cuaderno"\nprint(producto)\n'},
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Variable producto", "python.assignment", {"name": "producto"}),
            _test("Producto mostrado", "python.call_used", {"name": "print", "arg_names": ["producto"]}),
            _test("Sin formato adelantado", "python.node_kind", {"kind": "call"}, TestCase.Visibility.PRIVATE),
        ],
    },
    {
        "slug": "03-condicionales-de-stock",
        "title": "03 · Trabajar con números",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 120,
        "theory": """### Concepto\nLos números se escriben sin comillas. Podemos sumarlos, restarlos, multiplicarlos o dividirlos. El resultado de una operación también se puede guardar en una variable.\n\n### Ejemplo\n```python\nprecio = 6\nunidades = 3\nsubtotal = precio * unidades  # Multiplica los dos números.\nprint(subtotal)\n```\nEl asterisco `*` significa multiplicar; no es texto ni una letra.""",
        "task": "Cambia los dos números preparados para que `precio` sea 8 y `unidades` sea 3. Completa `total` con la multiplicación y muestra `total`.",
        "hints": ["8 y 3 no llevan comillas.", "Usa `precio * unidades` a la derecha de `total =`.", "Muestra la variable total al final."],
        "objectives": ["Distinguir números de textos", "Multiplicar dos variables numéricas", "Guardar un resultado"],
        "ra": [], "ce": [],
        "starter": {"python": "precio = 0\nunidades = 0\n# Calcula total y muéstralo debajo.\n"},
        "solution": {"python": "precio = 8\nunidades = 3\ntotal = precio * unidades\nprint(total)\n"},
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Precio guardado", "python.assignment", {"name": "precio"}),
            _test("Unidades guardadas", "python.assignment", {"name": "unidades"}),
            _test("Variable total declarada", "python.assignment", {"name": "total"}),
            _test("Total mostrado", "python.call_used", {"name": "print", "arg_names": ["total"]}, points=2),
        ],
    },
    {
        "slug": "04-listas-y-bucles",
        "title": "04 · Unir textos",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 130,
        "theory": """### Concepto\nUn texto, también llamado cadena, va entre comillas. El signo `+` une textos; si quieres separar palabras, incluye un espacio dentro de uno de los textos.\n\n### Ejemplo\n```python\nnombre = "Ana"\nsaludo = "Hola, " + nombre  # El espacio está dentro del primer texto.\nprint(saludo)\n```\nAquí `+` une letras porque ambos lados son textos. No uses esta operación para mezclar un texto y un número todavía.""",
        "task": "Completa `etiqueta` para unir el texto `Producto: ` con la variable `producto`. Muestra `etiqueta`.",
        "hints": ["El espacio final forma parte de `Producto: `.", "Usa `+` entre el texto y producto.", "La variable producto no lleva comillas al usarla."],
        "objectives": ["Crear textos", "Unir un texto con una variable", "Mostrar una etiqueta"],
        "ra": [], "ce": [],
        "starter": {"python": 'producto = "Lápiz"\netiqueta = "Producto: " + producto\n# Muestra etiqueta.\n'},
        "solution": {"python": 'producto = "Lápiz"\netiqueta = "Producto: " + producto\nprint(etiqueta)\n'},
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Producto existente", "python.assignment", {"name": "producto"}),
            _test("Etiqueta creada", "python.assignment", {"name": "etiqueta"}),
            _test("Etiqueta mostrada", "python.call_used", {"name": "print", "arg_names": ["etiqueta"]}),
        ],
    },
    {
        "slug": "05-diccionarios-de-registro",
        "title": "05 · Guardar varios elementos en una lista",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 140,
        "theory": """### Concepto\nUna lista guarda varios valores en orden. Se escribe entre corchetes y separa sus elementos con comas. Por ahora solo la crearemos y consultaremos una posición.\n\n### Ejemplo\n```python\ncolores = ["azul", "verde", "rojo"]\nprint(colores[0])  # La posición 0 es el primer elemento.\n```\nLas posiciones empiezan en 0; aún no necesitamos repetir nada para trabajar con una lista.""",
        "task": "Cambia la lista preparada para que `productos` contenga `Lápiz`, `Cuaderno` y `Regla`. Muestra el primer elemento con `productos[0]`.",
        "hints": ["Cada elemento es texto y lleva comillas.", "Conserva los corchetes de la lista.", "El primer elemento se consulta con `[0]`."],
        "objectives": ["Crear una lista de textos", "Consultar una posición de una lista"],
        "ra": [], "ce": [],
        "starter": {"python": 'productos = ["Cambia", "estos", "textos"]\n# Muestra el primer elemento.\n'},
        "solution": {"python": 'productos = ["Lápiz", "Cuaderno", "Regla"]\nprint(productos[0])\n'},
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Lista productos", "python.assignment", {"name": "productos"}),
            _test("Estructura de lista", "python.node_kind", {"kind": "list"}),
            _test("Primer elemento mostrado", "python.call_used", {"name": "print"}),
        ],
    },
    {
        "slug": "06-funciones-reutilizables",
        "title": "06 · Elegir con if y else",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 150,
        "theory": """### Concepto\n`if` pregunta si una condición es cierta. Si no lo es, `else` indica el otro camino. Los dos puntos abren cada bloque y las líneas del bloque llevan cuatro espacios. `pass` es un marcador temporal que no hace nada: permite dejar un bloque escrito mientras sustituyes ese marcador por una instrucción real.\n\n### Ejemplo\n```python\nedad = 18\nif edad >= 18:\n    print("Acceso permitido")  # Esta línea pertenece a if.\nelse:\n    print("Acceso pendiente")\n```\nLa comparación `>=` significa «mayor o igual que».""",
        "task": "Cambia `stock` a 5. Dentro del `if` preparado, muestra `Disponible`; dentro de `else`, muestra `Sin existencias`.",
        "hints": ["No cambies la condición `stock > 0`.", "Sustituye cada `pass` por un print.", "Los dos print deben conservar los cuatro espacios iniciales."],
        "objectives": ["Comparar un número con cero", "Escribir dos caminos con if y else"],
        "ra": [], "ce": [],
        "starter": {"python": "stock = 0\nif stock > 0:\n    pass\nelse:\n    pass\n"},
        "solution": {"python": 'stock = 5\nif stock > 0:\n    print("Disponible")\nelse:\n    print("Sin existencias")\n'},
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Variable stock", "python.assignment", {"name": "stock"}),
            _test("Decisión", "python.node_kind", {"kind": "if"}),
            _test("Alternativa", "python.node_kind", {"kind": "if_else"}),
            _test("Comparación de stock", "python.comparison_used", {"operator": "gt", "left": "stock", "right": 0}),
            _test("Mensajes de disponibilidad", "python.call_used", {"name": "print"}, points=2),
        ],
    },
    {
        "slug": "07-excepciones-de-datos",
        "title": "07 · Repetir con for",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 160,
        "theory": """### Concepto\n`for` visita uno a uno los elementos de una lista. La variable situada después de `for` representa el elemento actual y la línea repetida se escribe con sangría.\n\n### Ejemplo\n```python\ndias = ["lunes", "martes"]\nfor dia in dias:\n    print(dia)  # Se ejecuta una vez por cada elemento.\n```\n`dia` es un nombre temporal: puedes elegir uno que describa lo que contiene la lista.""",
        "task": "Completa el bucle preparado para mostrar cada elemento de `productos` con `print(producto)`.",
        "hints": ["No necesitas crear otra lista.", "La cabecera es `for producto in productos:`.", "print debe llevar cuatro espacios al inicio."],
        "objectives": ["Recorrer una lista", "Usar una variable de bucle", "Aplicar sangría en un bloque"],
        "ra": [], "ce": [],
        "starter": {"python": 'productos = ["Lápiz", "Cuaderno", "Regla"]\nfor producto in productos:\n    # Muestra producto.\n    pass\n'},
        "solution": {"python": 'productos = ["Lápiz", "Cuaderno", "Regla"]\nfor producto in productos:\n    print(producto)\n'},
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Lista productos", "python.assignment", {"name": "productos"}),
            _test("Bucle for", "python.node_kind", {"kind": "for", "non_empty": True}),
            _test("Recorrido correcto", "python.loop_target", {"name": "producto", "iterable": "productos"}),
            _test("Producto mostrado", "python.call_used", {"name": "print", "arg_names": ["producto"]}),
        ],
    },
    {
        "slug": "08-imports-y-fechas",
        "title": "08 · Agrupar datos en un diccionario",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 170,
        "theory": """### Concepto\nUn diccionario agrupa datos nombrados. Cada clave identifica un valor y se escribe antes de `:`. Para recuperar un dato se usa el nombre de la clave entre corchetes.\n\n### Ejemplo\n```python\nlibro = {"titulo": "Python", "paginas": 80}\nprint(libro["titulo"])  # Busca el valor asociado a la clave titulo.\n```\nLas claves son textos; `paginas` puede guardar un número sin comillas.""",
        "task": "Completa el diccionario `producto` con las claves `name` y `price`. Usa `Lápiz` y 2 como valores. Después muestra `producto[\"name\"]`.",
        "hints": ["Separa las dos parejas con una coma.", "name lleva un texto entre comillas.", "price guarda el número 2, sin comillas."],
        "objectives": ["Crear un diccionario", "Distinguir claves y valores", "Consultar un dato por su clave"],
        "ra": [], "ce": [],
        "starter": {"python": 'producto = {"name": "Cambia este texto", "price": 0}\n# Muestra producto["name"].\n'},
        "solution": {"python": 'producto = {"name": "Lápiz", "price": 2}\nprint(producto["name"])\n'},
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Diccionario producto", "python.assignment", {"name": "producto"}),
            _test("Estructura diccionario", "python.node_kind", {"kind": "dict"}),
            _test("Claves requeridas", "python.dict_keys", {"name": "producto", "keys": ["name", "price"]}),
            _test("Acceso al nombre", "python.subscript_used", {"name": "producto", "key": "name"}),
            _test("Nombre mostrado", "python.call_used", {"name": "print"}, points=2),
        ],
    },
    {
        "slug": "09-rutas-con-pathlib",
        "title": "09 · Declarar y llamar una función",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 180,
        "theory": """### Concepto\nUna función agrupa instrucciones bajo un nombre. Primero se declara con `def` y después se llama escribiendo su nombre seguido de paréntesis. Esta primera función no recibe datos ni devuelve un resultado.\n\n### Ejemplo\n```python\ndef despedirse():\n    print("Hasta luego")  # Esta instrucción solo se guarda al declarar.\n\ndespedirse()  # Aquí se ejecutaría la función en un programa normal.\n```\nLos dos puntos y la sangría forman parte del bloque de la función.""",
        "task": "Sustituye `pass` por `print(\"Hola\")` dentro de `saludar()`. Conserva la llamada `saludar()` preparada.",
        "hints": ["La función no lleva ningún nombre entre sus paréntesis.", "El print lleva cuatro espacios porque está dentro de la función.", "La llamada queda fuera del bloque."],
        "objectives": ["Declarar una función sin parámetros", "Llamar una función por su nombre"],
        "ra": [], "ce": [],
        "starter": {"python": "def saludar():\n    pass\n\nsaludar()\n"},
        "solution": {"python": 'def saludar():\n    print("Hola")\n\nsaludar()\n'},
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Función saludar", "python.function_declared", {"name": "saludar", "args": []}),
            _test("Cuerpo de función", "python.node_kind", {"kind": "function", "non_empty": True}, points=2),
            _test("Llamada a saludar", "python.call_used", {"name": "saludar"}),
        ],
    },
    {
        "slug": "10-lectura-de-texto",
        "title": "10 · Pasar un dato a una función",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 190,
        "theory": """### Concepto\nUn parámetro es un nombre que recibe un dato al llamar una función. El argumento es el valor que escribimos en la llamada. Dentro de la función se usa el nombre del parámetro.\n\n### Ejemplo\n```python\ndef mostrar_color(color):\n    print(color)  # color es el dato recibido por la función.\n\nmostrar_color("azul")\n```\n`color` es un nombre elegido para el parámetro; el texto `azul` es el argumento.""",
        "task": "Sustituye `pass` por `print(producto)` dentro de `mostrar(producto)`. Conserva la llamada preparada con `Cuaderno`.",
        "hints": ["producto no lleva comillas dentro de print.", "La cabecera ya tiene el parámetro correcto.", "La llamada queda fuera de la función."],
        "objectives": ["Declarar una función con un parámetro", "Pasar un argumento", "Usar el parámetro dentro de la función"],
        "ra": [], "ce": [],
        "starter": {"python": 'def mostrar(producto):\n    pass\n\nmostrar("Cuaderno")\n'},
        "solution": {"python": 'def mostrar(producto):\n    print(producto)\n\nmostrar("Cuaderno")\n'},
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Función mostrar", "python.function_declared", {"name": "mostrar", "args": ["producto"]}),
            _test("Cuerpo de función", "python.node_kind", {"kind": "function", "non_empty": True}, points=2),
            _test("Llamada a mostrar", "python.call_used", {"name": "mostrar"}),
            _test("Producto mostrado", "python.call_used", {"name": "print", "arg_names": ["producto"]}),
        ],
    },
    {
        "slug": "11-escritura-json",
        "title": "11 · Devolver un resultado con return",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 210,
        "theory": """### Concepto\n`return` entrega un resultado desde una función. Quien llama a la función puede guardarlo en una variable o mostrarlo después. `return` no es lo mismo que `print`: uno devuelve un dato y el otro lo muestra.\n\n### Ejemplo\n```python\ndef duplicar(numero):\n    return numero * 2  # Devuelve el resultado al lugar de la llamada.\n\nresultado = duplicar(4)\nprint(resultado)\n```\nLa multiplicación está dentro de la función; `resultado` recibe el valor devuelto.""",
        "task": "Sustituye `pass` por `return numero * 2`. Conserva la llamada preparada, que guarda el resultado en `resultado`, y muestra esa variable.",
        "hints": ["return lleva cuatro espacios dentro de la función.", "El número 2 no lleva comillas.", "Muestra resultado fuera de la función."],
        "objectives": ["Devolver un resultado con return", "Guardar el valor devuelto", "Distinguir return y print"],
        "ra": [], "ce": [],
        "starter": {"python": "def duplicar(numero):\n    pass\n\nresultado = duplicar(4)\n# Muestra resultado.\n"},
        "solution": {"python": "def duplicar(numero):\n    return numero * 2\n\nresultado = duplicar(4)\nprint(resultado)\n"},
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Función duplicar", "python.function_declared", {"name": "duplicar", "args": ["numero"], "returns": True}),
            _test("Llamada a duplicar", "python.call_used", {"name": "duplicar"}),
            _test("Resultado declarado", "python.assignment", {"name": "resultado"}),
            _test("Resultado mostrado", "python.call_used", {"name": "print", "arg_names": ["resultado"]}),
        ],
    },
    {
        "slug": "12-integracion-archivos",
        "title": "12 · Repaso: mostrar una lista con una función",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 230,
        "theory": """### Concepto\nEste último reto no introduce una API nueva: combina una lista, un parámetro, un `for` y `print`. Separar la repetición en una función hace que el programa tenga un nombre claro para esa tarea.\n\n### Ejemplo\n```python\ndef mostrar_numeros(numeros):\n    for numero in numeros:\n        print(numero)  # Se muestra el elemento de esta vuelta.\n\nmostrar_numeros([1, 2])\n```\nLa lista del ejercicio será distinta; el patrón es el mismo que ya has practicado.""",
        "task": "Sustituye `pass` por un `for producto in productos:` que muestre cada `producto`. Conserva la lista, la función y su llamada preparadas.",
        "hints": ["El for queda dentro de la función y lleva cuatro espacios.", "El print queda dentro del for y lleva ocho espacios.", "No necesitas importar ni abrir nada."],
        "objectives": ["Repasar listas y bucles", "Pasar una lista a una función", "Aplicar sangría en dos bloques"],
        "ra": [], "ce": [],
        "starter": {"python": 'productos = ["Lápiz", "Cuaderno", "Regla"]\n\ndef mostrar_productos(productos):\n    pass\n\nmostrar_productos(productos)\n'},
        "solution": {"python": 'productos = ["Lápiz", "Cuaderno", "Regla"]\n\ndef mostrar_productos(productos):\n    for producto in productos:\n        print(producto)\n\nmostrar_productos(productos)\n'},
        "tests": [
            _test("Sintaxis Python", "python.syntax_valid", {}),
            _test("Lista productos", "python.assignment", {"name": "productos"}),
            _test("Función mostrar_productos", "python.function_declared", {"name": "mostrar_productos", "args": ["productos"]}),
            _test("Bucle de productos", "python.node_kind", {"kind": "for", "non_empty": True}, points=2),
            _test("Recorrido correcto", "python.loop_target", {"name": "producto", "iterable": "productos"}),
            _test("Producto mostrado", "python.call_used", {"name": "print", "arg_names": ["producto"]}),
            _test("Llamada de repaso", "python.call_used", {"name": "mostrar_productos", "arg_names": ["productos"]}),
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
                "description": "Retos progresivos de fundamentos Python, desde print hasta funciones, como preparación inicial para el módulo 0491 Sistemas de gestión empresarial.",
                "created_by": owner,
                "active": True,
            },
        )
        if not course_created:
            course.title = "Introducción a Python para SGE · DAM"
            course.description = "Retos progresivos de fundamentos Python, desde print hasta funciones, como preparación inicial para el módulo 0491 Sistemas de gestión empresarial."
            course.save(update_fields=["title", "description", "updated_at"])

        module, module_created = Module.objects.get_or_create(
            course=course,
            position=1,
            defaults={
                "title": "De los primeros programas a las funciones",
                "description": "Progresión guiada desde print, variables y colecciones hasta funciones. Preparación inicial para 0491; no implementa Odoo ni operaciones de archivos.",
                "weight": 100,
            },
        )
        if not module_created:
            module.title = "De los primeros programas a las funciones"
            module.description = "Progresión guiada desde print, variables y colecciones hasta funciones. Preparación inicial para 0491; no implementa Odoo ni operaciones de archivos."
            module.save(update_fields=["title", "description"])

        created_versions = 0
        existing_versions = 0
        migrated_links = 0
        archived_assignments = 0
        skipped_later_revisions = 0
        for position, item in enumerate(CHALLENGES, start=1):
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
            if activity.position != position:
                activity.position = position
                activity.save(update_fields=["position", "updated_at"])
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
                previous_catalog_titles=(V2_TITLES[item["slug"]],),
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
            # A blank legacy title still gets the friendly v2 title.
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
