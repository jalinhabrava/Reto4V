"""Seed the introductory HTML and CSS catalogue for first-year SMR.

The catalogue is a practical, partial introduction to the code-related part
of the Navarra web applications module (0228). Evaluation is static and
declarative: neither a preview nor a submission is executed on the server.
"""

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
WEB_CATALOG_VERSION = 4
IMAGE_SRC = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 160 100'%3E"
    "%3Crect width='160' height='100' fill='%23e6f0ff'/%3E"
    "%3Crect x='45' y='20' width='70' height='45' rx='4' fill='%233b82f6'/%3E"
    "%3Crect x='60' y='72' width='40' height='6' fill='%231e3a5f'/%3E%3C/svg%3E"
)


# Titles published by built-in catalogues before this revision.  They let the
# revision helper keep an educator's title while replacing its own old title.
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

EXAMPLE_EXPLANATIONS = {
    "01-estructura-semantica": "El navegador muestra solo la frase; `<p>` le indica que es un párrafo y la barra marca dónde termina.",
    "enlaces-y-atributos": "Hay dos pares de etiquetas p, por eso el navegador presenta dos párrafos separados y en ese orden.",
    "listas-y-tablas": "h1 anuncia el tema de toda la página, h2 abre un apartado y p desarrolla ese apartado debajo.",
    "formularios-accesibles": "El selector p elige el párrafo. La declaración cambia su texto a verde sin tocar el HTML.",
    "multimedia-responsiva": "La regla empieza por h1, así que el color tomato se aplica al título principal y no al párrafo.",
    "html-limpio-y-valido": "class da al párrafo el nombre destacado; el punto de `.destacado` permite que CSS encuentre ese mismo elemento.",
    "css-selectores-y-color": "title queda dentro de head y nombra la pestaña; h1 queda dentro de body y es el texto visible de la página.",
    "css-modelo-de-caja": "href guarda la dirección y el texto entre las etiquetas a es el enlace que una persona puede leer y pulsar.",
    "css-responsive": "ul reúne la colección y cada li aporta un elemento, por lo que el navegador dibuja dos puntos sin que los escribamos.",
    "javascript-funciones-y-datos": "main contiene el contenido principal y section mantiene juntos el título Horario y su explicación.",
    "javascript-eventos-dom": "src localiza la imagen y alt explica con palabras qué muestra; ambos atributos están dentro de la única etiqueta img.",
    "panel-integrado-web": "margin deja dieciséis píxeles fuera de `.nota`, separando el párrafo de lo que tenga alrededor.",
    "13-relleno-interior": "padding reserva doce píxeles dentro de `.mensaje`, entre el texto y el borde que pudiera tener.",
    "14-borde-visible": "La declaración crea un borde de dos píxeles, continuo y azul alrededor de la caja con clase tarjeta.",
    "15-display-en-linea": "inline-block permite que la etiqueta siga en la frase y, al mismo tiempo, pueda recibir medidas de caja.",
    "16-flex-primera-fila": "display: flex coloca los hijos de `.fila` en una fila; gap deja ocho píxeles entre ellos.",
    "17-formulario-y-campo": "form reúne el control; el input crea un campo de texto y name identifica el dato que representa.",
    "18-etiqueta-del-campo": "for y id comparten `correo`, de modo que la etiqueta Correo queda asociada a ese campo concreto.",
    "19-tarjeta-html-css": "section agrupa el contenido del panel y `.panel` aplica a esa caja su relleno y su borde, sin mezclar ambos lenguajes.",
    "20-repaso-html-css": "HTML conserva un enlace real con su destino; CSS lo convierte visualmente en una ficha en línea mediante display, padding y border.",
}


def _challenge(
    slug, title, theory, example, task, starter, html, css, tests, objectives, *, example_language="html", xp=100
):
    """Keep every activity's content contract explicit and uniform."""

    return {
        "slug": slug,
        "title": title,
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": xp,
        "theory": theory,
        "example": example,
        "example_language": example_language,
        "example_explanation": EXAMPLE_EXPLANATIONS[slug],
        "task": task,
        "hints": ["Mira primero la forma de la etiqueta o regla en el ejemplo.", "Cambia únicamente la parte que pide el ejercicio."],
        "objectives": objectives,
        "ra": [],
        "ce": [],
        "starter": starter,
        "html": html,
        "css": css,
        # Kept for the web file contract. This HTML/CSS course never exposes
        # JavaScript in a starter and contains no js.* tests.
        "javascript": "",
        "tests": tests,
    }


