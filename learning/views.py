from __future__ import annotations

import csv
import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import F, Prefetch
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from accounts.models import User
from accounts.permissions import role_required
from grading.evaluator import EvaluationReport, EvaluatorValidationError
from grading.models import GradeCalculation, Submission
from grading.services import (
    DraftConflict,
    create_manual_grade,
    create_submission,
    gamification_for_assignment,
    gamification_for_assignments,
    get_or_create_draft,
    run_formative_tests,
    save_draft,
    student_assignment_or_404,
)

from .models import Assignment, Cohort, Draft

MAX_JSON_BODY = 2 * 1024 * 1024


def _user_payload(user):
    effective_role = User.Role.ADMIN if user.is_superuser else user.role
    groups = []
    tracks = []
    cohort_payload = None
    if effective_role == User.Role.STUDENT:
        active_enrollments = list(
            user.enrollments.filter(
                active=True,
                cohort__active=True,
                cohort__academic_year__active=True,
            )
            .select_related("cohort", "cohort__academic_year")
            .order_by("enrolled_at", "id")
        )
        groups = [enrollment.cohort.name for enrollment in active_enrollments]
        tracks = [enrollment.cohort.track for enrollment in active_enrollments]
        if active_enrollments:
            cohort = active_enrollments[0].cohort
            cohort_payload = {
                "id": str(cohort.pk),
                "name": cohort.name,
                "track": cohort.track,
                "track_label": cohort.get_track_display(),
                "academic_year": cohort.academic_year.name,
                "active": bool(cohort.active and cohort.academic_year.active),
            }
    elif effective_role == User.Role.TEACHER:
        groups = list(
            user.teaching_assignments.filter(active=True)
            .values_list("cohort__name", flat=True)
            .distinct()
        )
    return {
        "id": user.pk,
        "username": user.username,
        "display_name": user.display_name,
        "role": effective_role,
        "groups": groups,
        "group": groups[0] if groups else "",
        "tracks": tracks,
        "track": tracks[0] if tracks else "",
        "cohort": cohort_payload,
    }


