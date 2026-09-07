# Itinerario JavaScript · SMR

El catálogo local `fundamentos-javascript-smr` tiene 13 lecciones y usa
`Course.web_stage = Course.WebStage.JAVASCRIPT`. Cada
`ActivityVersion` conserva `language = "web"` y versión de catálogo `2`: no se
crea un lenguaje nuevo ni un motor de ejecución.

Se crea de forma idempotente con:

~~~text
python manage.py seed_javascript --owner <profesor> --cohort 1SMR --academic-year 2026-2027
~~~

El grupo debe pertenecer al itinerario web. El comando no crea alumnado ni
credenciales. HTML y CSS conservan su propio curso; la integración de
`seed_web` invoca este comando al final y le pasa el mismo propietario, grupo y
curso académico, de modo que HTML/CSS y JavaScript quedan asignados al mismo
grupo. `seed_javascript` no llama a `seed_web`.

La revisión incorporada actual es la **v2**. Al actualizar desde v1, el comando
publica nuevas versiones y asignaciones, archiva las anteriores y conserva sus
borradores, entregas y calificaciones vinculados a la evidencia original. Los
títulos incorporados v1 se sustituyen; un título distinto escrito por el
docente se conserva. Repetir el comando es idempotente y una revisión posterior
del centro no se modifica.

## Secuencia didáctica

1. Qué es JavaScript y una instrucción `console.log`.
2. Variable de texto.
3. Números y cálculo.
4. Unir texto y variable.
5. Lista.
6. Decisión `if` y `else`.
7. Bucle `for...of`.
8. Función sin parámetros.
9. Parámetro y argumento.
10. `return`.
11. DOM: buscar un elemento con `id` y cambiar su texto.
12. DOM: reaccionar a un clic mediante una función ya conocida.
13. Repaso de lista, función y bucle.

Cada lección presenta concepto, ejemplo con datos distintos y un ejercicio
corto con starter casi completo. Las primeras diez entregan solamente
`javascript`; los dos retos DOM incluyen HTML de andamiaje y no piden DOM
antes de explicarlo. No hay asincronía, librerías, importaciones ni saltos de
sintaxis.

«Ver mi página» ejecuta exclusivamente la preview aislada del navegador.
`console.log` se observa en **Mensajes de tu página** y las modificaciones DOM
en **Resultado**. «Comprobar mi trabajo» usa sólo análisis estático: no prueba
que un programa se ejecute o que un clic produzca el efecto esperado.

## DSL estática JavaScript

El corrector analiza una vez el AST de Esprima. No usa Node, `eval`, imports ni
ejecuta el texto del estudiante. Los comentarios y los textos no satisfacen
ningún test porque no son nodos de llamada o declaración.

Los tipos existentes continúan disponibles:

| Tipo | Definición |
| --- | --- |
| `js.syntax_valid` | `{}` |
| `js.function_declared` | `{"name": "saludar"}` |
| `js.variable_declared` | `{"name": "nombre"}` |
| `js.event_listener_registered` | `{"event": "click", "target": "boton"}` |
| `js.forbidden_api_absent` | `{"api": "eval"}` |

La ampliación mínima añade:

| Tipo | Definición exacta | Qué reconoce |
| --- | --- | --- |
| `js.call_used` | `{"name": "console.log"}` | Una llamada con ese nombre o cadena de miembros. |
| `js.call_used` | `{"name": "console.log", "args": ["Hola"]}` | Una llamada cuyos argumentos posicionales son exactamente esos literales. |
| `js.call_used` | `{"name": "console.log", "arg_names": ["nombre"]}` | Una llamada cuyos argumentos posicionales son exactamente esos identificadores o cadenas de miembros. |
| `js.node_kind` | `{"kind": "array"}` | Un tipo de nodo de la lista permitida. |
| `js.variable_declared` | `{"name": "stock", "expected": 5}` | Una declaración simple `const`, `let` o `var` con ese literal inicial. |
| `js.variable_declared` | `{"name": "total", "operator": "*", "left": "precio", "right": "unidades"}` | Un inicializador binario exacto, sin calcularlo. |
| `js.return_expression` | `{"operator": "*", "left": "numero", "right": 2}` | Un `return` con esa expresión binaria exacta. |
| `js.assignment_equals` | `{"target": "mensaje.textContent", "expected": "Hola"}` | Una asignación `=` al destino y literal indicados. |

`args` y `arg_names`, si se usan juntos, deben corresponder ambos a la misma
llamada. No se resuelven nombres ni se calculan expresiones. Los literales
permitidos en `expected` y `args` son `null`, booleanos, números finitos y
textos acotados. En `js.variable_declared`, `expected` también puede ser una
lista plana de hasta 16 de esos literales; no se aceptan objetos ni expresiones.

Los valores admitidos de `js.node_kind` son:

~~~text
array, array_expression
assignment
call
for_of, for_of_statement
function, function_declaration
if, if_statement
return, return_statement
variable_declaration
~~~

Los nombres de `js.call_used`, `js.variable_declared` y
`js.function_declared` se limitan a segmentos ASCII de identificador
JavaScript (`A-Z`, `a-z`, `_`, `$` y dígitos fuera de la primera posición).
Las listas de argumentos y nombres tienen como máximo 16 elementos; la
profundidad del AST se limita a 80 y sus nodos a 5.000.

## Evidencia de aceptación

- 13 actividades, 52 comprobaciones estáticas.
- Cada solución de referencia obtiene 10/10.
- Cada starter obtiene menos de 8/10.
- Pruebas negativas confirman que comentarios, cadenas, declaraciones sin
  literal, nombres arbitrarios y consultas DSL desconocidas no cuentan.
- La suite confirma que el parser se invoca una vez por lote y que una
  instrucción `throw` se analiza sin ejecutarse.