# CSS starts only after step 4 explains what a CSS rule, selector and
# declaration are.  Each following step reuses only previously explained
# syntax and leaves a small, meaningful change for the learner.
CHALLENGES = [
    _challenge(
        "01-estructura-semantica", "01 · Una página y un párrafo",
        "Una página web es un documento que muestra un navegador. HTML indica qué es cada parte del contenido. `<p>` abre un párrafo y `</p>` lo cierra; las palabras entre ambas etiquetas son las que se ven.",
        "<p>Hoy empieza el curso.</p>",
        "1. Cambia `Escribe aquí` por `Hola, web.`.\n2. Conserva las dos etiquetas p.\n3. Mira el Resultado antes de comprobar.",
        {"html": "<p>Escribe aquí</p>\n"}, "<p>Hola, web.</p>\n", "",
        [("Tu primer párrafo", "html.text_contains", {"selector": "p", "expected": "Hola, web."}, 1, "public")],
        ["Reconocer una página HTML", "Cambiar el contenido de un párrafo"], xp=100,
    ),
    _challenge(
        "enlaces-y-atributos", "02 · Escribir otra etiqueta",
        "Un elemento completo tiene apertura, contenido y cierre: `<p>Texto</p>`. Para crear otro párrafo escribimos otro par de etiquetas. Un salto de línea en el Editor no crea por sí solo un párrafo.",
        "<p>Me llamo Ana.</p>\n<p>Me gusta dibujar.</p>",
        "1. Debajo del párrafo preparado, escribe `<p>Estoy aprendiendo HTML.</p>`.\n2. Conserva el primer párrafo.\n3. Comprueba que se ven dos textos separados.",
        {"html": "<p>Hola, web.</p>\n"}, "<p>Hola, web.</p>\n<p>Estoy aprendiendo HTML.</p>\n", "",
        [("Dos párrafos", "html.selector_count", {"selector": "p", "expected": 2}, 1, "public"), ("Segundo párrafo", "html.text_contains", {"selector": "p:nth-of-type(2)", "expected": "Estoy aprendiendo HTML."}, 1, "public")],
        ["Escribir una etiqueta completa", "Ordenar dos párrafos"], xp=105,
    ),
    _challenge(
        "listas-y-tablas", "03 · Título, subtítulo y texto",
        "`<h1>` marca el título principal de la página y `<h2>` un apartado dentro de ella. No se usan solo para hacer letras grandes: organizan la información. Ambos se cierran igual que p.",
        "<h1>Mi barrio</h1>\n<h2>El parque</h2>\n<p>Tiene muchos árboles.</p>",
        "1. Entre el título y el párrafo añade `<h2>Mis aficiones</h2>`.\n2. No cambies los otros textos.\n3. Revisa el orden en el Resultado.",
        {"html": "<h1>Sobre mí</h1>\n\n<p>Me gusta leer.</p>\n"}, "<h1>Sobre mí</h1>\n<h2>Mis aficiones</h2>\n<p>Me gusta leer.</p>\n", "",
        [("Subtítulo", "html.text_contains", {"selector": "h2", "expected": "Mis aficiones"}, 1, "public"), ("Después del título", "html.element_order", {"first": "h1", "second": "h2"}, 1, "public"), ("Párrafo después", "html.element_order", {"first": "h2", "second": "p"}, 1, "public")],
        ["Distinguir h1 y h2", "Organizar contenido"], xp=110,
    ),
    _challenge(
        "formularios-accesibles", "04 · Qué es CSS y aplicar color",
        "HTML describe el contenido; CSS decide su aspecto. Una regla CSS tiene selector, llaves y una declaración: `p { color: blue; }`. `p` elige los párrafos, `color` es la propiedad, `blue` es un nombre de color en inglés y `;` termina la declaración. Desde este paso tienes una pestaña CSS.",
        "p {\n  color: green;\n}",
        "1. En la pestaña CSS completa el valor de color con `navy`.\n2. No borres el selector p, las llaves ni el punto y coma.\n3. Mira cómo cambia el párrafo en el Resultado.",
        {"html": "<p>Un mensaje para el aula.</p>\n", "css": "p {\n  color: ;\n}\n"}, "<p>Un mensaje para el aula.</p>\n", "p {\n  color: navy;\n}\n",
        [("Regla para p", "css.selector_exists", {"selector": "p"}, 1, "public"), ("Color pedido", "css.declaration_equals", {"selector": "p", "property": "color", "expected": "navy"}, 2, "public")],
        ["Distinguir HTML y CSS", "Escribir una regla CSS"], example_language="css", xp=115,
    ),
    _challenge(
        "multimedia-responsiva", "05 · Elegir otro elemento con un selector",
        "Un selector no tiene que ser p. Si escribimos `h1`, la regla se aplica a todos los títulos principales. Una propiedad solo cambia el aspecto, no convierte un h1 en otra etiqueta.",
        "h1 {\n  color: tomato;\n}",
        "1. Completa la declaración de la regla h1 con `color: teal;`.\n2. Conserva el título preparado en HTML.\n3. Comprueba que solo cambia el título.",
        {"html": "<h1>Noticias del aula</h1>\n<p>Hoy hay biblioteca.</p>\n", "css": "h1 {\n  color: ;\n}\n"}, "<h1>Noticias del aula</h1>\n<p>Hoy hay biblioteca.</p>\n", "h1 {\n  color: teal;\n}\n",
        [("Selector h1", "css.selector_exists", {"selector": "h1"}, 1, "public"), ("Color del título", "css.declaration_equals", {"selector": "h1", "property": "color", "expected": "teal"}, 2, "public")],
        ["Usar un selector de elemento", "Aplicar color a un título"], example_language="css", xp=120,
    ),
    _challenge(
        "html-limpio-y-valido", "06 · Una clase para un grupo",
        "El atributo HTML `class` pone un nombre reutilizable a un elemento. En CSS una clase se selecciona con un punto: `.aviso { color: purple; }`. Así podemos dar el mismo aspecto a los elementos que lleven `class=\"aviso\"`.",
        "<p class=\"destacado\">Trae el cuaderno.</p>\n\n.destacado {\n  color: purple;\n}",
        "1. Añade `class=\"aviso\"` al párrafo.\n2. Completa el color de `.aviso` con `crimson`.\n3. Conserva el punto antes de aviso en CSS.",
        {"html": "<p>Entrega el viernes.</p>\n", "css": ".aviso {\n  color: ;\n}\n"}, "<p class=\"aviso\">Entrega el viernes.</p>\n", ".aviso {\n  color: crimson;\n}\n",
        [("Clase en HTML", "html.selector_exists", {"selector": "p.aviso"}, 2, "public"), ("Selector de clase", "css.selector_exists", {"selector": ".aviso"}, 1, "public"), ("Color del aviso", "css.declaration_equals", {"selector": ".aviso", "property": "color", "expected": "crimson"}, 2, "public")],
        ["Añadir una clase", "Relacionar HTML y CSS"], example_language="css", xp=125,
    ),
    _challenge(
        "css-selectores-y-color", "07 · La estructura de un documento",
        "Un documento HTML completo empieza con `<!doctype html>`. `head` guarda información que no se ve en el cuerpo y `body` contiene lo visible. `title`, dentro de head, nombra la pestaña; h1 sigue siendo el título que aparece en la página.",
        "<!doctype html>\n<html>\n  <head><title>Mi diario</title></head>\n  <body><h1>Excursión</h1></body>\n</html>",
        "1. Cambia el contenido de title por `Mi primera web`.\n2. Conserva el h1 preparado.\n3. No pongas title dentro de body.",
        {"html": "<!doctype html>\n<html>\n  <head><title>Cambia este título</title></head>\n  <body><h1>Sobre mí</h1></body>\n</html>\n", "css": ""}, "<!doctype html>\n<html>\n  <head><title>Mi primera web</title></head>\n  <body><h1>Sobre mí</h1></body>\n</html>\n", "",
        [("Nombre del documento", "html.text_contains", {"selector": "title", "expected": "Mi primera web"}, 2, "public"), ("Título visible", "html.text_contains", {"selector": "body h1", "expected": "Sobre mí"}, 1, "public")],
        ["Reconocer head y body", "Distinguir title y h1"], xp=130,
    ),
    _challenge(
        "css-modelo-de-caja", "08 · Enlaces y atributos",
        "Un atributo añade información a una etiqueta. En un enlace, `href` indica el destino y las palabras entre `<a>` y `</a>` son el texto visible. Nombre, igual y valor entre comillas forman el atributo.",
        "<a href=\"https://example.org\">Visitar un ejemplo</a>",
        "1. Completa href con `https://example.com`.\n2. Escribe como texto visible `Página de ejemplo`.\n3. No hace falta abrir el enlace.",
        {"html": "<a href=\"\">Escribe el texto</a>\n", "css": ""}, "<a href=\"https://example.com\">Página de ejemplo</a>\n", "",
        [("Destino del enlace", "html.attribute_equals", {"selector": "a", "attribute": "href", "expected": "https://example.com"}, 2, "public"), ("Texto del enlace", "html.text_contains", {"selector": "a", "expected": "Página de ejemplo"}, 1, "public")],
        ["Escribir un atributo", "Crear un enlace"], xp=135,
    ),
    _challenge(
        "css-responsive", "09 · Una lista sin orden",
        "`<ul>` reúne una lista en la que el orden no importa. Cada elemento va dentro de `<li>`. Los puntos los añade el navegador: no los escribimos a mano.",
        "<ul>\n  <li>Pan</li>\n  <li>Fruta</li>\n</ul>",
        "1. Añade `<li>Ratón</li>` después de Teclado.\n2. Déjalo dentro de ul.\n3. Comprueba que aparecen dos puntos.",
        {"html": "<ul>\n  <li>Teclado</li>\n</ul>\n", "css": ""}, "<ul>\n  <li>Teclado</li>\n  <li>Ratón</li>\n</ul>\n", "",
        [("Dos elementos", "html.selector_count", {"selector": "ul > li", "expected": 2}, 1, "public"), ("Elemento añadido", "html.text_contains", {"selector": "ul > li:nth-of-type(2)", "expected": "Ratón"}, 1, "public")],
        ["Crear una lista", "Anidar li en ul"], xp=140,
    ),
    _challenge(
        "javascript-funciones-y-datos", "10 · Un apartado con sentido",
        "`<main>` reúne el contenido principal de una página. `<section>` agrupa un apartado relacionado y suele incluir un título. Son etiquetas de estructura: ayudan a entender el documento antes de aplicar estilos.",
        "<main>\n  <section>\n    <h2>Horario</h2>\n    <p>Consulta el tablón.</p>\n  </section>\n</main>",
        "1. Rodea el h2 y el párrafo con `<section>` y `</section>`.\n2. Conserva ambos dentro de main.\n3. No cambies sus textos.",
        {"html": "<main>\n  <h2>Material</h2>\n  <p>Trae una libreta.</p>\n</main>\n", "css": ""}, "<main>\n  <section>\n    <h2>Material</h2>\n    <p>Trae una libreta.</p>\n  </section>\n</main>\n", "",
        [("Contenido principal", "html.selector_exists", {"selector": "main"}, 1, "public"), ("Apartado", "html.selector_exists", {"selector": "main > section"}, 2, "public"), ("Título dentro", "html.selector_exists", {"selector": "section > h2"}, 1, "public")],
        ["Usar main", "Agrupar contenido con section"], xp=145,
    ),
    _challenge(
        "javascript-eventos-dom", "11 · Una imagen y su alternativa",
        "`<img>` muestra una imagen y no necesita etiqueta de cierre. `src` indica dónde está el archivo. `alt` describe con palabras su contenido para quien no pueda verla o use un lector de pantalla.",
        f"<img src=\"{IMAGE_SRC}\" alt=\"Un libro abierto\">",
        "1. Cambia solo alt por `Un ordenador sobre una mesa`.\n2. Conserva la dirección src preparada.\n3. No añadas un cierre para img.",
        {"html": f"<img src=\"{IMAGE_SRC}\" alt=\"Completa la descripción\">\n", "css": ""}, f"<img src=\"{IMAGE_SRC}\" alt=\"Un ordenador sobre una mesa\">\n", "",
        [("Descripción alternativa", "html.attribute_equals", {"selector": "img", "attribute": "alt", "expected": "Un ordenador sobre una mesa"}, 2, "public"), ("Imagen conservada", "html.attribute_equals", {"selector": "img", "attribute": "src", "expected": IMAGE_SRC}, 1, "public")],
        ["Usar img", "Escribir un texto alternativo"], xp=150,
    ),
    _challenge(
        "panel-integrado-web", "12 · Margen: separar por fuera",
        "El modelo de caja trata cada elemento como una caja. `margin` deja espacio fuera de esa caja, separándola de los elementos cercanos. `px` significa píxeles, una unidad pequeña de medida en pantalla: `16px` pide dieciséis píxeles. Se escribe como otra declaración dentro de una regla CSS.",
        ".nota {\n  margin: 16px;\n}",
        "1. Completa margin con `16px`.\n2. Conserva el selector `.nota`.\n3. Observa el espacio alrededor del párrafo.",
        {"html": "<p class=\"nota\">Aviso del día.</p>\n", "css": ".nota {\n  margin: ;\n}\n"}, "<p class=\"nota\">Aviso del día.</p>\n", ".nota {\n  margin: 16px;\n}\n",
        [("Regla de nota", "css.selector_exists", {"selector": ".nota"}, 1, "public"), ("Margen exterior", "css.declaration_equals", {"selector": ".nota", "property": "margin", "expected": "16px"}, 2, "public")],
        ["Distinguir espacio exterior", "Usar margin"], example_language="css", xp=155,
    ),
    _challenge(
        "13-relleno-interior", "13 · Relleno: espacio por dentro",
        "`padding` deja espacio entre el contenido y el borde de una caja. A diferencia de margin, el relleno queda dentro de la caja. Usaremos píxeles, escritos como `12px`.",
        ".mensaje {\n  padding: 12px;\n}",
        "1. Completa padding con `12px`.\n2. No cambies el párrafo HTML.\n3. Mira cómo el texto se aleja del borde imaginario.",
        {"html": "<p class=\"mensaje\">El aula abre a las ocho.</p>\n", "css": ".mensaje {\n  padding: ;\n}\n"}, "<p class=\"mensaje\">El aula abre a las ocho.</p>\n", ".mensaje {\n  padding: 12px;\n}\n",
        [("Regla de mensaje", "css.selector_exists", {"selector": ".mensaje"}, 1, "public"), ("Relleno interior", "css.declaration_equals", {"selector": ".mensaje", "property": "padding", "expected": "12px"}, 2, "public")],
        ["Distinguir margin y padding", "Usar padding"], example_language="css", xp=160,
    ),
    _challenge(
        "14-borde-visible", "14 · Dibujar un borde",
        "`border` dibuja el límite visible de una caja. En `border: 2px solid steelblue;`, 2px es el grosor, solid es una línea continua y steelblue es el color. Las tres partes van en la misma declaración.",
        ".tarjeta {\n  border: 2px solid steelblue;\n}",
        "1. Completa border con `2px solid steelblue`.\n2. Deja el punto del selector `.tarjeta`.\n3. Comprueba el borde del texto.",
        {"html": "<p class=\"tarjeta\">Una nota con borde.</p>\n", "css": ".tarjeta {\n  border: ;\n}\n"}, "<p class=\"tarjeta\">Una nota con borde.</p>\n", ".tarjeta {\n  border: 2px solid steelblue;\n}\n",
        [("Regla de tarjeta", "css.selector_exists", {"selector": ".tarjeta"}, 1, "public"), ("Borde pedido", "css.declaration_equals", {"selector": ".tarjeta", "property": "border", "expected": "2px solid steelblue"}, 2, "public")],
        ["Reconocer las partes de border", "Dibujar un borde"], example_language="css", xp=165,
    ),
    _challenge(
        "15-display-en-linea", "15 · Display: cómo ocupa sitio",
        "`display` indica cómo se coloca una caja. `<span>` es una etiqueta HTML en línea: suele seguir junto al texto que la rodea. Con `display: inline-block` puede recibir padding y border sin iniciar una línea nueva. Es una regla CSS aplicada a un selector.",
        ".etiqueta {\n  display: inline-block;\n}",
        "1. Completa display con `inline-block`.\n2. Conserva la clase etiqueta en el span.\n3. Mira que el texto sigue junto a su frase.",
        {"html": "<p>Estado: <span class=\"etiqueta\">listo</span></p>\n", "css": ".etiqueta {\n  display: ;\n}\n"}, "<p>Estado: <span class=\"etiqueta\">listo</span></p>\n", ".etiqueta {\n  display: inline-block;\n}\n",
        [("Regla de etiqueta", "css.selector_exists", {"selector": ".etiqueta"}, 1, "public"), ("Display en línea", "css.declaration_equals", {"selector": ".etiqueta", "property": "display", "expected": "inline-block"}, 2, "public")],
        ["Reconocer display", "Usar inline-block"], example_language="css", xp=170,
    ),
    _challenge(
        "16-flex-primera-fila", "16 · Flex: una fila de cajas",
        "Cuando un contenedor tiene `display: flex`, sus elementos hijos se colocan en una fila por defecto. `gap` deja espacio entre esos hijos. Flex se escribe en el contenedor, no en cada elemento interior.",
        ".fila {\n  display: flex;\n  gap: 8px;\n}",
        "1. Completa `display: flex;`.\n2. Completa `gap: 8px;`.\n3. No cambies los dos enlaces HTML.",
        {"html": "<section class=\"fila\">\n  <a href=\"#inicio\">Inicio</a>\n  <a href=\"#ayuda\">Ayuda</a>\n</section>\n", "css": ".fila {\n  display: ;\n  gap: ;\n}\n"}, "<section class=\"fila\">\n  <a href=\"#inicio\">Inicio</a>\n  <a href=\"#ayuda\">Ayuda</a>\n</section>\n", ".fila {\n  display: flex;\n  gap: 8px;\n}\n",
        [("Regla de fila", "css.selector_exists", {"selector": ".fila"}, 1, "public"), ("Activa flex", "css.declaration_equals", {"selector": ".fila", "property": "display", "expected": "flex"}, 2, "public"), ("Separa elementos", "css.declaration_equals", {"selector": ".fila", "property": "gap", "expected": "8px"}, 1, "public")],
        ["Crear un contenedor flex", "Separar hijos con gap"], example_language="css", xp=175,
    ),
    _challenge(
        "17-formulario-y-campo", "17 · Un formulario y un campo",
        "`<form>` reúne controles con los que una persona puede escribir datos. `<input>` crea un campo y no tiene cierre. `type=\"text\"` indica texto y `name` da un nombre al dato; ambos son atributos entre comillas.",
        "<form>\n  <input type=\"text\" name=\"ciudad\">\n</form>",
        "1. Dentro de form escribe un input.\n2. Dale `type=\"text\"` y `name=\"nombre\"`.\n3. No añadas JavaScript: este formulario solo muestra un campo.",
        {"html": "<form>\n  \n</form>\n", "css": ""}, "<form>\n  <input type=\"text\" name=\"nombre\">\n</form>\n", "",
        [("Campo de texto", "html.attribute_equals", {"selector": "form input", "attribute": "type", "expected": "text"}, 2, "public"), ("Nombre del dato", "html.attribute_equals", {"selector": "form input", "attribute": "name", "expected": "nombre"}, 2, "public")],
        ["Usar form", "Crear un input de texto"], xp=180,
    ),
    _challenge(
        "18-etiqueta-del-campo", "18 · Etiquetar un campo",
        "`<label>` explica para qué sirve un campo. Su atributo `for` debe tener el mismo valor que el `id` del input. Esa pareja conecta texto y campo, y hace más claro el formulario.",
        "<label for=\"correo\">Correo</label>\n<input id=\"correo\" type=\"text\" name=\"correo\">",
        "1. Escribe `Nombre` dentro de label.\n2. Completa `for=\"nombre\"` y `id=\"nombre\"`.\n3. Conserva type y name preparados.",
        {"html": "<form>\n  <label for=\"\">Escribe aquí</label>\n  <input id=\"\" type=\"text\" name=\"nombre\">\n</form>\n", "css": ""}, "<form>\n  <label for=\"nombre\">Nombre</label>\n  <input id=\"nombre\" type=\"text\" name=\"nombre\">\n</form>\n", "",
        [("Texto de etiqueta", "html.text_contains", {"selector": "label", "expected": "Nombre"}, 1, "public"), ("Etiqueta asociada", "html.attribute_equals", {"selector": "label", "attribute": "for", "expected": "nombre"}, 2, "public"), ("Id del campo", "html.attribute_equals", {"selector": "input", "attribute": "id", "expected": "nombre"}, 2, "public")],
        ["Crear label", "Relacionar for e id"], xp=185,
    ),
    _challenge(
        "19-tarjeta-html-css", "19 · Una tarjeta con HTML y CSS",
        "Ahora reunimos ideas ya conocidas: section agrupa un apartado; una clase permite seleccionar esa caja; padding deja espacio interior y border marca su límite. CSS mantiene el aspecto separado del HTML.",
        "<section class=\"panel\"><h2>Consejos</h2><p>Lee antes de empezar.</p></section>\n\n.panel {\n  padding: 10px;\n  border: 1px solid slateblue;\n}",
        "1. Añade `class=\"ficha\"` a section.\n2. Completa padding con `12px`.\n3. Completa border con `2px solid steelblue`.",
        {"html": "<section>\n  <h2>Biblioteca</h2>\n  <p>Abierta hoy.</p>\n</section>\n", "css": ".ficha {\n  padding: ;\n  border: ;\n}\n"}, "<section class=\"ficha\">\n  <h2>Biblioteca</h2>\n  <p>Abierta hoy.</p>\n</section>\n", ".ficha {\n  padding: 12px;\n  border: 2px solid steelblue;\n}\n",
        [("Apartado", "html.selector_exists", {"selector": "section"}, 1, "public"), ("Clase de ficha", "html.selector_exists", {"selector": "section.ficha"}, 1, "public"), ("Relleno", "css.declaration_equals", {"selector": ".ficha", "property": "padding", "expected": "12px"}, 2, "public"), ("Borde", "css.declaration_equals", {"selector": ".ficha", "property": "border", "expected": "2px solid steelblue"}, 2, "public")],
        ["Combinar estructura y estilo", "Reutilizar padding y border"], example_language="css", xp=190,
    ),
    _challenge(
        "20-repaso-html-css", "20 · Repaso: una ficha enlazada",
        "En este repaso no aparece sintaxis nueva. HTML aporta main, h1, p y a; la clase `accion` conecta el enlace con CSS. `display: inline-block`, padding y border permiten que el enlace se vea como una pequeña ficha sin cambiar su significado de enlace.",
        "<main><h1>Club de ciencias</h1><p>Experimentos cada jueves.</p><a class=\"accion\" href=\"#actividades\">Actividades</a></main>\n\n.accion { display: inline-block; padding: 6px; border: 1px solid purple; }",
        "1. Cambia el texto del enlace por `Ver horario`.\n2. Completa padding con `8px`.\n3. Completa border con `1px solid teal` y conserva `display: inline-block`.",
        {"html": "<main>\n  <h1>Club de lectura</h1>\n  <p>Una reunión semanal.</p>\n  <a class=\"accion\" href=\"#horario\">Cambia este texto</a>\n</main>\n", "css": ".accion {\n  display: inline-block;\n  padding: ;\n  border: ;\n}\n"}, "<main>\n  <h1>Club de lectura</h1>\n  <p>Una reunión semanal.</p>\n  <a class=\"accion\" href=\"#horario\">Ver horario</a>\n</main>\n", ".accion {\n  display: inline-block;\n  padding: 8px;\n  border: 1px solid teal;\n}\n",
        [("Contenido principal", "html.selector_exists", {"selector": "main"}, 1, "public"), ("Enlace final", "html.text_contains", {"selector": ".accion", "expected": "Ver horario"}, 1, "public"), ("Display conocido", "css.declaration_equals", {"selector": ".accion", "property": "display", "expected": "inline-block"}, 1, "public"), ("Relleno final", "css.declaration_equals", {"selector": ".accion", "property": "padding", "expected": "8px"}, 2, "public"), ("Borde final", "css.declaration_equals", {"selector": ".accion", "property": "border", "expected": "1px solid teal"}, 2, "public")],
        ["Repasar HTML y CSS", "Completar una ficha enlazada"], example_language="css", xp=200,
    ),
]