def _json_body(request) -> dict:
    if request.content_type == "application/json" or request.body[:1] in {b"{", b"["}:
        if len(request.body) > MAX_JSON_BODY:
            raise ValidationError("La petición supera el límite de tamaño.")
        try:
            value = json.loads(request.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValidationError("El JSON no es válido.") from None
        if not isinstance(value, dict):
            raise ValidationError("El cuerpo debe ser un objeto JSON.")
        return value
    return {key: request.POST.get(key) for key in request.POST}


def _decimal(value):
    if value is None:
        return None
    try:
        return str(Decimal(str(value)))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _report_payload(report: EvaluationReport | None, *, visible_results: list[bool] | None = None):
    if report is None:
        return None
    payload = report.as_dict()
    payload["score"] = _decimal(report.score)
    payload["passed_points"] = _decimal(report.passed_points)
    payload["total_points"] = _decimal(report.total_points)
    # The browser contract uses points as the maximum and keeps earned points
    # separately, while the DB retains full Decimal precision.
    result_rows = report.results
    if visible_results is not None:
        # The official score may include private tests, but their names,
        # definitions, feedback and individual outcomes must never be sent to
        # a student.  Test ordering is fixed by TestCase.Meta and is the same
        # ordering used by the evaluator.
        result_rows = [
            result
            for result, visible in zip(report.results, visible_results, strict=False)
            if visible
        ]
    payload["results"] = [
        {
            "name": result.name,
            "type": result.type,
            "passed": result.passed,
            "status": result.status,
            "feedback": result.feedback,
            "points": _decimal(result.points),
            "earned_points": _decimal(result.earned_points),
            "detail": result.detail,
        }
        for result in result_rows
    ]
    return payload


def _activity_public_payload(assignment: Assignment, draft: Draft | None = None, submissions=None, *, student=None):
    version = assignment.activity_version
    public_tests = [
        {
            "id": str(test.id),
            "name": test.name,
            "type": test.type,
            "definition": test.definition,
            "points": _decimal(test.points),
            "feedback": test.feedback,
        }
        for test in version.test_cases.filter(visibility="public")
    ]
    payload = {
        "id": str(assignment.id),
        "title": assignment.title,
        "status": assignment.status,
        "opens_at": assignment.opens_at.isoformat() if assignment.opens_at else None,
        "due_at": assignment.due_at.isoformat() if assignment.due_at else None,
        "max_attempts": assignment.max_attempts,
        "attempt_policy": assignment.attempt_policy,
        "weight": assignment.weight,
        "activity": {
            "id": str(assignment.activity_id),
            "title": assignment.activity.title,
            "kind": assignment.activity.kind,
            "module": assignment.activity.module.title,
        },
        "version": {
            "id": str(version.id),
            "number": version.version_number,
            "language": version.language,
            "difficulty": version.difficulty,
            "xp_reward": version.xp_reward,
            "hints": version.hints,
            "instructions": version.instructions,
            "objectives": version.objectives,
            "learning_outcomes": version.learning_outcomes,
            "assessment_criteria": version.assessment_criteria,
            "professional_module_code": version.professional_module_code,
            "curriculum_scope": version.curriculum_scope,
            "curriculum_edition": version.curriculum_edition,
            "curriculum_unit": version.curriculum_unit,
            "curriculum_source": version.curriculum_source,
            "files": version.files,
            "grading_mode": version.grading_mode,
            "auto_weight": _decimal(version.auto_weight),
            "manual_weight": _decimal(version.manual_weight),
            "public_tests": public_tests,
        },
        "draft": {"id": str(draft.id), "files": draft.files, "revision": draft.revision, "updated_at": draft.updated_at.isoformat()} if draft else None,
        "submissions": [
            {
                "id": str(submission.id),
                "attempt_number": submission.attempt_number,
                "submitted_at": submission.submitted_at.isoformat(),
                "status": submission.status,
                "is_late": submission.is_late,
                "auto_score": _decimal(submission.auto_score),
                "published_score": _decimal(_published_grade(submission).final_score if _published_grade(submission) else None),
            }
            for submission in (submissions or [])
        ],
    }
    if student is not None:
        payload["gamification"] = gamification_for_assignment(student, assignment, submissions)
    return payload


def _dashboard_payload(rows, gamification=None):
    return {
        "assignments": [
            {
                "id": str(row["assignment"].id),
                "title": row["assignment"].title,
                "status": row["status"],
                "due_at": row["assignment"].due_at.isoformat() if row["assignment"].due_at else None,
                "module": row["assignment"].activity.module.title,
                "professional_module_code": row["assignment"].activity_version.professional_module_code,
                "language": row["assignment"].activity_version.language,
                "difficulty": row["assignment"].activity_version.difficulty,
                "xp_reward": row["assignment"].activity_version.xp_reward,
                "curriculum_scope": row["assignment"].activity_version.curriculum_scope,
                "curriculum_edition": row["assignment"].activity_version.curriculum_edition,
                "learning_outcomes": row["assignment"].activity_version.learning_outcomes,
                "assessment_criteria": row["assignment"].activity_version.assessment_criteria,
                "submissions": row.get("submissions", 0),
                "graded": row.get("graded", 0),
                "earned_xp": row.get("gamification", {}).get("earned_xp", 0),
                "completed": row.get("gamification", {}).get("completed", False),
                "progress": row.get("gamification", {}).get("progress", 0),
            }
            for row in rows
        ],
        "gamification": gamification
        or {"total_xp": 0, "level": 1, "level_progress": 0, "xp_to_next_level": 500, "completed_challenges": 0, "badges": []},
    }


@login_required
@ensure_csrf_cookie
def student_dashboard(request):
    if request.user.role != User.Role.STUDENT:
        return redirect("teacher_dashboard")
    assignments = list(
        Assignment.objects.select_related("activity", "activity__module", "activity_version")
        .prefetch_related(
            Prefetch(
                "submissions",
                queryset=Submission.objects.filter(student=request.user).order_by("-attempt_number").prefetch_related("grade_calculations"),
                to_attr="student_submissions",
            ),
            Prefetch(
                "drafts",
                queryset=Draft.objects.filter(student=request.user),
                to_attr="student_drafts",
            ),
        )
        .filter(
            status__in=(Assignment.Status.PUBLISHED, Assignment.Status.CLOSED),
            cohort_links__cohort__enrollments__student=request.user,
            cohort_links__cohort__enrollments__active=True,
            cohort_links__cohort__active=True,
            cohort_links__cohort__academic_year__active=True,
            cohort_links__cohort__track=F("activity_version__language"),
        )
        .order_by("activity__module__position", "activity__title", "id")
        .distinct()
    )
    rows = []
    for assignment in assignments:
        submissions = list(getattr(assignment, "student_submissions", []))
        draft = next(iter(getattr(assignment, "student_drafts", [])), None)
        if submissions:
            status = "graded" if any(_published_grade(s) for s in submissions) else "submitted"
        elif draft and draft.revision:
            status = "in_progress"
        elif assignment.due_at and timezone.now() > assignment.due_at:
            status = "overdue"
        else:
            status = "not_started"
        rows.append({"assignment": assignment, "status": status, "draft": draft, "submissions": submissions})
    gamification = gamification_for_assignments(request.user, assignments)
    gamification_by_assignment = {row["assignment_id"]: row for row in gamification["assignments"]}
    for row in rows:
        row["gamification"] = gamification_by_assignment.get(str(row["assignment"].id), {})
        row["submissions"] = len(row["submissions"])
        row["graded"] = sum(
            1
            for submission in getattr(row["assignment"], "student_submissions", [])
            if _published_grade(submission)
        )
    if request.headers.get("Accept") == "application/json":
        return JsonResponse(_dashboard_payload(rows, gamification))
    user_payload = _user_payload(request.user)
    return render(request, "student/dashboard.html", {"assignment_rows": rows, "user_payload": user_payload, "bootstrap": {"user": user_payload, "dashboard": _dashboard_payload(rows, gamification)}})


@login_required
@ensure_csrf_cookie
def workspace_page(request, assignment_id):
    assignment = student_assignment_or_404(request.user, assignment_id)
    if assignment is None:
        raise Http404
    draft = get_or_create_draft(request.user, assignment)
    submissions = list(Submission.objects.filter(assignment=assignment, student=request.user).prefetch_related("grade_calculations"))
    payload = _activity_public_payload(assignment, draft=draft, submissions=submissions, student=request.user)
    if request.headers.get("Accept") == "application/json":
        return JsonResponse(payload)
    user_payload = _user_payload(request.user)
    return render(request, "learning/workspace.html", {"assignment": assignment, "workspace": payload, "user_payload": user_payload, "bootstrap": {"user": user_payload, "workspace": payload}})


@login_required
@ensure_csrf_cookie
@require_GET
def workspace_detail_api(request, assignment_id):
    assignment = student_assignment_or_404(request.user, assignment_id)
    if assignment is None:
        raise Http404
    draft = get_or_create_draft(request.user, assignment)
    submissions = list(Submission.objects.filter(assignment=assignment, student=request.user).prefetch_related("grade_calculations"))
    return JsonResponse(_activity_public_payload(assignment, draft=draft, submissions=submissions, student=request.user))


@login_required
@ensure_csrf_cookie
@require_http_methods(["GET", "POST"])
def workspace_draft_api(request, assignment_id):
    assignment = student_assignment_or_404(request.user, assignment_id)
    if assignment is None:
        raise Http404
    if request.method == "GET":
        draft = get_or_create_draft(request.user, assignment)
        response = JsonResponse({"id": str(draft.id), "files": draft.files, "revision": draft.revision, "updated_at": draft.updated_at.isoformat()})
        response["ETag"] = f'"{draft.revision}"'
        return response
    try:
        payload = _json_body(request)
        if "revision" not in payload:
            match = request.headers.get("If-Match", "").strip().strip('"')
            if match.isdigit():
                payload["revision"] = int(match)
        draft = save_draft(request.user, assignment, payload)
    except DraftConflict as conflict:
        response = JsonResponse({"detail": "El borrador ha cambiado en otra pestaña.", "revision": conflict.draft.revision, "current": {"files": conflict.draft.files, "updated_at": conflict.draft.updated_at.isoformat()}}, status=409)
        response["ETag"] = f'"{conflict.draft.revision}"'
        return response
    except (ValidationError, EvaluatorValidationError) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    response = JsonResponse({"revision": draft.revision, "saved_at": draft.updated_at.isoformat()})
    response["ETag"] = f'"{draft.revision}"'
    return response


@login_required
@require_POST
def workspace_tests_api(request, assignment_id):
    assignment = student_assignment_or_404(request.user, assignment_id)
    if assignment is None:
        raise Http404
    try:
        payload = _json_body(request)
        report = run_formative_tests(request.user, assignment, payload)
    except (ValidationError, EvaluatorValidationError) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    return JsonResponse(_report_payload(report))


@login_required
@require_POST
def workspace_submit_api(request, assignment_id):
    assignment = student_assignment_or_404(request.user, assignment_id)
    if assignment is None:
        raise Http404
    try:
        payload = _json_body(request)
        submission, report = create_submission(request.user, assignment, payload)
    except PermissionDenied as exc:
        return JsonResponse({"detail": str(exc)}, status=403)
    except (ValidationError, EvaluatorValidationError) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    public_result_mask = None
    if report is not None:
        public_result_mask = [
            test.visibility == test.Visibility.PUBLIC
            for test in assignment.activity_version.test_cases.all()
        ]
    body = {
        "submission": {
            "id": str(submission.id),
            "attempt_number": submission.attempt_number,
            "submitted_at": submission.submitted_at.isoformat(),
            "status": submission.status,
            "is_late": submission.is_late,
        },
        "report": _report_payload(report, visible_results=public_result_mask),
        # Return the server-derived row immediately so the workspace can
        # refresh XP/completion without requiring a second dashboard request.
        "gamification": gamification_for_assignment(request.user, assignment),
    }
    if request.headers.get("Accept") == "application/json" or request.content_type == "application/json":
        return JsonResponse(body, status=201)
    return redirect("student_submission", submission_id=submission.id)


@login_required
def student_submission(request, submission_id):
    submission = get_object_or_404(Submission.objects.prefetch_related("files", "test_runs__results", "grade_calculations"), pk=submission_id, student=request.user)
    if request.headers.get("Accept") == "application/json":
        grade = submission.grade_calculations.filter(status="published").first()
        return JsonResponse({"id": str(submission.id), "attempt_number": submission.attempt_number, "submitted_at": submission.submitted_at.isoformat(), "status": submission.status, "files": {file.path: file.content for file in submission.files.all()}, "grade": {"score": _decimal(grade.final_score), "comment": grade.teacher_comment} if grade else None})
    return render(request, "grading/submission.html", {"submission": submission})


def teacher_assignments_for(user):
    queryset = Assignment.objects.select_related("activity", "activity__module", "activity_version").prefetch_related("cohort_links__cohort").order_by("activity__module__position", "activity__title", "id")
    if user.is_superuser or user.role == User.Role.ADMIN:
        return queryset
    return queryset.filter(cohort_links__cohort__teaching_assignments__teacher=user, cohort_links__cohort__teaching_assignments__active=True).distinct()


def teacher_students_for_assignment(user, assignment):
    filters = {
        "enrollments__active": True,
        "enrollments__cohort__assignment_links__assignment": assignment,
        "is_active": True,
        "role": User.Role.STUDENT,
    }
    if not (user.is_superuser or user.role == User.Role.ADMIN):
        filters.update(
            {
                "enrollments__cohort__teaching_assignments__teacher": user,
                "enrollments__cohort__teaching_assignments__active": True,
            }
        )
    return User.objects.filter(**filters).distinct().order_by("username")


def teacher_cohorts_for_assignment(user, assignment):
    cohorts = Cohort.objects.filter(assignment_links__assignment=assignment)
    if not (user.is_superuser or user.role == User.Role.ADMIN):
        cohorts = cohorts.filter(teaching_assignments__teacher=user, teaching_assignments__active=True)
    return cohorts.distinct().order_by("name")


def _published_grade(submission):
    prefetched = getattr(submission, "_prefetched_objects_cache", {}).get("grade_calculations")
    calculations = prefetched if prefetched is not None else submission.grade_calculations.all()
    return next(
        (calculation for calculation in calculations if calculation.status == GradeCalculation.Status.PUBLISHED),
        None,
    )


def _select_attempt(assignment, submissions):
    """Return selected submission, published calculation and optional aggregate score."""

    ordered = sorted(submissions, key=lambda item: item.attempt_number)
    if not ordered:
        return None, None, None
    if assignment.attempt_policy == Assignment.AttemptPolicy.LATEST_BEFORE_DUE:
        eligible = [item for item in ordered if not assignment.due_at or item.submitted_at <= assignment.due_at]
        selected = eligible[-1] if eligible else None
        return selected, _published_grade(selected) if selected else None, None
    if assignment.attempt_policy == Assignment.AttemptPolicy.BEST:
        candidates = []
        for submission in ordered:
            grade = _published_grade(submission)
            if grade and grade.final_score is not None and grade.final_score.is_finite():
                candidates.append((submission, grade))
        if candidates:
            selected, grade = max(
                candidates,
                key=lambda item: (item[1].final_score, item[0].attempt_number),
            )
            return selected, grade, None
        selected = ordered[-1]
        return selected, _published_grade(selected), None
    if assignment.attempt_policy == Assignment.AttemptPolicy.AVERAGE:
        candidates = []
        for submission in ordered:
            grade = _published_grade(submission)
            if grade and grade.final_score is not None and grade.final_score.is_finite():
                candidates.append((submission, grade))
        if not candidates:
            selected = ordered[-1]
            return selected, _published_grade(selected), None
        total = sum((grade.final_score for _, grade in candidates), Decimal("0"))
        selected, grade = candidates[-1]
        return selected, grade, total / Decimal(len(candidates))
    selected = ordered[-1]
    return selected, _published_grade(selected), None


@role_required("teacher", "admin")
@ensure_csrf_cookie
def teacher_dashboard(request):
    assignments = list(teacher_assignments_for(request.user))
    rows = []
    reviews = []
    for assignment in assignments:
        visible_students = teacher_students_for_assignment(request.user, assignment)
        submissions = list(
            Submission.objects.filter(assignment=assignment, student__in=visible_students)
            .select_related("student")
            .prefetch_related("grade_calculations")
        )
        published_count = sum(1 for submission in submissions if _published_grade(submission))
        rows.append({"assignment": assignment, "submissions": len(submissions), "graded": published_count})
        for submission in submissions:
            if _published_grade(submission):
                continue
            latest_calculation = submission.grade_calculations.first()
            reviews.append(
                {
                    "id": str(submission.id),
                    "student": submission.student.display_name,
                    "username": submission.student.username,
                    "assignment": assignment.title,
                    "attempt_number": submission.attempt_number,
                    "submitted_at": submission.submitted_at.isoformat(),
                    "auto_score": _decimal(submission.auto_score),
                    "grade_status": latest_calculation.status if latest_calculation else "pending_review",
                    "url": f"/teacher/review/{submission.id}/",
                }
            )
    reviews.sort(key=lambda item: item["submitted_at"], reverse=True)
    assignments_payload = [
        {
            "id": str(row["assignment"].id),
            "title": row["assignment"].title,
            "module": row["assignment"].activity.module.title,
            "professional_module_code": row["assignment"].activity_version.professional_module_code,
            "language": row["assignment"].activity_version.language,
            "difficulty": row["assignment"].activity_version.difficulty,
            "xp_reward": row["assignment"].activity_version.xp_reward,
            "curriculum_scope": row["assignment"].activity_version.curriculum_scope,
            "curriculum_edition": row["assignment"].activity_version.curriculum_edition,
            "learning_outcomes": row["assignment"].activity_version.learning_outcomes,
            "assessment_criteria": row["assignment"].activity_version.assessment_criteria,
            "submissions": row["submissions"],
            "graded": row["graded"],
        }
        for row in rows
    ]
    dashboard_payload = {
        "assignments": assignments_payload,
        "reviews": reviews[:20],
        "pending_reviews": len(reviews),
    }
    if request.headers.get("Accept") == "application/json":
        return JsonResponse(dashboard_payload)
    user_payload = _user_payload(request.user)
    return render(
        request,
        "teacher/dashboard.html",
        {
            "assignment_rows": rows,
            "user_payload": user_payload,
            "bootstrap": {"user": user_payload, "dashboard": dashboard_payload},
        },
    )


@role_required("teacher", "admin")
@require_http_methods(["GET", "POST"])
def teacher_review(request, submission_id):
    submission = get_object_or_404(Submission.objects.select_related("assignment", "activity_version", "student").prefetch_related("files", "test_runs__results", "grade_calculations"), pk=submission_id)
    if (
        not teacher_assignments_for(request.user).filter(pk=submission.assignment_id).exists()
        or not teacher_students_for_assignment(request.user, submission.assignment).filter(pk=submission.student_id).exists()
    ):
        raise Http404
    if request.method == "POST":
        wants_json = request.content_type == "application/json" or request.headers.get("Accept") == "application/json"
        try:
            payload = _json_body(request)
            score = payload.get("manual_score")
            if score == "":
                score = None
            comment = str(payload.get("comment", ""))[:10_000]
            publish_value = payload.get("publish", False)
            if not isinstance(publish_value, bool):
                if isinstance(publish_value, str) and publish_value.lower() in {"1", "true", "on", "yes", "sí", "si"}:
                    publish_value = True
                elif isinstance(publish_value, str) and publish_value.lower() in {"0", "false", "off", "no", ""}:
                    publish_value = False
                else:
                    raise ValidationError("publish debe ser un valor booleano.")
            calculation = create_manual_grade(actor=request.user, submission=submission, score=score, comment=comment, publish=publish_value, reason=str(payload.get("reason", ""))[:2_000])
        except (ValidationError, PermissionDenied) as exc:
            if wants_json:
                return JsonResponse({"detail": str(exc)}, status=400)
            messages.error(request, str(exc))
            return redirect("teacher_review", submission_id=submission.id)
        if wants_json:
            return JsonResponse({"id": str(calculation.id), "status": calculation.status, "final_score": _decimal(calculation.final_score)})
        messages.success(
            request,
            "Calificación publicada." if calculation.status == GradeCalculation.Status.PUBLISHED else "Calificación guardada.",
        )
        return redirect("teacher_review", submission_id=submission.id)
    return render(
        request,
        "grading/review.html",
        {
            "submission": submission,
            "latest_calculation": submission.grade_calculations.first(),
            "published_calculation": submission.grade_calculations.filter(status=GradeCalculation.Status.PUBLISHED).first(),
        },
    )


def _csv_safe(value):
    text = "" if value is None else str(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


@role_required("teacher", "admin")
def teacher_export(request):
    assignments = list(teacher_assignments_for(request.user))
    assignment_ids = {str(item.id) for item in assignments}
    selected = request.GET.get("assignment")
    if selected and selected in assignment_ids:
        assignments = [item for item in assignments if str(item.id) == selected]
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="programmy4v-calificaciones.csv"'
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";", lineterminator="\r\n")
    if request.GET.get("format") == "wide":
        student_ids = set()
        visible_ids_by_assignment = {}
        for assignment in assignments:
            ids = set(teacher_students_for_assignment(request.user, assignment).values_list("pk", flat=True))
            visible_ids_by_assignment[assignment.pk] = ids
            student_ids.update(ids)
        students = User.objects.filter(pk__in=student_ids).order_by("username")
        writer.writerow(["student_id", "username", "display_name"] + [_csv_safe(assignment.title) for assignment in assignments])
        for student in students:
            scores = []
            for assignment in assignments:
                if student.pk not in visible_ids_by_assignment[assignment.pk]:
                    scores.append("")
                    continue
                attempts = list(
                    Submission.objects.filter(assignment=assignment, student=student)
                    .order_by("attempt_number")
                    .prefetch_related("grade_calculations")
                )
                _, grade, aggregate_score = _select_attempt(assignment, attempts)
                final_score = aggregate_score if aggregate_score is not None else (grade.final_score if grade else None)
                scores.append(_csv_safe(_decimal(final_score)))
            writer.writerow([_csv_safe(student.pk), _csv_safe(student.username), _csv_safe(student.display_name), *scores])
        return response
    writer.writerow(["student_id", "username", "display_name", "group", "activity_id", "activity_title", "module", "learning_outcome", "assessment_criterion", "submitted_at", "attempts", "auto_score", "manual_score", "final_score", "status", "teacher_comment"])
    for assignment in assignments:
        assigned_students = teacher_students_for_assignment(request.user, assignment)
        submissions = list(
            Submission.objects.filter(assignment=assignment, student__in=assigned_students)
            .select_related("student")
            .prefetch_related("grade_calculations")
        )
        cohorts = ", ".join(teacher_cohorts_for_assignment(request.user, assignment).values_list("name", flat=True))
        latest_by_student = {}
        for submission in submissions:
            latest_by_student.setdefault(submission.student_id, []).append(submission)
        for student in assigned_students:
            student_submissions = latest_by_student.get(student.pk, [])
            chosen, grade, aggregate_score = _select_attempt(assignment, student_submissions)
            final_score = aggregate_score if aggregate_score is not None else (grade.final_score if grade else None)
            aggregate = aggregate_score is not None
            version = assignment.activity_version
            writer.writerow([_csv_safe(student.pk), _csv_safe(student.username), _csv_safe(student.display_name), _csv_safe(cohorts), _csv_safe(assignment.activity_id), _csv_safe(assignment.title), _csv_safe(assignment.activity.module.title), _csv_safe(",".join(version.learning_outcomes)), _csv_safe(",".join(version.assessment_criteria)), _csv_safe(chosen.submitted_at.isoformat() if chosen else None), _csv_safe(len(student_submissions)), _csv_safe(None if aggregate else (_decimal(chosen.auto_score) if chosen else None)), _csv_safe(None if aggregate else (_decimal(grade.manual_score) if grade else None)), _csv_safe(_decimal(final_score)), _csv_safe("published" if final_score is not None else "pending"), _csv_safe("" if aggregate else (grade.teacher_comment if grade else ""))])
    return response
