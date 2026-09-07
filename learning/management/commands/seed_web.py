"""Seed the guided HTML/CSS catalogue for first-year SMR."""

from __future__ import annotations

from datetime import date

from django.core.management import call_command
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

from ._catalog import ensure_cohort_track, get_or_create_catalog_revision_assignment

TRACK_SLUG = "fundamentos-web-smr"
CURRICULUM_SOURCE = "https://www.lexnavarra.navarra.es/detalle.asp?r=9129"
WEB_CATALOG_VERSION = 5
IMAGE_SRC = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 160 100'%3E"
    "%3Crect width='160' height='100' fill='%23e6f0ff'/%3E"
    "%3Crect x='45' y='20' width='70' height='45' rx='4' fill='%233b82f6'/%3E"
    "%3Crect x='60' y='72' width='40' height='6' fill='%231e3a5f'/%3E%3C/svg%3E"
)


# All published built-in titles must be recognised so a catalogue update does
# not mistake them for a teacher's own title override.
V1_TITLES = {
    "01-estructura-semantica": "01 · Estructura semántica",
    "enlaces-y-atributos": "02 · Enlaces y atributos",
    "listas-y-tablas": "03 · Listas y tablas de datos",
    "formularios-accesibles": "04 · Formularios accesibles",
    "multimedia-responsiva": "05 · Multimedia y alternativas",
    "html-limpio-y-valido": "06 · HTML limpio y mantenible",
    "css-selectores-y-color": "07 · Selectores y color",
    "css-modelo-de-caja": "08 · Modelo de caja y layout",
    "css-responsive": "09 · Diseño responsive",
    "javascript-funciones-y-datos": "10 · Variables y funciones JavaScript",
    "javascript-eventos-dom": "11 · Eventos del DOM",
    "panel-integrado-web": "12 · Panel web integrado",
}
V2_TITLES = {
    "01-estructura-semantica": "01 · Mi primera página",
    "enlaces-y-atributos": "02 · Títulos y párrafos",
    "listas-y-tablas": "03 · Mi primer enlace",
    "formularios-accesibles": "04 · Una imagen en la página",
    "multimedia-responsiva": "05 · Una lista de cosas",
    "html-limpio-y-valido": "06 · Colores con CSS",
    "css-selectores-y-color": "07 · Espacios y bordes",
    "css-modelo-de-caja": "08 · Colocar elementos juntos",
    "css-responsive": "09 · Un formulario sencillo",
    "javascript-funciones-y-datos": "10 · Guardar un texto en JavaScript",
    "javascript-eventos-dom": "11 · Reaccionar a un clic",
    "panel-integrado-web": "12 · Mi tarjeta de presentación",
}
V3_TITLES = {
    "01-estructura-semantica": "01 · Qué es una página web",
    "enlaces-y-atributos": "02 · Escribir una etiqueta",
    "listas-y-tablas": "03 · Títulos y subtítulos",
    "formularios-accesibles": "04 · El documento y la pestaña",
    "multimedia-responsiva": "05 · Un enlace y su destino",
    "html-limpio-y-valido": "06 · Una imagen y su descripción",
    "css-selectores-y-color": "07 · Una lista con puntos",
    "css-modelo-de-caja": "08 · Una lista de pasos",
    "css-responsive": "09 · Una palabra importante",
    "javascript-funciones-y-datos": "10 · Un apartado de la página",
    "javascript-eventos-dom": "11 · Un formulario con etiqueta",
    "panel-integrado-web": "12 · Repaso: una ficha ordenada",
}
V4_TITLES = {
    "01-estructura-semantica": "01 · Una página y un párrafo",
    "enlaces-y-atributos": "02 · Escribir otra etiqueta",
    "listas-y-tablas": "03 · Título, subtítulo y texto",
    "formularios-accesibles": "04 · Qué es CSS y aplicar color",
    "multimedia-responsiva": "05 · Elegir otro elemento con un selector",
    "html-limpio-y-valido": "06 · Una clase para un grupo",
    "css-selectores-y-color": "07 · La estructura de un documento",
    "css-modelo-de-caja": "08 · Enlaces y atributos",
    "css-responsive": "09 · Una lista sin orden",
    "javascript-funciones-y-datos": "10 · Un apartado con sentido",
    "javascript-eventos-dom": "11 · Una imagen y su alternativa",
    "panel-integrado-web": "12 · Margen: separar por fuera",
    "13-relleno-interior": "13 · Relleno: espacio por dentro",
    "14-borde-visible": "14 · Dibujar un borde",
    "15-display-en-linea": "15 · Display: cómo ocupa sitio",
    "16-flex-primera-fila": "16 · Flex: una fila de cajas",
    "17-formulario-y-campo": "17 · Un formulario y un campo",
    "18-etiqueta-del-campo": "18 · Etiquetar un campo",
    "19-tarjeta-html-css": "19 · Una tarjeta con HTML y CSS",
    "20-repaso-html-css": "20 · Repaso: una ficha enlazada",
}
PREVIOUS_CATALOGUE_TITLES = (V1_TITLES, V2_TITLES, V3_TITLES, V4_TITLES)


