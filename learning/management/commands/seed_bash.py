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
    AssignmentCohort,
    Cohort,
    Course,
    Module,
    TeachingAssignment,
    TestCase,
)

TRACK_SLUG = "laboratorio-bash-seguridad-asir"


CHALLENGES = [
    {
        "slug": "01-variables-y-salida",
        "title": "01 · Variables y salida segura",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 100,
        "theory": "Las variables permiten separar los datos de la lógica. Usa nombres descriptivos, comillas al interpolar rutas y printf para controlar el formato de salida.",
        "task": "Prepara un script que defina BACKUP_DIR y muestre su valor con printf. No ejecutes ninguna orden: el laboratorio analiza el texto del script.",
        "hints": [
            "Empieza por #!/usr/bin/env bash.",
            "Una asignación no lleva espacios alrededor del signo igual.",
            "printf '%s\\n' \"$BACKUP_DIR\" mantiene el valor como un solo argumento.",
        ],
        "starter": "#!/usr/bin/env bash\n\n# Define BACKUP_DIR y muestra su valor.\n",
        "solution": "#!/usr/bin/env bash\nBACKUP_DIR=\"laboratorio/backups\"\nprintf '%s\\n' \"$BACKUP_DIR\"\n",
        "tests": [
            ("Sintaxis válida", "bash.syntax_valid", {}, 1, TestCase.Visibility.PUBLIC),
            ("Shebang Bash", "bash.shebang", {"expected": "/usr/bin/env bash"}, 1, TestCase.Visibility.PUBLIC),
            ("Variable de destino", "bash.variable_assigned", {"name": "BACKUP_DIR"}, 1, TestCase.Visibility.PUBLIC),
            ("Salida con printf", "bash.command_used", {"command": "printf"}, 1, TestCase.Visibility.PRIVATE),
        ],
    },
    {
        "slug": "02-condiciones-y-rutas",
        "title": "02 · Condiciones y rutas",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 110,
        "theory": "Una condición if permite tomar decisiones sin mezclar comprobaciones y acciones. En scripting de operaciones conviene guardar las rutas en variables y usar -d o -f antes de trabajar con ellas.",
        "task": "Escribe un script que asigne DEST_DIR, compruebe con if si existe como directorio y prepare una orden mkdir -p dentro de la rama adecuada. El corrector solo inspecciona la estructura.",
        "hints": [
            "El patrón básico es if [ -d \"$DEST_DIR\" ]; then ... fi.",
            "La opción -p de mkdir evita errores si los directorios padre no existen.",
            "Usa siempre comillas alrededor de variables que representan rutas.",
        ],
        "starter": "#!/usr/bin/env bash\n\nDEST_DIR=\"laboratorio/destino\"\n# Comprueba el directorio y completa la rama de decisión.\n",
        "solution": "#!/usr/bin/env bash\nDEST_DIR=\"laboratorio/destino\"\nif [ -d \"$DEST_DIR\" ]; then\n  printf 'Existe: %s\\n' \"$DEST_DIR\"\nelse\n  mkdir -p \"$DEST_DIR\"\nfi\n",
        "tests": [
            ("Sintaxis válida", "bash.syntax_valid", {}, 1, TestCase.Visibility.PUBLIC),
            ("Estructura if", "bash.node_kind", {"kind": "if_statement"}, 1, TestCase.Visibility.PUBLIC),
            ("Variable de destino", "bash.variable_assigned", {"name": "DEST_DIR"}, 1, TestCase.Visibility.PUBLIC),
            ("Creación no destructiva", "bash.command_used", {"command": "mkdir", "args": ["-p", "$DEST_DIR"]}, 1, TestCase.Visibility.PRIVATE),
        ],
    },
    {
        "slug": "03-bucle-de-registros",
        "title": "03 · Recorrer registros con for",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 120,
        "theory": "Los bucles for automatizan la misma operación sobre una colección. Un patrón de búsqueda puede expresarse como dato y pasar a grep sin concatenar órdenes dinámicas.",
        "task": "Construye un bucle for que recorra una colección LOG_FILES y utilice grep -c para contar coincidencias de error. Usa una variable LOG para cada elemento.",
        "hints": [
            "for LOG in ...; do ... done es suficiente para este reto.",
            "grep -c devuelve un recuento, pero aquí solo necesitamos que aparezca la orden.",
            "No uses eval ni construyas una orden completa dentro de una cadena.",
        ],
        "starter": "#!/usr/bin/env bash\n\nLOG_FILES=(\"laboratorio/app.log\" \"laboratorio/auth.log\")\n# Recorre LOG_FILES y busca la palabra error.\n",
        "solution": "#!/usr/bin/env bash\nLOG_FILES=(\"laboratorio/app.log\" \"laboratorio/auth.log\")\nfor LOG in \"${LOG_FILES[@]}\"; do\n  grep -c error \"$LOG\"\ndone\n",
        "tests": [
            ("Sintaxis válida", "bash.syntax_valid", {}, 1, TestCase.Visibility.PUBLIC),
            ("Bucle for", "bash.node_kind", {"kind": "for_statement"}, 1, TestCase.Visibility.PUBLIC),
            ("Variable del bucle", "bash.variable_assigned", {"name": "LOG"}, 1, TestCase.Visibility.PUBLIC),
            ("Recuento de errores", "bash.command_used", {"command": "grep", "args": ["-c", "error", "$LOG"]}, 1, TestCase.Visibility.PRIVATE),
        ],
    },
    {
        "slug": "04-funciones-reutilizables",
        "title": "04 · Funciones reutilizables",
        "difficulty": ActivityVersion.Difficulty.BEGINNER,
        "xp": 130,
        "theory": "Una función nombra una operación repetible y facilita revisar un script. Las funciones de copia deben recibir datos por variables claras y no depender de rutas ocultas.",
        "task": "Define una función backup_folder que utilice SOURCE_DIR y ARCHIVE para expresar una copia tar -czf. Es un ejercicio de estructura: no se ejecutará la orden.",
        "hints": [
            "Declara backup_folder() { ... } o function backup_folder { ... }.",
            "tar -czf recibe primero el archivo destino y después la fuente.",
            "Conserva las variables entre comillas en la orden de ejemplo.",
        ],
        "starter": "#!/usr/bin/env bash\n\nSOURCE_DIR=\"laboratorio/fuente\"\nARCHIVE=\"laboratorio/copia.tgz\"\n# Declara backup_folder.\n",
        "solution": "#!/usr/bin/env bash\nSOURCE_DIR=\"laboratorio/fuente\"\nARCHIVE=\"laboratorio/copia.tgz\"\nbackup_folder() {\n  tar -czf \"$ARCHIVE\" \"$SOURCE_DIR\"\n}\n",
        "tests": [
            ("Sintaxis válida", "bash.syntax_valid", {}, 1, TestCase.Visibility.PUBLIC),
            ("Declaración de función", "bash.node_kind", {"kind": "function_definition"}, 1, TestCase.Visibility.PUBLIC),
            ("Variable fuente", "bash.variable_assigned", {"name": "SOURCE_DIR"}, 1, TestCase.Visibility.PUBLIC),
            ("Orden tar de copia", "bash.command_used", {"command": "tar", "args": ["-czf", "$ARCHIVE", "$SOURCE_DIR"]}, 1, TestCase.Visibility.PRIVATE),
        ],
    },
    {
        "slug": "05-pipelines-de-registros",
        "title": "05 · Pipelines para filtrar registros",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 140,
        "theory": "Un pipeline conecta la salida de una orden con la entrada de la siguiente. Esta composición permite filtrar y ordenar información sin guardar resultados intermedios innecesarios.",
        "task": "Crea un pipeline que filtre advertencias de LOG_FILE con grep -i warning y pase el resultado a sort. Mantén la ruta en una variable.",
        "hints": [
            "El símbolo | crea el nodo pipeline que observará el corrector.",
            "grep -i ignora diferencias entre mayúsculas y minúsculas.",
            "No encadenes comandos mediante eval ni sustituciones de comandos para este reto.",
        ],
        "starter": "#!/usr/bin/env bash\n\nLOG_FILE=\"laboratorio/app.log\"\n# Filtra y ordena las líneas de advertencia.\n",
        "solution": "#!/usr/bin/env bash\nLOG_FILE=\"laboratorio/app.log\"\ngrep -i warning \"$LOG_FILE\" | sort\n",
        "tests": [
            ("Sintaxis válida", "bash.syntax_valid", {}, 1, TestCase.Visibility.PUBLIC),
            ("Estructura pipeline", "bash.node_kind", {"kind": "pipeline"}, 1, TestCase.Visibility.PUBLIC),
            ("Filtro de advertencias", "bash.command_used", {"command": "grep", "args": ["-i", "warning", "$LOG_FILE"]}, 1, TestCase.Visibility.PUBLIC),
            ("Ordenación del resultado", "bash.command_used", {"command": "sort"}, 1, TestCase.Visibility.PRIVATE),
        ],
    },
    {
        "slug": "06-parametros-posicionales",
        "title": "06 · Parámetros y validación",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 150,
        "theory": "Los parámetros posicionales permiten reutilizar un script con distintos datos. Antes de usarlos conviene comprobar que el argumento existe y explicar al usuario el formato esperado.",
        "task": "Prepara un script que guarde PREFIX, compruebe con if si se ha recibido un valor y muestre un mensaje con printf. No hace falta ejecutar el script.",
        "hints": [
            "Puedes asignar PREFIX=\"${1:-}\" para trabajar con un valor vacío de forma explícita.",
            "Una rama if permite separar el caso con argumento del caso sin argumento.",
            "Usa printf para mensajes previsibles, incluso cuando el texto venga de una variable.",
        ],
        "starter": "#!/usr/bin/env bash\n\nPREFIX=\"${1:-}\"\n# Valida PREFIX y muestra un mensaje.\n",
        "solution": "#!/usr/bin/env bash\nPREFIX=\"${1:-}\"\nif [ -n \"$PREFIX\" ]; then\n  printf 'Prefijo: %s\\n' \"$PREFIX\"\nelse\n  printf 'Falta un prefijo\\n'\nfi\n",
        "tests": [
            ("Sintaxis válida", "bash.syntax_valid", {}, 1, TestCase.Visibility.PUBLIC),
            ("Variable de parámetro", "bash.variable_assigned", {"name": "PREFIX"}, 1, TestCase.Visibility.PUBLIC),
            ("Validación if", "bash.node_kind", {"kind": "if_statement"}, 1, TestCase.Visibility.PUBLIC),
            ("Mensaje controlado", "bash.command_used", {"command": "printf"}, 1, TestCase.Visibility.PRIVATE),
        ],
    },
    {
        "slug": "07-codigos-de-salida",
        "title": "07 · Códigos de salida",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 160,
        "theory": "El código de salida comunica si una operación terminó correctamente. Guardarlo en una variable y devolverlo con exit hace que otros scripts puedan encadenar el trabajo.",
        "task": "Define STATUS, usa una decisión if para informar del resultado y termina con exit \"$STATUS\". El ejercicio solo verifica la intención estructural.",
        "hints": [
            "Los códigos 0 suelen representar éxito y los valores distintos de 0 un problema.",
            "No confundas el texto mostrado con el estado que devuelves.",
            "El evaluador busca la orden exit y la variable STATUS como nodos literales.",
        ],
        "starter": "#!/usr/bin/env bash\n\nSTATUS=0\n# Informa del estado y devuelve STATUS.\n",
        "solution": "#!/usr/bin/env bash\nSTATUS=0\nif [ \"$STATUS\" -eq 0 ]; then\n  printf 'Correcto\\n'\nelse\n  printf 'Revisar\\n'\nfi\nexit \"$STATUS\"\n",
        "tests": [
            ("Sintaxis válida", "bash.syntax_valid", {}, 1, TestCase.Visibility.PUBLIC),
            ("Estado asignado", "bash.variable_assigned", {"name": "STATUS"}, 1, TestCase.Visibility.PUBLIC),
            ("Decisión por estado", "bash.node_kind", {"kind": "if_statement"}, 1, TestCase.Visibility.PUBLIC),
            ("Retorno del estado", "bash.command_used", {"command": "exit", "args": ["$STATUS"]}, 1, TestCase.Visibility.PRIVATE),
        ],
    },
    {
        "slug": "08-plan-de-copia",
        "title": "08 · Plan de copia versionado",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 180,
        "theory": "Un plan de copia completo separa origen, destino y nombre de archivo. La función sirve para centralizar la política y dejar preparada una revisión antes de automatizarla.",
        "task": "Escribe backup_plan con SOURCE_DIR, ARCHIVE y una orden tar -czf. Añade una comprobación if para no continuar si falta la fuente.",
        "hints": [
            "Primero comprueba la fuente con [ -d \"$SOURCE_DIR\" ].",
            "Guarda el nombre del archivo de copia en ARCHIVE.",
            "La función debe contener la orden de copia y no una cadena para eval.",
        ],
        "starter": "#!/usr/bin/env bash\n\nSOURCE_DIR=\"laboratorio/fuente\"\nARCHIVE=\"laboratorio/copia.tgz\"\n# Implementa backup_plan.\n",
        "solution": "#!/usr/bin/env bash\nSOURCE_DIR=\"laboratorio/fuente\"\nARCHIVE=\"laboratorio/copia.tgz\"\nbackup_plan() {\n  if [ -d \"$SOURCE_DIR\" ]; then\n    tar -czf \"$ARCHIVE\" \"$SOURCE_DIR\"\n  fi\n}\n",
        "tests": [
            ("Sintaxis válida", "bash.syntax_valid", {}, 1, TestCase.Visibility.PUBLIC),
            ("Función de copia", "bash.node_kind", {"kind": "function_definition"}, 1, TestCase.Visibility.PUBLIC),
            ("Comprobación if", "bash.node_kind", {"kind": "if_statement"}, 1, TestCase.Visibility.PUBLIC),
            ("Archivo de copia", "bash.command_used", {"command": "tar", "args": ["-czf", "$ARCHIVE", "$SOURCE_DIR"]}, 1, TestCase.Visibility.PRIVATE),
        ],
    },
    {
        "slug": "09-permisos-del-script",
        "title": "09 · Permisos y ejecución controlada",
        "difficulty": ActivityVersion.Difficulty.INTERMEDIATE,
        "xp": 170,
        "theory": "Los permisos deben ser explícitos y mínimos. chmod u+x concede ejecución al propietario del script sin abrir permisos innecesarios a todo el sistema.",
        "task": "Define SCRIPT, comprueba que es un archivo y deja expresada la orden chmod u+x para prepararlo. El laboratorio no cambia permisos reales.",
        "hints": [
            "Usa [ -f \"$SCRIPT\" ] para distinguir un archivo de un directorio.",
            "La opción u+x modifica solo el permiso del propietario.",
            "Mantén la ruta en SCRIPT y no la concatenes en una orden creada dinámicamente.",
        ],
        "starter": "#!/usr/bin/env bash\n\nSCRIPT=\"laboratorio/backup.sh\"\n# Comprueba el archivo y prepara su permiso.\n",
        "solution": "#!/usr/bin/env bash\nSCRIPT=\"laboratorio/backup.sh\"\nif [ -f \"$SCRIPT\" ]; then\n  chmod u+x \"$SCRIPT\"\nfi\n",
        "tests": [
            ("Sintaxis válida", "bash.syntax_valid", {}, 1, TestCase.Visibility.PUBLIC),
            ("Variable de script", "bash.variable_assigned", {"name": "SCRIPT"}, 1, TestCase.Visibility.PUBLIC),
            ("Comprobación de archivo", "bash.node_kind", {"kind": "if_statement"}, 1, TestCase.Visibility.PUBLIC),
            ("Permiso mínimo", "bash.command_used", {"command": "chmod", "args": ["u+x", "$SCRIPT"]}, 1, TestCase.Visibility.PRIVATE),
        ],
    },
    {
        "slug": "10-pipeline-awk-y-orden",
        "title": "10 · Extraer campos con awk",
        "difficulty": ActivityVersion.Difficulty.ADVANCED,
        "xp": 190,
        "theory": "awk puede seleccionar campos de una línea y combinarse con sort. En análisis de registros es útil mantener cada etapa pequeña y visible para poder auditarla.",
        "task": "Define LOG_FILE y crea un pipeline awk '{print $1}' \"$LOG_FILE\" | sort. El corrector compara los nodos y argumentos literales.",
        "hints": [
            "El programa awk puede pasarse como una cadena literal entre comillas simples.",
            "El primer campo se representa como $1 dentro del programa awk.",
            "La segunda etapa debe ser exactamente sort para este reto.",
        ],
        "starter": "#!/usr/bin/env bash\n\nLOG_FILE=\"laboratorio/access.log\"\n# Extrae el primer campo y ordénalo.\n",
        "solution": "#!/usr/bin/env bash\nLOG_FILE=\"laboratorio/access.log\"\nawk '{print $1}' \"$LOG_FILE\" | sort\n",
        "tests": [
            ("Sintaxis válida", "bash.syntax_valid", {}, 1, TestCase.Visibility.PUBLIC),
            ("Pipeline de análisis", "bash.node_kind", {"kind": "pipeline"}, 1, TestCase.Visibility.PUBLIC),
            ("Extracción awk", "bash.command_used", {"command": "awk", "args": ["{print $1}", "$LOG_FILE"]}, 1, TestCase.Visibility.PUBLIC),
            ("Ordenación final", "bash.command_used", {"command": "sort"}, 1, TestCase.Visibility.PRIVATE),
        ],
    },
    {
        "slug": "11-case-de-operacion",
        "title": "11 · Selección de operación con case",
        "difficulty": ActivityVersion.Difficulty.ADVANCED,
        "xp": 200,
        "theory": "case expresa varias opciones de forma legible y evita una cadena de if difíciles de revisar. Es apropiado para seleccionar una operación declarada por el operador.",
        "task": "Asigna MODE y usa case para distinguir backup, check y cualquier otro valor. Cada rama debe mostrar una indicación con printf; no incluyas órdenes de red ni borrados.",
        "hints": [
            "La estructura termina con esac.",
            "Usa patrones literales como backup) y check).",
            "El patrón *) cubre el caso desconocido y debe informar del problema.",
        ],
        "starter": "#!/usr/bin/env bash\n\nMODE=\"check\"\n# Selecciona la operación con case.\n",
        "solution": "#!/usr/bin/env bash\nMODE=\"check\"\ncase \"$MODE\" in\n  backup) printf 'Preparar copia\\n' ;;\n  check) printf 'Comprobar estado\\n' ;;\n  *) printf 'Operación no reconocida\\n' ;;\nesac\n",
        "tests": [
            ("Sintaxis válida", "bash.syntax_valid", {}, 1, TestCase.Visibility.PUBLIC),
            ("Variable de operación", "bash.variable_assigned", {"name": "MODE"}, 1, TestCase.Visibility.PUBLIC),
            ("Estructura case", "bash.node_kind", {"kind": "case_statement"}, 1, TestCase.Visibility.PUBLIC),
            ("Mensajes por rama", "bash.command_used", {"command": "printf"}, 1, TestCase.Visibility.PRIVATE),
        ],
    },
    {
        "slug": "12-rutina-integrada",
        "title": "12 · Rutina integrada de backup",
        "difficulty": ActivityVersion.Difficulty.ADVANCED,
        "xp": 240,
        "theory": "Una rutina operativa combina validación, función y salida clara. Antes de ejecutarla en un entorno real hay que revisar rutas, permisos, retención y recuperación; este reto solo trabaja la estructura.",
        "task": "Integra una función make_backup con SOURCE_DIR y ARCHIVE, comprueba la fuente con if, usa tar -czf y devuelve un mensaje. No uses red, sudo ni borrados.",
        "hints": [
            "Conserva el shebang y separa configuración de lógica.",
            "El if debe envolver la orden tar para no intentar copiar una fuente inexistente.",
            "La función se puede invocar al final, una vez declarada.",
        ],
        "starter": "#!/usr/bin/env bash\n\nSOURCE_DIR=\"laboratorio/fuente\"\nARCHIVE=\"laboratorio/backup-final.tgz\"\n# Completa make_backup y su llamada.\n",
        "solution": "#!/usr/bin/env bash\nSOURCE_DIR=\"laboratorio/fuente\"\nARCHIVE=\"laboratorio/backup-final.tgz\"\nmake_backup() {\n  if [ -d \"$SOURCE_DIR\" ]; then\n    tar -czf \"$ARCHIVE\" \"$SOURCE_DIR\"\n    printf 'Copia preparada: %s\\n' \"$ARCHIVE\"\n  else\n    printf 'No existe la fuente: %s\\n' \"$SOURCE_DIR\"\n  fi\n}\nmake_backup\n",
        "tests": [
            ("Sintaxis válida", "bash.syntax_valid", {}, 1, TestCase.Visibility.PUBLIC),
            ("Shebang Bash", "bash.shebang", {"interpreter": "bash"}, 1, TestCase.Visibility.PUBLIC),
            ("Rutina integrada", "bash.node_kind", {"kind": "function_definition"}, 1, TestCase.Visibility.PUBLIC),
            ("Copia condicionada", "bash.command_used", {"command": "tar", "args": ["-czf", "$ARCHIVE", "$SOURCE_DIR"]}, 1, TestCase.Visibility.PRIVATE),
        ],
    },
]


