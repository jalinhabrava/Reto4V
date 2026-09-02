"""Seed the local Bash support track for second-year ASIR.

The catalogue is deliberately curriculum-neutral: it belongs to module 0378
as transversal scripting support and does not claim to implement a complete
RA/CE.  The examples are analysed statically by the application and are not
commands to run on a real server.
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
BASH_CATALOG_VERSION = 2


def _test(name, test_type, definition, points=1, visibility=TestCase.Visibility.PUBLIC):
    return (name, test_type, definition, points, visibility)


CHALLENGES = [
    {
        "slug": "01-variables-y-salida",
        "title": "01 · Mi primer script",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 100,
        "theory": "Bash es una forma de dar instrucciones al ordenador. Un script es un archivo de texto que guarda esas instrucciones para leerlas juntas.",
        "task": "1. Escribe un saludo con `echo`.\n2. Escribe una despedida con `printf`.",
        "hints": [
            "Empieza por `#!/usr/bin/env bash`.",
            "`echo \"Hola\"` muestra un texto sencillo.",
            "`printf '%s\\n' \"Texto\"` muestra una línea con formato controlado.",
        ],
        "objectives": [
            "Reconocer un script Bash",
            "Mostrar texto en la pantalla",
            "Distinguir echo y printf",
        ],
        "starter": "#!/usr/bin/env bash\n\n# Escribe debajo un saludo con echo y una despedida con printf.\n",
        "solution": "#!/usr/bin/env bash\necho \"Hola, Bash\"\nprintf '%s\\n' \"Fin del primer script\"\n",
        "tests": [
            _test("Sintaxis válida", "bash.syntax_valid", {}),
            _test("Shebang Bash", "bash.shebang", {"expected": "/usr/bin/env bash"}),
            _test("Saludo con echo", "bash.command_used", {"command": "echo"}),
            _test("Despedida con printf", "bash.command_used", {"command": "printf"}),
        ],
    },
    {
        "slug": "02-condiciones-y-rutas",
        "title": "02 · Guardar un dato en una variable",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 110,
        "theory": "Una variable es una caja con nombre donde guardamos un dato. Después podemos usar ese dato en un mensaje u otra instrucción.",
        "task": "1. Crea una variable llamada `NOMBRE`.\n2. Guarda dentro un nombre.\n3. Saluda usando el contenido de la variable.",
        "hints": [
            "Una asignación sencilla es `NOMBRE=\"Aula\"`.",
            "No pongas espacios alrededor del signo `=`.",
            "Para usar el contenido escribe `\"$NOMBRE\"`.",
        ],
        "objectives": [
            "Crear una variable Bash",
            "Guardar texto en una variable",
            "Usar una variable en printf",
        ],
        "starter": "#!/usr/bin/env bash\n\n# Crea NOMBRE y muestra un saludo usando su contenido.\n",
        "solution": "#!/usr/bin/env bash\nNOMBRE=\"Aula ASIR\"\nprintf 'Hola, %s\\n' \"$NOMBRE\"\n",
        "tests": [
            _test("Sintaxis válida", "bash.syntax_valid", {}),
            _test("Shebang Bash", "bash.shebang", {"interpreter": "bash"}),
            _test("Variable NOMBRE", "bash.variable_assigned", {"name": "NOMBRE"}),
            _test("Saludo con printf", "bash.command_used", {"command": "printf"}),
        ],
    },
    {
        "slug": "03-bucle-de-registros",
        "title": "03 · Guardar una carpeta y un archivo",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 120,
        "theory": "En tareas de sistemas trabajamos continuamente con rutas. Guardarlas en variables hace que el script sea más fácil de cambiar y revisar.",
        "task": "1. Crea la variable `CARPETA`.\n2. Crea la variable `ARCHIVO`.\n3. Muestra la ruta completa uniendo las dos partes.",
        "hints": [
            "Puedes guardar `laboratorio` en CARPETA y `notas.txt` en ARCHIVO.",
            "Una variable se escribe sin espacios: `CARPETA=\"laboratorio\"`.",
            "Usa `printf` para mostrar las dos variables.",
        ],
        "objectives": [
            "Guardar una carpeta en una variable",
            "Guardar un nombre de archivo en una variable",
            "Preparar una ruta a partir de sus partes",
        ],
        "starter": "#!/usr/bin/env bash\n\n# Guarda una carpeta y un archivo en variables y muestra la ruta.\n",
        "solution": "#!/usr/bin/env bash\nCARPETA=\"laboratorio\"\nARCHIVO=\"notas.txt\"\nprintf '%s/%s\\n' \"$CARPETA\" \"$ARCHIVO\"\n",
        "tests": [
            _test("Sintaxis válida", "bash.syntax_valid", {}),
            _test("Shebang Bash", "bash.shebang", {"expected": "/usr/bin/env bash"}),
            _test("Variable de carpeta", "bash.variable_assigned", {"name": "CARPETA"}),
            _test("Variable de archivo", "bash.variable_assigned", {"name": "ARCHIVO"}),
        ],
    },
    {
        "slug": "04-funciones-reutilizables",
        "title": "04 · Recibir un dato",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 130,
        "theory": "Un script puede recibir datos cuando lo llamamos. El primer dato se conoce como `$1`; así podemos reutilizar el mismo script con nombres diferentes.",
        "task": "1. Usa el primer dato recibido para saludar.\n2. Si no llega ningún dato, utiliza `alumno` como nombre de reserva.",
        "hints": [
            "Puedes preparar el dato con `NOMBRE=\"${1:-alumno}\"`.",
            "El símbolo `${1:-alumno}` usa `alumno` cuando no hay primer dato.",
            "Muestra NOMBRE con `printf`.",
        ],
        "objectives": [
            "Reconocer el primer argumento de un script",
            "Usar un valor de reserva",
            "Reutilizar un script con distintos nombres",
        ],
        "starter": "#!/usr/bin/env bash\n\n# $1 es el primer dato que recibe el script.\nNOMBRE=\"${1:-alumno}\"\n# Muestra NOMBRE con un saludo.\n",
        "solution": "#!/usr/bin/env bash\nNOMBRE=\"${1:-alumno}\"\nprintf 'Hola, %s\\n' \"$NOMBRE\"\n",
        "tests": [
            _test("Sintaxis válida", "bash.syntax_valid", {}),
            _test("Shebang Bash", "bash.shebang", {"interpreter": "bash"}),
            _test("Variable NOMBRE", "bash.variable_assigned", {"name": "NOMBRE"}),
            _test("Saludo con printf", "bash.command_used", {"command": "printf"}),
        ],
    },
    {
        "slug": "05-pipelines-de-registros",
        "title": "05 · Tomar una decisión con if",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 140,
        "theory": "Una condición permite que el script elija qué hacer. Con `if` podemos comprobar si un archivo existe antes de trabajar con él.",
        "task": "1. Guarda el nombre `datos.txt` en `ARCHIVO`.\n2. Completa un `if` que compruebe si existe el archivo.\n3. Muestra un mensaje distinto en cada caso.",
        "hints": [
            "La comprobación de archivo tiene esta forma: `[ -f \"$ARCHIVO\" ]`.",
            "La estructura se cierra con `fi`.",
            "Pon una orden `printf` dentro de cada camino.",
        ],
        "objectives": [
            "Leer una condición if",
            "Comprobar si existe un archivo",
            "Separar el caso verdadero del caso falso",
        ],
        "starter": "#!/usr/bin/env bash\n\nARCHIVO=\"datos.txt\"\n# Completa el if para informar si existe ARCHIVO.\n",
        "solution": "#!/usr/bin/env bash\nARCHIVO=\"datos.txt\"\nif [ -f \"$ARCHIVO\" ]; then\n  printf 'Existe: %s\\n' \"$ARCHIVO\"\nelse\n  printf 'No existe: %s\\n' \"$ARCHIVO\"\nfi\n",
        "tests": [
            _test("Sintaxis válida", "bash.syntax_valid", {}),
            _test("Variable ARCHIVO", "bash.variable_assigned", {"name": "ARCHIVO"}),
            _test("Decisión if", "bash.node_kind", {"kind": "if"}),
            _test("Mensaje de comprobación", "bash.command_used", {"command": "printf"}),
        ],
    },
    {
        "slug": "06-parametros-posicionales",
        "title": "06 · Repetir una tarea con for",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 150,
        "theory": "Un bucle repite una tarea sin copiar la misma orden muchas veces. `for` sirve para recorrer varios nombres, archivos o elementos.",
        "task": "1. Conserva la lista de archivos preparada.\n2. Completa el bucle para mostrar el nombre de cada archivo.\n3. Usa `FICHERO`, que cambia en cada vuelta.",
        "hints": [
            "La estructura termina con `done`.",
            "Escribe `printf` dentro del bucle, antes de `done`.",
            "`FICHERO` representa el elemento actual de la lista.",
        ],
        "objectives": [
            "Reconocer la estructura for",
            "Recorrer varios elementos",
            "Usar la variable de control del bucle",
        ],
        "starter": "#!/usr/bin/env bash\n\nfor FICHERO in \"uno.txt\" \"dos.txt\"; do\n  # Muestra cada nombre.\ndone\n",
        "solution": "#!/usr/bin/env bash\nfor FICHERO in \"uno.txt\" \"dos.txt\"; do\n  printf '%s\\n' \"$FICHERO\"\ndone\n",
        "tests": [
            _test("Sintaxis válida", "bash.syntax_valid", {}),
            _test("Bucle for", "bash.node_kind", {"kind": "for"}),
            _test("Variable del bucle", "bash.variable_assigned", {"name": "FICHERO"}),
            _test("Salida de cada vuelta", "bash.command_used", {"command": "printf"}),
        ],
    },
    {
        "slug": "07-codigos-de-salida",
        "title": "07 · Repetir hasta terminar con while",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 160,
        "theory": "`while` repite unas instrucciones mientras se cumple una condición. Es útil cuando queremos avanzar paso a paso hasta llegar a un límite.",
        "task": "1. Usa `CONTADOR` para mostrar tres números.\n2. Aumenta el contador en cada vuelta.\n3. Haz que el bucle termine al llegar al límite.",
        "hints": [
            "La estructura se cierra con `done`.",
            "La condición puede ser `[ \"$CONTADOR\" -le 3 ]`.",
            "Aumenta el valor con `CONTADOR=$((CONTADOR + 1))`.",
        ],
        "objectives": [
            "Reconocer la estructura while",
            "Cambiar una variable dentro de un bucle",
            "Evitar un bucle que no termina",
        ],
        "starter": "#!/usr/bin/env bash\n\nCONTADOR=1\nwhile [ \"$CONTADOR\" -le 3 ]; do\n  # Muestra el contador y aumenta su valor.\ndone\n",
        "solution": "#!/usr/bin/env bash\nCONTADOR=1\nwhile [ \"$CONTADOR\" -le 3 ]; do\n  printf 'Vuelta %s\\n' \"$CONTADOR\"\n  CONTADOR=$((CONTADOR + 1))\ndone\n",
        "tests": [
            _test("Sintaxis válida", "bash.syntax_valid", {}),
            _test("Bucle while", "bash.node_kind", {"kind": "while"}),
            _test("Variable CONTADOR", "bash.variable_assigned", {"name": "CONTADOR"}),
            _test("Salida de cada vuelta", "bash.command_used", {"command": "printf"}),
        ],
    },
    {
        "slug": "08-plan-de-copia",
        "title": "08 · Crear una función sencilla",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 180,
        "theory": "Una función agrupa varias instrucciones bajo un nombre. Así podemos llamar a la misma tarea cuando la necesitemos sin repetir todo el código.",
        "task": "1. Crea la función `mostrar_ruta`.\n2. Haz que muestre la variable `RUTA`.\n3. Llama a la función después de declararla.",
        "hints": [
            "Una función Bash puede escribirse como `mostrar_ruta() { ... }`.",
            "La orden `printf` debe quedar dentro de las llaves.",
            "Después de la función puedes escribir `mostrar_ruta` para llamarla.",
        ],
        "objectives": [
            "Declarar una función Bash",
            "Poner instrucciones dentro de una función",
            "Llamar a una función por su nombre",
        ],
        "starter": "#!/usr/bin/env bash\n\nRUTA=\"laboratorio\"\n# Crea mostrar_ruta y llama a la función.\n",
        "solution": "#!/usr/bin/env bash\nRUTA=\"laboratorio\"\nmostrar_ruta() {\n  printf 'Ruta: %s\\n' \"$RUTA\"\n}\nmostrar_ruta\n",
        "tests": [
            _test("Sintaxis válida", "bash.syntax_valid", {}),
            _test("Función Bash", "bash.node_kind", {"kind": "function"}),
            _test("Variable RUTA", "bash.variable_assigned", {"name": "RUTA"}),
            _test("Salida de la función", "bash.command_used", {"command": "printf"}),
        ],
    },
    {
        "slug": "09-permisos-del-script",
        "title": "09 · Filtrar información con un pipeline",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 190,
        "theory": "Un pipeline pasa la salida de una orden a la siguiente. Separar cada paso ayuda a leer y revisar un informe de registros.",
        "task": "1. Guarda la ruta en `LOG_FILE`.\n2. Busca las líneas que contienen `warning`.\n3. Usa `|` para pasar el resultado a `sort`.",
        "hints": [
            "Guarda la ruta en `LOG_FILE`.",
            "La primera orden puede ser `grep -i warning \"$LOG_FILE\"`.",
            "Añade `| sort` al final para ordenar las líneas encontradas.",
        ],
        "objectives": [
            "Reconocer un pipeline",
            "Filtrar texto con grep",
            "Ordenar la salida con sort",
        ],
        "starter": "#!/usr/bin/env bash\n\nLOG_FILE=\"laboratorio/app.log\"\n# Filtra y ordena las líneas de warning.\n",
        "solution": "#!/usr/bin/env bash\nLOG_FILE=\"laboratorio/app.log\"\ngrep -i warning \"$LOG_FILE\" | sort\n",
        "tests": [
            _test("Sintaxis válida", "bash.syntax_valid", {}),
            _test("Pipeline", "bash.node_kind", {"kind": "pipeline"}),
            _test("Filtro con grep", "bash.command_used", {"command": "grep"}),
            _test("Ordenación con sort", "bash.command_used", {"command": "sort"}),
        ],
    },
    {
        "slug": "10-pipeline-awk-y-orden",
        "title": "10 · Preparar una carpeta de copias",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 200,
        "theory": "Antes de guardar una copia necesitamos un lugar para ella. Comprobar y crear una carpeta evita continuar con una ruta que no está preparada.",
        "task": "1. Comprueba si existe `BACKUP_DIR`.\n2. Si no existe, prepara la carpeta.\n3. Usa `mkdir -p` para crearla.",
        "hints": [
            "Usa `[ -d \"$BACKUP_DIR\" ]` para comprobar una carpeta.",
            "La negación se escribe `[ ! -d \"$BACKUP_DIR\" ]`.",
            "`mkdir -p` prepara también las carpetas intermedias.",
        ],
        "objectives": [
            "Comprobar si existe una carpeta",
            "Preparar una ruta de copias",
            "Usar mkdir de forma cuidadosa",
        ],
        "starter": "#!/usr/bin/env bash\n\nBACKUP_DIR=\"laboratorio/copias\"\n# Comprueba y prepara la carpeta.\n",
        "solution": "#!/usr/bin/env bash\nBACKUP_DIR=\"laboratorio/copias\"\nif [ ! -d \"$BACKUP_DIR\" ]; then\n  mkdir -p \"$BACKUP_DIR\"\nfi\n",
        "tests": [
            _test("Sintaxis válida", "bash.syntax_valid", {}),
            _test("Variable de copias", "bash.variable_assigned", {"name": "BACKUP_DIR"}),
            _test("Comprobación de carpeta", "bash.node_kind", {"kind": "if"}),
            _test("Crear carpeta", "bash.command_used", {"command": "mkdir"}),
        ],
    },
    {
        "slug": "11-case-de-operacion",
        "title": "11 · Preparar una copia con tar",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 220,
        "theory": "Una copia debe indicar qué carpeta se guarda y qué archivo la contiene. `tar` puede reunir una carpeta en un archivo comprimido.",
        "task": "1. Declara `SOURCE_DIR` y `ARCHIVE`.\n2. Crea la función `preparar_copia`.\n3. Si existe `SOURCE_DIR`, prepara `ARCHIVE` con `tar -czf`.",
        "hints": [
            "Declara primero `SOURCE_DIR` y `ARCHIVE`.",
            "La orden es `tar -czf \"$ARCHIVE\" \"$SOURCE_DIR\"`.",
            "Coloca `tar` dentro del `if` para revisar la fuente antes de copiar.",
        ],
        "objectives": [
            "Separar origen y destino de una copia",
            "Usar una función para una tarea concreta",
            "Comprobar la fuente antes de preparar tar",
        ],
        "starter": "#!/usr/bin/env bash\n\nSOURCE_DIR=\"laboratorio/fuente\"\nARCHIVE=\"laboratorio/copia.tgz\"\n# Crea preparar_copia con una comprobación.\n",
        "solution": "#!/usr/bin/env bash\nSOURCE_DIR=\"laboratorio/fuente\"\nARCHIVE=\"laboratorio/copia.tgz\"\npreparar_copia() {\n  if [ -d \"$SOURCE_DIR\" ]; then\n    tar -czf \"$ARCHIVE\" \"$SOURCE_DIR\"\n  fi\n}\n",
        "tests": [
            _test("Sintaxis válida", "bash.syntax_valid", {}),
            _test("Función de copia", "bash.node_kind", {"kind": "function"}),
            _test("Comprobación de fuente", "bash.node_kind", {"kind": "if"}),
            _test("Orden tar", "bash.command_used", {"command": "tar", "args": ["-czf", "$ARCHIVE", "$SOURCE_DIR"]}),
        ],
    },
    {
        "slug": "12-rutina-integrada",
        "title": "12 · Crear y verificar una copia",
        "difficulty": ActivityVersion.Difficulty.ADVANCED,
        "xp": 240,
        "theory": "Una rutina de copia debe revisar la fuente, preparar el archivo y dejar una forma de comprobarlo. Este reto reúne lo aprendido; el corrector solo analiza el texto.",
        "task": "1. Comprueba `SOURCE_DIR` dentro de `crear_copia`.\n2. Prepara `ARCHIVE` con `tar`.\n3. Calcula su huella con `sha256sum`.\n4. No uses red, `sudo` ni borrados.",
        "hints": [
            "Conserva las dos variables de ruta que ya están preparadas.",
            "El `if` debe envolver `tar` para no copiar una fuente inexistente.",
            "`sha256sum \"$ARCHIVE\"` deja una huella que se puede revisar después.",
        ],
        "objectives": [
            "Combinar variables, condiciones y funciones",
            "Preparar una copia comprimida",
            "Añadir una verificación mediante huella",
        ],
        "starter": "#!/usr/bin/env bash\n\nSOURCE_DIR=\"laboratorio/fuente\"\nARCHIVE=\"laboratorio/backup-final.tgz\"\n# Completa crear_copia: comprueba, crea y verifica.\n",
        "solution": "#!/usr/bin/env bash\nSOURCE_DIR=\"laboratorio/fuente\"\nARCHIVE=\"laboratorio/backup-final.tgz\"\ncrear_copia() {\n  if [ -d \"$SOURCE_DIR\" ]; then\n    tar -czf \"$ARCHIVE\" \"$SOURCE_DIR\"\n    sha256sum \"$ARCHIVE\"\n  else\n    printf 'No existe la fuente: %s\\n' \"$SOURCE_DIR\"\n  fi\n}\ncrear_copia\n",
        "tests": [
            _test("Sintaxis válida", "bash.syntax_valid", {}),
            _test("Comprobación de fuente", "bash.node_kind", {"kind": "if"}),
            _test("Orden tar", "bash.command_used", {"command": "tar", "args": ["-czf", "$ARCHIVE", "$SOURCE_DIR"]}),
            _test("Verificación sha256sum", "bash.command_used", {"command": "sha256sum"}),
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
            name=self._academic_year_name(options.get("academic_year")),
            defaults={"active": True},
        )
        cohort, _ = Cohort.objects.get_or_create(
            name=options["cohort"],
            academic_year=year,
            defaults={"active": True, "track": Cohort.Track.BASH},
        )
        ensure_cohort_track(cohort, Cohort.Track.BASH)
        if owner.role == User.Role.TEACHER and not owner.is_superuser:
            TeachingAssignment.objects.get_or_create(cohort=cohort, teacher=owner, defaults={"active": True})

        course, course_created = Course.objects.get_or_create(
            slug=TRACK_SLUG,
            defaults={
                "title": "Laboratorio Bash para Seguridad · ASIR",
                "description": "Retos progresivos desde el primer script hasta la preparación y verificación estructural de copias de seguridad, como apoyo transversal al módulo 0378.",
                "created_by": owner,
                "active": True,
            },
        )
        if not course_created:
            course.title = "Laboratorio Bash para Seguridad · ASIR"
            course.description = "Retos progresivos desde el primer script hasta la preparación y verificación estructural de copias de seguridad, como apoyo transversal al módulo 0378."
            course.save(update_fields=["title", "description", "updated_at"])

        module, module_created = Module.objects.get_or_create(
            course=course,
            position=1,
            defaults={
                "title": "De cero a tus primeras automatizaciones",
                "description": "Una ruta guiada: salida, variables, rutas, argumentos, decisiones, bucles, funciones, filtros y copias.",
                "weight": 100,
            },
        )
        if not module_created:
            module.title = "De cero a tus primeras automatizaciones"
            module.description = "Una ruta guiada: salida, variables, rutas, argumentos, decisiones, bucles, funciones, filtros y copias."
            module.save(update_fields=["title", "description"])

        created_versions = 0
        existing_versions = 0
        migrated_links = 0
        archived_assignments = 0
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
            current_version = activity.current_version
            # A later hand-authored catalogue revision must never be replaced
            # by this older built-in revision during a restart, even when the
            # activity pointer is temporarily empty or still points at v1.
            if activity.versions.filter(version_number__gt=BASH_CATALOG_VERSION).exists():
                existing_versions += 1
                continue

            version, version_created = ActivityVersion.objects.get_or_create(
                activity=activity,
                version_number=BASH_CATALOG_VERSION,
                defaults={
                    "language": ActivityVersion.Language.BASH,
                    "difficulty": item["difficulty"],
                    "xp_reward": item["xp"],
                    "hints": item["hints"],
                    "instructions": f"## Antes de empezar\nEl editor ya tiene un archivo `script.sh`; no necesitas crear carpetas ni descargar nada. En esta actividad el corrector analiza el texto y no ejecuta las órdenes.\n\n## La idea\n{item['theory']}\n\n## Pasos\n{item['task']}\n\n> Las órdenes aparecen como práctica de escritura: no se ejecutan en el servidor ni deben probarse sobre un sistema real.",
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

            # Assigned versions are immutable. Complete missing tests only on
            # a new/unassigned version; never alter an existing assigned one.
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
            )
            if assignment_created and not assignment.title_override:
                assignment.title_override = item["title"]
                assignment.save(update_fields=["title_override"])
            migrated_links += upgrade["migrated_links"]
            archived_assignments += upgrade["archived_assignments"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Itinerario Bash v{BASH_CATALOG_VERSION} listo: {len(CHALLENGES)} retos, grupo {cohort.name}, "
                f"{created_versions} versiones nuevas y {existing_versions} ya existentes. "
                f"Actualizados {migrated_links} vínculos y archivadas {archived_assignments} asignaciones anteriores."
            )
        )
        self.stdout.write("No se han creado alumnos ni contraseñas; el catálogo es contenido formativo local.")