def _document(title, body):
    return (
        "<!doctype html>\n<html>\n  <head>\n"
        f"    <title>{title}</title>\n"
        "  </head>\n  <body>\n"
        f"{body}"
        "  </body>\n</html>\n"
    )


def _test(name, test_type, definition, points=1):
    return (name, test_type, definition, points, TestCase.Visibility.PUBLIC)


def _challenge(
    slug,
    title,
    theory,
    example,
    explanation,
    task,
    starter,
    html,
    css,
    tests,
    objectives,
    *,
    example_language="html",
    xp=100,
):
    return {
        "slug": slug,
        "title": title,
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": xp,
        "theory": theory,
        "example": example,
        "example_language": example_language,
        "example_explanation": explanation,
        "task": task,
        "hints": [
            "Mira primero la forma del código del ejemplo.",
            "Cambia únicamente la parte que pide el ejercicio.",
        ],
        "objectives": objectives,
        "ra": [],
        "ce": [],
        "starter": starter,
        "html": html,
        "css": css,
        "javascript": "",
        "tests": tests,
    }


# HTML begins with a complete, prepared document. CSS is absent until step 8;
# semantics comes after the HTML/CSS basics; box, display and forms are last.
CHALLENGES = [
    _challenge(
        "01-estructura-semantica",
        "01 · Un documento y un párrafo",
        "Un documento HTML es un archivo de texto que describe el contenido de una página web. Un navegador, como Firefox, lo lee y muestra la página. En el Editor ese archivo se llama `index.html`.\n\nHTML significa HyperText Markup Language: es el lenguaje que usamos para marcar qué es cada parte de un documento. Una `etiqueta` se escribe entre los signos `<` y `>`.\n\n`<!doctype html>` avisa de que es HTML. `<html>` rodea todo el documento. `<head>` guarda información; `<title>` nombra la pestaña. `<body>` guarda lo visible. `<p>` abre un párrafo y `</p>` lo cierra.\n\nEl Editor ya prepara esas partes: hoy solo cambias las palabras del párrafo.",
        "<!doctype html>\n<html>\n  <head>\n    <title>Mi cuaderno</title>\n  </head>\n  <body>\n    <p>Hoy empiezo.</p>\n  </body>\n</html>",
        "El texto de `<p>` se ve dentro de `<body>`. `<title>` queda en `<head>` y da nombre a la pestaña.",
        "1. Cambia `Escribe aquí` por `Hola, web.`.\n2. Conserva las demás líneas del documento.\n3. Mira el Resultado antes de Comprobaciones.",
        {"html": _document("Mi primera página", "    <p>Escribe aquí</p>\n")},
        _document("Mi primera página", "    <p>Hola, web.</p>\n"),
        "",
        [
            _test("Documento HTML", "html.selector_exists", {"selector": "html"}),
            _test("Información de la pestaña", "html.selector_exists", {"selector": "head title"}),
            _test("Contenido visible", "html.selector_exists", {"selector": "body p"}),
            _test("Tu primer párrafo", "html.text_contains", {"selector": "p", "expected": "Hola, web."}, 3),
        ],
        ["Reconocer las partes preparadas de un documento", "Cambiar el texto de un párrafo"],
    ),
    _challenge(
        "enlaces-y-atributos",
        "02 · Otro párrafo",
        "Un párrafo completo tiene apertura, texto y cierre: <p>Texto</p>. Para escribir otra idea usamos otro par de etiquetas p. Un salto de línea en el Editor no crea un párrafo por sí solo.",
        "<p>Me llamo Ana.</p>\n<p>Me gusta dibujar.</p>",
        "Cada par p abre y cierra un párrafo, así que el navegador separa las dos frases.",
        "1. Debajo del párrafo preparado escribe <p>Estoy aprendiendo HTML.</p>.\n2. Conserva el primer párrafo.\n3. Comprueba que se ven dos frases separadas.",
        {"html": _document("Dos párrafos", "    <p>Hola, web.</p>\n")},
        _document("Dos párrafos", "    <p>Hola, web.</p>\n    <p>Estoy aprendiendo HTML.</p>\n"),
        "",
        [
            _test("Dos párrafos", "html.selector_count", {"selector": "body p", "expected": 2}),
            _test("Segundo párrafo", "html.text_contains", {"selector": "p:nth-of-type(2)", "expected": "Estoy aprendiendo HTML."}, 3),
        ],
        ["Escribir una etiqueta completa", "Separar dos ideas en párrafos"],
        xp=105,
    ),
    _challenge(
        "listas-y-tablas",
        "03 · El título principal",
        "h1 marca el título principal de una página. La h viene de heading, que significa título en inglés; el 1 indica el nivel principal. Se abre con <h1> y se cierra con </h1>. El párrafo conocido queda debajo.",
        "<h1>Mi barrio</h1>\n<p>Tiene un parque.</p>",
        "h1 marca el título principal; p conserva el texto que explica ese título.",
        "1. Cambia las palabras del h1 por Sobre mí.\n2. Conserva el párrafo preparado.\n3. Revisa que el título queda antes del texto.",
        {"html": _document("Sobre mí", "    <h1>Escribe el título</h1>\n    <p>Me gusta leer.</p>\n")},
        _document("Sobre mí", "    <h1>Sobre mí</h1>\n    <p>Me gusta leer.</p>\n"),
        "",
        [
            _test("Título principal", "html.text_contains", {"selector": "h1", "expected": "Sobre mí"}, 3),
            _test("Título antes del texto", "html.element_order", {"first": "h1", "second": "p"}),
        ],
        ["Reconocer un título principal", "Escribir texto dentro de h1"],
        xp=110,
    ),
    _challenge(
        "formularios-accesibles",
        "04 · Un subtítulo",
        "h2 marca un título de segundo nivel. Abre una parte dentro del tema que ya presenta h1. Usa <h2> y </h2>; no cambia el título de la pestaña, que sigue en title.",
        "<h1>Mi barrio</h1>\n<h2>El parque</h2>\n<p>Tiene muchos árboles.</p>",
        "h2 presenta una parte del tema de h1 y queda antes de su texto.",
        "1. Entre h1 y el párrafo añade <h2>Mis aficiones</h2>.\n2. No cambies los otros textos.\n3. Comprueba el orden.",
        {"html": _document("Sobre mí", "    <h1>Sobre mí</h1>\n    <p>Me gusta leer.</p>\n")},
        _document("Sobre mí", "    <h1>Sobre mí</h1>\n    <h2>Mis aficiones</h2>\n    <p>Me gusta leer.</p>\n"),
        "",
        [
            _test("Subtítulo", "html.text_contains", {"selector": "h2", "expected": "Mis aficiones"}, 3),
            _test("Después de h1", "html.element_order", {"first": "h1", "second": "h2"}),
            _test("Antes del texto", "html.element_order", {"first": "h2", "second": "p"}),
        ],
        ["Distinguir h1 y h2", "Organizar un texto con un subtítulo"],
        xp=115,
    ),
    _challenge(
        "multimedia-responsiva",
        "05 · Un enlace y su destino",
        "Un enlace lleva a otra dirección. a abre el enlace y /a lo cierra. Dentro de la apertura, href guarda el destino: href=\"https://example.org\". href, el signo igual y las comillas forman un atributo, una información extra de la etiqueta.",
        "<a href=\"https://example.org\">Visitar un ejemplo</a>",
        "href guarda el destino; el texto entre a y /a es la parte que una persona lee y pulsa.",
        "1. Completa href con https://example.com.\n2. Escribe como texto visible Página de ejemplo.\n3. No hace falta abrir el enlace.",
        {"html": _document("Enlaces", "    <a href=\"\">Escribe el texto</a>\n")},
        _document("Enlaces", "    <a href=\"https://example.com\">Página de ejemplo</a>\n"),
        "",
        [
            _test("Destino del enlace", "html.attribute_equals", {"selector": "a", "attribute": "href", "expected": "https://example.com"}, 2),
            _test("Texto del enlace", "html.text_contains", {"selector": "a", "expected": "Página de ejemplo"}, 2),
        ],
        ["Escribir un atributo", "Crear un enlace con texto claro"],
        xp=120,
    ),
    _challenge(
        "html-limpio-y-valido",
        "06 · Una lista de cosas",
        "ul abre una lista cuando el orden de las cosas no importa. Cada cosa se escribe dentro de li y /li. La barra de /ul cierra toda la lista. Los puntos los añade el navegador; no se escriben a mano.",
        "<ul>\n  <li>Pan</li>\n  <li>Fruta</li>\n</ul>",
        "ul reúne la lista y cada li aporta una cosa; los puntos los dibuja el navegador.",
        "1. Dentro de ul, debajo de Teclado, añade <li>Ratón</li>.\n2. Déjalo antes de </ul>.\n3. Comprueba que aparecen dos puntos.",
        {"html": _document("Material", "    <ul>\n      <li>Teclado</li>\n    </ul>\n")},
        _document("Material", "    <ul>\n      <li>Teclado</li>\n      <li>Ratón</li>\n    </ul>\n"),
        "",
        [
            _test("Dos elementos", "html.selector_count", {"selector": "ul > li", "expected": 2}),
            _test("Elemento añadido", "html.text_contains", {"selector": "ul > li:nth-of-type(2)", "expected": "Ratón"}, 2),
        ],
        ["Crear una lista", "Colocar li dentro de ul"],
        xp=125,
    ),
    _challenge(
        "css-selectores-y-color",
        "07 · Una imagen y su descripción",
        "img muestra una imagen y no lleva etiqueta de cierre. src indica dónde está la imagen. alt contiene una descripción corta para quien no pueda verla. Los dos son atributos entre comillas y el Editor ya prepara src.",
        f"<img src=\"{IMAGE_SRC}\" alt=\"Un ordenador sobre una mesa\">",
        "`<img>` no se cierra. `src` conserva la dirección de la imagen y `alt` explica qué muestra.",
        "1. Cambia solo `alt` por `Un monitor encendido`.\n2. Conserva `src`.\n3. No añadas un cierre para `img`.",
        {"html": _document("Una imagen", f"    <img src=\"{IMAGE_SRC}\" alt=\"Completa la descripción\">\n")},
        _document("Una imagen", f"    <img src=\"{IMAGE_SRC}\" alt=\"Un monitor encendido\">\n"),
        "",
        [
            _test("Descripción alternativa", "html.attribute_equals", {"selector": "img", "attribute": "alt", "expected": "Un monitor encendido"}, 3),
            _test("Imagen conservada", "html.attribute_equals", {"selector": "img", "attribute": "src", "expected": IMAGE_SRC}),
        ],
        ["Usar img", "Escribir un texto alternativo"],
        xp=130,
    ),
    _challenge(
        "css-modelo-de-caja",
        "08 · Dar color con CSS",
        "HTML escribe el contenido; CSS decide su aspecto. Desde este paso el Editor muestra también CSS. Una regla tiene selector, llaves y declaración: p { color: blue; }. p elige los párrafos, color es lo que cambia, blue es el valor y el punto y coma termina la declaración.",
        "p {\n  color: green;\n}",
        "`p` es el selector, `color` es lo que cambia y `green` es el valor. Las llaves guardan la regla.",
        "1. En CSS completa color con navy.\n2. No borres p, llaves ni punto y coma.\n3. Mira el Resultado.",
        {"html": _document("Estilos", "    <p>Un mensaje para el aula.</p>\n"), "css": "p {\n  color: ;\n}\n"},
        _document("Estilos", "    <p>Un mensaje para el aula.</p>\n"),
        "p {\n  color: navy;\n}\n",
        [
            _test("Regla para p", "css.selector_exists", {"selector": "p"}),
            _test("Color pedido", "css.declaration_equals", {"selector": "p", "property": "color", "expected": "navy"}, 3),
        ],
        ["Distinguir HTML y CSS", "Completar una regla CSS"],
        example_language="css",
        xp=135,
    ),
    _challenge(
        "css-responsive",
        "09 · Elegir otro elemento",
        "Un selector no tiene que ser p. Si escribimos h1, la regla se aplica al título principal. color solo cambia el aspecto: no convierte h1 en otra etiqueta ni cambia sus palabras.",
        "h1 {\n  color: tomato;\n}",
        "La regla que empieza por h1 se aplica al título, sin cambiar el párrafo.",
        "1. En CSS completa h1 con color: teal;.\n2. Conserva el párrafo.\n3. Comprueba que solo cambia el título.",
        {"html": _document("Noticias", "    <h1>Noticias del aula</h1>\n    <p>Hoy hay biblioteca.</p>\n"), "css": "h1 {\n  color: ;\n}\n"},
        _document("Noticias", "    <h1>Noticias del aula</h1>\n    <p>Hoy hay biblioteca.</p>\n"),
        "h1 {\n  color: teal;\n}\n",
        [
            _test("Selector h1", "css.selector_exists", {"selector": "h1"}),
            _test("Color del título", "css.declaration_equals", {"selector": "h1", "property": "color", "expected": "teal"}, 3),
        ],
        ["Usar un selector de elemento", "Aplicar color a un título"],
        example_language="css",
        xp=140,
    ),
    _challenge(
        "javascript-funciones-y-datos",
        "10 · Una clase para destacar",
        "Ya conoces los atributos por href. class pone un nombre reutilizable a un elemento. En CSS, un punto antes del nombre selecciona esa clase: .aviso { color: crimson; }. Así HTML marca qué párrafo es aviso y CSS decide su color.",
        ".aviso {\n  color: crimson;\n}",
        "El selector CSS `.aviso` encuentra el elemento HTML que lleva `class=\"aviso\"`.",
        "1. Añade class=\"aviso\" al párrafo.\n2. Completa el color de .aviso con crimson.\n3. Conserva el punto de CSS.",
        {"html": _document("Aviso", "    <p>Entrega el viernes.</p>\n"), "css": ".aviso {\n  color: ;\n}\n"},
        _document("Aviso", "    <p class=\"aviso\">Entrega el viernes.</p>\n"),
        ".aviso {\n  color: crimson;\n}\n",
        [
            _test("Clase en HTML", "html.selector_exists", {"selector": "p.aviso"}, 2),
            _test("Selector de clase", "css.selector_exists", {"selector": ".aviso"}),
            _test("Color del aviso", "css.declaration_equals", {"selector": ".aviso", "property": "color", "expected": "crimson"}, 2),
        ],
        ["Añadir una clase", "Relacionar HTML y CSS"],
        example_language="css",
        xp=145,
    ),
    _challenge(
        "javascript-eventos-dom",
        "11 · El contenido principal",
        "Ahora que puedes escribir y dar estilo a contenido básico, conocerás etiquetas que explican su papel. main rodea el contenido principal. No cambia texto ni color: aclara qué parte es la más importante de la página.",
        "<main>\n  <h1>Horario</h1>\n  <p>Consulta el tablón.</p>\n</main>",
        "main rodea el contenido principal y no cambia cómo se escriben h1 o p.",
        "1. Rodea h1 y p con <main> y </main>.\n2. No cambies sus textos.\n3. Conserva CSS.",
        {"html": _document("Horario", "    <h1>Horario</h1>\n    <p>Consulta el tablón.</p>\n"), "css": ""},
        _document("Horario", "    <main>\n      <h1>Horario</h1>\n      <p>Consulta el tablón.</p>\n    </main>\n"),
        "",
        [
            _test("Contenido principal", "html.selector_exists", {"selector": "body > main"}, 3),
            _test("Título dentro de main", "html.selector_exists", {"selector": "main > h1"}),
        ],
        ["Usar main", "Reconocer el contenido principal"],
        xp=150,
    ),
    _challenge(
        "panel-integrado-web",
        "12 · Un apartado relacionado",
        "section agrupa contenido que trata el mismo asunto. Dentro puede haber h2 y p. Ya conoces esas etiquetas: section solo deja claro que forman un apartado dentro de main.",
        "<main>\n  <section><h2>Horario</h2><p>Consulta el tablón.</p></section>\n</main>",
        "section mantiene juntos el título y el párrafo que hablan del mismo asunto.",
        "1. Dentro de main, rodea h2 y p con <section> y </section>.\n2. Conserva h2 y p.\n3. No cambies CSS.",
        {"html": _document("Material", "    <main>\n      <h2>Material</h2>\n      <p>Trae una libreta.</p>\n    </main>\n"), "css": ""},
        _document("Material", "    <main>\n      <section>\n        <h2>Material</h2>\n        <p>Trae una libreta.</p>\n      </section>\n    </main>\n"),
        "",
        [
            _test("Apartado", "html.selector_exists", {"selector": "main > section"}, 3),
            _test("Título del apartado", "html.selector_exists", {"selector": "section > h2"}),
        ],
        ["Agrupar contenido con section", "Mantener un apartado dentro de main"],
        xp=155,
    ),
    _challenge(
        "13-relleno-interior",
        "13 · Un artículo independiente",
        "article reúne un contenido que se puede entender por sí solo, como una noticia corta. No necesitas estilos nuevos: pon dentro un título y su texto, como en los pasos anteriores.",
        "<article><h2>Biblioteca abierta</h2><p>Hoy hasta las cinco.</p></article>",
        "article reúne una pieza completa: el título y el texto de una noticia.",
        "1. Rodea h2 y p con <article> y </article>.\n2. Conserva sus textos.\n3. Comprueba que quedan dentro del artículo.",
        {"html": _document("Noticias", "    <h2>Biblioteca abierta</h2>\n    <p>Hoy hasta las cinco.</p>\n"), "css": ""},
        _document("Noticias", "    <article>\n      <h2>Biblioteca abierta</h2>\n      <p>Hoy hasta las cinco.</p>\n    </article>\n"),
        "",
        [
            _test("Artículo", "html.selector_exists", {"selector": "body > article"}, 3),
            _test("Título del artículo", "html.selector_exists", {"selector": "article > h2"}),
        ],
        ["Usar article", "Agrupar una noticia corta"],
        xp=160,
    ),
    _challenge(
        "14-borde-visible",
        "14 · Margen: separar por fuera",
        "Ya sabes usar una clase y una regla CSS. margin deja espacio fuera de la caja de un elemento, para separarlo de lo que tiene alrededor. px significa píxeles: 12px pide doce píxeles.",
        ".nota {\n  margin: 12px;\n}",
        "margin deja doce píxeles fuera de .nota y la separa de lo que tenga alrededor.",
        "1. En CSS completa margin con 12px.\n2. Conserva .nota.\n3. Observa el espacio alrededor del párrafo.",
        {"html": _document("Margen", "    <p class=\"nota\">Aviso del día.</p>\n"), "css": ".nota {\n  margin: ;\n}\n"},
        _document("Margen", "    <p class=\"nota\">Aviso del día.</p>\n"),
        ".nota {\n  margin: 12px;\n}\n",
        [
            _test("Regla de nota", "css.selector_exists", {"selector": ".nota"}),
            _test("Margen exterior", "css.declaration_equals", {"selector": ".nota", "property": "margin", "expected": "12px"}, 3),
        ],
        ["Distinguir el espacio exterior", "Usar margin"],
        example_language="css",
        xp=165,
    ),
    _challenge(
        "15-display-en-linea",
        "15 · Relleno: espacio por dentro",
        "Antes de dibujar un borde, puedes dejar espacio dentro de la caja. padding separa contenido y borde. A diferencia de margin, el relleno queda dentro del elemento. Seguimos usando píxeles: 12px.",
        ".mensaje {\n  padding: 12px;\n}",
        "padding deja espacio dentro de .mensaje, entre el texto y el borde.",
        "1. En CSS completa padding con 12px.\n2. No cambies HTML.\n3. Mira cómo el texto se aleja del borde imaginario.",
        {"html": _document("Relleno", "    <p class=\"mensaje\">El aula abre a las ocho.</p>\n"), "css": ".mensaje {\n  padding: ;\n}\n"},
        _document("Relleno", "    <p class=\"mensaje\">El aula abre a las ocho.</p>\n"),
        ".mensaje {\n  padding: 12px;\n}\n",
        [
            _test("Regla de mensaje", "css.selector_exists", {"selector": ".mensaje"}),
            _test("Relleno interior", "css.declaration_equals", {"selector": ".mensaje", "property": "padding", "expected": "12px"}, 3),
        ],
        ["Distinguir margin y padding", "Usar padding"],
        example_language="css",
        xp=170,
    ),
    _challenge(
        "16-flex-primera-fila",
        "16 · Dibujar un borde",
        "Ahora que conoces padding, el borde se verá separado del texto. border dibuja el límite de una caja. En border: 2px solid steelblue;, 2px es grosor, solid es línea continua y steelblue es color. Las tres partes van juntas.",
        ".tarjeta {\n  border: 2px solid steelblue;\n}",
        "border reúne grosor, tipo de línea y color: 2px, solid y steelblue.",
        "1. En CSS completa border con 2px solid steelblue.\n2. Conserva .tarjeta.\n3. Comprueba el borde.",
        {"html": _document("Borde", "    <p class=\"tarjeta\">Una nota con borde.</p>\n"), "css": ".tarjeta {\n  border: ;\n}\n"},
        _document("Borde", "    <p class=\"tarjeta\">Una nota con borde.</p>\n"),
        ".tarjeta {\n  border: 2px solid steelblue;\n}\n",
        [
            _test("Regla de tarjeta", "css.selector_exists", {"selector": ".tarjeta"}),
            _test("Borde pedido", "css.declaration_equals", {"selector": ".tarjeta", "property": "border", "expected": "2px solid steelblue"}, 3),
        ],
        ["Reconocer las partes de border", "Dibujar un borde"],
        example_language="css",
        xp=175,
    ),
    _challenge(
        "17-formulario-y-campo",
        "17 · Display: ocupar sitio",
        "Ya sabes seleccionar una clase y darle padding y border. display indica cómo ocupa sitio esa caja. span sigue dentro de una frase. Con display: inline-block puede recibir padding y border sin empezar una línea nueva.",
        ".etiqueta {\n  display: inline-block;\n}",
        "inline-block deja que span siga junto a la frase y permite darle espacio y borde.",
        "1. En CSS completa display con inline-block.\n2. Conserva la clase etiqueta en span.\n3. Mira que el texto sigue junto a la frase.",
        {"html": _document("Estado", "    <p>Estado: <span class=\"etiqueta\">listo</span></p>\n"), "css": ".etiqueta {\n  display: ;\n}\n"},
        _document("Estado", "    <p>Estado: <span class=\"etiqueta\">listo</span></p>\n"),
        ".etiqueta {\n  display: inline-block;\n}\n",
        [
            _test("Regla de etiqueta", "css.selector_exists", {"selector": ".etiqueta"}),
            _test("Display en línea", "css.declaration_equals", {"selector": ".etiqueta", "property": "display", "expected": "inline-block"}, 3),
        ],
        ["Reconocer display", "Usar inline-block"],
        example_language="css",
        xp=180,
    ),
    _challenge(
        "18-etiqueta-del-campo",
        "18 · Flex: una fila",
        "Este paso usa lo que acabas de aprender sobre display. Un `contenedor` es el elemento que rodea a otros; sus `hijos` son los elementos que están dentro directamente. Cuando el contenedor tiene `display: flex`, sus hijos se colocan en una fila por defecto. `gap` deja espacio entre ellos. Flex se escribe en `.fila`, no en cada enlace.",
        ".fila {\n  display: flex;\n  gap: 8px;\n}",
        "`display: flex` va en `.fila`; `gap` deja ocho píxeles entre sus dos enlaces.",
        "1. En CSS completa `display: flex;`.\n2. Completa `gap: 8px;`.\n3. No cambies los enlaces HTML.",
        {"html": _document("Enlaces", "    <section class=\"fila\">\n      <a href=\"https://example.com\">Inicio</a>\n      <a href=\"https://example.org\">Ayuda</a>\n    </section>\n"), "css": ".fila {\n  display: ;\n  gap: ;\n}\n"},
        _document("Enlaces", "    <section class=\"fila\">\n      <a href=\"https://example.com\">Inicio</a>\n      <a href=\"https://example.org\">Ayuda</a>\n    </section>\n"),
        ".fila {\n  display: flex;\n  gap: 8px;\n}\n",
        [
            _test("Regla de fila", "css.selector_exists", {"selector": ".fila"}),
            _test("Activa flex", "css.declaration_equals", {"selector": ".fila", "property": "display", "expected": "flex"}, 2),
            _test("Separa elementos", "css.declaration_equals", {"selector": ".fila", "property": "gap", "expected": "8px"}),
        ],
        ["Crear un contenedor flex", "Separar hijos con gap"],
        example_language="css",
        xp=185,
    ),
    _challenge(
        "19-tarjeta-html-css",
        "19 · Un formulario y un campo",
        "Después de organizar y colocar contenido, puedes pedir un dato. form reúne controles de una petición. input crea un campo y no tiene cierre. type=\"text\" indica texto y name da un nombre al dato. Este reto solo muestra el formulario: no envía nada ni usa JavaScript.",
        "<form>\n  <input type=\"text\" name=\"ciudad\">\n</form>",
        "form reúne el campo. input crea un lugar para escribir y type indica texto.",
        "1. Dentro de form escribe un input.\n2. Dale type=\"text\" y name=\"nombre\".\n3. No añadas JavaScript.",
        {"html": _document("Formulario", "    <form>\n    </form>\n"), "css": ""},
        _document("Formulario", "    <form>\n      <input type=\"text\" name=\"nombre\">\n    </form>\n"),
        "",
        [
            _test("Formulario", "html.selector_exists", {"selector": "form"}),
            _test("Campo de texto", "html.attribute_equals", {"selector": "form input", "attribute": "type", "expected": "text"}, 2),
            _test("Nombre del dato", "html.attribute_equals", {"selector": "form input", "attribute": "name", "expected": "nombre"}, 2),
        ],
        ["Usar form", "Crear un input de texto"],
        xp=190,
    ),
    _challenge(
        "20-repaso-html-css",
        "20 · Etiquetar un campo",
        "Un campo necesita un texto que explique para qué sirve. label contiene esa explicación. for debe tener el mismo valor que id de input. Esa pareja une el texto y el campo. Reutiliza form, input, type y name del paso anterior.",
        "<label for=\"correo\">Correo</label>\n<input id=\"correo\" type=\"text\" name=\"correo\">",
        "`for` e `id` comparten `correo`, por eso la etiqueta Correo queda unida a su campo.",
        "1. Escribe Nombre dentro de label.\n2. Completa for=\"nombre\" e id=\"nombre\".\n3. Conserva type y name.",
        {"html": _document("Formulario", "    <form>\n      <label for=\"\">Escribe aquí</label>\n      <input id=\"\" type=\"text\" name=\"nombre\">\n    </form>\n"), "css": ""},
        _document("Formulario", "    <form>\n      <label for=\"nombre\">Nombre</label>\n      <input id=\"nombre\" type=\"text\" name=\"nombre\">\n    </form>\n"),
        "",
        [
            _test("Texto de etiqueta", "html.text_contains", {"selector": "label", "expected": "Nombre"}),
            _test("Etiqueta asociada", "html.attribute_equals", {"selector": "label", "attribute": "for", "expected": "nombre"}, 2),
            _test("Id del campo", "html.attribute_equals", {"selector": "input", "attribute": "id", "expected": "nombre"}, 2),
        ],
        ["Crear label", "Relacionar for e id"],
        xp=200,
    ),
    _challenge(
        "21-repaso-html-css",
        "21 · Repaso: una ficha de contacto",
        "Este último paso no presenta sintaxis nueva. Reúne un documento HTML, main, una clase CSS, padding, border, form, label e input que ya has usado.",
        ".ficha {\n  padding: 12px;\n  border: 1px solid teal;\n}",
        "HTML organiza el contenido y CSS da aspecto a la misma clase sin cambiar el formulario.",
        "1. Cambia el h1 por `Contacto del aula`.\n2. Completa `padding` con `12px`.\n3. Completa `border` con `1px solid teal`.\n4. No añadas sintaxis nueva.",
        {
            "html": _document("Contacto", "    <main class=\"ficha\">\n      <h1>Escribe el título</h1>\n      <form>\n        <label for=\"nombre\">Nombre</label>\n        <input id=\"nombre\" type=\"text\" name=\"nombre\">\n      </form>\n    </main>\n"),
            "css": ".ficha {\n  padding: ;\n  border: ;\n}\n",
        },
        _document("Contacto", "    <main class=\"ficha\">\n      <h1>Contacto del aula</h1>\n      <form>\n        <label for=\"nombre\">Nombre</label>\n        <input id=\"nombre\" type=\"text\" name=\"nombre\">\n      </form>\n    </main>\n"),
        ".ficha {\n  padding: 12px;\n  border: 1px solid teal;\n}\n",
        [
            _test("Título final", "html.text_contains", {"selector": "h1", "expected": "Contacto del aula"}, 2),
            _test("Relleno conocido", "css.declaration_equals", {"selector": ".ficha", "property": "padding", "expected": "12px"}, 2),
            _test("Borde conocido", "css.declaration_equals", {"selector": ".ficha", "property": "border", "expected": "1px solid teal"}, 2),
        ],
        ["Reutilizar HTML y CSS conocidos", "Completar una ficha sin sintaxis nueva"],
        example_language="css",
        xp=205,
    ),
]


