from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from grading.services import DraftConflict, create_submission, get_or_create_draft, save_draft
from learning.management.commands.seed_web import CHALLENGES as WEB_CHALLENGES
from learning.services import clear_student_enrollment, set_student_cohort

from .models import (
    AcademicYear,
    Activity,
    ActivityVersion,
    Assignment,
    AssignmentCohort,
    Cohort,
    Course,
    Draft,
    Enrollment,
    Module,
    TeachingAssignment,
)
from .models import (
    TestCase as ActivityTestCase,
)


class LearningFactoryMixin:
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher", password="UnaClaveSegura123!", role=User.Role.TEACHER)
        self.student = User.objects.create_user(username="student", password="UnaClaveSegura123!", role=User.Role.STUDENT)
        self.other_student = User.objects.create_user(username="other", password="UnaClaveSegura123!", role=User.Role.STUDENT)
        self.year = AcademicYear.objects.create(name="2025-2026")
        self.cohort = Cohort.objects.create(name="1SMR-A", academic_year=self.year, track=Cohort.Track.WEB)
        Enrollment.objects.create(cohort=self.cohort, student=self.student)
        TeachingAssignment.objects.create(cohort=self.cohort, teacher=self.teacher)
        self.course = Course.objects.create(title="Web", slug="web", created_by=self.teacher)
        self.module = Module.objects.create(course=self.course, title="Unidad", position=1)
        self.activity = Activity.objects.create(module=self.module, title="Actividad", slug="actividad", created_by=self.teacher)
        self.version = ActivityVersion.objects.create(activity=self.activity, version_number=1, created_by=self.teacher, starter_files={"html": "<main></main>", "css": "body{}", "javascript": ""}, learning_outcomes=["RA1"], assessment_criteria=["RA1.a"], curriculum_scope="Navarra")
        self.activity.current_version = self.version
        self.activity.save(update_fields=["current_version", "updated_at"])
        self.assignment = Assignment.objects.create(activity=self.activity, activity_version=self.version, created_by=self.teacher, status=Assignment.Status.PUBLISHED, published_at=timezone.now())
        AssignmentCohort.objects.create(assignment=self.assignment, cohort=self.cohort)


