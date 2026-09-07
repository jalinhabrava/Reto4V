# Itinerario Python · Programmy4V

## Propósito y límite

Este itinerario introduce Python para 2.º de DAM antes de trabajar en un
entorno de Sistemas de gestión empresarial. Usa ejemplos pequeños de productos
porque resultan reconocibles, pero prioriza los fundamentos del lenguaje sobre
Odoo. No instala Odoo, no simula su ORM, no usa sus APIs ni acredita por sí
solo el módulo `0491`.

Es una preparación didáctica parcial. La programación oficial decide los
resultados de aprendizaje, criterios y evaluación; por eso
`learning_outcomes` y `assessment_criteria` permanecen vacíos. Como referencia
curricular se conserva el [Decreto Foral 110/2024](https://www.educacion.navarra.es/documents/27590/558252/DF%2B110_2024%2Bmodificacion%2BGS.pdf/a649cf9e-7adf-3c5d-c5ac-eaa602a553a5?version=1.0),
que modifica el [Decreto Foral 203/2011](https://www.educacion.navarra.es/documents/27590/558256/DF_203_2011_Desarrollo%2Bde%2BAplicaciones%2BMultiplataforma.pdf/29947bf5-4235-4ade-9fac-832fd006df8a?version=1.0).

La documentación de [Odoo Server framework 101](https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101.html)
puede usarse después como contexto de Python profesional. Sus modelos, APIs,
seguridad y entorno de ejecución requieren prácticas separadas y aisladas.

## Forma de cada reto

El catálogo sigue un patrón de aprendizaje corto inspirado en tutoriales
interactivos de iniciación, como [Hello, World!](https://www.learnpython.org/en/Hello%2C_World%21)
y [Variables and Types](https://www.learnpython.org/en/Variables_and_Types),
sin reproducir su texto:

1. Explica una sola idea nueva en lenguaje directo.
2. Presenta un ejemplo comentado, distinto del ejercicio.
3. Propone un ejercicio diminuto que solo usa esa idea y las anteriores.
4. Deja el editor casi preparado y ofrece comprobaciones estructurales acordes.

En particular, el reto 02 no usa f-strings: primero fija variables y textos;
los números, la unión de textos, las listas, las decisiones y los bucles se
introducen de forma independiente. Un `for` no aparece hasta que ya existe una
lista. El cierre repasa funciones, no introduce archivos, rutas, JSON ni APIs.

## Catálogo v3

Los doce slugs son identificadores históricos y no describen necesariamente el
tema actual. No se deben cambiar.

| # | Slug histórico | Idea nueva | Ejercicio mínimo |
|---:|---|---|---|
| 01 | `01-salida-y-variables` | `print()` | Cambiar un mensaje preparado. |
| 02 | `02-tipos-y-cadenas` | Variable con texto | Guardar y mostrar `producto`. |
| 03 | `03-condicionales-de-stock` | Números y multiplicación | Calcular un total. |
| 04 | `04-listas-y-bucles` | Unión de textos | Crear una etiqueta. |
| 05 | `05-diccionarios-de-registro` | Lista e índice | Mostrar el primer producto. |
| 06 | `06-funciones-reutilizables` | `if` / `else` | Mostrar disponibilidad. |
| 07 | `07-excepciones-de-datos` | Bucle `for` | Mostrar cada elemento de una lista. |
| 08 | `08-imports-y-fechas` | Diccionario | Consultar el nombre de un registro. |
| 09 | `09-rutas-con-pathlib` | `def` y llamada | Mostrar un saludo sin parámetros. |
| 10 | `10-lectura-de-texto` | Parámetro | Mostrar el dato recibido. |
| 11 | `11-escritura-json` | `return` | Devolver y mostrar un resultado. |
| 12 | `12-integracion-archivos` | Repaso de lista, función y `for` | Mostrar todos los productos. |

Los archivos, JSON y las APIs de Odoo quedan deliberadamente fuera de esta
revisión: requieren una ampliación posterior cuando el grupo ya domine estos
fundamentos. Los ejemplos y soluciones son material de referencia, no
respuestas secretas de un examen.

## Crear y actualizar el itinerario

En una instalación nueva se precarga al arrancar `web` con
`PRELOAD_CATALOGS=1`. También puede crearse para un grupo existente:

```bash
python manage.py seed_python --owner profesor --cohort 2DAM
```

`--owner` es obligatorio y debe ser profesor o administrador. `--cohort`
predetermina `2DAM`; `--academic-year AAAA-AAAA` permite fijar el curso. El
comando crea el curso **Introducción a Python para SGE · DAM**, su módulo y las
asignaciones publicadas. No crea alumnado, contraseñas ni datos personales.

La versión incorporada actual es **v3**. Las versiones y asignaciones ya
publicadas son evidencias inmutables: al ejecutar el comando sobre v2 crea v3,
migra los vínculos del grupo y archiva la asignación anterior sin modificar sus
ficheros, entregas ni calificaciones. Si una actividad tiene una versión
posterior del centro, el comando no la rebaja.

Durante la migración, un título de asignación que coincide exactamente con el
título incorporado de v2 se actualiza al título v3. Un título docente distinto
se conserva. Así se corrigen los títulos del catálogo sin perder una
personalización local. Repetir el comando es idempotente.

## Corrección estática

Cada prueba es declarativa y se valida antes de publicar. El evaluador analiza
el texto con [`ast`](https://docs.python.org/3/library/ast.html), una vez por
archivo, y reutiliza ese árbol; nunca evalúa ni ejecuta el código entregado.

| Tipo de prueba | Qué comprueba |
|---|---|
| `python.syntax_valid` | Que el texto se puede analizar como Python. |
| `python.assignment` | Que existe una asignación con un nombre dado. |
| `python.node_kind` | Una construcción AST, por ejemplo `if`, `for`, `list`, `dict`, `function`, `with` o `call`. |
| `python.call_used` | Una llamada por su nombre y, si procede, sus argumentos estructurales. |
| `python.loop_target` | El nombre de elemento y la lista de un `for`. |
| `python.function_declared` | Una función, sus argumentos declarados y un `return`. |
| `python.subscript_used` | Un acceso como `producto["name"]`. |
| `python.dict_keys` | Claves literales de un diccionario asignado. |
| `python.comparison_used` | Una comparación como `stock > 0`. |

El alias histórico `python.variable_assigned` sigue siendo compatible con
`python.assignment`. No se permiten expresiones arbitrarias, regex ni
llamadas de corrección. Hay límites de tamaño y complejidad del árbol para
mantener el análisis acotado.

La revisión v3 no incluye comprobaciones de importación o archivos. El
evaluador no llama a `exec`, `eval`, procesos, red, importación dinámica ni al
sistema de archivos a partir del trabajo del alumno.

## XP y evaluación

La experiencia es feedback formativo y no una calificación oficial:

```text
earned_xp = floor(xp_reward * best_automatic_score / 10)
```

El máximo de `xp_reward` es 1.000 y un resultado automático de al menos 8
completa el reto. Varios intentos no suman XP: solo cuenta el mejor resultado
por asignación. La docencia debe usar instrumentos separados para evaluar
prácticas reales de archivos u Odoo, con una VM y datos ficticios.
