"""Seed a guided, static JavaScript introduction for first-year SMR."""

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

TRACK_SLUG = "fundamentos-javascript-smr"
JAVASCRIPT_CATALOG_VERSION = 1
CURRICULUM_SOURCE = "https://www.lexnavarra.navarra.es/detalle.asp?r=9129"


def _test(name, test_type, definition, points=1, visibility=TestCase.Visibility.PUBLIC):
    return (name, test_type, definition, points, visibility)


def _theory(concept, example, explanation):
    return (
        f"### Concepto\n{concept}\n\n### Ejemplo\n```javascript\n{example}\n```"
        f"\n\n### Explicación del ejemplo\n{explanation}"
    )


EXAMPLE_EXPLANATIONS = {
    "01-que-es-javascript": "console.log recibe un texto entre comillas y lo deja como mensaje; no cambia elementos de la página.",
    "02-variable-de-texto": "ciudad es el nombre de la variable y Tudela el dato guardado; console.log usa ese nombre sin comillas.",
    "03-numeros-y-calculo": "subtotal se declara con el resultado de multiplicar las dos variables numéricas ya creadas.",
    "04-unir-textos": "El espacio final queda dentro de Color:  y color se usa como variable, por eso no lleva comillas.",
    "05-listas": "Los corchetes agrupan dos textos en orden y console.log recibe la lista completa.",
    "06-decision-if": "La condición compara edad; las llaves separan el mensaje de cada una de las dos alternativas.",
    "07-bucle-for-of": "color toma un elemento distinto de colores en cada vuelta y el mismo console.log se repite.",
    "08-primera-funcion": "La declaración guarda el bloque bajo el nombre despedirse; la llamada situada después lo utiliza.",
    "09-parametros": "color es el nombre local que recibe el texto azul de la llamada y se muestra dentro de la función.",
    "10-return": "return entrega el cálculo a resultado; console.log está fuera para enseñar que devolver y mostrar son pasos distintos.",
    "11-dom-mensaje": "La primera línea busca el id aviso y la segunda asigna un texto a su propiedad textContent.",
    "12-evento-clic": "El listener queda asociado al botón y conserva una función flecha; su bloque se prepara para el clic.",
    "13-repaso-lista-funcion-bucle": "El bucle entrega cada tarea a mostrar y la función construye y muestra un saludo para esa tarea.",
}


def _challenge(
    slug, title, concept, example, task, starter, solution, tests, objectives, hints, *, html=""
):
    starter_files = {"javascript": starter}
    solution_files = {"javascript": solution}
    if html:
        starter_files = {"html": html, **starter_files}
        solution_files = {"html": html, **solution_files}
    return {
        "slug": slug,
        "title": title,
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 100,
        "theory": _theory(concept, example, EXAMPLE_EXPLANATIONS[slug]),
        "task": task,
        "starter": starter_files,
        "solution": solution_files,
        "tests": tests,
        "objectives": objectives,
        "hints": hints,
    }