class Command(BaseCommand):
    help = "Crea el itinerario local de 12 retos Bash para apoyo transversal de ASIR (módulo 0378)."

    def add_arguments(self, parser):
        parser.add_argument("--owner", required=True, help="Usuario profesor o administrador propietario del contenido.")
        parser.add_argument("--cohort", default="2ASIR", help="Grupo al que se asignan los retos (por defecto: 2ASIR).")
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
            defaults={"active": True},
        )
        if owner.role == User.Role.TEACHER and not owner.is_superuser:
            TeachingAssignment.objects.get_or_create(cohort=cohort, teacher=owner, defaults={"active": True})

        course, _ = Course.objects.get_or_create(
            slug=TRACK_SLUG,
            defaults={
                "title": "Laboratorio Bash para Seguridad · ASIR",
                "description": "Retos de scripting, automatización y copias de seguridad como apoyo transversal al módulo 0378 Seguridad y alta disponibilidad.",
                "created_by": owner,
                "active": True,
            },
        )
        module, _ = Module.objects.get_or_create(
            course=course,
            position=1,
            defaults={
                "title": "Laboratorio Bash · /laboratorio",
                "description": "Itinerario estático de Bash para prácticas de seguridad y operación; no sustituye los resultados de aprendizaje oficiales.",
                "weight": 100,
            },
        )

        created_versions = 0
        existing_versions = 0
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
            version, version_created = ActivityVersion.objects.get_or_create(
                activity=activity,
                version_number=1,
                defaults={
                    "language": ActivityVersion.Language.BASH,
                    "difficulty": item["difficulty"],
                    "xp_reward": item["xp"],
                    "hints": item["hints"],
                    "instructions": f"## Teoría\n{item['theory']}\n\n## Reto\n{item['task']}\n\n> El corrector analiza el texto de forma estática; no ejecutes estas órdenes en un sistema real.",
                    "objectives": ["Leer y escribir scripts Bash mantenibles", "Identificar estructuras de control y comandos de operación", "Relacionar scripting con copias de seguridad y revisión segura"],
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
            if activity.current_version_id is None:
                activity.current_version = version
                activity.status = Activity.Status.PUBLISHED
                activity.save(update_fields=["current_version", "status", "updated_at"])

            # Assigned versions are immutable.  Complete missing tests only on
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
            assignment, _ = Assignment.objects.get_or_create(
                activity=activity,
                activity_version=version,
                defaults={
                    "status": Assignment.Status.PUBLISHED,
                    "created_by": owner,
                    "attempt_policy": Assignment.AttemptPolicy.BEST,
                    "max_attempts": None,
                    "weight": 100,
                    "allow_late": True,
                    "published_at": timezone.now(),
                },
            )
            AssignmentCohort.objects.get_or_create(assignment=assignment, cohort=cohort)

        self.stdout.write(
            self.style.SUCCESS(
                f"Itinerario Bash listo: {len(CHALLENGES)} retos, grupo {cohort.name}, "
                f"{created_versions} versiones nuevas y {existing_versions} ya existentes."
            )
        )
        self.stdout.write("No se han creado alumnos ni contraseñas; el catálogo es contenido formativo local.")
