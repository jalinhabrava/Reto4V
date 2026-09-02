from __future__ import annotations

import hashlib
from decimal import ROUND_FLOOR, Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F, Max
from django.utils import timezone

from learning.models import Assignment, Draft, Enrollment, TestCase

from .evaluator import (
    EVALUATOR_VERSION,
    EvaluationReport,
    EvaluatorValidationError,
    evaluate_tests,
)
from .models import AuditEvent, GradeCalculation, Submission, SubmissionFile, TestResult, TestRun

FILE_KEYS = ("html", "css", "javascript")
BASH_FILE_KEYS = ("bash",)
PYTHON_FILE_KEYS = ("python",)
MAX_FILE_BYTES = 256 * 1024
MAX_TOTAL_BYTES = 1024 * 1024

XP_LEVEL_SIZE = 500
COMPLETION_SCORE = Decimal("8")

BADGE_DEFINITIONS = (
    ("first-challenge", "Primer reto", "Has completado tu primer reto."),
    ("five-challenges", "Cinco retos", "Has completado cinco retos."),
    ("web-path", "Constructor web", "Has completado un reto de HTML, CSS o JavaScript."),
    ("bash-path", "Terminal en marcha", "Has completado un reto de Bash."),
    ("python-path", "Python en marcha", "Has completado un reto de Python."),
    ("cross-path", "Doble itinerario", "Has completado retos de al menos dos itinerarios."),
    ("triple-path", "Tridente digital", "Has completado retos web, Bash y Python."),
    ("xp-500", "Medio millar", "Has alcanzado 500 XP."),
    ("perfect-score", "Reto perfecto", "Has conseguido un 10 en un reto automático."),
)


class DraftConflict(Exception):
    def __init__(self, draft: Draft):
        self.draft = draft
        super().__init__("El borrador ha cambiado en otra pestaña.")


class SubmissionError(ValidationError):
    pass


def normalise_workspace_files(payload: dict, *, language: str = "web") -> dict[str, str]:
    if not isinstance(payload, dict):
        raise EvaluatorValidationError("Los archivos deben recibirse como un objeto JSON.")
    if isinstance(payload.get("files"), dict):
        payload = payload["files"]
    if language not in {"web", "bash", "python"}:
        raise EvaluatorValidationError("El lenguaje de la actividad no es válido.")
    aliases = {"html": "html", "css": "css", "js": "javascript", "javascript": "javascript"}
    if language == "bash":
        allowed = set(BASH_FILE_KEYS)
    elif language == "python":
        allowed = set(PYTHON_FILE_KEYS)
    else:
        allowed = set(FILE_KEYS)
    files = {key: "" for key in allowed}
    total = 0
    for raw_name, raw_content in payload.items():
        if raw_name in {"revision", "csrfmiddlewaretoken"}:
            continue
        raw_key = str(raw_name).lower()
        if language == "bash":
            key = "bash" if raw_key == "bash" else None
        elif language == "python":
            key = "python" if raw_key in {"python", "main.py"} else None
        else:
            key = aliases.get(raw_key)
        if key is None or key not in allowed:
            expected = {
                "bash": "bash",
                "python": "python (main.py)",
                "web": "html, css y javascript",
            }[language]
            raise EvaluatorValidationError(f"Solo se permiten {expected} en esta actividad.")
        if not isinstance(raw_content, str):
            raise EvaluatorValidationError(f"El archivo {raw_name} debe ser texto.")
        size = len(raw_content.encode("utf-8"))
        if size > MAX_FILE_BYTES:
            raise EvaluatorValidationError(f"El archivo {raw_name} supera 256 KiB.")
        files[key] = raw_content
        total += size
    if total > MAX_TOTAL_BYTES:
        raise EvaluatorValidationError("El conjunto de archivos supera 1 MiB.")
    return files


def student_assignment_or_404(user, assignment_id: str) -> Assignment:
    if not user.is_authenticated or user.role != "student":
        raise PermissionDenied("Solo los alumnos pueden abrir este espacio de trabajo.")
    return (
        Assignment.objects.select_related("activity", "activity_version", "activity_version__activity")
        .filter(
            pk=assignment_id,
            status__in=(Assignment.Status.PUBLISHED, Assignment.Status.CLOSED),
            cohort_links__cohort__enrollments__student=user,
            cohort_links__cohort__enrollments__active=True,
            cohort_links__cohort__active=True,
            cohort_links__cohort__academic_year__active=True,
            cohort_links__cohort__track=F("activity_version__language"),
        )
        .distinct()
        .first()
    )


