from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase

from accounts.models import User
from grading.evaluator import evaluate_tests
from learning.management.commands.seed_javascript import (
    CHALLENGES,
    JAVASCRIPT_CATALOG_VERSION,
    TRACK_SLUG,
)
from learning.models import AcademicYear, ActivityVersion, Assignment, Course


class JavaScriptCatalogTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="javascript-teacher",
            password="UnaClaveSegura123!",
            role=User.Role.TEACHER,
        )
        self.year = AcademicYear.objects.create(name="2026-2027")

    def seed(self, cohort="1SMR"):
        call_command(
            "seed_javascript",
            owner=self.teacher.username,
            cohort=cohort,
            academic_year=self.year.name,
            stdout=None,
        )

    def test_catalogue_is_guided_static_and_all_solutions_score_ten(self):
        self.seed()

        self.assertEqual(len(CHALLENGES), 13)
        self.assertEqual(
            [challenge["slug"] for challenge in CHALLENGES],
            [
                "01-que-es-javascript",
                "02-variable-de-texto",
                "03-numeros-y-calculo",
                "04-unir-textos",
                "05-listas",
                "06-decision-if",
                "07-bucle-for-of",
                "08-primera-funcion",
                "09-parametros",
                "10-return",
                "11-dom-mensaje",
                "12-evento-clic",
                "13-repaso-lista-funcion-bucle",
            ],
        )
        self.assertTrue(all("### Concepto" in item["theory"] for item in CHALLENGES))
        self.assertTrue(all("### Ejemplo" in item["theory"] for item in CHALLENGES))
        self.assertTrue(all(item["task"].startswith("1.") and "\n2." in item["task"] for item in CHALLENGES))
        self.assertTrue(all(set(item["starter"]) == {"javascript"} for item in CHALLENGES[:10]))
        self.assertTrue(all("document." not in str(item["starter"]) for item in CHALLENGES[:10]))
        self.assertTrue(all("async " not in str(item["solution"]) for item in CHALLENGES))
        self.assertTrue(all("Promise" not in str(item["solution"]) for item in CHALLENGES))

        course = Course.objects.get(slug=TRACK_SLUG)
        self.assertEqual(course.web_stage, Course.WebStage.JAVASCRIPT)
        versions = list(
            ActivityVersion.objects.filter(activity__module__course=course)
            .select_related("activity")
            .prefetch_related("test_cases")
            .order_by("activity__slug")
        )
        self.assertEqual(len(versions), len(CHALLENGES))
        self.assertEqual(sum(len(item["tests"]) for item in CHALLENGES), 52)
        self.assertEqual(sum(version.test_cases.count() for version in versions), 52)
        self.assertEqual(Assignment.objects.filter(activity_version__in=versions).count(), 13)

        by_slug = {item["slug"]: item for item in CHALLENGES}
        for version in versions:
            item = by_slug[version.activity.slug]
            self.assertEqual(version.version_number, JAVASCRIPT_CATALOG_VERSION)
            self.assertEqual(version.language, ActivityVersion.Language.WEB)
            self.assertEqual(version.starter_files, item["starter"])
            self.assertEqual(version.reference_solution, item["solution"])
            self.assertEqual(version.professional_module_code, "0228")
            self.assertIn("previsualización aislada", version.instructions)
            self.assertIn("no ejecuta tu JavaScript", version.instructions)

            starter = evaluate_tests(
                version.starter_files, list(version.test_cases.all()), language="web"
            )
            solution = evaluate_tests(
                version.reference_solution, list(version.test_cases.all()), language="web"
            )
            self.assertIsNotNone(starter.score, version.activity.slug)
            self.assertLess(starter.score, 8, version.activity.slug)
            self.assertEqual(solution.status, "passed", version.activity.slug)
            self.assertEqual(solution.score, Decimal("10"), version.activity.slug)

        self.seed()
        self.assertEqual(
            ActivityVersion.objects.filter(
                activity__module__course=course,
                version_number=JAVASCRIPT_CATALOG_VERSION,
            ).count(),
            13,
        )

        weak_sources = {
            "03-numeros-y-calculo": "const precio = 8;\nconst unidades = 3;\nconst total = 0;\nconsole.log(total);\n",
            "05-listas": 'const productos = ["Uno", "Dos", "Tres"];\nconsole.log(productos);\n',
            "10-return": "function duplicar(numero) {\n  return 0;\n}\n\nconst doble = duplicar(4);\nconsole.log(doble);\n",
            "11-dom-mensaje": 'const mensaje = document.getElementById("mensaje");\notra.textContent = "Hola desde JavaScript";\n',
            "12-evento-clic": 'const boton = document.getElementById("boton");\nconst mensaje = document.getElementById("mensaje");\nboton.addEventListener("click", () => {\n  otra.textContent = "Has pulsado el botón";\n});\n',
        }
        for slug, source in weak_sources.items():
            challenge = by_slug[slug]
            cases = [
                {"name": name, "type": test_type, "definition": definition, "points": points}
                for name, test_type, definition, points, _visibility in challenge["tests"]
            ]
            weak_report = evaluate_tests({"javascript": source}, cases, language="web")
            self.assertLess(weak_report.score, 8, slug)
