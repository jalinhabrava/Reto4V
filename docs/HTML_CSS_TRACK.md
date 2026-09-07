# Itinerario HTML y CSS · SMR

## Alcance

El catálogo inicial de Aplicaciones web (0228) es una introducción práctica y
parcial a HTML y CSS. No pretende cubrir el módulo completo, publicación web,
CMS ni JavaScript. La plataforma analiza archivos de forma estática: no ejecuta
el código del alumnado en el servidor.

La revisión vigente es la **v4**. El curso `fundamentos-web-smr` usa
`web_stage="html_css"`; JavaScript vive en un curso separado con su propia
etapa, aunque `seed_web` prepara ambos para los grupos web activos que ya
reciben el HTML/CSS actual.

## Secuencia didáctica

| Pasos | Idea nueva | Práctica pequeña |
| --- | --- | --- |
| 1–3 | Página, párrafo, etiquetas, h1 y h2 | Completar texto y un subtítulo |
| 4–5 | CSS, regla, selector, declaración y color | Completar `color` para p y h1 |
| 6 | `class` y selector de clase | Conectar una clase HTML con su regla CSS |
| 7–11 | Documento, enlaces, listas, estructura e imagen/alt | Completar un atributo o una etiqueta cada vez |
| 12–15 | Modelo de caja y display | Usar margin, padding, border e inline-block |
| 16 | Flex básico | Convertir un contenedor en fila y añadir gap |
| 17–18 | Formulario, input, label, for e id | Crear un campo y asociar su etiqueta |
| 19–20 | Integración y repaso | Construir una ficha HTML/CSS sin sintaxis nueva |

Los tres primeros pasos solo muestran la pestaña HTML. CSS aparece por primera
vez en el paso 4, después de explicar qué es una regla, un selector y una
declaración. JavaScript no se introduce ni se comprueba en este catálogo.

Cada paso conserva el mismo contrato: teoría, ejemplo distinto al ejercicio,
explicación, tarea numerada, starter, solución HTML/CSS y pruebas públicas. La
solución debe obtener 10; el starter debe permanecer por debajo de 8 para que
la comprobación represente una acción real del alumno.

## Comprobaciones estáticas

Los retos usan el DSL web existente:

- HTML: `html.selector_exists`, `html.selector_count`, `html.text_contains`,
  `html.attribute_equals` y `html.element_order`.
- CSS: `css.selector_exists` y `css.declaration_equals`.

Las pruebas CSS puntúan la declaración que el paso pide completar. No asignan
puntos adicionales por la plantilla o por declaraciones que el Editor ya trae.

## Fuente pedagógica

La progresión toma como orientación general la separación entre contenido y
estilo, el uso de selectores y el uso de clases explicados por
[Learn HTML: Styles](https://www.learn-html.org/en/Styles),
[Classes](https://www.learn-html.org/en/Classes) y
[Selectors](https://www.learn-html.org/en/Selectors). Los textos, ejemplos y
ejercicios del catálogo son propios.