class DraftTests(LearningFactoryMixin, TestCase):
    def test_seed_web_is_idempotent_and_reference_solutions_pass(self):
        from grading.evaluator import evaluate_tests

        call_command("seed_web", owner=self.teacher.username, cohort="1SMR", academic_year="2025-2026")
        course = Course.objects.get(slug="fundamentos-web-smr")
        versions = list(
            ActivityVersion.objects.filter(activity__module__course=course)
            .prefetch_related("test_cases")
            .order_by("activity__title")
        )
        self.assertEqual(len(versions), 12)
        self.assertTrue(all(version.language == ActivityVersion.Language.WEB for version in versions))
        self.assertEqual(
            sum(version.test_cases.count() for version in versions),
            sum(len(item["tests"]) for item in WEB_CHALLENGES),
        )
        for index, version in enumerate(versions, start=1):
            self.assertNotEqual(version.starter_files, version.reference_solution)
            if index <= 6:
                self.assertNotIn("<main", version.starter_files["html"])
            elif index <= 9:
                self.assertEqual(version.starter_files["css"], "")
            else:
                self.assertEqual(version.starter_files["javascript"], "")
        reports = [
            evaluate_tests(version.reference_solution, list(version.test_cases.all()), language="web")
            for version in versions
        ]
        self.assertTrue(all(report.status == "passed" and report.score == 10 for report in reports))
        call_command("seed_web", owner=self.teacher.username, cohort="1SMR", academic_year="2025-2026", stdout=None)
        self.assertEqual(
            ActivityVersion.objects.filter(activity__module__course=course).count(),
            12,
        )

    def test_bootstrap_catalogs_is_idempotent_and_creates_all_tracks_without_students(self):
        from accounts.models import CATALOG_SERVICE_USERNAME

        before_students = User.objects.filter(role=User.Role.STUDENT).count()
        call_command("bootstrap_catalogs")
        expected_courses = {
            "fundamentos-web-smr": ActivityVersion.Language.WEB,
            "laboratorio-bash-seguridad-asir": ActivityVersion.Language.BASH,
            "introduccion-python-sge-dam": ActivityVersion.Language.PYTHON,
        }
        for slug, language in expected_courses.items():
            course = Course.objects.get(slug=slug)
            versions = ActivityVersion.objects.filter(activity__module__course=course)
            self.assertEqual(versions.count(), 12)
            self.assertEqual(versions.values_list("language", flat=True).distinct().get(), language)
            self.assertEqual(
                Assignment.objects.filter(activity_version__in=versions).count(),
                12,
            )
        self.assertEqual(User.objects.filter(role=User.Role.STUDENT).count(), before_students)
        service_owner = User.objects.get(username=CATALOG_SERVICE_USERNAME)
        self.assertFalse(service_owner.is_active)
        self.assertFalse(service_owner.has_usable_password())
        call_command("bootstrap_catalogs", stdout=None)
        self.assertEqual(Course.objects.filter(slug__in=expected_courses).count(), 3)
        self.assertEqual(
            ActivityVersion.objects.filter(activity__module__course__slug__in=expected_courses).count(),
            36,
        )

    def test_bootstrap_uses_an_active_fallback_without_reactivating_closed_year(self):
        from learning.management.commands.bootstrap_catalogs import Command

        current_name = Command.academic_year_name()
        current = AcademicYear.objects.create(name=current_name, active=False)
        self.year.active = False
        self.year.save(update_fields=["active"])
        call_command("bootstrap_catalogs", stdout=None)
        current.refresh_from_db()
        self.assertFalse(current.active)
        fallback = AcademicYear.objects.exclude(pk=current.pk).get(active=True)
        self.assertTrue(fallback.name.startswith(f"{current_name}-catalogo"))
        self.assertEqual(
            Cohort.objects.filter(
                academic_year=fallback,
                track__in=(Cohort.Track.WEB, Cohort.Track.BASH, Cohort.Track.PYTHON),
            ).count(),
            3,
        )

    def test_student_cohort_switch_keeps_history_and_only_one_active_enrollment(self):
        other_cohort = Cohort.objects.create(
            name="2ASIR-B",
            academic_year=self.year,
            track=Cohort.Track.BASH,
        )
        call_command(
            "seed_bash",
            owner=self.teacher.username,
            cohort=other_cohort.name,
            academic_year=self.year.name,
            stdout=None,
        )
        switched = set_student_cohort(self.student, other_cohort)
        self.assertEqual(switched.cohort_id, other_cohort.id)
        self.assertEqual(Enrollment.objects.filter(student=self.student, active=True).count(), 1)
        self.assertFalse(Enrollment.objects.get(student=self.student, cohort=self.cohort).active)
        restored = set_student_cohort(self.student, self.cohort)
        self.assertEqual(restored.pk, Enrollment.objects.get(student=self.student, cohort=self.cohort).pk)
        self.assertEqual(Enrollment.objects.filter(student=self.student, active=True).count(), 1)
        self.assertEqual(Enrollment.objects.filter(student=self.student).count(), 2)
        clear_student_enrollment(self.student)
        self.assertFalse(Enrollment.objects.filter(student=self.student, active=True).exists())
        with self.assertRaises(ValidationError):
            set_student_cohort(self.teacher, self.cohort)

    def test_student_sees_first_seeded_assignment_and_cross_track_isolation(self):
        call_command("seed_web", owner=self.teacher.username, cohort="1SMR", academic_year="2025-2026", stdout=None)
        seeded_cohort = Cohort.objects.get(name="1SMR", academic_year=self.year)
        set_student_cohort(self.student, seeded_cohort)
        self.client.force_login(self.student)
        dashboard = self.client.get(reverse("student_dashboard"), HTTP_ACCEPT="application/json")
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(len(dashboard.json()["assignments"]), 12)
        self.assertEqual(dashboard.json()["assignments"][0]["title"], "01 · Estructura semántica")

        foreign_cohort = Cohort.objects.create(
            name="2ASIR-C",
            academic_year=self.year,
            track=Cohort.Track.BASH,
        )
        foreign_activity = Activity.objects.create(
            module=self.module,
            title="Privado Bash",
            slug="privado-bash",
            created_by=self.teacher,
        )
        foreign_version = ActivityVersion.objects.create(
            activity=foreign_activity,
            version_number=1,
            language=ActivityVersion.Language.BASH,
            starter_files={"bash": "#!/usr/bin/env bash\n"},
            created_by=self.teacher,
        )
        foreign_assignment = Assignment.objects.create(
            activity=foreign_activity,
            activity_version=foreign_version,
            created_by=self.teacher,
            status=Assignment.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        AssignmentCohort.objects.create(assignment=foreign_assignment, cohort=foreign_cohort)
        self.assertEqual(
            self.client.get(reverse("workspace_detail_api", args=[foreign_assignment.id])).status_code,
            404,
        )

    def test_seed_reuses_one_deterministic_assignment_when_legacy_duplicates_exist(self):
        call_command("seed_bash", owner=self.teacher.username, cohort="2ASIR", academic_year="2025-2026", stdout=None)
        activity = Activity.objects.filter(module__course__slug="laboratorio-bash-seguridad-asir").order_by("title").first()
        version = activity.current_version
        first = Assignment.objects.get(activity=activity, activity_version=version)
        duplicate = Assignment.objects.create(
            activity=activity,
            activity_version=version,
            status=Assignment.Status.PUBLISHED,
            published_at=timezone.now(),
            created_by=self.teacher,
        )
        call_command("seed_bash", owner=self.teacher.username, cohort="2ASIR", academic_year="2025-2026", stdout=None)
        self.assertEqual(Assignment.objects.filter(activity=activity, activity_version=version).count(), 2)
        self.assertTrue(AssignmentCohort.objects.filter(assignment=first, cohort__name="2ASIR").exists())
        self.assertFalse(AssignmentCohort.objects.filter(assignment=duplicate, cohort__name="2ASIR").exists())

    def test_assignment_cohort_track_mismatch_is_rejected_and_not_granted(self):
        foreign_cohort = Cohort.objects.create(
            name="2ASIR-mismatch",
            academic_year=self.year,
            track=Cohort.Track.BASH,
        )
        invalid_link = AssignmentCohort(assignment=self.assignment, cohort=foreign_cohort)
        with self.assertRaises(ValidationError):
            invalid_link.full_clean()
        AssignmentCohort.objects.create(assignment=self.assignment, cohort=foreign_cohort)
        Enrollment.objects.create(cohort=foreign_cohort, student=self.other_student)
        self.assertIsNone(
            __import__("grading.services", fromlist=["student_assignment_or_404"]).student_assignment_or_404(
                self.other_student,
                self.assignment.id,
            )
        )

    def test_inactive_cohort_and_academic_year_hide_assignments(self):
        self.client.force_login(self.student)
        self.cohort.active = False
        self.cohort.save(update_fields=["active"])
        dashboard = self.client.get(reverse("student_dashboard"), HTTP_ACCEPT="application/json")
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.json()["assignments"], [])
        self.cohort.active = True
        self.cohort.save(update_fields=["active"])
        self.year.active = False
        self.year.save(update_fields=["active"])
        dashboard = self.client.get(reverse("student_dashboard"), HTTP_ACCEPT="application/json")
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.json()["assignments"], [])
        self.assertEqual(self.client.get(reverse("workspace_detail_api", args=[self.assignment.id])).status_code, 404)

    def test_seed_bash_is_idempotent_and_does_not_overwrite_assigned_versions(self):
        call_command("seed_bash", owner=self.teacher.username, cohort="2ASIR", academic_year="2025-2026")
        versions = ActivityVersion.objects.filter(language=ActivityVersion.Language.BASH)
        self.assertEqual(versions.count(), 12)
        self.assertEqual(ActivityTestCase.objects.filter(activity_version__in=versions).count(), 48)
        self.assertEqual(Assignment.objects.filter(activity_version__in=versions).count(), 12)
        self.assertTrue(all(not version.learning_outcomes and not version.assessment_criteria for version in versions))
        changed = versions.order_by("id").first()
        changed.reference_solution = {"bash": "solución docente externa"}
        ActivityVersion.objects.filter(pk=changed.pk).update(reference_solution=changed.reference_solution)
        call_command("seed_bash", owner=self.teacher.username, cohort="2ASIR", academic_year="2025-2026", stdout=None)
        changed.refresh_from_db()
        self.assertEqual(changed.reference_solution, {"bash": "solución docente externa"})

    def test_seed_python_is_idempotent_and_reference_solutions_pass(self):
        from grading.evaluator import evaluate_tests

        call_command("seed_python", owner=self.teacher.username, cohort="2DAM", academic_year="2026-2027")
        versions = list(
            ActivityVersion.objects.filter(language=ActivityVersion.Language.PYTHON)
            .prefetch_related("test_cases")
        )
        self.assertEqual(len(versions), 12)
        self.assertEqual(sum(version.test_cases.count() for version in versions), 67)
        self.assertEqual(Assignment.objects.filter(activity_version__in=versions).count(), 12)
        self.assertTrue(all(not version.learning_outcomes and not version.assessment_criteria for version in versions))
        reports = [
            evaluate_tests(version.reference_solution, list(version.test_cases.all()), language="python")
            for version in versions
        ]
        self.assertTrue(all(report.status == "passed" and report.score == 10 for report in reports))
        changed = versions[0]
        changed.reference_solution = {"python": "solución docente externa"}
        ActivityVersion.objects.filter(pk=changed.pk).update(reference_solution=changed.reference_solution)
        call_command("seed_python", owner=self.teacher.username, cohort="2DAM", academic_year="2026-2027", stdout=None)
        changed.refresh_from_db()
        self.assertEqual(changed.reference_solution, {"python": "solución docente externa"})

    def test_python_version_scopes_files_and_snapshot(self):
        python_activity = Activity.objects.create(
            module=self.module,
            title="Reto Python",
            slug="reto-python",
            created_by=self.teacher,
            status=Activity.Status.PUBLISHED,
        )
        python_version = ActivityVersion.objects.create(
            activity=python_activity,
            version_number=1,
            language=ActivityVersion.Language.PYTHON,
            starter_files={"python": "print('inicio')\n"},
            reference_solution={"python": "print('solución')\n"},
            grading_mode=ActivityVersion.GradingMode.AUTOMATIC_STATIC,
            created_by=self.teacher,
        )
        python_activity.current_version = python_version
        python_activity.save(update_fields=["current_version", "updated_at"])
        ActivityTestCase.objects.create(
            activity_version=python_version,
            name="sintaxis",
            type="python.syntax_valid",
            definition={},
        )
        assignment = Assignment.objects.create(
            activity=python_activity,
            activity_version=python_version,
            created_by=self.teacher,
            status=Assignment.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        python_cohort = Cohort.objects.create(
            name="2DAM-A",
            academic_year=self.year,
            track=Cohort.Track.PYTHON,
        )
        AssignmentCohort.objects.create(assignment=assignment, cohort=python_cohort)
        set_student_cohort(self.student, python_cohort)
        draft = get_or_create_draft(self.student, assignment)
        self.assertEqual(draft.files, {"python": "print('inicio')\n"})
        submission, report = create_submission(
            self.student,
            assignment,
            {"python": "print('ok')\n"},
        )
        self.assertEqual(submission.files.count(), 1)
        self.assertEqual(submission.files.get().path, "python")
        self.assertEqual(report.score, 10)

    def test_python_version_rejects_other_language_files(self):
        invalid = ActivityVersion(
            activity=self.activity,
            version_number=2,
            language=ActivityVersion.Language.PYTHON,
            starter_files={"bash": "echo no"},
            created_by=self.teacher,
        )
        with self.assertRaises(ValidationError):
            invalid.full_clean()

    def test_test_case_validates_python_dsl_and_maximum_on_save(self):
        python_activity = Activity.objects.create(
            module=self.module,
            title="Validación Python",
            slug="validacion-python",
            created_by=self.teacher,
        )
        python_version = ActivityVersion.objects.create(
            activity=python_activity,
            version_number=1,
            language=ActivityVersion.Language.PYTHON,
            created_by=self.teacher,
        )
        with self.assertRaises(ValidationError):
            ActivityTestCase.objects.create(
                activity_version=python_version,
                name="definición inválida",
                type="python.call_used",
                definition={"name": "print", "execute": True},
            )

        ActivityTestCase.objects.bulk_create(
            [
                ActivityTestCase(
                    activity_version=python_version,
                    name=f"sintaxis-{index}",
                    type="python.syntax_valid",
                    definition={},
                )
                for index in range(200)
            ]
        )
        with self.assertRaises(ValidationError):
            ActivityTestCase.objects.create(
                activity_version=python_version,
                name="sintaxis-201",
                type="python.syntax_valid",
                definition={},
            )

    def test_activity_version_language_scopes_files(self):
        bash_version = ActivityVersion(
            activity=self.activity,
            version_number=2,
            language=ActivityVersion.Language.BASH,
            starter_files={"html": "<p>no</p>"},
            created_by=self.teacher,
        )
        with self.assertRaises(ValidationError):
            bash_version.full_clean()
        valid = ActivityVersion(
            activity=self.activity,
            version_number=2,
            language=ActivityVersion.Language.BASH,
            starter_files={"bash": "#!/usr/bin/env bash\nprintf ok\n"},
            reference_solution={"bash": "#!/usr/bin/env bash\nprintf solution\n"},
            hints=["Primera pista"],
            created_by=self.teacher,
        )
        valid.full_clean()
        valid.save()
        self.assertEqual(valid.files, {"bash": "#!/usr/bin/env bash\nprintf ok\n"})

    def test_web_version_rejects_bash_files(self):
        invalid = ActivityVersion(
            activity=self.activity,
            version_number=2,
            language=ActivityVersion.Language.WEB,
            starter_files={"bash": "printf nope\n"},
            created_by=self.teacher,
        )
        with self.assertRaises(ValidationError):
            invalid.full_clean()

    def test_bash_draft_and_submission_use_only_bash_snapshot(self):
        bash_activity = Activity.objects.create(
            module=self.module,
            title="Reto Bash",
            slug="reto-bash",
            created_by=self.teacher,
            status=Activity.Status.PUBLISHED,
        )
        bash_version = ActivityVersion.objects.create(
            activity=bash_activity,
            version_number=1,
            language=ActivityVersion.Language.BASH,
            starter_files={"bash": "#!/usr/bin/env bash\n"},
            reference_solution={"bash": "#!/usr/bin/env bash\nprintf ok\n"},
            grading_mode=ActivityVersion.GradingMode.AUTOMATIC_STATIC,
            created_by=self.teacher,
        )
        bash_activity.current_version = bash_version
        bash_activity.save(update_fields=["current_version", "updated_at"])
        ActivityTestCase.objects.create(
            activity_version=bash_version,
            name="sintaxis",
            type="bash.syntax_valid",
            definition={},
        )
        assignment = Assignment.objects.create(
            activity=bash_activity,
            activity_version=bash_version,
            created_by=self.teacher,
            status=Assignment.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        bash_cohort = Cohort.objects.create(
            name="2ASIR-A",
            academic_year=self.year,
            track=Cohort.Track.BASH,
        )
        AssignmentCohort.objects.create(assignment=assignment, cohort=bash_cohort)
        set_student_cohort(self.student, bash_cohort)
        draft = get_or_create_draft(self.student, assignment)
        self.assertEqual(draft.files, {"bash": "#!/usr/bin/env bash\n"})
        submission, report = create_submission(
            self.student,
            assignment,
            {"bash": "#!/usr/bin/env bash\nprintf ok\n"},
        )
        self.assertEqual(submission.files.count(), 1)
        self.assertEqual(submission.files.get().path, "bash")
        self.assertEqual(report.score, 10)

    def test_revision_conflict_does_not_overwrite(self):
        draft = get_or_create_draft(self.student, self.assignment)
        updated = save_draft(self.student, self.assignment, {"html": "<h1>uno</h1>", "css": "", "javascript": "", "revision": draft.revision})
        self.assertEqual(updated.revision, 1)
        with self.assertRaises(DraftConflict) as raised:
            save_draft(self.student, self.assignment, {"html": "<h1>viejo</h1>", "css": "", "javascript": "", "revision": 0})
        self.assertEqual(raised.exception.draft.files["html"], "<h1>uno</h1>")
        self.assertEqual(Draft.objects.get(pk=draft.pk).files["html"], "<h1>uno</h1>")

    def test_other_student_has_no_draft_access(self):
        self.assertFalse(Assignment.objects.filter(pk=self.assignment.pk, cohort_links__cohort__enrollments__student=self.other_student).exists())

    def test_activity_version_used_by_assignment_is_append_only(self):
        self.version.instructions = "cambio no permitido"
        with self.assertRaises(ValidationError):
            self.version.save()

    def test_assigned_version_rejects_new_or_deleted_tests(self):
        with self.assertRaises(ValidationError):
            ActivityTestCase.objects.create(
                activity_version=self.version,
                name="nuevo",
                type="html.selector_exists",
                definition={"selector": "main"},
            )

        # Simulate legacy data created before the assignment was published;
        # bulk/queryset deletion must be blocked as well.
        legacy_version = ActivityVersion.objects.create(
            activity=self.activity,
            version_number=3,
            created_by=self.teacher,
        )
        legacy_test = ActivityTestCase.objects.create(
            activity_version=legacy_version,
            name="protegido",
            type="html.selector_exists",
            definition={"selector": "main"},
        )
        protected_assignment = Assignment.objects.create(
            activity=self.activity,
            activity_version=legacy_version,
            created_by=self.teacher,
            status=Assignment.Status.DRAFT,
        )
        with self.assertRaises(ValidationError), transaction.atomic():
            ActivityTestCase.objects.filter(pk=legacy_test.pk).delete()
        self.assertTrue(ActivityTestCase.objects.filter(pk=legacy_test.pk).exists())
        protected_assignment.delete()

        unlocked = ActivityVersion.objects.create(
            activity=self.activity,
            version_number=2,
            created_by=self.teacher,
        )
        test_case = ActivityTestCase.objects.create(
            activity_version=unlocked,
            name="borrable",
            type="html.selector_exists",
            definition={"selector": "main"},
        )
        test_case.delete()
        self.assertFalse(ActivityTestCase.objects.filter(pk=test_case.pk).exists())

    def test_teacher_only_sees_students_from_cohorts_they_teach(self):
        own_submission, _ = create_submission(
            self.student,
            self.assignment,
            {"html": "<main>propio</main>", "css": "", "javascript": ""},
        )
        other_teacher = User.objects.create_user(
            username="teacher2",
            password="UnaClaveSegura123!",
            role=User.Role.TEACHER,
        )
        other_cohort = Cohort.objects.create(
            name="1SMR-B",
            academic_year=self.year,
            track=Cohort.Track.WEB,
        )
        Enrollment.objects.create(cohort=other_cohort, student=self.other_student)
        TeachingAssignment.objects.create(cohort=other_cohort, teacher=other_teacher)
        AssignmentCohort.objects.create(assignment=self.assignment, cohort=other_cohort)
        other_submission, _ = create_submission(
            self.other_student,
            self.assignment,
            {"html": "<main>ajeno</main>", "css": "", "javascript": ""},
        )

        self.client.force_login(self.teacher)
        dashboard = self.client.get(reverse("teacher_dashboard"), HTTP_ACCEPT="application/json")
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.json()["assignments"][0]["submissions"], 1)
        self.assertEqual(self.client.get(reverse("teacher_review", args=[own_submission.id])).status_code, 200)
        self.assertEqual(self.client.get(reverse("teacher_review", args=[other_submission.id])).status_code, 404)
        export = self.client.get(reverse("teacher_export"))
        csv_text = export.content.decode("utf-8-sig")
        self.assertIn(self.student.username, csv_text)
        self.assertNotIn(self.other_student.username, csv_text)

    def test_student_dashboard_reload_returns_normalised_counts_and_gamification(self):
        self.client.force_login(self.student)
        initial = self.client.get(reverse("student_dashboard"), HTTP_ACCEPT="application/json")
        self.assertEqual(initial.status_code, 200)
        self.assertEqual(initial.json()["assignments"][0]["submissions"], 0)
        self.assertEqual(initial.json()["gamification"]["total_xp"], 0)

        create_submission(
            self.student,
            self.assignment,
            {"html": "<main>entrega</main>", "css": "body{}", "javascript": ""},
        )
        refreshed = self.client.get(reverse("student_dashboard"), HTTP_ACCEPT="application/json")
        self.assertEqual(refreshed.status_code, 200)
        assignment = refreshed.json()["assignments"][0]
        self.assertEqual(assignment["submissions"], 1)
        self.assertEqual(assignment["language"], "web")
        self.assertEqual(assignment["xp_reward"], 100)
        self.assertEqual(assignment["earned_xp"], 0)
        self.assertFalse(assignment["completed"])
