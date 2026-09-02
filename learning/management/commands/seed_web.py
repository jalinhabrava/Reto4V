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
    Cohort,
    Course,
    Module,
    TeachingAssignment,
    TestCase,
)

from ._catalog import ensure_cohort_track, get_or_create_catalog_revision_assignment

TRACK_SLUG = "fundamentos-web-smr"
CURRICULUM_SOURCE = "https://www.lexnavarra.navarra.es/detalle.asp?r=9129"


def _test(name, test_type, definition, points=1, visibility=TestCase.Visibility.PUBLIC):
    return (name, test_type, definition, points, visibility)


WEB_CATALOG_VERSION = 2


def _files(html, css=None, javascript=None):
    """Return the web files introduced up to this point in the path.

    Keeping the starter beside the solution makes the amount of work visible
    when somebody reviews the catalogue.  The editor already supplies the
    files, so a beginner never has to create folders or guess a filename.
    """

    files = {"html": html}
    if css is not None:
        files["css"] = css
    if javascript is not None:
        files["javascript"] = javascript
    return files


CHALLENGES = [
    {
        # Keep the historical activity slug so an upgrade can publish v2 on
        # the same activity instead of creating a second copy of the path.
        "slug": "01-estructura-semantica",
        "title": "01 · Mi primera página",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 100,
        "theory": "Una página web empieza con palabras. HTML es la forma de decirle al navegador qué texto es un título y qué texto es un párrafo.",
        "task": "1. En la pestaña `index.html`, busca el texto que aparece dentro de `<h1>` y escribe `Mi primera página web`.\n2. Cambia el texto del párrafo por `Estoy aprendiendo a crear páginas web.`.\n3. Pulsa «Ver mi página» para ver el resultado.",
        "hints": [
            "El título grande está entre `<h1>` y `</h1>`.",
            "El párrafo está entre `<p>` y `</p>`. Cambia solo las palabras que hay dentro.",
        ],
        "objectives": [
            "Cambiar el texto que verá una persona en un título",
            "Escribir una frase dentro de un párrafo",
            "Reconocer que una página puede empezar con dos etiquetas sencillas",
        ],
        "ra": ["RA1"],
        "ce": ["RA1.b", "RA1.d"],
        "html": "<h1>Mi primera página web</h1>\n<p>Estoy aprendiendo a crear páginas web.</p>\n",
        "starter": _files(
            "<h1>Escribe aquí el título</h1>\n<p>Escribe aquí una frase.</p>\n",
        ),
        "css": "",
        "javascript": "",
        "tests": [
            _test("Título preparado", "html.selector_exists", {"selector": "h1"}),
            _test("Texto del título", "html.text_contains", {"selector": "h1", "expected": "Mi primera página web"}),
            _test("Texto del párrafo", "html.text_contains", {"selector": "p", "expected": "Estoy aprendiendo a crear páginas web."}),
            _test("Párrafo preparado", "html.selector_exists", {"selector": "p"}),
        ],
    },
    {
        "slug": "enlaces-y-atributos",
        "title": "02 · Títulos y párrafos",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 110,
        "theory": "Los títulos ayudan a ordenar una página y los párrafos sirven para explicar cada idea. Usar cada etiqueta para lo que corresponde hace que la página se entienda mejor.",
        "task": "1. Conserva el título grande que ya está preparado.\n2. Debajo, escribe un subtítulo con `<h2>` y pon dentro `Mi afición`.\n3. En la línea siguiente, escribe un párrafo con `Me gusta aprender cosas nuevas.`.\n4. Pulsa «Ver mi página» y comprueba que los tres textos aparecen en ese orden.",
        "hints": [
            "Un subtítulo se escribe así: `<h2>Texto del subtítulo</h2>`.",
            "Un párrafo se escribe así: `<p>Una frase completa.</p>`.",
            "Escribe las dos líneas nuevas debajo de `<h1>Mi página</h1>`.",
        ],
        "objectives": [
            "Distinguir un título principal de un subtítulo",
            "Usar un párrafo para explicar una idea",
            "Colocar el texto dentro de la etiqueta adecuada",
        ],
        "ra": ["RA1"],
        "ce": ["RA1.b", "RA1.d"],
        "html": "<h1>Mi página</h1>\n<h2>Mi afición</h2>\n<p>Me gusta aprender cosas nuevas.</p>\n",
        "starter": _files(
            "<h1>Mi página</h1>\n<!-- Escribe aquí debajo un h2 y un p. -->\n",
        ),
        "css": "",
        "javascript": "",
        "tests": [
            _test("Título principal", "html.text_contains", {"selector": "h1", "expected": "Mi página"}),
            _test("Texto del subtítulo", "html.text_contains", {"selector": "h2", "expected": "Mi afición"}),
            _test("Texto de explicación", "html.text_contains", {"selector": "p", "expected": "Me gusta aprender cosas nuevas."}),
            _test("Título antes del subtítulo", "html.element_order", {"first": "h1", "second": "h2"}),
        ],
    },
    {
        "slug": "listas-y-tablas",
        "title": "03 · Mi primer enlace",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 120,
        "theory": "Un enlace es una palabra o botón que lleva a otra página. Tiene dos partes: el texto que se ve y el destino que se escribe en `href`.",
        "task": "1. Cambia el primer enlace para que diga `Inicio` y tenga como destino `/inicio`.\n2. Añade un segundo enlace que diga `Aula` y tenga como destino `/clase`.\n3. No borres `<nav>`: es el bloque que reúne los enlaces.\n4. No hace falta abrir los enlaces: sus destinos son de ejemplo. Revisa el código y pulsa «Comprobar mi trabajo».",
        "hints": [
            "Un enlace tiene esta forma: `<a href=\"destino\">palabras</a>`.",
            "Empieza con destinos fáciles como `/inicio` y `/clase`.",
            "El valor de `href` va entre comillas.",
        ],
        "objectives": [
            "Crear dos enlaces que se puedan pulsar",
            "Escribir un destino sencillo en href",
            "Dar un nombre claro a cada enlace",
        ],
        "ra": ["RA1"],
        "ce": ["RA1.b", "RA1.d"],
        "html": "<nav aria-label=\"Enlaces de clase\">\n  <a href=\"/inicio\">Inicio</a>\n  <a href=\"/clase\">Aula</a>\n</nav>\n",
        "starter": _files(
            "<nav aria-label=\"Enlaces de clase\">\n  <a href=\"#\">Cambia este texto</a>\n  <!-- Añade aquí el segundo enlace. -->\n</nav>\n",
        ),
        "css": "",
        "javascript": "",
        "tests": [
            _test("Dos enlaces", "html.selector_count", {"selector": "nav a", "expected": 2}),
            _test("Nombre de navegación", "html.attribute_equals", {"selector": "nav", "attribute": "aria-label", "expected": "Enlaces de clase"}),
            _test("Destino de inicio", "html.attribute_equals", {"selector": "a[href='/inicio']", "attribute": "href", "expected": "/inicio"}),
            _test("Destino del aula", "html.attribute_equals", {"selector": "a[href='/clase']", "attribute": "href", "expected": "/clase"}),
        ],
    },
    {
        "slug": "formularios-accesibles",
        "title": "04 · Una imagen en la página",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 130,
        "theory": "Una imagen puede enseñar algo de un vistazo. La dirección `src` ya está preparada. El texto `alt` cuenta con palabras qué aparece, por si la imagen no se puede ver.",
        "task": "1. Pulsa «Ver mi página» y observa la imagen que ya está preparada.\n2. En la pestaña `index.html`, busca `alt=\"Escribe aquí qué aparece\"`.\n3. Cambia solo esas palabras por `Un ordenador sobre una mesa`.\n4. Vuelve a pulsar «Ver mi página» y conserva el título `Mi lugar de estudio`.",
        "hints": [
            "No cambies `src`: esa parte ya indica dónde está la imagen.",
            "`alt` debe explicar qué se vería, no decir solamente «imagen».",
            "No hace falta crear carpetas ni descargar nada para superar este reto.",
        ],
        "objectives": [
            "Describir una imagen con texto alternativo",
            "Aprender para qué sirve src",
            "Colocar una imagen debajo de un título",
        ],
        "ra": ["RA1"],
        "ce": ["RA1.b", "RA1.e"],
        "html": "<h2>Mi lugar de estudio</h2>\n<img src=\"/static/learning/ordenador.svg\" alt=\"Un ordenador sobre una mesa\">\n",
        "starter": _files(
            "<h2>Mi lugar de estudio</h2>\n<img src=\"/static/learning/ordenador.svg\" alt=\"Escribe aquí qué aparece\">\n",
        ),
        "css": "",
        "javascript": "",
        "tests": [
            _test("Imagen preparada", "html.selector_exists", {"selector": "img"}),
            _test("Imagen del ejercicio", "html.attribute_equals", {"selector": "img", "attribute": "src", "expected": "/static/learning/ordenador.svg"}),
            _test("Descripción alternativa", "html.attribute_equals", {"selector": "img", "attribute": "alt", "expected": "Un ordenador sobre una mesa"}),
            _test("Título de la imagen", "html.text_contains", {"selector": "h2", "expected": "Mi lugar de estudio"}),
        ],
    },
    {
        "slug": "multimedia-responsiva",
        "title": "05 · Una lista de cosas",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 140,
        "theory": "Cuando tenemos varios elementos, una lista los ordena y facilita leerlos. `ul` es la lista y cada `li` es una línea de esa lista.",
        "task": "1. Conserva la lista que ya aparece.\n2. Cambia el primer elemento por `Teclado`.\n3. Añade dos elementos más: `Cuaderno` y `Mochila`.\n4. Comprueba que hay tres líneas dentro de la misma lista.",
        "hints": [
            "Cada elemento de una lista va entre `<li>` y `</li>`.",
            "Todos los `<li>` tienen que quedar entre `<ul>` y `</ul>`.",
            "Puedes copiar la línea que empieza por `<li>` y cambiar sus palabras.",
        ],
        "objectives": [
            "Usar una lista para presentar varios elementos",
            "Crear tres elementos li",
            "Mantener la lista ordenada dentro de ul",
        ],
        "ra": ["RA1"],
        "ce": ["RA1.b", "RA1.d"],
        "html": "<section>\n  <h2>Material de clase</h2>\n  <ul>\n    <li>Teclado</li>\n    <li>Cuaderno</li>\n    <li>Mochila</li>\n  </ul>\n</section>\n",
        "starter": _files(
            "<section>\n  <h2>Material de clase</h2>\n  <ul>\n    <li>Escribe aquí el primer elemento</li>\n    <!-- Añade dos elementos más. -->\n  </ul>\n</section>\n",
        ),
        "css": "",
        "javascript": "",
        "tests": [
            _test("Lista preparada", "html.selector_exists", {"selector": "ul"}),
            _test("Tres elementos", "html.selector_count", {"selector": "ul li", "expected": 3}),
            _test("Material de teclado", "html.text_contains", {"selector": "li", "expected": "Teclado"}),
            _test("Título de la lista", "html.text_contains", {"selector": "h2", "expected": "Material de clase"}),
        ],
    },
    {
        "slug": "html-limpio-y-valido",
        "title": "06 · Colores con CSS",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 150,
        "theory": "HTML pone las palabras y CSS decide cómo se ven. Una regla CSS empieza por un elemento, como `body`, y dentro indica los cambios que quieres hacer.",
        "task": "1. Abre la pestaña `styles.css`; no necesitas tocar `index.html`.\n2. Escribe una regla para `body`.\n3. Dentro de la regla, pon el texto en color `#16324f` y el fondo en color `#f7f9fc`.\n4. Pulsa «Ver mi página» para ver el cambio.",
        "hints": [
            "Una regla tiene esta forma: `body { propiedad: valor; }`.",
            "El color del texto se cambia con `color` y el fondo con `background-color`.",
            "No olvides el punto y coma después de cada cambio.",
        ],
        "objectives": [
            "Reconocer una regla CSS",
            "Cambiar el color del texto de la página",
            "Cambiar el color de fondo de la página",
        ],
        "ra": ["RA1"],
        "ce": ["RA1.f"],
        "html": "<!doctype html>\n<html lang=\"es\">\n  <head><meta charset=\"utf-8\"><title>Mi rincón</title></head>\n  <body>\n    <main>\n      <h1>Mi rincón</h1>\n      <p>Un espacio para aprender.</p>\n    </main>\n  </body>\n</html>\n",
        "starter": _files(
            "<!doctype html>\n<html lang=\"es\">\n  <head><meta charset=\"utf-8\"><title>Mi rincón</title></head>\n  <body>\n    <main>\n      <h1>Mi rincón</h1>\n      <p>Un espacio para aprender.</p>\n    </main>\n  </body>\n</html>\n",
            "/* Escribe aquí una regla para body. */\n",
        ),
        "css": "body { color: #16324f; background-color: #f7f9fc; }\n",
        "javascript": "",
        "tests": [
            _test("Regla para la página", "css.selector_exists", {"selector": "body"}),
            _test("Color del texto", "css.declaration_equals", {"selector": "body", "property": "color", "expected": "#16324f"}),
            _test("Color del fondo", "css.declaration_equals", {"selector": "body", "property": "background-color", "expected": "#f7f9fc"}),
            _test("Título visible", "html.text_contains", {"selector": "h1", "expected": "Mi rincón"}),
        ],
    },
    {
        "slug": "css-selectores-y-color",
        "title": "07 · Espacios y bordes",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 160,
        "theory": "Los elementos de una página son como cajas. `padding` deja espacio dentro de la caja y `border` dibuja una línea alrededor.",
        "task": "1. En la pestaña `styles.css`, busca el selector `.tarjeta`.\n2. Añade `padding: 16px` para separar el texto del borde.\n3. Añade un borde `2px solid #cbd5e1`.\n4. Puedes añadir `border-radius: 8px` para redondear las esquinas.",
        "hints": [
            "El punto delante de `tarjeta` indica que es una clase: `.tarjeta { ... }`.",
            "Escribe cada cambio dentro de las llaves del selector.",
            "El borde se escribe con grosor, tipo y color: `2px solid #cbd5e1`.",
        ],
        "objectives": [
            "Dar espacio interior a una tarjeta",
            "Dibujar un borde visible",
            "Aplicar reglas a una clase concreta",
        ],
        "ra": ["RA1"],
        "ce": ["RA1.f", "RA1.g"],
        "html": "<article class=\"tarjeta\">\n  <h2>Mi material</h2>\n  <p>Una tarjeta es una caja para agrupar información.</p>\n</article>\n",
        "starter": _files(
            "<article class=\"tarjeta\">\n  <h2>Mi material</h2>\n  <p>Una tarjeta es una caja para agrupar información.</p>\n</article>\n",
            ".tarjeta {\n  /* Añade espacio y un borde. */\n}\n",
        ),
        "css": ".tarjeta { padding: 16px; border: 2px solid #cbd5e1; border-radius: 8px; }\n",
        "javascript": "",
        "tests": [
            _test("Selector de tarjeta", "css.selector_exists", {"selector": ".tarjeta"}),
            _test("Espacio interior", "css.declaration_equals", {"selector": ".tarjeta", "property": "padding", "expected": "16px"}),
            _test("Borde visible", "css.declaration_equals", {"selector": ".tarjeta", "property": "border", "expected": "2px solid #cbd5e1"}),
            _test("Contenido de tarjeta", "html.selector_exists", {"selector": ".tarjeta h2"}),
        ],
    },
    {
        "slug": "css-modelo-de-caja",
        "title": "08 · Colocar elementos juntos",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 170,
        "theory": "A veces queremos que dos cajas queden una al lado de la otra. Con `display: flex` el navegador las coloca en fila y con `gap` deja un espacio entre ellas.",
        "task": "1. Abre la pestaña `styles.css` y busca el selector `.fila`.\n2. Escribe `display: flex` para colocar las cajas en la misma fila.\n3. Añade `gap: 16px` para separarlas.\n4. La regla `.caja` ya está preparada para que las dos cajas compartan el espacio; no necesitas cambiarla.",
        "hints": [
            "La regla que necesitas es `.fila { display: flex; }`.",
            "Añade `gap: 16px` dentro de las mismas llaves.",
            "`display` decide cómo se colocan los elementos; `gap` decide la distancia.",
        ],
        "objectives": [
            "Colocar dos cajas en la misma fila",
            "Usar display:flex",
            "Separar cajas con gap",
        ],
        "ra": ["RA1"],
        "ce": ["RA1.f", "RA1.g"],
        "html": "<div class=\"fila\">\n  <div class=\"caja\">Primera caja</div>\n  <div class=\"caja\">Segunda caja</div>\n</div>\n",
        "starter": _files(
            "<div class=\"fila\">\n  <div class=\"caja\">Primera caja</div>\n  <div class=\"caja\">Segunda caja</div>\n</div>\n",
            ".fila {\n  /* Coloca las cajas juntas y sepáralas. */\n}\n.caja {\n  flex: 1;\n  /* Ya está preparada: las dos cajas comparten el espacio. */\n}\n",
        ),
        "css": ".fila { display: flex; gap: 16px; }\n.caja { flex: 1; }\n",
        "javascript": "",
        "tests": [
            _test("Cajas preparadas", "html.selector_count", {"selector": ".caja", "expected": 2}),
            _test("Cajas en fila", "css.declaration_equals", {"selector": ".fila", "property": "display", "expected": "flex"}),
            _test("Separación entre cajas", "css.declaration_equals", {"selector": ".fila", "property": "gap", "expected": "16px"}),
            _test("Cajas del mismo tamaño", "css.declaration_equals", {"selector": ".caja", "property": "flex", "expected": "1"}),
        ],
    },
    {
        "slug": "css-responsive",
        "title": "09 · Un formulario sencillo",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 180,
        "theory": "Un formulario permite pedir un dato. La etiqueta explica qué hay que escribir y `required` avisa de que el campo no se debe dejar vacío.",
        "task": "1. En la pestaña `index.html`, relaciona la etiqueta con el campo: la etiqueta debe tener `for=\"nombre\"` y el campo `id=\"nombre\"`.\n2. Añade `required` al campo para indicar que es obligatorio.\n3. Añade el texto `Escribe tu nombre` como `placeholder`.\n4. Conserva el botón `Enviar`.",
        "hints": [
            "`for` e `id` tienen que contener exactamente el mismo nombre.",
            "Un campo obligatorio puede escribirse así: `<input ... required>`.",
            "El texto de ayuda va en `placeholder=\"Escribe tu nombre\"`.",
        ],
        "objectives": [
            "Relacionar una etiqueta con su campo",
            "Marcar un dato obligatorio",
            "Usar un botón para enviar un formulario",
        ],
        "ra": ["RA1"],
        "ce": ["RA1.b", "RA1.d"],
        "html": "<form action=\"/enviar\" method=\"post\">\n  <label for=\"nombre\">Tu nombre</label>\n  <input id=\"nombre\" name=\"nombre\" type=\"text\" required placeholder=\"Escribe tu nombre\">\n  <button type=\"submit\">Enviar</button>\n</form>\n",
        "starter": _files(
            "<form action=\"/enviar\" method=\"post\">\n  <label for=\"nombre\">Tu nombre</label>\n  <input id=\"nombre\" name=\"nombre\" type=\"text\">\n  <button type=\"submit\">Enviar</button>\n</form>\n",
            "form { max-width: 24rem; }\n",
        ),
        "css": "form { max-width: 24rem; }\n",
        "javascript": "",
        "tests": [
            _test("Formulario preparado", "html.selector_exists", {"selector": "form"}),
            _test("Etiqueta relacionada", "html.attribute_equals", {"selector": "label", "attribute": "for", "expected": "nombre"}),
            _test("Campo de texto", "html.attribute_equals", {"selector": "#nombre", "attribute": "type", "expected": "text"}),
            _test("Campo obligatorio", "html.selector_exists", {"selector": "input[required]"}),
            _test("Botón de envío", "html.attribute_equals", {"selector": "button", "attribute": "type", "expected": "submit"}),
        ],
    },
    {
        "slug": "javascript-funciones-y-datos",
        "title": "10 · Guardar un texto en JavaScript",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 190,
        "theory": "JavaScript permite añadir pequeñas acciones a una página. Una variable es como una caja con nombre donde guardamos un dato para usarlo después.",
        "task": "1. Abre la pestaña `script.js`.\n2. Crea una variable llamada `saludo`.\n3. Guarda dentro el texto `Hola, estoy aprendiendo JavaScript`.\n4. No necesitas hacer que ocurra nada todavía: en el siguiente reto aprenderás a responder al clic de un botón.",
        "hints": [
            "Una variable de texto puede escribirse así: `const saludo = 'Un texto';`.",
            "El nombre que pide el reto es `saludo`, todo en minúsculas.",
            "El texto debe ir entre comillas simples o dobles.",
        ],
        "objectives": [
            "Guardar un texto en una variable",
            "Escribir JavaScript con sintaxis válida",
            "Distinguir una instrucción de una etiqueta HTML",
        ],
        "ra": ["RA1"],
        "ce": ["RA1.h"],
        "html": "<main><h1>Un saludo</h1></main>\n",
        "starter": _files(
            "<main><h1>Un saludo</h1></main>\n",
            "main { max-width: 40rem; }\n",
            "// Guarda aquí tu primer texto en una variable.\n",
        ),
        "css": "main { max-width: 40rem; }\n",
        "javascript": "const saludo = 'Hola, estoy aprendiendo JavaScript';\n",
        "tests": [
            _test("JavaScript válido", "js.syntax_valid", {}),
            _test("Variable saludo", "js.variable_declared", {"name": "saludo"}),
            _test("Sin ejecución dinámica", "js.forbidden_api_absent", {"api": "eval"}),
        ],
    },
    {
        "slug": "javascript-eventos-dom",
        "title": "11 · Reaccionar a un clic",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 210,
        "theory": "Una página puede responder cuando hacemos clic. JavaScript puede localizar un botón y escuchar su evento `click` para cambiar un mensaje.",
        "task": "1. El botón y el mensaje ya están preparados en la pestaña `index.html`.\n2. En la pestaña `script.js`, conserva la línea que busca el botón.\n3. Añade un aviso para el evento `click` usando `addEventListener`.\n4. Cuando se pulse, cambia el texto de `#mensaje` por `¡Hola!`.",
        "hints": [
            "El patrón es `boton.addEventListener('click', () => { ... });`.",
            "Para buscar el mensaje puedes usar `document.querySelector('#mensaje')`.",
            "El texto que cambia está en `.textContent`.",
        ],
        "objectives": [
            "Seleccionar un elemento de la página",
            "Escuchar un clic del botón",
            "Cambiar un mensaje mediante JavaScript",
        ],
        "ra": ["RA1"],
        "ce": ["RA1.h"],
        "html": "<button id=\"saludar\" type=\"button\">Saludar</button>\n<p id=\"mensaje\">Aquí aparecerá el mensaje.</p>\n",
        "starter": _files(
            "<button id=\"saludar\" type=\"button\">Saludar</button>\n<p id=\"mensaje\">Aquí aparecerá el mensaje.</p>\n",
            "button { cursor: pointer; }\n",
            "const boton = document.querySelector('#saludar');\n// Escucha el clic y cambia el mensaje.\n",
        ),
        "css": "button { cursor: pointer; }\n",
        "javascript": "const boton = document.querySelector('#saludar');\nboton.addEventListener('click', () => {\n  document.querySelector('#mensaje').textContent = '¡Hola!';\n});\n",
        "tests": [
            _test("JavaScript válido", "js.syntax_valid", {}),
            _test("Botón seleccionado", "js.variable_declared", {"name": "boton"}),
            _test("Evento de clic", "js.event_listener_registered", {"event": "click", "target": "boton"}),
            _test("Sin API peligrosa", "js.forbidden_api_absent", {"api": "document.write"}),
        ],
    },
    {
        "slug": "panel-integrado-web",
        "title": "12 · Mi tarjeta de presentación",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 240,
        "theory": "Ya sabes preparar texto, cajas, colores y un clic. En el último reto unirás esas piezas en una tarjeta sencilla, como una pequeña página sobre ti.",
        "task": "1. En la pestaña `index.html`, cambia el título por `Mi tarjeta` y deja un mensaje debajo.\n2. En `styles.css`, centra la tarjeta con `display: grid` y `place-items: center`.\n3. Dale espacio interior a `.tarjeta` con `padding: 24px`.\n4. En `script.js`, haz que el botón cambie el mensaje a `¡Bienvenido!`.\n5. Pulsa «Ver mi página» y revisa las comprobaciones antes de entregar.",
        "hints": [
            "El contenedor que se centra es `.app`; la tarjeta está dentro.",
            "Para responder al botón puedes reutilizar el patrón de `addEventListener('click', ...)`.",
            "Mantén cada cosa en su pestaña: `index.html` para el contenido, `styles.css` para el aspecto y `script.js` para las acciones.",
        ],
        "objectives": [
            "Combinar HTML, CSS y JavaScript",
            "Crear una tarjeta clara y centrada",
            "Responder a una acción sin mezclar archivos",
        ],
        "ra": ["RA1"],
        "ce": ["RA1.b", "RA1.f", "RA1.g", "RA1.h"],
        "html": "<!doctype html>\n<html lang=\"es\">\n  <head><meta charset=\"utf-8\"><title>Mi tarjeta</title></head>\n  <body>\n    <main class=\"app\">\n      <article class=\"tarjeta\">\n        <h1>Mi tarjeta</h1>\n        <p id=\"mensaje\">Pulsa el botón para saludar.</p>\n        <button id=\"mostrar\" type=\"button\">Saludar</button>\n      </article>\n    </main>\n  </body>\n</html>\n",
        "starter": _files(
            "<!doctype html>\n<html lang=\"es\">\n  <head><meta charset=\"utf-8\"><title>Mi tarjeta</title></head>\n  <body>\n    <main class=\"app\">\n      <article class=\"tarjeta\">\n        <h1>Escribe tu título</h1>\n        <p id=\"mensaje\">Pulsa el botón para saludar.</p>\n        <button id=\"mostrar\" type=\"button\">Saludar</button>\n      </article>\n    </main>\n  </body>\n</html>\n",
            ".app {\n  /* Centra la tarjeta. */\n}\n.tarjeta {\n  /* Deja espacio alrededor del texto. */\n}\n",
            "const boton = document.querySelector('#mostrar');\n// Haz que el botón cambie #mensaje.\n",
        ),
        "css": ".app { min-height: 100vh; display: grid; place-items: center; }\n.tarjeta { padding: 24px; }\n",
        "javascript": "const boton = document.querySelector('#mostrar');\nboton.addEventListener('click', () => {\n  document.querySelector('#mensaje').textContent = '¡Bienvenido!';\n});\n",
        "tests": [
            _test("Contenedor principal", "html.selector_exists", {"selector": "main.app"}),
            _test("Tarjeta preparada", "html.selector_exists", {"selector": ".tarjeta"}),
            _test("Título de la tarjeta", "html.text_contains", {"selector": ".tarjeta h1", "expected": "Mi tarjeta"}),
            _test("Layout centrado", "css.declaration_equals", {"selector": ".app", "property": "place-items", "expected": "center"}),
            _test("Espacio de la tarjeta", "css.declaration_equals", {"selector": ".tarjeta", "property": "padding", "expected": "24px"}),
            _test("Evento de saludo", "js.event_listener_registered", {"event": "click", "target": "boton"}),
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

        course, course_created = Course.objects.get_or_create(
            slug=TRACK_SLUG,
            defaults={
                "title": "Primeros pasos en la web · SMR",
                "description": "Un camino guiado para empezar desde cero con páginas web. Avanza poco a poco desde el texto hasta una tarjeta interactiva; cobertura parcial del módulo 0228 Aplicaciones web.",
                "created_by": owner,
                "active": True,
            },
        )
        if not course_created:
            course.title = "Primeros pasos en la web · SMR"
            course.description = "Un camino guiado para empezar desde cero con páginas web. Avanza poco a poco desde el texto hasta una tarjeta interactiva; cobertura parcial del módulo 0228 Aplicaciones web."
            course.save(update_fields=["title", "description", "updated_at"])

        module, module_created = Module.objects.get_or_create(
            course=course,
            position=1,
            defaults={
                "title": "De cero a tu primera página",
                "description": "Retos muy cortos y guiados: primero texto y etiquetas, después enlaces, imágenes, listas, estilos, formularios y JavaScript elemental.",
                "weight": 100,
            },
        )
        if not module_created:
            module.title = "De cero a tu primera página"
            module.description = "Retos muy cortos y guiados: primero texto y etiquetas, después enlaces, imágenes, listas, estilos, formularios y JavaScript elemental."
            module.save(update_fields=["title", "description"])

        created_versions = 0
        existing_versions = 0
        migrated_links = 0
        archived_assignments = 0
        newer_versions_skipped = 0
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
            # A centre may have published its own later revision.  Bootstrap
            # must never move that activity back to the built-in revision.
            if activity.versions.filter(version_number__gt=WEB_CATALOG_VERSION).exists():
                newer_versions_skipped += 1
                continue
            version, version_created = ActivityVersion.objects.get_or_create(
                activity=activity,
                version_number=WEB_CATALOG_VERSION,
                defaults={
                    "language": ActivityVersion.Language.WEB,
                    "difficulty": item["difficulty"],
                    "xp_reward": item["xp"],
                    "hints": item["hints"],
                    "instructions": f"## Antes de empezar\nEl editor ya está preparado: no necesitas crear carpetas ni descargar archivos. Escribe solo en la pestaña que indican los pasos.\n\n## La idea\n{item['theory']}\n\n## Pasos\n{item['task']}\n\n> Las comprobaciones leen lo que has escrito; la plataforma no ejecuta tu código en el servidor.",
                    "objectives": item["objectives"],
                    "learning_outcomes": item["ra"],
                    "assessment_criteria": item["ce"],
                    "professional_module_code": "0228",
                    "curriculum_scope": "Navarra · cobertura parcial",
                    "curriculum_edition": "navarra-2025",
                    "curriculum_unit": "",
                    "curriculum_source": CURRICULUM_SOURCE,
                    "starter_files": item["starter"],
                    "reference_solution": {key: item[key] for key in item["starter"]},
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
            if activity.current_version_id != version.id:
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
            assignment, assignment_created, _upgrade = get_or_create_catalog_revision_assignment(
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
            # The revision helper preserves a teacher's explicit title.  A
            # legacy assignment with no override still needs the friendly v2
            # title without changing the shared Activity (and therefore v1's
            # historical display).
            if assignment_created and not assignment.title_override:
                assignment.title_override = item["title"]
                assignment.save(update_fields=["title_override"])
            migrated_links += _upgrade["migrated_links"]
            archived_assignments += _upgrade["archived_assignments"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Itinerario Web v{WEB_CATALOG_VERSION} listo: {len(CHALLENGES)} retos, grupo {cohort.name}, "
                f"{created_versions} versiones nuevas y {existing_versions} ya existentes. "
                f"Actualizados {migrated_links} vínculos y archivadas {archived_assignments} asignaciones anteriores. "
                f"Respetadas {newer_versions_skipped} revisiones posteriores del centro."
            )
        )
        self.stdout.write("No se han creado alumnos ni contraseñas; el catálogo es contenido formativo local.")