CHALLENGES = [
    _challenge(
        "01-que-es-javascript",
        "01 · Tu primera instrucción JavaScript",
        "JavaScript es un lenguaje que da instrucciones a una página. console.log() envía un texto a los Mensajes de tu página de la previsualización. Las comillas indican que es texto.",
        'console.log("Preparado");',
        "1. Cambia solo el texto preparado por Hola, JavaScript.\n2. Pulsa «Ver mi página» y busca el mensaje bajo Mensajes de tu página.\n3. Usa «Comprobar mi trabajo» antes de entregar.",
        'console.log("Cambia este mensaje");\n',
        'console.log("Hola, JavaScript");\n',
        [
            _test("Sintaxis JavaScript", "js.syntax_valid", {}, 1),
            _test("Mensaje solicitado", "js.call_used", {"name": "console.log", "args": ["Hola, JavaScript"]}, 9),
        ],
        ["Reconocer JavaScript como lenguaje de instrucciones", "Mostrar texto con console.log"],
        ["Conserva console.log, los paréntesis y las comillas.", "La mayúscula de JavaScript importa en el mensaje."],
    ),
    _challenge(
        "02-variable-de-texto",
        "02 · Guardar un texto en una variable",
        "Una variable guarda un dato bajo un nombre. const crea una variable que no vas a cambiar aquí. El texto queda a la derecha de = y lleva comillas; al usar la variable no se repiten.",
        'const ciudad = "Tudela";\nconsole.log(ciudad);',
        "1. Sustituye el texto preparado para que nombre guarde Ada.\n2. Añade debajo console.log(nombre).\n3. Pulsa «Ver mi página» para comprobar el mensaje.",
        'const nombre = "Cambia este texto";\n// Muestra nombre debajo.\n',
        'const nombre = "Ada";\nconsole.log(nombre);\n',
        [
            _test("Sintaxis JavaScript", "js.syntax_valid", {}, 1),
            _test("Variable nombre", "js.variable_declared", {"name": "nombre", "expected": "Ada"}, 4),
            _test("Nombre mostrado", "js.call_used", {"name": "console.log", "arg_names": ["nombre"]}, 5),
        ],
        ["Crear una variable de texto", "Usar el valor de una variable"],
        ["No borres const nombre =.", "Dentro de console.log escribe nombre sin comillas."],
    ),
    _challenge(
        "03-numeros-y-calculo",
        "03 · Trabajar con números",
        "Los números se escriben sin comillas. Puedes multiplicar con * y guardar el resultado en otra variable.",
        "const precio = 6;\nconst unidades = 2;\nconst subtotal = precio * unidades;\nconsole.log(subtotal);",
        "1. Cambia precio a 8 y unidades a 3.\n2. Completa total con precio * unidades.\n3. Muestra total con console.log.",
        "const precio = 0;\nconst unidades = 0;\n// Crea total y muéstralo debajo.\n",
        "const precio = 8;\nconst unidades = 3;\nconst total = precio * unidades;\nconsole.log(total);\n",
        [
            _test("Sintaxis JavaScript", "js.syntax_valid", {}, 1),
            _test("Precio guardado", "js.variable_declared", {"name": "precio", "expected": 8}, 2),
            _test("Unidades guardadas", "js.variable_declared", {"name": "unidades", "expected": 3}, 2),
            _test("Cálculo total", "js.variable_declared", {"name": "total", "operator": "*", "left": "precio", "right": "unidades"}, 3),
            _test("Total mostrado", "js.call_used", {"name": "console.log", "arg_names": ["total"]}, 2),
        ],
        ["Distinguir texto y número", "Guardar un cálculo", "Mostrar una variable numérica"],
        ["8 y 3 no llevan comillas.", "A la derecha de total = usa los dos nombres.", "Muestra total sin comillas."],
    ),
    _challenge(
        "04-unir-textos",
        "04 · Unir un texto y una variable",
        "El signo + puede unir textos. Si quieres separar palabras, el espacio forma parte del texto entre comillas.",
        'const color = "azul";\nconst frase = "Color: " + color;\nconsole.log(frase);',
        "1. Conserva la línea que construye etiqueta.\n2. Añade console.log(etiqueta) debajo.\n3. Pulsa «Ver mi página» para leer el mensaje completo.",
        'const producto = "Lápiz";\nconst etiqueta = "Producto: " + producto;\n// Muestra etiqueta debajo.\n',
        'const producto = "Lápiz";\nconst etiqueta = "Producto: " + producto;\nconsole.log(etiqueta);\n',
        [
            _test("Sintaxis JavaScript", "js.syntax_valid", {}, 1),
            _test("Etiqueta preparada", "js.variable_declared", {"name": "etiqueta"}, 2),
            _test("Etiqueta mostrada", "js.call_used", {"name": "console.log", "arg_names": ["etiqueta"]}, 7),
        ],
        ["Unir un texto con una variable", "Mostrar el texto construido"],
        ["No pongas comillas alrededor de etiqueta.", "El espacio ya está preparado dentro de Producto: ."],
    ),
    _challenge(
        "05-listas",
        "05 · Guardar varios elementos en una lista",
        "Una lista guarda varios valores ordenados entre corchetes. Cada elemento se separa con una coma y la lista puede guardarse en una variable.",
        'const dias = ["lunes", "martes"];\nconsole.log(dias);',
        "1. Cambia la lista para que productos contenga Lápiz, Cuaderno y Regla.\n2. Añade console.log(productos).\n3. Pulsa «Ver mi página» para mirar la lista.",
        'const productos = ["Cambia", "estos", "textos"];\n// Muestra productos debajo.\n',
        'const productos = ["Lápiz", "Cuaderno", "Regla"];\nconsole.log(productos);\n',
        [
            _test("Sintaxis JavaScript", "js.syntax_valid", {}, 1),
            _test("Productos preparados", "js.variable_declared", {"name": "productos", "expected": ["Lápiz", "Cuaderno", "Regla"]}, 3),
            _test("Lista mostrada", "js.call_used", {"name": "console.log", "arg_names": ["productos"]}, 6),
        ],
        ["Crear una lista de textos", "Mostrar una lista"],
        ["Cada producto es texto y lleva comillas.", "Conserva los corchetes y separa con comas."],
    ),
    _challenge(
        "06-decision-if",
        "06 · Elegir con if y else",
        "if elige unas instrucciones cuando una condición es cierta. else contiene el otro camino. Las llaves delimitan las instrucciones de cada camino.",
        'const edad = 18;\nif (edad >= 18) {\n  console.log("Puede entrar");\n} else {\n  console.log("Debe esperar");\n}',
        "1. Cambia stock a 5.\n2. Dentro de if escribe console.log con Disponible.\n3. Dentro de else escribe console.log con Sin existencias.",
        "const stock = 0;\nif (stock > 0) {\n  // Escribe el mensaje disponible.\n} else {\n  // Escribe el otro mensaje.\n}\n",
        'const stock = 5;\nif (stock > 0) {\n  console.log("Disponible");\n} else {\n  console.log("Sin existencias");\n}\n',
        [
            _test("Sintaxis JavaScript", "js.syntax_valid", {}, 1),
            _test("Stock preparado", "js.variable_declared", {"name": "stock", "expected": 5}, 3),
            _test("Decisión if", "js.node_kind", {"kind": "if"}, 2),
            _test("Mensaje disponible", "js.call_used", {"name": "console.log", "args": ["Disponible"]}, 2),
            _test("Mensaje alternativo", "js.call_used", {"name": "console.log", "args": ["Sin existencias"]}, 2),
        ],
        ["Reconocer una condición", "Escribir los dos caminos de if y else"],
        ["No cambies la condición stock > 0.", "Cada console.log termina con punto y coma.", "No borres las llaves."],
    ),
    _challenge(
        "07-bucle-for-of",
        "07 · Repetir con for...of",
        "for...of visita los elementos de una lista uno a uno. El nombre después de const representa el elemento actual en cada vuelta.",
        'const colores = ["azul", "verde"];\nfor (const color of colores) {\n  console.log(color);\n}',
        "1. Conserva la lista y la cabecera del bucle preparadas.\n2. Dentro de las llaves añade console.log(producto).\n3. Pulsa «Ver mi página» para ver un mensaje por producto.",
        'const productos = ["Lápiz", "Cuaderno", "Regla"];\nfor (const producto of productos) {\n  // Muestra producto.\n}\n',
        'const productos = ["Lápiz", "Cuaderno", "Regla"];\nfor (const producto of productos) {\n  console.log(producto);\n}\n',
        [
            _test("Sintaxis JavaScript", "js.syntax_valid", {}, 1),
            _test("Lista productos", "js.variable_declared", {"name": "productos"}, 2),
            _test("Bucle for...of", "js.node_kind", {"kind": "for_of"}, 2),
            _test("Producto mostrado", "js.call_used", {"name": "console.log", "arg_names": ["producto"]}, 5),
        ],
        ["Recorrer una lista", "Usar la variable de cada vuelta"],
        ["producto no lleva comillas.", "La línea debe quedar entre las llaves del bucle."],
    ),
    _challenge(
        "08-primera-funcion",
        "08 · Declarar y llamar una función",
        "Una función agrupa instrucciones con un nombre. Primero se declara con function y después se llama escribiendo el nombre y paréntesis. Esta primera función no recibe datos.",
        'function despedirse() {\n  console.log("Hasta luego");\n}\n\ndespedirse();',
        "1. Sustituye el comentario dentro de saludar por console.log con Hola.\n2. Conserva la llamada saludar preparada.\n3. Pulsa «Ver mi página» y lee el mensaje.",
        "function saludar() {\n  // Escribe el saludo.\n}\n\nsaludar();\n",
        'function saludar() {\n  console.log("Hola");\n}\n\nsaludar();\n',
        [
            _test("Sintaxis JavaScript", "js.syntax_valid", {}, 1),
            _test("Función saludar", "js.function_declared", {"name": "saludar"}, 2),
            _test("Llamada a saludar", "js.call_used", {"name": "saludar", "args": []}, 2),
            _test("Saludo de la función", "js.call_used", {"name": "console.log", "args": ["Hola"]}, 5),
        ],
        ["Declarar una función sin parámetros", "Llamar una función"],
        ["El console.log queda entre las llaves.", "La llamada se queda después de la llave final."],
    ),
    _challenge(
        "09-parametros",
        "09 · Pasar un dato a una función",
        "Un parámetro es el nombre que una función recibe entre sus paréntesis. El argumento es el dato escrito al llamar la función. Dentro de la función se usa el parámetro.",
        'function mostrarColor(color) {\n  console.log(color);\n}\n\nmostrarColor("azul");',
        "1. Dentro de mostrar(producto) sustituye el comentario por console.log(producto).\n2. Conserva la llamada preparada con Cuaderno.\n3. Comprueba el mensaje en la previsualización.",
        'function mostrar(producto) {\n  // Muestra el producto recibido.\n}\n\nmostrar("Cuaderno");\n',
        'function mostrar(producto) {\n  console.log(producto);\n}\n\nmostrar("Cuaderno");\n',
        [
            _test("Sintaxis JavaScript", "js.syntax_valid", {}, 1),
            _test("Función mostrar", "js.function_declared", {"name": "mostrar"}, 2),
            _test("Llamada con Cuaderno", "js.call_used", {"name": "mostrar", "args": ["Cuaderno"]}, 2),
            _test("Parámetro mostrado", "js.call_used", {"name": "console.log", "arg_names": ["producto"]}, 5),
        ],
        ["Reconocer parámetro y argumento", "Usar un parámetro dentro de una función"],
        ["Dentro de console.log usa producto sin comillas.", "No cambies Cuaderno."],
    ),
    _challenge(
        "10-return",
        "10 · Devolver un resultado con return",
        "return entrega un resultado desde una función. Quien llama la función puede guardarlo en una variable. return no muestra por sí solo un mensaje.",
        "function duplicar(numero) {\n  return numero * 2;\n}\n\nconst resultado = duplicar(3);\nconsole.log(resultado);",
        "1. Sustituye el comentario por return numero * 2.\n2. Conserva la llamada duplicar(4) y el console.log preparados.\n3. Pulsa «Ver mi página» para leer el resultado.",
        "function duplicar(numero) {\n  // Devuelve el doble.\n}\n\nconst doble = duplicar(4);\nconsole.log(doble);\n",
        "function duplicar(numero) {\n  return numero * 2;\n}\n\nconst doble = duplicar(4);\nconsole.log(doble);\n",
        [
            _test("Sintaxis JavaScript", "js.syntax_valid", {}, 1),
            _test("Función duplicar", "js.function_declared", {"name": "duplicar"}, 2),
            _test("Llamada con 4", "js.call_used", {"name": "duplicar", "args": [4]}, 2),
            _test("Resultado devuelto", "js.return_expression", {"operator": "*", "left": "numero", "right": 2}, 4),
            _test("Doble mostrado", "js.call_used", {"name": "console.log", "arg_names": ["doble"]}, 1),
        ],
        ["Distinguir return de console.log", "Guardar el resultado de una función"],
        ["return queda dentro de las llaves.", "numero no lleva comillas."],
    ),
    _challenge(
        "11-dom-mensaje",
        "11 · Cambiar un mensaje de la página",
        "El DOM representa los elementos de la página. document.getElementById busca el elemento HTML con ese id. textContent cambia el texto visible de ese elemento.",
        'const aviso = document.getElementById("aviso");\naviso.textContent = "Página preparada";',
        "1. Conserva la línea que busca mensaje.\n2. Añade mensaje.textContent con Hola desde JavaScript.\n3. Pulsa «Ver mi página» y observa el texto del Resultado.",
        'const mensaje = document.getElementById("mensaje");\n// Cambia el texto visible.\n',
        'const mensaje = document.getElementById("mensaje");\nmensaje.textContent = "Hola desde JavaScript";\n',
        [
            _test("Sintaxis JavaScript", "js.syntax_valid", {}, 1),
            _test("Elemento mensaje buscado", "js.call_used", {"name": "document.getElementById", "args": ["mensaje"]}, 3),
            _test("Variable mensaje", "js.variable_declared", {"name": "mensaje"}, 2),
            _test("Asignación al DOM", "js.assignment_equals", {"target": "mensaje.textContent", "expected": "Hola desde JavaScript"}, 4),
        ],
        ["Relacionar un id HTML con JavaScript", "Cambiar un texto visible mediante el DOM"],
        ["mensaje no lleva comillas.", "El nuevo contenido sí lleva comillas.", "No edites el HTML preparado."],
        html='<!doctype html>\n<html lang="es">\n  <body>\n    <p id="mensaje">Aún no hay mensaje.</p>\n  </body>\n</html>\n',
    ),
    _challenge(
        "12-evento-clic",
        "12 · Reaccionar a un clic",
        "Un evento es algo que sucede en la página, por ejemplo un clic. addEventListener indica qué instrucciones preparar para ese evento. Dentro del bloque se puede cambiar un elemento ya buscado.",
        'const boton = document.getElementById("abrir");\nboton.addEventListener("click", () => {\n  console.log("Se ha pulsado");\n});',
        "1. Conserva las líneas preparadas y el evento click.\n2. Dentro de las llaves añade una asignación a mensaje.textContent con Has pulsado el botón.\n3. Pulsa «Ver mi página», pulsa el botón del Resultado y comprueba el cambio.",
        'const boton = document.getElementById("boton");\nconst mensaje = document.getElementById("mensaje");\n\nboton.addEventListener("click", () => {\n  // Cambia el mensaje.\n});\n',
        'const boton = document.getElementById("boton");\nconst mensaje = document.getElementById("mensaje");\n\nboton.addEventListener("click", () => {\n  mensaje.textContent = "Has pulsado el botón";\n});\n',
        [
            _test("Sintaxis JavaScript", "js.syntax_valid", {}, 1),
            _test("Botón buscado", "js.call_used", {"name": "document.getElementById", "args": ["boton"]}, 1),
            _test("Evento click", "js.event_listener_registered", {"event": "click", "target": "boton"}, 2),
            _test("Cambio preparado", "js.assignment_equals", {"target": "mensaje.textContent", "expected": "Has pulsado el botón"}, 6),
        ],
        ["Registrar un evento click", "Cambiar el DOM al responder a un evento"],
        ["La asignación va dentro de las llaves.", "mensaje no lleva comillas.", "El texto nuevo sí necesita comillas."],
        html='<!doctype html>\n<html lang="es">\n  <body>\n    <button id="boton">Saludar</button>\n    <p id="mensaje">Esperando clic.</p>\n  </body>\n</html>\n',
    ),
    _challenge(
        "13-repaso-lista-funcion-bucle",
        "13 · Repaso: lista, función y bucle",
        "Los programas pequeños combinan ideas conocidas: una lista guarda datos, un bucle los visita y una función evita repetir una instrucción. Cada pieza mantiene su trabajo sencillo.",
        'const tareas = ["leer", "practicar"];\nfunction mostrar(tarea) {\n  console.log("Tarea: " + tarea);\n}\nfor (const tarea of tareas) {\n  mostrar(tarea);\n}',
        "1. Dentro de mostrar(nombre), cambia el comentario por console.log con Hola, y nombre.\n2. Conserva la lista, el bucle y la llamada preparados.\n3. Pulsa «Ver mi página» para comprobar un mensaje por nombre.",
        'const nombres = ["Ana", "Leo"];\n\nfunction mostrar(nombre) {\n  // Saluda al nombre recibido.\n}\n\nfor (const nombre of nombres) {\n  mostrar(nombre);\n}\n',
        'const nombres = ["Ana", "Leo"];\n\nfunction mostrar(nombre) {\n  console.log("Hola, " + nombre);\n}\n\nfor (const nombre of nombres) {\n  mostrar(nombre);\n}\n',
        [
            _test("Sintaxis JavaScript", "js.syntax_valid", {}, 1),
            _test("Lista de nombres", "js.node_kind", {"kind": "array"}, 1),
            _test("Función mostrar", "js.function_declared", {"name": "mostrar"}, 2),
            _test("Bucle for...of", "js.node_kind", {"kind": "for_of"}, 2),
            _test("Llamada con nombre", "js.call_used", {"name": "mostrar", "arg_names": ["nombre"]}, 1),
            _test("Saludo mostrado", "js.call_used", {"name": "console.log"}, 3),
        ],
        ["Combinar lista, función y bucle", "Reutilizar un parámetro"],
        ["El espacio después de la coma forma parte de Hola, .", "nombre no lleva comillas.", "No hace falta añadir DOM ni ideas nuevas."],
    ),
]