def get_or_create_draft(user, assignment: Assignment) -> Draft:
    defaults = {"activity_version": assignment.activity_version, "files": assignment.activity_version.files}
    try:
        draft, created = Draft.objects.get_or_create(assignment=assignment, student=user, defaults=defaults)
    except IntegrityError:
        draft = Draft.objects.get(assignment=assignment, student=user)
        created = False
    if not created and draft.activity_version_id != assignment.activity_version_id:
        # This should be impossible due to the assignment/version constraint;
        # fail closed if old data was imported incorrectly.
        raise ValidationError("El borrador no coincide con la versión asignada.")
    return draft


def save_draft(user, assignment: Assignment, payload: dict) -> Draft:
    expected_revision = payload.get("revision")
    if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 0:
        raise ValidationError("revision debe ser un entero no negativo.")
    files = normalise_workspace_files(payload.get("files", payload), language=assignment.activity_version.language)
    with transaction.atomic():
        draft = get_or_create_draft(user, assignment)
        draft = Draft.objects.select_for_update().get(pk=draft.pk)
        if draft.revision != expected_revision:
            raise DraftConflict(draft)
        updated = (
            Draft.objects.filter(pk=draft.pk, revision=expected_revision)
            .update(files=files, revision=expected_revision + 1, updated_at=timezone.now())
        )
        if updated != 1:
            current = Draft.objects.get(pk=draft.pk)
            raise DraftConflict(current)
        return Draft.objects.get(pk=draft.pk)


