from django.db import migrations, models
from django.db.models import Q


TRACK_VALUES = {"web", "bash", "python"}


def infer_cohort_tracks(apps, schema_editor):
    """Backfill an unlabelled legacy cohort when its assignments are clear."""

    Cohort = apps.get_model("learning", "Cohort")
    AssignmentCohort = apps.get_model("learning", "AssignmentCohort")

    for cohort in Cohort.objects.filter(track=""):
        languages = set(
            AssignmentCohort.objects.filter(cohort_id=cohort.pk)
            .values_list("assignment__activity_version__language", flat=True)
        )
        if len(languages) == 1 and languages.issubset(TRACK_VALUES):
            cohort.track = next(iter(languages))
            cohort.save(update_fields=["track"])


def deactivate_duplicate_active_enrollments(apps, schema_editor):
    """Keep the most recently active enrollment before adding the partial key."""

    Enrollment = apps.get_model("learning", "Enrollment")
    student_ids = (
        Enrollment.objects.filter(active=True)
        .values_list("student_id", flat=True)
        .distinct()
    )
    for student_id in student_ids:
        active_rows = list(
            Enrollment.objects.filter(student_id=student_id, active=True).order_by("-enrolled_at", "-id")
        )
        for duplicate in active_rows[1:]:
            duplicate.active = False
            duplicate.save(update_fields=["active"])


class Migration(migrations.Migration):

    dependencies = [
        ("learning", "0004_activityversion_python_language"),
    ]

    operations = [
        migrations.AddField(
            model_name="cohort",
            name="track",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Itinerario formativo del grupo (Web, Bash o Python).",
                max_length=20,
                choices=[("web", "Web · SMR"), ("bash", "Bash · ASIR"), ("python", "Python · DAM")],
            ),
        ),
        migrations.RunPython(infer_cohort_tracks, migrations.RunPython.noop),
        migrations.RunPython(deactivate_duplicate_active_enrollments, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="enrollment",
            constraint=models.UniqueConstraint(
                condition=Q(active=True),
                fields=("student",),
                name="uniq_active_enrollment_student",
            ),
        ),
    ]
