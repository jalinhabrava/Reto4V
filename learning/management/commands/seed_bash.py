"""Seed the local Bash support track for second-year ASIR.

The catalogue is curriculum-neutral support for module 0378. Every example is
checked statically; neither it nor a student's script is ever executed.
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

TRACK_SLUG = "laboratorio-bash-seguridad-asir"
BASH_CATALOG_VERSION = 3


def _test(name, test_type, definition, points=1, visibility=TestCase.Visibility.PUBLIC):
    return (name, test_type, definition, points, visibility)


# Historical identifiers cannot change: their names do not describe the v3 order.
V2_TITLES = {
    "01-variables-y-salida": "01 · Mi primer script",
    "02-condiciones-y-rutas": "02 · Guardar un dato en una variable",
    "03-bucle-de-registros": "03 · Guardar una carpeta y un archivo",
    "04-funciones-reutilizables": "04 · Recibir un dato",
    "05-pipelines-de-registros": "05 · Tomar una decisión con if",
    "06-parametros-posicionales": "06 · Repetir una tarea con for",
    "07-codigos-de-salida": "07 · Repetir hasta terminar con while",
    "08-plan-de-copia": "08 · Crear una función sencilla",
    "09-permisos-del-script": "09 · Filtrar información con un pipeline",
    "10-pipeline-awk-y-orden": "10 · Preparar una carpeta de copias",
    "11-case-de-operacion": "11 · Preparar una copia con tar",
    "12-rutina-integrada": "12 · Crear y verificar una copia",
}


# Each item explains one new idea, uses a different example, and leaves a small,
# clearly bounded completion in the starter. Earlier ideas can be reused only
# after being introduced.
CHALLENGES = [
    {
        "slug": "01-variables-y-salida",
        "title": "01 · Terminal, shell y primer script",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 100,
        "theory": (
            "La terminal es la ventana donde escribimos órdenes. El shell las interpreta; Bash "
            "es uno de esos shells. Un script es un archivo de texto con órdenes en orden. El "
            "primer `#!` se llama shebang e indica que el archivo está pensado para Bash. Un "
            "`#` que no inicia esa primera línea abre un comentario: Bash ignora el resto de "
            "esa línea. `echo` muestra una línea de texto."
        ),
        "example": (
            "```bash\necho \"Informe preparado\"\n```\n\n"
            "`echo` recibe el texto entre comillas y lo muestra como una línea. Es solo una "
            "muestra de escritura: esta plataforma no ejecuta la orden."
        ),
        "task": "1. Conserva el shebang y el comentario.\n2. Cambia solo el texto de `echo` por `Hola, Bash`.\n3. No añadas otras órdenes todavía.",
        "hints": [
            "No borres `echo`: solo cambia su mensaje.",
            "El texto queda entre las mismas comillas dobles.",
            "La línea final debe ser `echo \"Hola, Bash\"`.",
        ],
        "objectives": ["Distinguir terminal, shell y script", "Reconocer el shebang", "Usar echo"],
        "starter": "#!/usr/bin/env bash\n\n# Cambia solo el mensaje de la línea siguiente.\necho \"Cambia este mensaje\"\n",
        "solution": "#!/usr/bin/env bash\n\necho \"Hola, Bash\"\n",
        "tests": [
            _test("Sintaxis válida", "bash.syntax_valid", {}),
            _test("Shebang Bash", "bash.shebang", {"expected": "/usr/bin/env bash"}),
            _test("Saludo con echo", "bash.command_used", {"command": "echo", "args": ["Hola, Bash"]}),
            _test("Intérprete Bash", "bash.shebang", {"interpreter": "bash"}),
        ],
    },
    {
        "slug": "02-condiciones-y-rutas",
        "title": "02 · Guardar un texto en una variable",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 110,
        "theory": (
            "Una variable guarda un dato con un nombre. Se asigna con `=` sin espacios a los "
            "lados y se lee escribiendo `$NOMBRE`. Bash distingue mayúsculas y minúsculas: "
            "`TURNO` y `turno` no son la misma variable."
        ),
        "example": (
            "```bash\nEQUIPO=nodo-a\necho $EQUIPO\n```\n\n"
            "La primera línea guarda `nodo-a` en `EQUIPO`. En la segunda, `$EQUIPO` se sustituye "
            "por el valor que se guardó antes."
        ),
        "task": "1. Conserva `TURNO=manana`.\n2. Muestra `$TURNO` con `echo`.\n3. No pongas espacios junto a `=`.",
        "hints": ["Lee el valor como `$TURNO`.", "La salida empieza por `echo`.", "No necesitas printf."],
        "objectives": ["Asignar una variable", "Leer una variable", "Distinguir nombre y valor"],
        "starter": "#!/usr/bin/env bash\n\nTURNO=manana\n# Muestra aquí el contenido de TURNO.\n",
        "solution": "#!/usr/bin/env bash\n\nTURNO=manana\necho $TURNO\n",
        "tests": [
            _test("Sintaxis válida", "bash.syntax_valid", {}),
            _test("Shebang Bash", "bash.shebang", {"interpreter": "bash"}),
            _test("Variable TURNO", "bash.variable_assigned", {"name": "TURNO"}),
            _test("Salida de la variable", "bash.command_used", {"command": "echo"}),
        ],
    },
    {
        "slug": "03-bucle-de-registros",
        "title": "03 · Proteger texto con comillas",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 120,
        "theory": (
            "Las comillas dobles agrupan un texto con espacios y permiten usar variables dentro. "
            "Así un mensaje completo llega a `echo` como una sola pieza, mientras `$EQUIPO` se "
            "reemplaza por el valor guardado."
        ),
        "example": (
            "```bash\nSERVICIO=web\necho \"Estado de $SERVICIO: correcto\"\n```\n\n"
            "Las comillas mantienen unido todo el mensaje. Dentro de ellas Bash sustituye "
            "`$SERVICIO` por `web` antes de mostrar el resultado."
        ),
        "task": "1. Conserva `EQUIPO`.\n2. Completa un `echo` entre comillas dobles.\n3. Incluye `$EQUIPO` y `listo hoy`.",
        "hints": ["Abre y cierra una comilla doble.", "Deja `$EQUIPO` dentro.", "Usa una sola línea echo."],
        "objectives": ["Usar comillas dobles", "Insertar una variable", "Conservar texto con espacios"],
        "starter": "#!/usr/bin/env bash\n\nEQUIPO=almacenamiento\n# Completa un echo con EQUIPO y el texto listo hoy.\n",
        "solution": "#!/usr/bin/env bash\n\nEQUIPO=almacenamiento\necho \"$EQUIPO listo hoy\"\n",
        "tests": [
            _test("Sintaxis válida", "bash.syntax_valid", {}),
            _test("Shebang Bash", "bash.shebang", {"expected": "/usr/bin/env bash"}),
            _test("Variable EQUIPO", "bash.variable_assigned", {"name": "EQUIPO"}),
            _test("Uso de echo", "bash.command_used", {"command": "echo", "args": ["$EQUIPO listo hoy"]}),
        ],
    },
    {
        "slug": "04-funciones-reutilizables",
        "title": "04 · Nombrar una ruta",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 130,
        "theory": (
            "Una ruta indica dónde está un archivo o carpeta. Una ruta que empieza por `/` es "
            "absoluta: parte de la raíz del sistema. Guardarla en una variable evita repetirla "
            "y permite mostrarla antes de usarla más adelante."
        ),
        "example": (
            "```bash\nRUTA=/var/log\necho \"Carpeta: $RUTA\"\n```\n\n"
            "`/var/log` empieza por `/`, por lo que es absoluta. La variable se inserta en el "
            "mensaje sin cambiar el texto de la ruta."
        ),
        "task": "1. Conserva `RUTA=/srv/informes`.\n2. Completa el `echo` preparado.\n3. Muestra `Destino:` seguido de `$RUTA`.",
        "hints": ["No crees carpetas.", "Usa `$RUTA` dentro del mensaje.", "Las comillas mantienen el espacio."],
        "objectives": ["Reconocer una ruta absoluta", "Guardar una ruta", "Mostrar una ruta"],
        "starter": "#!/usr/bin/env bash\n\nRUTA=/srv/informes\n# Completa el mensaje Destino: seguido de RUTA.\n",
        "solution": "#!/usr/bin/env bash\n\nRUTA=/srv/informes\necho \"Destino: $RUTA\"\n",
        "tests": [
            _test("Sintaxis válida", "bash.syntax_valid", {}),
            _test("Shebang Bash", "bash.shebang", {"interpreter": "bash"}),
            _test("Variable RUTA", "bash.variable_assigned", {"name": "RUTA"}),
            _test("Uso de echo", "bash.command_used", {"command": "echo", "args": ["Destino: $RUTA"]}),
        ],
    },
    {
        "slug": "05-pipelines-de-registros",
        "title": "05 · Dar formato con printf",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 140,
        "theory": (
            "`printf` muestra texto siguiendo una plantilla. `%s` reserva un lugar para un texto "
            "y `\\n` termina la línea. La plantilla deja visible dónde va cada dato, por eso "
            "sirve para mensajes que un script repite."
        ),
        "example": (
            "```bash\nUSUARIO=ana\nprintf 'Usuario: %s\\n' \"$USUARIO\"\n```\n\n"
            "La plantilla se conserva tal cual salvo `%s`. El valor de `$USUARIO` ocupa ese lugar "
            "y `\\n` añade el salto de línea."
        ),
        "task": "1. Conserva `ARCHIVO`.\n2. Completa `printf` con `Archivo: %s\\n`.\n3. Pasa `$ARCHIVO` al lugar de `%s`.",
        "hints": ["La plantilla va entre comillas simples.", "Después escribe `\"$ARCHIVO\"`.", "No añadas echo."],
        "objectives": ["Reconocer una plantilla printf", "Colocar un texto en %s", "Usar \\n"],
        "starter": "#!/usr/bin/env bash\n\nARCHIVO=estado.txt\n# Completa printf para mostrar Archivo: y ARCHIVO.\n",
        "solution": "#!/usr/bin/env bash\n\nARCHIVO=estado.txt\nprintf 'Archivo: %s\\n' \"$ARCHIVO\"\n",
        "tests": [
            _test("Sintaxis válida", "bash.syntax_valid", {}),
            _test("Shebang Bash", "bash.shebang", {"expected": "/usr/bin/env bash"}),
            _test("Variable ARCHIVO", "bash.variable_assigned", {"name": "ARCHIVO"}),
            _test("Uso de printf", "bash.command_used", {"command": "printf", "args": ["Archivo: %s\\n", "$ARCHIVO"]}),
        ],
    },
    {
        "slug": "06-parametros-posicionales",
        "title": "06 · Comprobar un archivo con if",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 150,
        "theory": (
            "`if` permite escribir una orden solo si una comprobación es verdadera. `[ -f "
            "\"$ARCHIVO\" ]` pregunta si una ruta es un archivo normal. `then` abre el bloque "
            "para ese caso y `fi` lo cierra."
        ),
        "example": (
            "```bash\nCONFIG=/etc/hosts\nif [ -f \"$CONFIG\" ]; then\n  echo \"Encontrado\"\nfi\n```\n\n"
            "La condición consulta la ruta de `CONFIG`. Solo cuando es verdadera se alcanza el "
            "echo; `fi` marca el final de la decisión."
        ),
        "task": "1. Conserva `INVENTARIO` y el `if`.\n2. Añade un `echo` dentro.\n3. Muestra `Inventario disponible`.",
        "hints": ["El echo va entre `then` y `fi`.", "No añadas else todavía.", "La condición ya usa -f."],
        "objectives": ["Leer un if", "Comprobar con -f", "Situar una orden en then"],
        "starter": "#!/usr/bin/env bash\n\nINVENTARIO=/srv/inventario.txt\nif [ -f \"$INVENTARIO\" ]; then\n  # Añade el mensaje del reto.\nfi\n",
        "solution": "#!/usr/bin/env bash\n\nINVENTARIO=/srv/inventario.txt\nif [ -f \"$INVENTARIO\" ]; then\n  echo \"Inventario disponible\"\nfi\n",
        "tests": [
            _test("Sintaxis válida", "bash.syntax_valid", {}),
            _test("Variable INVENTARIO", "bash.variable_assigned", {"name": "INVENTARIO"}),
            _test("Condición if", "bash.node_kind", {"kind": "if"}),
            _test("Uso de echo", "bash.command_used", {"command": "echo", "args": ["Inventario disponible"]}),
        ],
    },
    {
        "slug": "07-codigos-de-salida",
        "title": "07 · Elegir un mensaje con if y else",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 160,
        "theory": (
            "`else` añade el camino cuando la condición de un `if` no se cumple. `[ -d "
            "\"$BACKUP_DIR\" ]` comprueba una carpeta. Con las dos ramas el script informa "
            "tanto si la encuentra como si no la encuentra."
        ),
        "example": (
            "```bash\nDESTINO=/srv/copias\nif [ -d \"$DESTINO\" ]; then\n  echo \"Destino listo\"\nelse\n  echo \"Destino pendiente\"\nfi\n```\n\n"
            "La rama tras `then` se usa cuando existe la carpeta. La rama tras `else` cubre el "
            "otro caso: en una revisión real se alcanzaría solo una de ellas."
        ),
        "task": "1. Conserva la condición sobre `BACKUP_DIR`.\n2. Completa `then` con `Carpeta lista`.\n3. Completa `else` con `Carpeta pendiente`.",
        "hints": ["Hay un echo en cada rama.", "No cambies -d.", "Deja fi al final."],
        "objectives": ["Añadir else", "Comprobar con -d", "Distinguir dos resultados"],
        "starter": "#!/usr/bin/env bash\n\nBACKUP_DIR=/srv/copias\nif [ -d \"$BACKUP_DIR\" ]; then\n  # Muestra Carpeta lista.\nelse\n  # Muestra Carpeta pendiente.\nfi\n",
        "solution": "#!/usr/bin/env bash\n\nBACKUP_DIR=/srv/copias\nif [ -d \"$BACKUP_DIR\" ]; then\n  echo \"Carpeta lista\"\nelse\n  echo \"Carpeta pendiente\"\nfi\n",
        "tests": [
            _test("Sintaxis válida", "bash.syntax_valid", {}),
            _test("Variable BACKUP_DIR", "bash.variable_assigned", {"name": "BACKUP_DIR"}),
            _test("Decisión if", "bash.node_kind", {"kind": "if"}),
            _test("Uso de echo", "bash.command_used", {"command": "echo"}),
        ],
    },
    {
        "slug": "08-plan-de-copia",
        "title": "08 · Repetir nombres con for",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 170,
        "theory": (
            "Un bucle `for` repite un bloque por cada elemento de una lista. La palabra tras "
            "`for` representa el elemento actual; `do` abre el bloque y `done` lo cierra. Así "
            "evitamos copiar la misma orden para una lista corta."
        ),
        "example": (
            "```bash\nfor SERVICIO in web ssh; do\n  echo \"Revisar: $SERVICIO\"\ndone\n```\n\n"
            "La primera vuelta guarda `web` en `SERVICIO` y la segunda guarda `ssh`. El mismo "
            "echo se repite usando el valor actual."
        ),
        "task": "1. Conserva la lista y el `for`.\n2. Completa el `echo` dentro.\n3. Muestra `Archivo:` seguido de `$FICHERO`.",
        "hints": ["El echo va entre do y done.", "`$FICHERO` cambia en cada vuelta.", "Usa comillas dobles."],
        "objectives": ["Reconocer un for", "Usar la variable de vuelta", "Repetir una salida"],
        "starter": "#!/usr/bin/env bash\n\nfor FICHERO in acceso.log error.log; do\n  # Muestra Archivo: seguido del elemento actual.\ndone\n",
        "solution": "#!/usr/bin/env bash\n\nfor FICHERO in acceso.log error.log; do\n  echo \"Archivo: $FICHERO\"\ndone\n",
        "tests": [
            _test("Sintaxis válida", "bash.syntax_valid", {}),
            _test("Bucle for", "bash.node_kind", {"kind": "for"}),
            _test("Variable FICHERO", "bash.variable_assigned", {"name": "FICHERO"}),
            _test("Uso de echo", "bash.command_used", {"command": "echo", "args": ["Archivo: $FICHERO"]}),
        ],
    },
    {
        "slug": "09-permisos-del-script",
        "title": "09 · Preguntar a grep con if",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 180,
        "theory": (
            "Algunas órdenes indican si encontraron lo buscado mediante su resultado. `grep -q "
            "TEXTO ARCHIVO` busca sin mostrar líneas; en un `if`, `then` se usa si encuentra "
            "el texto y `else` si no lo encuentra."
        ),
        "example": (
            "```bash\nLOG=/var/log/app.log\nif grep -q ERROR \"$LOG\"; then\n  echo \"Hay errores\"\nelse\n  echo \"Sin errores\"\nfi\n```\n\n"
            "`-q` evita imprimir coincidencias. El if toma el resultado de `grep` para decidir "
            "cuál de los dos mensajes mostraría."
        ),
        "task": "1. Conserva `LOG_FILE` y `if grep -q`.\n2. Completa la primera rama con `Aviso encontrado`.\n3. Completa la segunda con `Sin avisos`.",
        "hints": ["No quites -q.", "Añade un echo bajo then y otro bajo else.", "WARNING ya está preparado."],
        "objectives": ["Usar grep -q", "Relacionar grep e if", "Informar dos resultados"],
        "starter": "#!/usr/bin/env bash\n\nLOG_FILE=/var/log/app.log\nif grep -q WARNING \"$LOG_FILE\"; then\n  # Muestra Aviso encontrado.\nelse\n  # Muestra Sin avisos.\nfi\n",
        "solution": "#!/usr/bin/env bash\n\nLOG_FILE=/var/log/app.log\nif grep -q WARNING \"$LOG_FILE\"; then\n  echo \"Aviso encontrado\"\nelse\n  echo \"Sin avisos\"\nfi\n",
        "tests": [
            _test("Sintaxis válida", "bash.syntax_valid", {}),
            _test("Variable LOG_FILE", "bash.variable_assigned", {"name": "LOG_FILE"}),
            _test("Búsqueda con grep", "bash.command_used", {"command": "grep", "args": ["-q", "WARNING", "$LOG_FILE"]}),
            _test("Uso de echo", "bash.command_used", {"command": "echo", "args": ["Aviso encontrado"]}),
        ],
    },
    {
        "slug": "10-pipeline-awk-y-orden",
        "title": "10 · Conectar órdenes con un pipeline",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 190,
        "theory": (
            "El símbolo `|` conecta la salida de una orden con la entrada de la siguiente. En "
            "un pipeline, `grep` puede seleccionar líneas y `sort` ordenarlas. Cada orden hace "
            "un paso pequeño y visible."
        ),
        "example": (
            "```bash\ngrep INFO \"$LOG_FILE\" | sort\n```\n\n"
            "`grep` entrega las líneas con `INFO`. La barra vertical se las pasa a `sort`, que "
            "las ordena. El ejemplo busca un texto distinto al ejercicio."
        ),
        "task": "1. Conserva `LOG_FILE`.\n2. Escribe `grep WARNING` sobre ese archivo.\n3. Conecta su salida con `sort` usando `|`.",
        "hints": ["Primero `grep WARNING \"$LOG_FILE\"`.", "Después `|`.", "La última orden es sort."],
        "objectives": ["Reconocer un pipeline", "Filtrar con grep", "Ordenar con sort"],
        "starter": "#!/usr/bin/env bash\n\nLOG_FILE=/var/log/app.log\n# Escribe el pipeline grep WARNING ... | sort.\n",
        "solution": "#!/usr/bin/env bash\n\nLOG_FILE=/var/log/app.log\ngrep WARNING \"$LOG_FILE\" | sort\n",
        "tests": [
            _test("Sintaxis válida", "bash.syntax_valid", {}),
            _test("Pipeline", "bash.node_kind", {"kind": "pipeline"}),
            _test("Filtro con grep", "bash.command_used", {"command": "grep", "args": ["WARNING", "$LOG_FILE"]}),
            _test("Ordenación con sort", "bash.command_used", {"command": "sort"}),
        ],
    },
    {
        "slug": "11-case-de-operacion",
        "title": "11 · Agrupar un paso en una función",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 200,
        "theory": (
            "Una función agrupa instrucciones bajo un nombre. Se declara con `nombre() {` y "
            "termina con `}`. Después se llama escribiendo ese nombre. Esto permite nombrar un "
            "paso antes de reutilizarlo en scripts más largos."
        ),
        "example": (
            "```bash\nmostrar_equipo() {\n  echo \"Equipo: $EQUIPO\"\n}\nmostrar_equipo\n```\n\n"
            "Las llaves contienen lo que hará `mostrar_equipo`. La última línea llama a la "
            "función; el echo no queda suelto en el script principal."
        ),
        "task": "1. Conserva `SOURCE_DIR`, la función y su llamada.\n2. Añade un `printf` dentro.\n3. Muestra `Origen: ` seguido de `$SOURCE_DIR`.",
        "hints": ["El printf va entre las llaves.", "Usa `Origen: %s\\n`.", "No cambies mostrar_origen."],
        "objectives": ["Reconocer una función", "Escribir dentro de ella", "Llamarla por nombre"],
        "starter": "#!/usr/bin/env bash\n\nSOURCE_DIR=/srv/datos\nmostrar_origen() {\n  # Muestra Origen: seguido de SOURCE_DIR con printf.\n}\n\nmostrar_origen\n",
        "solution": "#!/usr/bin/env bash\n\nSOURCE_DIR=/srv/datos\nmostrar_origen() {\n  printf 'Origen: %s\\n' \"$SOURCE_DIR\"\n}\n\nmostrar_origen\n",
        "tests": [
            _test("Sintaxis válida", "bash.syntax_valid", {}),
            _test("Función Bash", "bash.node_kind", {"kind": "function"}),
            _test("Variable SOURCE_DIR", "bash.variable_assigned", {"name": "SOURCE_DIR"}),
            _test("Uso de printf", "bash.command_used", {"command": "printf", "args": ["Origen: %s\\n", "$SOURCE_DIR"]}),
        ],
    },
    {
        "slug": "12-rutina-integrada",
        "title": "12 · Repaso: listar rutas preparadas",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 220,
        "theory": (
            "Este reto no añade órdenes nuevas: repasa variables, rutas, comillas, `printf` y "
            "`for`. Una variable puede guardar la carpeta común y otra representa cada nombre "
            "de la lista; la plantilla de printf los muestra juntos en cada vuelta."
        ),
        "example": (
            "```bash\nCARPETA=/var/log\nfor ARCHIVO in auth.log kern.log; do\n  printf 'Revisar: %s/%s\\n' \"$CARPETA\" \"$ARCHIVO\"\ndone\n```\n\n"
            "`CARPETA` no cambia; `ARCHIVO` toma un nombre en cada vuelta. Los dos `%s` de "
            "printf reciben esas variables en el mismo orden y forman una ruta visible."
        ),
        "task": "1. Conserva `DIRECTORIO` y el `for` preparados.\n2. Añade un `printf` dentro del bucle.\n3. Muestra `Ruta: ` seguido de `$DIRECTORIO/$FICHERO`.",
        "hints": ["El printf va entre do y done.", "Usa `Ruta: %s/%s\\n`.", "Pasa primero DIRECTORIO y después FICHERO."],
        "objectives": ["Reutilizar variables y rutas", "Reutilizar un bucle for", "Dar formato a una ruta"],
        "starter": "#!/usr/bin/env bash\n\nDIRECTORIO=/srv/informes\nfor FICHERO in estado.txt alertas.txt; do\n  # Muestra Ruta: DIRECTORIO/FICHERO con printf.\ndone\n",
        "solution": "#!/usr/bin/env bash\n\nDIRECTORIO=/srv/informes\nfor FICHERO in estado.txt alertas.txt; do\n  printf 'Ruta: %s/%s\\n' \"$DIRECTORIO\" \"$FICHERO\"\ndone\n",
        "tests": [
            _test("Sintaxis válida", "bash.syntax_valid", {}),
            _test("Bucle de repaso", "bash.node_kind", {"kind": "for"}),
            _test("Variable DIRECTORIO", "bash.variable_assigned", {"name": "DIRECTORIO"}),
            _test("Uso de printf", "bash.command_used", {"command": "printf", "args": ["Ruta: %s/%s\\n", "$DIRECTORIO", "$FICHERO"]}),
        ],
    },
]


class Command(BaseCommand):
    help = "Crea el itinerario local de 12 retos Bash para apoyo transversal de ASIR (módulo 0378)."

    def add_arguments(self, parser):
        parser.add_argument("--owner", required=True, help="Usuario profesor o administrador propietario del contenido.")
        parser.add_argument("--cohort", default="2ASIR", help="Grupo al que se asignan los retos (por defecto: 2ASIR).")
        parser.add_argument("--academic-year", default=None, help="Curso académico; si se omite se calcula según la fecha del servidor.")

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
            name=options["cohort"], academic_year=year, defaults={"active": True, "track": Cohort.Track.BASH}
        )
        ensure_cohort_track(cohort, Cohort.Track.BASH)
        if owner.role == User.Role.TEACHER and not owner.is_superuser:
            TeachingAssignment.objects.get_or_create(cohort=cohort, teacher=owner, defaults={"active": True})

        course, course_created = Course.objects.get_or_create(
            slug=TRACK_SLUG,
            defaults={
                "title": "Laboratorio Bash para Seguridad · ASIR",
                "description": "Fundamentos de Bash: mensajes, variables, comillas, rutas, printf, decisiones, bucles, grep, pipelines, funciones y repaso, como apoyo transversal al módulo 0378.",
                "created_by": owner,
                "active": True,
            },
        )
        if not course_created:
            course.title = "Laboratorio Bash para Seguridad · ASIR"
            course.description = "Fundamentos de Bash: mensajes, variables, comillas, rutas, printf, decisiones, bucles, grep, pipelines, funciones y repaso, como apoyo transversal al módulo 0378."
            course.save(update_fields=["title", "description", "updated_at"])

        module, module_created = Module.objects.get_or_create(
            course=course,
            position=1,
            defaults={
                "title": "De cero a tus primeras automatizaciones",
                "description": "Una ruta guiada: fundamentos, mensajes, variables, comillas, rutas, printf, if, for, grep, pipeline, función y repaso.",
                "weight": 100,
            },
        )
        if not module_created:
            module.title = "De cero a tus primeras automatizaciones"
            module.description = "Una ruta guiada: fundamentos, mensajes, variables, comillas, rutas, printf, if, for, grep, pipeline, función y repaso."
            module.save(update_fields=["title", "description"])

        created_versions = existing_versions = migrated_links = archived_assignments = 0
        for position, item in enumerate(CHALLENGES, start=1):
            activity, _ = Activity.objects.get_or_create(
                module=module,
                slug=item["slug"],
                defaults={"title": item["title"], "kind": Activity.Kind.CODE, "status": Activity.Status.PUBLISHED, "created_by": owner},
            )
            current_version = activity.current_version
            if activity.versions.filter(version_number__gt=BASH_CATALOG_VERSION).exists():
                existing_versions += 1
                continue
            if activity.position != position:
                activity.position = position
                activity.save(update_fields=["position", "updated_at"])

            instructions = (
                "## Antes de empezar\nEl editor ya tiene un archivo `script.sh`; no necesitas crear "
                "carpetas ni descargar nada. En esta actividad el corrector analiza el texto y no "
                "ejecuta las órdenes.\n\n"
                f"## Concepto\n{item['theory']}\n\n"
                f"## Ejemplo explicado\n{item['example']}\n\n"
                f"## Ejercicio\n{item['task']}\n\n"
                "> Las órdenes son práctica de escritura. No las pruebes sobre un sistema real para este reto."
            )
            version, version_created = ActivityVersion.objects.get_or_create(
                activity=activity,
                version_number=BASH_CATALOG_VERSION,
                defaults={
                    "language": ActivityVersion.Language.BASH,
                    "difficulty": item["difficulty"],
                    "xp_reward": item["xp"],
                    "hints": item["hints"],
                    "instructions": instructions,
                    "objectives": item["objectives"],
                    "learning_outcomes": [],
                    "assessment_criteria": [],
                    "professional_module_code": "0378",
                    "curriculum_scope": "Apoyo transversal ASIR",
                    "curriculum_edition": "local-2026",
                    "curriculum_unit": "",
                    "curriculum_source": "",
                    "starter_files": {"bash": item["starter"]},
                    "reference_solution": {"bash": item["solution"]},
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
            if current_version is None or current_version.version_number < version.version_number:
                activity.current_version = version
                activity.status = Activity.Status.PUBLISHED
                activity.save(update_fields=["current_version", "status", "updated_at"])

            if not version.assignments.exists():
                for position, (name, test_type, definition, points, visibility) in enumerate(item["tests"]):
                    TestCase.objects.get_or_create(
                        activity_version=version,
                        name=name,
                        defaults={"type": test_type, "definition": definition, "points": points, "visibility": visibility, "feedback": "Revisa la estructura indicada en el enunciado.", "position": position},
                    )
            assignment, assignment_created, upgrade = get_or_create_catalog_revision_assignment(
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
                previous_catalog_titles=(V2_TITLES[item["slug"]],),
            )
            if assignment_created and not assignment.title_override:
                assignment.title_override = item["title"]
                assignment.save(update_fields=["title_override"])
            migrated_links += upgrade["migrated_links"]
            archived_assignments += upgrade["archived_assignments"]

        self.stdout.write(self.style.SUCCESS(
            f"Itinerario Bash v{BASH_CATALOG_VERSION} listo: {len(CHALLENGES)} retos, grupo {cohort.name}, "
            f"{created_versions} versiones nuevas y {existing_versions} ya existentes. Actualizados "
            f"{migrated_links} vínculos y archivadas {archived_assignments} asignaciones anteriores."
        ))
        self.stdout.write("No se han creado alumnos ni contraseñas; el catálogo es contenido formativo local.")
