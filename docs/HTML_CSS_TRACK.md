# Itinerario HTML y CSS · SMR

## Alcance

El catálogo de Aplicaciones web (0228) es una introducción práctica y parcial
a HTML y CSS. No cubre el módulo completo, publicación web, CMS ni
JavaScript. La plataforma analiza los archivos de forma estática: no ejecuta
el código del alumnado en el servidor.

La revisión vigente es la **v5**. El curso fundamentos-web-smr usa la etapa
html_css; JavaScript vive en un curso separado. seed_web prepara ambos cursos
para los grupos web activos que ya reciben el HTML/CSS actual.

## Secuencia didáctica

| Pasos | Idea nueva | Práctica pequeña |
| --- | --- | --- |
| 1 | Documento HTML preparado: doctype, html, head, title, body y p | Cambiar solo el texto de un párrafo |
| 2 | Otro párrafo | Añadir un segundo p |
| 3–4 | h1 y h2 | Escribir el título principal y un subtítulo |
| 5 | Enlace y atributo href | Completar destino y texto visible |
| 6 | Lista ul con elementos li | Añadir un elemento a una lista |
| 7 | Imagen img, src y alt | Cambiar solo la descripción alternativa |
| 8 | Primera regla CSS: selector, llaves, declaración y color | Completar un valor de color |
| 9 | Selector de otro elemento | Estilizar h1 sin tocar p |
| 10 | class y selector de clase | Conectar una clase HTML con CSS |
| 11–13 | main, section y article | Rodear contenido conocido con una etiqueta de estructura |
| 14–16 | Margen, relleno y borde | Completar una declaración CSS cada vez |
| 17–18 | display inline-block y flex con gap | Aplicar display tras conocer clases, selectores y caja |
| 19–20 | form, input, label, for e id | Crear un campo y asociar su etiqueta |
| 21 | Repaso sin sintaxis nueva | Completar una ficha de contacto |

El primer paso muestra desde el inicio un documento completo, pero el trabajo
del alumnado se reduce a cambiar una frase ya situada en p. Los siete primeros
pasos presentan únicamente HTML. CSS aparece en el paso 8, una vez vistos
párrafos, títulos, enlaces, listas e imágenes. Las etiquetas semánticas llegan
después de esas bases. Caja, display y formularios cierran el recorrido y cada
paso declara los conocimientos que reutiliza.

Cada paso mantiene el mismo contrato: explicación de los símbolos nuevos,
ejemplo distinto al ejercicio, explicación del ejemplo, tarea numerada,
starter, solución HTML/CSS y comprobaciones públicas. La solución debe obtener
10; el starter queda por debajo de 8 para que la comprobación represente una
acción real del alumno.

## Comprobaciones estáticas

Los retos usan el DSL web existente:

- HTML: selector_exists, selector_count, text_contains, attribute_equals y
  element_order.
- CSS: selector_exists y declaration_equals.

Las pruebas CSS puntúan solo la declaración que pide completar el paso. Los
tests estructurales no prueban que se abra un enlace, se envíe un formulario o
se cargue un recurso; tampoco ejecutan HTML o CSS en el servidor.

## Compatibilidad de revisiones

Los slugs históricos se conservan. El seeding publica v5 como una nueva
versión de cada actividad y reconoce los títulos integrados de v1 a v4 para
actualizar su título visible sin reemplazar un título escrito por el docente.
Cada actividad recibe una posición didáctica de 1 a 21. Si un centro ya tiene
una revisión posterior, el seeding no cambia ni su título ni su posición.

## Fuente pedagógica

La secuencia se orienta en [Learn HTML: Hello,
World!](https://www.learn-html.org/en/Hello,_World!), [Basic
Elements](https://www.learn-html.org/en/Basic_Elements) y [Styles](https://www.learn-html.org/en/Styles).
Las fases de clase y selector se apoyan también en [Classes](https://www.learn-html.org/en/Classes)
y [Selectors](https://www.learn-html.org/en/Selectors). Los textos, ejemplos y
ejercicios del catálogo son propios.
