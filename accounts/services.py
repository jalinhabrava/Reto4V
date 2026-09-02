"""Application services for local account administration.

The account screens deliberately keep persistence in one transaction.  A
student is useful to the learning application only when the account and its
active cohort enrollment agree, so saving either half on its own would leave
an account that can log in but cannot see a single challenge (or, worse, an
account with stale access to a previous itinerary).
"""

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import User


@transaction.atomic
def save_user_with_cohort(user, cohort=None):
    """Save ``user`` and synchronise its active learning enrollment.

    ``learning.services`` owns the enrollment invariants and permission
    checks.  This wrapper owns the transaction boundary that also includes
    the user row, so a failed enrollment never leaves a partially-created
    account behind.
    """

    if not user.is_superuser and user.role == User.Role.STUDENT and cohort is None:
        raise ValidationError({"cohort": "Selecciona un ciclo e itinerario para el alumno."})

    user.save()

    # Import lazily to keep the accounts app importable while Django builds
    # the app registry and to leave all enrollment rules in learning.services.
    from learning.services import clear_student_enrollment, set_student_cohort

    if not user.is_superuser and user.role == User.Role.STUDENT:
        set_student_cohort(user, cohort)
    else:
        clear_student_enrollment(user)
    return user