class Command(BaseCommand):
    help = "Crea el itinerario HTML/CSS de 21 pasos para SMR y el catálogo JavaScript asociado."

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

        course, created = Course.objects.get_or_create(
            slug=TRACK_SLUG,
            defaults={
                "title": "HTML y CSS desde cero · SMR",
                "description": "Veintiún pasos guiados desde el documento HTML hasta una ficha de contacto con HTML y CSS; cobertura parcial del módulo 0228 Aplicaciones web.",
                "web_stage": Course.WebStage.HTML_CSS,
                "created_by": owner,
                "active": True,
            },
        )
        if not created:
            course.title = "HTML y CSS desde cero · SMR"
            course.description = "Veintiún pasos guiados desde el documento HTML hasta una ficha de contacto con HTML y CSS; cobertura parcial del módulo 0228 Aplicaciones web."
            course.web_stage = Course.WebStage.HTML_CSS
            course.save(update_fields=["title", "description", "web_stage", "updated_at"])

        module, module_created = Module.objects.get_or_create(
            course=course,
            position=1,
            defaults={
                "title": "Del documento HTML a los formularios",
                "description": "Retos cortos y guiados de HTML y CSS, sin JavaScript.",
                "weight": 100,
            },
        )
        if not module_created:
            module.title = "Del documento HTML a los formularios"
            module.description = "Retos cortos y guiados de HTML y CSS, sin JavaScript."
            module.save(update_fields=["title", "description"])

        created_versions = existing_versions = migrated_links = archived_assignments = newer_versions_skipped = 0
        for position, item in enumerate(CHALLENGES, start=1):
            activity, _ = Activity.objects.get_or_create(
                module=module,
                slug=item["slug"],
                defaults={
                    "title": item["title"],
                    "position": position,
                    "kind": Activity.Kind.CODE,
                    "status": Activity.Status.PUBLISHED,
                    "created_by": owner,
                },
            )
            # A centre's newer revision owns both its title and its position.
            if activity.versions.filter(version_number__gt=WEB_CATALOG_VERSION).exists():
                newer_versions_skipped += 1
                continue

            known_titles = {
                title
                for catalogue_titles in PREVIOUS_CATALOGUE_TITLES
                if (title := catalogue_titles.get(item["slug"]))
            }
            fields_to_update = []
            if activity.title in known_titles and activity.title != item["title"]:
                activity.title = item["title"]
                fields_to_update.append("title")
            if activity.position != position:
                activity.position = position
                fields_to_update.append("position")
            if fields_to_update:
                activity.save(update_fields=[*fields_to_update, "updated_at"])

            version, version_created = ActivityVersion.objects.get_or_create(
                activity=activity,
                version_number=WEB_CATALOG_VERSION,
                defaults={
                    "language": ActivityVersion.Language.WEB,
                    "difficulty": item["difficulty"],
                    "xp_reward": item["xp"],
                    "hints": item["hints"],
                    "instructions": (
                        "## Antes de empezar\n"
                        "El Editor ya está preparado. Escribe solo en las pestañas que el paso te ha presentado.\n\n"
                        f"## La idea\n{item['theory']}\n\n"
                        f"## Ejemplo explicado\n```{item['example_language']}\n{item['example']}\n```\n\n"
                        f"{item['example_explanation']}\n\n"
                        f"## Tu ejercicio\n{item['task']}\n\n"
                        "> Las comprobaciones leen tu HTML y CSS; la plataforma no ejecuta código en el servidor."
                    ),
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
            if not version.assignments.exists():
                for test_position, (name, test_type, definition, points, visibility) in enumerate(item["tests"]):
                    TestCase.objects.get_or_create(
                        activity_version=version,
                        name=name,
                        defaults={
                            "type": test_type,
                            "definition": definition,
                            "points": points,
                            "visibility": visibility,
                            "feedback": "Revisa la estructura indicada en el enunciado.",
                            "position": test_position,
                        },
                    )
            previous_catalog_titles = tuple(
                title
                for catalogue_titles in PREVIOUS_CATALOGUE_TITLES
                if (title := catalogue_titles.get(item["slug"]))
            )
            assignment, assignment_created, upgrade = get_or_create_catalog_revision_assignment(
                previous_catalog_titles=previous_catalog_titles,
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
            if assignment_created and not assignment.title_override:
                assignment.title_override = item["title"]
                assignment.save(update_fields=["title_override"])
            migrated_links += upgrade["migrated_links"]
            archived_assignments += upgrade["archived_assignments"]

        current_assignments = list(
            Assignment.objects.filter(
                status=Assignment.Status.PUBLISHED,
                activity_version__activity__module__course=course,
                activity_version__version_number=WEB_CATALOG_VERSION,
            ).distinct()
        )
        javascript_cohorts = (
            Cohort.objects.filter(
                active=True,
                track=Cohort.Track.WEB,
                assignment_links__assignment__status=Assignment.Status.PUBLISHED,
                assignment_links__assignment__activity_version__activity__module__course=course,
                assignment_links__assignment__activity_version__version_number=WEB_CATALOG_VERSION,
            )
            .select_related("academic_year")
            .distinct()
        )
        completed_group_links = 0
        for linked_cohort in javascript_cohorts:
            for current_assignment in current_assignments:
                _, linked = AssignmentCohort.objects.get_or_create(assignment=current_assignment, cohort=linked_cohort)
                completed_group_links += int(linked)

        self.stdout.write(
            self.style.SUCCESS(
                f"Itinerario HTML/CSS v{WEB_CATALOG_VERSION} listo: {len(CHALLENGES)} retos, "
                f"grupo {cohort.name}, {created_versions} versiones nuevas y {existing_versions} ya existentes. "
                f"Actualizados {migrated_links} vínculos, completados {completed_group_links} enlaces de "
                f"grupos activos y archivadas {archived_assignments} asignaciones anteriores. Respetadas "
                f"{newer_versions_skipped} revisiones posteriores del centro."
            )
        )
        for javascript_cohort in javascript_cohorts:
            call_command(
                "seed_javascript",
                owner=owner.username,
                cohort=javascript_cohort.name,
                academic_year=javascript_cohort.academic_year.name,
            )