def _file_digest(files: dict[str, str], *, language: str = "web") -> str:
    digest = hashlib.sha256()
    keys = {
        "bash": BASH_FILE_KEYS,
        "python": PYTHON_FILE_KEYS,
        "web": FILE_KEYS,
    }.get(language)
    if keys is None:
        raise EvaluatorValidationError("El lenguaje de la actividad no es válido.")
    for key in keys:
        content = files.get(key, "")
        digest.update(key.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _test_cases_for(assignment: Assignment, *, public_only=False):
    query = assignment.activity_version.test_cases.all()
    if public_only:
        query = query.filter(visibility=TestCase.Visibility.PUBLIC)
    return list(query)


def run_formative_tests(user, assignment: Assignment, files: dict) -> EvaluationReport:
    files = normalise_workspace_files(files, language=assignment.activity_version.language)
    cases = _test_cases_for(assignment, public_only=True)
    return evaluate_tests(files, cases, public_only=True, language=assignment.activity_version.language)


def _score_for_submission(assignment: Assignment, files: dict) -> EvaluationReport | None:
    mode = assignment.activity_version.grading_mode
    if mode not in {assignment.activity_version.GradingMode.AUTOMATIC_STATIC, assignment.activity_version.GradingMode.HYBRID}:
        return None
    return evaluate_tests(files, _test_cases_for(assignment), public_only=False, language=assignment.activity_version.language)


def create_submission(user, assignment: Assignment, payload: dict) -> tuple[Submission, EvaluationReport | None]:
    files = normalise_workspace_files(payload.get("files", payload), language=assignment.activity_version.language)
    report = _score_for_submission(assignment, files)
    now = timezone.now()
    with transaction.atomic():
        # Serialising on the assignment makes attempt allocation deterministic
        # on PostgreSQL.  The unique constraint remains the final guard for
        # alternate database backends and imported data.
        locked_assignment = Assignment.objects.select_for_update().select_related("activity_version").get(pk=assignment.pk)
        if not locked_assignment.is_open_for(now):
            raise SubmissionError("La actividad está cerrada o fuera de su ventana de entrega.")
        if not Enrollment.objects.filter(
            student=user,
            active=True,
            cohort__assignment_links__assignment=locked_assignment,
            cohort__active=True,
            cohort__academic_year__active=True,
            cohort__track=locked_assignment.activity_version.language,
        ).exists():
            raise PermissionDenied("No estás matriculado en esta actividad.")
        latest = Submission.objects.filter(assignment=locked_assignment, student=user).aggregate(max_attempt=Max("attempt_number"))["max_attempt"]
        attempt = (latest or 0) + 1
        if locked_assignment.max_attempts and attempt > locked_assignment.max_attempts:
            raise SubmissionError("Has agotado el número de intentos permitido.")
        is_late = bool(locked_assignment.due_at and now > locked_assignment.due_at)
        status = Submission.Status.INFRA_ERROR if report and report.status == "infra_error" else Submission.Status.GRADED
        auto_score = report.score if report and report.status != "infra_error" else None
        submission = Submission.objects.create(
            assignment=locked_assignment,
            activity_version=locked_assignment.activity_version,
            student=user,
            attempt_number=attempt,
            status=status,
            is_late=is_late,
            auto_score=auto_score,
            files_digest=_file_digest(files, language=locked_assignment.activity_version.language),
            metadata={"evaluator_version": EVALUATOR_VERSION} if report else {},
        )
        SubmissionFile.objects.bulk_create(
            [
                SubmissionFile(
                    submission=submission,
                    path=key,
                    content=files[key],
                    size_bytes=len(files[key].encode("utf-8")),
                    sha256=hashlib.sha256(files[key].encode("utf-8")).hexdigest(),
                )
                for key in {
                    "bash": BASH_FILE_KEYS,
                    "python": PYTHON_FILE_KEYS,
                    "web": FILE_KEYS,
                }[locked_assignment.activity_version.language]
            ]
        )
        if report is not None:
            test_run = TestRun.objects.create(
                submission=submission,
                activity_version=locked_assignment.activity_version,
                evaluator_version=EVALUATOR_VERSION,
                status={"passed": TestRun.Status.PASSED, "failed": TestRun.Status.FAILED, "infra_error": TestRun.Status.INFRA_ERROR}[report.status],
                passed_points=report.passed_points,
                total_points=report.total_points,
                score=report.score,
                finished_at=timezone.now(),
                error_message=report.error_message,
            )
            TestResult.objects.bulk_create(
                [
                    TestResult(
                        test_run=test_run,
                        test_case_id=getattr(case, "id", None),
                        name=result.name,
                        type=result.type,
                        passed=result.passed,
                        status=result.status,
                        points=result.points,
                        earned_points=result.earned_points,
                        feedback=result.feedback,
                        detail=result.detail,
                        position=index,
                    )
                    for index, (case, result) in enumerate(zip(_test_cases_for(locked_assignment), report.results, strict=True))
                ]
            )
            mode = locked_assignment.activity_version.grading_mode
            auto_weight = locked_assignment.activity_version.auto_weight
            manual_weight = locked_assignment.activity_version.manual_weight
            grade_status = GradeCalculation.Status.READY if mode == locked_assignment.activity_version.GradingMode.AUTOMATIC_STATIC else GradeCalculation.Status.PENDING_REVIEW
            final_score = auto_score if mode == locked_assignment.activity_version.GradingMode.AUTOMATIC_STATIC else None
            GradeCalculation.objects.create(
                submission=submission,
                activity_version=locked_assignment.activity_version,
                auto_score=auto_score,
                final_score=final_score,
                auto_weight=auto_weight,
                manual_weight=manual_weight,
                status=grade_status,
                breakdown={"passed_points": str(report.passed_points), "total_points": str(report.total_points)},
            )
        AuditEvent.objects.create(actor=user, action="submission.created", object_type="submission", object_id=str(submission.pk), metadata={"attempt": attempt})
        return submission, report


def create_manual_grade(*, actor, submission: Submission, score: Decimal | None, comment: str = "", publish=False, reason: str = "") -> GradeCalculation:
    if actor.role not in {"admin", "teacher"} and not actor.is_superuser:
        raise PermissionDenied("Solo el profesorado puede calificar.")
    if score is not None:
        try:
            score = Decimal(str(score))
        except (ArithmeticError, TypeError, ValueError):
            raise ValidationError("La nota debe ser un número entre 0 y 10.") from None
        if not score.is_finite() or score < 0 or score > 10:
            raise ValidationError("La nota debe estar entre 0 y 10.")
    latest = submission.grade_calculations.filter(status__in=[GradeCalculation.Status.DRAFT, GradeCalculation.Status.READY, GradeCalculation.Status.PENDING_REVIEW, GradeCalculation.Status.PUBLISHED]).first()
    auto_score = latest.auto_score if latest else submission.auto_score
    version = submission.activity_version
    auto_weight, manual_weight = version.auto_weight, version.manual_weight
    if auto_weight + manual_weight > 1:
        raise ValidationError("Los pesos de la actividad no son válidos.")
    if score is None and manual_weight > 0:
        final_score = None
        status = GradeCalculation.Status.PENDING_REVIEW
    elif auto_score is None and auto_weight > 0:
        final_score = None
        status = GradeCalculation.Status.PENDING_REVIEW
    else:
        final_score = ((auto_score or Decimal("0")) * auto_weight) + ((score or Decimal("0")) * manual_weight)
        status = GradeCalculation.Status.PUBLISHED if publish else GradeCalculation.Status.READY
    calculation = GradeCalculation.objects.create(
        submission=submission,
        activity_version=version,
        auto_score=auto_score,
        manual_score=score,
        final_score=final_score,
        auto_weight=auto_weight,
        manual_weight=manual_weight,
        status=status,
        teacher_comment=comment,
        actor=actor,
        published_at=timezone.now() if status == GradeCalculation.Status.PUBLISHED else None,
    )
    if reason:
        AuditEvent.objects.create(actor=actor, action="grade.override", object_type="submission", object_id=str(submission.pk), metadata={"reason": reason, "score": str(score) if score is not None else None})
    AuditEvent.objects.create(actor=actor, action="grade.published" if status == GradeCalculation.Status.PUBLISHED else "grade.saved", object_type="grade_calculation", object_id=str(calculation.pk), metadata={})
    return calculation


def _valid_automatic_score(submission: Submission) -> Decimal | None:
    """Return an evaluator score suitable for XP, never a teacher grade."""

    if submission.status != Submission.Status.GRADED or submission.auto_score is None:
        return None
    try:
        score = Decimal(str(submission.auto_score))
    except (ArithmeticError, TypeError, ValueError):
        return None
    if not score.is_finite() or score < Decimal("0") or score > Decimal("10"):
        return None
    return score


def _assignment_gamification(assignment: Assignment, submissions: list[Submission]) -> dict:
    scores = [score for submission in submissions if (score := _valid_automatic_score(submission)) is not None]
    best_score = max(scores) if scores else None
    reward = max(0, int(assignment.activity_version.xp_reward or 0))
    if best_score is None:
        earned_xp = 0
        progress = 0
    else:
        earned_xp = int(
            (Decimal(reward) * best_score / Decimal("10")).to_integral_value(rounding=ROUND_FLOOR)
        )
        progress = min(100, int((best_score * Decimal("10")).to_integral_value(rounding=ROUND_FLOOR)))
    return {
        "assignment_id": str(assignment.id),
        "language": assignment.activity_version.language,
        "difficulty": assignment.activity_version.difficulty,
        "xp_reward": reward,
        "earned_xp": earned_xp,
        "best_score": format(best_score.normalize(), "f") if best_score is not None else None,
        "completed": bool(best_score is not None and best_score >= COMPLETION_SCORE),
        "progress": progress,
    }


def gamification_for_assignments(student, assignments) -> dict:
    """Derive private, non-ranking XP from each student's best auto score.

    XP is intentionally not persisted: repeated attempts cannot farm points,
    because only the best valid automatic score per assignment contributes.
    The helper consumes the ``student_submissions`` prefetch attribute when
    present, otherwise performs one bounded query for all assignments.
    """

    assignment_list = list(assignments)
    assignment_ids = [assignment.pk for assignment in assignment_list]
    submissions_by_assignment: dict[object, list[Submission]] = {}
    prefetched = all(hasattr(assignment, "student_submissions") for assignment in assignment_list)
    if prefetched:
        submissions_by_assignment = {
            assignment.pk: list(assignment.student_submissions) for assignment in assignment_list
        }
    elif assignment_ids:
        submissions = Submission.objects.filter(
            student=student,
            assignment_id__in=assignment_ids,
        ).only("assignment_id", "status", "auto_score")
        for submission in submissions:
            submissions_by_assignment.setdefault(submission.assignment_id, []).append(submission)
    challenge_rows = [
        _assignment_gamification(assignment, submissions_by_assignment.get(assignment.pk, []))
        for assignment in assignment_list
    ]
    total_xp = sum(row["earned_xp"] for row in challenge_rows)
    completed_rows = [row for row in challenge_rows if row["completed"]]
    level = total_xp // XP_LEVEL_SIZE + 1
    level_xp = total_xp % XP_LEVEL_SIZE
    level_progress = int(level_xp * 100 // XP_LEVEL_SIZE)
    xp_to_next_level = XP_LEVEL_SIZE - level_xp
    if level_xp == 0 and total_xp > 0:
        level_progress = 0
        xp_to_next_level = XP_LEVEL_SIZE
    languages = {row["language"] for row in completed_rows}
    best_scores = [Decimal(row["best_score"]) for row in completed_rows if row["best_score"] is not None]
    badges = []
    badge_state = {
        "first-challenge": len(completed_rows) >= 1,
        "five-challenges": len(completed_rows) >= 5,
        "web-path": "web" in languages,
        "bash-path": "bash" in languages,
        "python-path": "python" in languages,
        "cross-path": len(languages) >= 2,
        "triple-path": {"web", "bash", "python"}.issubset(languages),
        "xp-500": total_xp >= 500,
        "perfect-score": any(score >= Decimal("10") for score in best_scores),
    }
    for badge_id, title, description in BADGE_DEFINITIONS:
        if badge_state[badge_id]:
            badges.append({"id": badge_id, "title": title, "description": description})
    return {
        "total_xp": total_xp,
        "level": level,
        "level_progress": level_progress,
        "xp_to_next_level": xp_to_next_level,
        "completed_challenges": len(completed_rows),
        "badges": badges,
        "assignments": challenge_rows,
    }


def gamification_for_assignment(student, assignment, submissions=None) -> dict:
    """Return one assignment's XP row using supplied submissions when available."""

    if submissions is None:
        data = gamification_for_assignments(student, [assignment])
    else:
        assignment.student_submissions = list(submissions)
        data = gamification_for_assignments(student, [assignment])
    return data["assignments"][0]
