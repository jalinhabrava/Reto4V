# Itinerario Python · Reto4V

## Propósito

Este itinerario ofrece una introducción progresiva a Python para 2.º de DAM y
el módulo `0491 Sistemas de gestión empresarial`. Llega desde salida,
variables y tipos hasta funciones, excepciones, `pathlib` y lectura/escritura
de archivos. Los ejemplos usan registros, catálogos y exportaciones para
preparar el trabajo posterior con Odoo, sin conectarse a un servidor Odoo ni
simular su ORM.

Es una **preparación didáctica y un alineamiento parcial**, no una acreditación
completa del módulo ni una equivalencia automática con RA/CE. La referencia
curricular principal para Navarra es el [Decreto Foral 110/2024 de
modificación del currículo de grado superior](https://www.educacion.navarra.es/documents/27590/558252/DF%2B110_2024%2Bmodificacion%2BGS.pdf/a649cf9e-7adf-3c5d-c5ac-eaa602a553a5?version=1.0), que modifica el [Decreto Foral
203/2011](https://www.educacion.navarra.es/documents/27590/558256/DF_203_2011_Desarrollo%2Bde%2BAplicaciones%2BMultiplataforma.pdf/29947bf5-4235-4ade-9fac-832fd006df8a?version=1.0). En la ordenación vigente, `0491` figura en segundo curso con 160 horas y 5 horas semanales. El catálogo no pretende cubrir por sí solo el RA5 ni sus criterios: deja `learning_outcomes` y `assessment_criteria` vacíos para que el centro decida su programación y evaluación.

Como contexto técnico, la documentación oficial de [Odoo Server
framework 101](https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101.html)
presenta objetos y modelos desarrollados con Python. Reto4V solo trabaja los
fundamentos previos; las APIs, módulos, seguridad y ORM de Odoo requieren un
entorno Odoo de prácticas separado.

## Crear el itinerario

Después de crear una cuenta de profesor o administrador y ejecutar las
migraciones:

```bash
python manage.py seed_python --owner profesor --cohort 2DAM
```

Opciones disponibles:

- `--owner USERNAME` (obligatoria): cuenta existente de profesor o administrador.
- `--cohort NOMBRE`: grupo destinatario; por defecto `2DAM`.
- `--academic-year AAAA-AAAA`: curso académico; si se omite se calcula según la fecha del servidor.

El comando crea el curso `Introducción a Python para SGE · DAM`, un módulo de
apoyo y doce actividades publicadas con sus asignaciones al grupo. No crea
alumnos, contraseñas ni datos personales. Es idempotente: reutiliza actividades,
versiones, tests y asignaciones que ya existan; nunca reemplaza una versión
asignada ni modifica su evidencia.

El catálogo incluye una solución de referencia para revisar el diseño. Como el
repositorio es público, las soluciones **no son respuestas secretas** ni deben
usarse como banco de exámenes. Para una evaluación con secreto real, crea una
nueva versión y tests privados directamente en la instalación del centro.

## Catálogo progresivo

| # | Tema | Contexto de SGE/Odoo | Dificultad |
|---:|---|---|---|
| 01 | Salida y variables | Mensaje de bienvenida | Inicial |
| 02 | Tipos y cadenas | Etiqueta de producto | Inicial |
| 03 | Condicionales | Regla de disponibilidad de stock | Inicial |
| 04 | Listas y bucles | Recorrido de productos | Inicial |
| 05 | Diccionarios | Registro de producto en memoria | Inicial |
| 06 | Funciones | Normalización de nombres | Intermedia |
| 07 | Excepciones | Conversión de datos importados | Intermedia |
| 08 | Imports y fechas | Preparar datos de intercambio | Intermedia |
| 09 | `pathlib` | Rutas portables | Intermedia |
| 10 | Lectura de texto | Importar líneas con `with open` | Intermedia |
| 11 | Escritura JSON | Exportar registros | Avanzada |
| 12 | Integración | Leer, transformar y escribir | Avanzada |

## DSL de tests Python

Las definiciones son declarativas y se validan antes de guardar/publicar una
actividad. No aceptan campos desconocidos, expresiones Python, regex de
corrección ni llamadas arbitrarias:

| Tipo | Definición | Comportamiento |
|---|---|---|
| `python.syntax_valid` | `{}` | El texto se puede analizar con el parser AST de Python. |
| `python.assignment` | `{"name": "productos"}` | Busca una asignación, destino de bucle, anotación o expresión asignada con ese nombre. |
| `python.function_declared` | `{"name": "transformar", "args": ["linea"], "returns": true}` | Busca una función `def` o `async def`; `args` exige sus argumentos declarados y `returns` comprueba que su cuerpo contiene un `return`. |
| `python.node_kind` | `{"kind": "for", "non_empty": true}` | Busca un nodo AST permitido. Alias: `if`, `if_else`, `for`, `while`, `try`, `with`, `function`, `dict`, `list`, `f_string`, `return`, `except_handler`, `comparison`, `call`, `import`. `non_empty` evita aceptar bloques cuyo único cuerpo es `pass`. |
| `python.call_used` | `{"name": "json.dump", "arg_names": ["productos", "archivo"]}` | Busca una llamada cuyo nombre cualificado coincide; admite `args` de literales o `arg_names` de expresiones de nombre, sin evaluarlas. |
| `python.import_used` | `{"module": "pathlib"}` | Busca `import modulo` o `from modulo import ...`. |
| `python.file_opened` | `{"mode": "r", "context_manager": true, "body_non_empty": true, "encoding": "utf-8"}` | Inspecciona el `open` incorporado o `.open()` sobre una instancia estructuralmente reconocible de `pathlib.Path`/`PurePath`, junto con su modo, codificación y uso dentro de `with`; `body_non_empty` exige contenido real en el bloque. |
| `python.attribute_used` | `{"name": "fichero.name"}` | Busca un acceso de atributo cualificado sin resolver ni ejecutar el objeto. |
| `python.subscript_used` | `{"name": "producto", "key": "name"}` | Busca un acceso con clave literal, como `producto["name"]`. |
| `python.dict_keys` | `{"name": "producto", "keys": ["name", "price"]}` | Comprueba que una asignación de diccionario declara las claves literales indicadas. |
| `python.loop_target` | `{"name": "producto", "iterable": "productos"}` | Comprueba que un `for` usa el destino e iterable indicados. |
| `python.exception_handled` | `{"name": "ValueError"}` | Comprueba que existe un `except` tipado para esa excepción. |
| `python.comparison_used` | `{"operator": "gt", "left": "stock", "right": 0}` | Busca una comparación AST con operador y operandos literales/nombres indicados. |

`python.variable_assigned` se conserva como alias compatible de
`python.assignment` para catálogos anteriores. Los nombres y módulos deben ser identificadores Python;
los modos de archivo están limitados a las variantes habituales de lectura,
escritura y anexado (`r`, `w`, `a`, `x` y sus variantes `+`/binarias).

El [módulo `ast` de la biblioteca estándar](https://docs.python.org/3/library/ast.html)
solo convierte el texto en un árbol de datos. Cada evaluación analiza el
archivo una sola vez y reutiliza ese árbol para todos los tests. Se limita cada
archivo a 256 KiB, el conjunto a 1 MiB, una versión a 200 tests, el árbol
Python a 5.000 nodos y la profundidad a 80 niveles. `SyntaxError`, entradas
malformadas y los límites de recursos producen feedback controlado; no
provocan la ejecución del código.

En ningún caso se evalúa o ejecuta el árbol, se genera bytecode o se llama a
`exec`, `eval`, `importlib`, un proceso, una red o el sistema de archivos a
partir del texto entregado. Los tests de
`file_opened` reconocen la estructura de lectura/escritura, pero no abren la
ruta, no leen contenido y no demuestran que una integración, una copia o un
modelo Odoo funcione. Las prácticas de ejecución real deben hacerse en una VM
separada con datos ficticios.

## XP, niveles y calificación

La experiencia se calcula en el servidor a partir del mejor resultado
automático válido de cada asignación:

```text
earned_xp = floor(xp_reward * best_automatic_score / 10)
```

El valor máximo de `xp_reward` es 1.000. La puntuación automática está entre 0
y 10; un resultado de al menos 8 completa el reto. Los intentos repetidos no
generan XP adicional: solo el máximo automático por asignación cuenta. XP,
niveles e insignias son feedback formativo y no calificaciones oficiales.

Al completar un reto Python se obtiene la insignia `python-path`. La insignia
`cross-path` se activa al completar retos de al menos dos itinerarios y
`triple-path` al completar retos web, Bash y Python. No existe clasificación
pública entre alumnos.

## Límites didácticos

El itinerario usa Python como lenguaje de preparación para SGE. No incluye
instalación de Odoo, conexión XML-RPC/JSON-RPC, acceso a una base de datos,
creación de módulos, permisos del ERP ni ejecución de scripts del alumnado.
Esas prácticas deben planificarse y evaluarse aparte por el equipo docente,
con un Odoo de laboratorio aislado y cuentas ficticias.