class Command(BaseCommand):
    help = "Crea el itinerario local de 13 retos JavaScript para primero de SMR."

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
            name=self._academic_year_name(options.get("academic_year")), defaults={"active": True}
        )
        cohort, _ = Cohort.objects.get_or_create(
            name=options["cohort"],
            academic_year=year,
            defaults={"active": True, "track": Cohort.Track.WEB},
        )
        ensure_cohort_track(cohort, Cohort.Track.WEB)
        if owner.role == User.Role.TEACHER and not owner.is_superuser:
            TeachingAssignment.objects.get_or_create(cohort=cohort, teacher=owner, defaults={"active": True})

        course, course_created = Course.objects.get_or_create(
            slug=TRACK_SLUG,
            defaults={
                "title": "Fundamentos de JavaScript · SMR",
                "description": "Ruta guiada desde las primeras instrucciones hasta DOM y clics. El corrector del servidor es estático y la previsualización aislada permite observar el resultado del navegador.",
                "created_by": owner,
                "active": True,
            },
        )
        if not course_created:
            course.title = "Fundamentos de JavaScript · SMR"
            course.description = "Ruta guiada desde las primeras instrucciones hasta DOM y clics. El corrector del servidor es estático y la previsualización aislada permite observar el resultado del navegador."
            course.save(update_fields=["title", "description", "updated_at"])
        course.web_stage = Course.WebStage.JAVASCRIPT
        course.save(update_fields=["web_stage", "updated_at"])

        module, module_created = Module.objects.get_or_create(
            course=course,
            position=1,
            defaults={
                "title": "De la primera instrucción al clic",
                "description": "Consola, variables, listas, decisiones, bucles, funciones y un DOM mínimo con HTML preparado.",
                "weight": 100,
            },
        )
        if not module_created:
            module.title = "De la primera instrucción al clic"
            module.description = "Consola, variables, listas, decisiones, bucles, funciones y un DOM mínimo con HTML preparado."
            module.save(update_fields=["title", "description"])

        created_versions = existing_versions = migrated_links = archived_assignments = skipped = 0
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
            if activity.versions.filter(version_number__gt=JAVASCRIPT_CATALOG_VERSION).exists():
                skipped += 1
                continue
            version, version_created = ActivityVersion.objects.get_or_create(
                activity=activity,
                version_number=JAVASCRIPT_CATALOG_VERSION,
                defaults={
                    "language": ActivityVersion.Language.WEB,
                    "difficulty": item["difficulty"],
                    "xp_reward": item["xp"],
                    "hints": item["hints"],
                    "instructions": f"## Antes de empezar\nTrabaja solo en la pestaña JavaScript, salvo que los pasos indiquen el HTML ya preparado. No necesitas instalar nada ni crear archivos.\n\n{item['theory']}\n\n## Ejercicio\n{item['task']}\n\n> «Ver mi página» ejecuta solo la previsualización aislada del navegador: usa el Resultado y los Mensajes de tu página para observar el ejemplo. «Comprobar mi trabajo» analiza la estructura con Esprima en el servidor; no ejecuta tu JavaScript ni demuestra por sí solo el resultado del navegador.",
                    "objectives": item["objectives"],
                    "learning_outcomes": [],
                    "assessment_criteria": [],
                    "professional_module_code": "0228",
                    "curriculum_scope": "Navarra · cobertura parcial",
                    "curriculum_edition": "navarra-2025",
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

            current_version_number = (
                ActivityVersion.objects.filter(pk=activity.current_version_id)
                .values_list("version_number", flat=True)
                .first()
                if activity.current_version_id
                else None
            )
            if current_version_number is None or current_version_number < version.version_number:
                activity.current_version = version
                activity.status = Activity.Status.PUBLISHED
                activity.save(update_fields=["current_version", "status", "updated_at"])

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
                            "feedback": "Revisa los pasos y la estructura indicada; el servidor analiza el código sin ejecutarlo.",
                            "position": position,
                        },
                    )
            _assignment, _created, upgrade = get_or_create_catalog_revision_assignment(
                activity=activity,
                version=version,
                cohort=cohort,
                previous_catalog_titles=(),
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
            migrated_links += upgrade["migrated_links"]
            archived_assignments += upgrade["archived_assignments"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Itinerario JavaScript v{JAVASCRIPT_CATALOG_VERSION} listo: {len(CHALLENGES)} retos, grupo {cohort.name}, "
                f"{created_versions} versiones nuevas y {existing_versions} ya existentes. "
                f"Actualizados {migrated_links} vínculos y archivadas {archived_assignments} asignaciones anteriores. "
                f"Omitidas {skipped} actividades con una revisión posterior."
            )
        )
        self.stdout.write("No se han creado alumnos ni contraseñas; el catálogo es contenido formativo local.")