class Command(BaseCommand):
    help = "Crea el itinerario HTML/CSS de 20 pasos para SMR y el catálogo JavaScript asociado."

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

        year, _ = AcademicYear.objects.get_or_create(name=self._academic_year_name(options.get("academic_year")), defaults={"active": True})
        cohort, _ = Cohort.objects.get_or_create(name=options["cohort"], academic_year=year, defaults={"active": True, "track": Cohort.Track.WEB})
        ensure_cohort_track(cohort, Cohort.Track.WEB)
        if owner.role == User.Role.TEACHER and not owner.is_superuser:
            TeachingAssignment.objects.get_or_create(cohort=cohort, teacher=owner, defaults={"active": True})

        course, created = Course.objects.get_or_create(
            slug=TRACK_SLUG,
            defaults={
                "title": "HTML y CSS desde cero · SMR",
                "description": "Veinte pasos guiados desde el primer párrafo hasta una pequeña ficha con HTML y CSS; cobertura parcial del módulo 0228 Aplicaciones web.",
                "web_stage": Course.WebStage.HTML_CSS,
                "created_by": owner,
                "active": True,
            },
        )
        if not created:
            course.title = "HTML y CSS desde cero · SMR"
            course.description = "Veinte pasos guiados desde el primer párrafo hasta una pequeña ficha con HTML y CSS; cobertura parcial del módulo 0228 Aplicaciones web."
            course.web_stage = Course.WebStage.HTML_CSS
            course.save(update_fields=["title", "description", "web_stage", "updated_at"])

        module, module_created = Module.objects.get_or_create(
            course=course,
            position=1,
            defaults={"title": "De la primera etiqueta a una ficha", "description": "Retos cortos y guiados de HTML y CSS, sin JavaScript.", "weight": 100},
        )
        if not module_created:
            module.title = "De la primera etiqueta a una ficha"
            module.description = "Retos cortos y guiados de HTML y CSS, sin JavaScript."
            module.save(update_fields=["title", "description"])

        created_versions = existing_versions = migrated_links = archived_assignments = newer_versions_skipped = 0
        for item in CHALLENGES:
            activity, _ = Activity.objects.get_or_create(
                module=module,
                slug=item["slug"],
                defaults={"title": item["title"], "kind": Activity.Kind.CODE, "status": Activity.Status.PUBLISHED, "created_by": owner},
            )
            # The dashboard orders by Activity.title.  Refresh only the
            # built-in v2/v3 labels so an upgraded centre sees v4's ordinal
            # sequence while a teacher's own title remains untouched.
            known_titles = {V2_TITLES.get(item["slug"]), V3_TITLES.get(item["slug"])}
            if activity.title in known_titles and activity.title != item["title"]:
                activity.title = item["title"]
                activity.save(update_fields=["title", "updated_at"])
            if activity.versions.filter(version_number__gt=WEB_CATALOG_VERSION).exists():
                newer_versions_skipped += 1
                continue
            version, version_created = ActivityVersion.objects.get_or_create(
                activity=activity,
                version_number=WEB_CATALOG_VERSION,
                defaults={
                    "language": ActivityVersion.Language.WEB,
                    "difficulty": item["difficulty"], "xp_reward": item["xp"], "hints": item["hints"],
                    "instructions": f"## Antes de empezar\nEl Editor ya está preparado. Escribe solo en las pestañas que el paso te ha presentado.\n\n## La idea\n{item['theory']}\n\n## Ejemplo explicado\n```{item['example_language']}\n{item['example']}\n```\n\n{item['example_explanation']}\n\n## Tu ejercicio\n{item['task']}\n\n> Las comprobaciones leen tu HTML y CSS; la plataforma no ejecuta código en el servidor.",
                    "objectives": item["objectives"], "learning_outcomes": item["ra"], "assessment_criteria": item["ce"],
                    "professional_module_code": "0228", "curriculum_scope": "Navarra · cobertura parcial", "curriculum_edition": "navarra-2025", "curriculum_unit": "", "curriculum_source": CURRICULUM_SOURCE,
                    "starter_files": item["starter"], "reference_solution": {key: item[key] for key in item["starter"]},
                    "grading_mode": ActivityVersion.GradingMode.AUTOMATIC_STATIC, "auto_weight": "1.0000", "manual_weight": "0.0000", "created_by": owner,
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
                for position, (name, test_type, definition, points, visibility) in enumerate(item["tests"]):
                    TestCase.objects.get_or_create(activity_version=version, name=name, defaults={"type": test_type, "definition": definition, "points": points, "visibility": visibility, "feedback": "Revisa la estructura indicada en el enunciado.", "position": position})
            assignment, assignment_created, upgrade = get_or_create_catalog_revision_assignment(
                previous_catalog_titles=tuple(title for title in (V2_TITLES.get(item["slug"]), V3_TITLES.get(item["slug"])) if title),
                activity=activity, version=version, cohort=cohort,
                defaults={"status": Assignment.Status.PUBLISHED, "created_by": owner, "title_override": item["title"], "attempt_policy": Assignment.AttemptPolicy.BEST, "max_attempts": None, "weight": 100, "allow_late": True, "published_at": timezone.now()},
            )
            if assignment_created and not assignment.title_override:
                assignment.title_override = item["title"]
                assignment.save(update_fields=["title_override"])
            migrated_links += upgrade["migrated_links"]
            archived_assignments += upgrade["archived_assignments"]

        # A revision migrates the existing 12 activities for linked historical
        # groups, but the eight new activities initially belong only to the
        # requested cohort. Complete this HTML/CSS v4 course for every active
        # web group that is already linked to one of its current assignments.
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
                _, linked = AssignmentCohort.objects.get_or_create(
                    assignment=current_assignment,
                    cohort=linked_cohort,
                )
                completed_group_links += int(linked)

        self.stdout.write(self.style.SUCCESS(f"Itinerario HTML/CSS v{WEB_CATALOG_VERSION} listo: {len(CHALLENGES)} retos, grupo {cohort.name}, {created_versions} versiones nuevas y {existing_versions} ya existentes. Actualizados {migrated_links} vínculos, completados {completed_group_links} enlaces de grupos activos y archivadas {archived_assignments} asignaciones anteriores. Respetadas {newer_versions_skipped} revisiones posteriores del centro."))
        # JavaScript is a separate course but uses these same fully linked web
        # cohorts. Its command deliberately does not call back here.
        for javascript_cohort in javascript_cohorts:
            # seed_javascript deliberately does not call back here, avoiding
            # recursion while retaining the cohort's own academic year.
            call_command(
                "seed_javascript",
                owner=owner.username,
                cohort=javascript_cohort.name,
                academic_year=javascript_cohort.academic_year.name,
            )
