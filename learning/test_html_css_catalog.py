from io import StringIO
from unittest.mock import call, patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from grading.evaluator import evaluate_tests
from learning.management.commands.seed_web import (
    CHALLENGES,
    CURRICULUM_SOURCE,
    TRACK_SLUG,
    V3_TITLES,
    WEB_CATALOG_VERSION,
)
from learning.models import (
    AcademicYear,
    Activity,
    ActivityVersion,
    Assignment,
    AssignmentCohort,
    Cohort,
    Course,
    Module,
)


class HtmlCssCatalogTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="html-css-catalog-owner",
            password="UnaClaveSegura123!",
            role=User.Role.TEACHER,
        )
        self.year = AcademicYear.objects.create(name="2026-2027")

    def seed(self, cohort="1SMR"):
        with patch("learning.management.commands.seed_web.call_command") as seed_javascript:
            call_command(
                "seed_web",
                owner=self.owner.username,
                cohort=cohort,
                academic_year=self.year.name,
                stdout=StringIO(),
            )
        return seed_javascript

    def test_v4_catalogue_has_a_guided_html_css_progression(self):
        seed_javascript = self.seed()

        self.assertEqual(WEB_CATALOG_VERSION, 4)
        self.assertEqual(len(CHALLENGES), 20)
        self.assertEqual(
            [item["title"].split(" · ")[0] for item in CHALLENGES],
            [f"{number:02}" for number in range(1, 21)],
        )
        self.assertTrue(all(item["javascript"] == "" for item in CHALLENGES))
        self.assertTrue(
            all(not any(test[1].startswith("js.") for test in item["tests"]) for item in CHALLENGES)
        )
        self.assertEqual([set(item["starter"]) for item in CHALLENGES[:3]], [{"html"}] * 3)
        self.assertTrue(all(set(item["starter"]) == {"html", "css"} for item in CHALLENGES[3:]))
        self.assertIn("regla CSS", CHALLENGES[3]["theory"])
        self.assertIn("selector", CHALLENGES[3]["theory"])
        self.assertIn("declaración", CHALLENGES[3]["theory"])
        self.assertTrue(all("CSS" not in item["theory"] for item in CHALLENGES[:3]))

        course = Course.objects.get(slug=TRACK_SLUG)
        self.assertEqual(course.web_stage, Course.WebStage.HTML_CSS)
        versions = list(
            ActivityVersion.objects.filter(activity__module__course=course)
            .select_related("activity")
            .prefetch_related("test_cases")
            .order_by("activity__title")
        )
        self.assertEqual(len(versions), len(CHALLENGES))
        self.assertEqual(Assignment.objects.filter(activity_version__in=versions).count(), len(CHALLENGES))

        by_slug = {item["slug"]: item for item in CHALLENGES}
        for version in versions:
            item = by_slug[version.activity.slug]
            self.assertEqual(version.version_number, WEB_CATALOG_VERSION)
            self.assertEqual(version.language, ActivityVersion.Language.WEB)
            self.assertEqual(version.starter_files, item["starter"])
            self.assertEqual(version.reference_solution, {key: item[key] for key in item["starter"]})
            self.assertEqual(version.curriculum_source, CURRICULUM_SOURCE)
            self.assertNotIn("javascript", version.starter_files)
            self.assertNotIn("javascript", version.reference_solution)
            self.assertTrue(all(not case.type.startswith("js.") for case in version.test_cases.all()))
            starter = evaluate_tests(version.starter_files, list(version.test_cases.all()), language="web")
            solution = evaluate_tests(version.reference_solution, list(version.test_cases.all()), language="web")
            self.assertLess(starter.score, 8, version.activity.slug)
            self.assertEqual(solution.status, "passed", version.activity.slug)
            self.assertEqual(solution.score, 10, version.activity.slug)

        seed_javascript.assert_called_once_with(
            "seed_javascript",
            owner=self.owner.username,
            cohort="1SMR",
            academic_year=self.year.name,
        )

        first_activity = Activity.objects.get(
            module__course=course,
            slug=CHALLENGES[0]["slug"],
        )
        first_activity.title = V3_TITLES[CHALLENGES[0]["slug"]]
        first_activity.save(update_fields=["title", "updated_at"])
        self.seed()
        first_activity.refresh_from_db()
        self.assertEqual(first_activity.title, CHALLENGES[0]["title"])

    def test_html_css_upgrade_seeds_javascript_for_all_linked_active_web_cohorts(self):
        course = Course.objects.create(title="HTML histórico", slug=TRACK_SLUG, created_by=self.owner)
        module = Module.objects.create(course=course, title="HTML histórico", position=1)
        challenge = CHALLENGES[0]
        activity = Activity.objects.create(
            module=module,
            title="Actividad histórica",
            slug=challenge["slug"],
            status=Activity.Status.PUBLISHED,
            created_by=self.owner,
        )
        old_files = {"html": "<p>Entrega antigua</p>\n", "css": "", "javascript": ""}
        old_version = ActivityVersion.objects.create(
            activity=activity,
            version_number=3,
            language=ActivityVersion.Language.WEB,
            starter_files=old_files,
            reference_solution=old_files,
            created_by=self.owner,
            published_at=timezone.now(),
        )
        activity.current_version = old_version
        activity.save(update_fields=["current_version", "updated_at"])
        old_assignment = Assignment.objects.create(
            activity=activity,
            activity_version=old_version,
            status=Assignment.Status.PUBLISHED,
            published_at=timezone.now(),
            created_by=self.owner,
            title_override=V3_TITLES[challenge["slug"]],
        )
        historical_cohort = Cohort.objects.create(
            name="1SMR-histórico", academic_year=self.year, track=Cohort.Track.WEB
        )
        AssignmentCohort.objects.create(assignment=old_assignment, cohort=historical_cohort)

        seed_javascript = self.seed(cohort="1SMR-nuevo")

        current_versions = ActivityVersion.objects.filter(
            activity__module__course__slug=TRACK_SLUG,
            version_number=WEB_CATALOG_VERSION,
        )
        self.assertEqual(
            AssignmentCohort.objects.filter(
                cohort=historical_cohort,
                assignment__activity_version__in=current_versions,
            ).count(),
            len(CHALLENGES),
        )
        seed_javascript.assert_has_calls(
            [
                call("seed_javascript", owner=self.owner.username, cohort="1SMR-histórico", academic_year=self.year.name),
                call("seed_javascript", owner=self.owner.username, cohort="1SMR-nuevo", academic_year=self.year.name),
            ],
            any_order=True,
        )
        self.assertEqual(seed_javascript.call_count, 2)
