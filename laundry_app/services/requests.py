"""Creating laundry requests and moving them between statuses.

Extracted verbatim from ``routes.submit_request`` and ``routes.update_status``.
Both functions take the SQLAlchemy session explicitly so they can run against a
plain ``sessionmaker()`` session with no Flask application in sight.
"""

from datetime import datetime

from models import LaundryRequest
from services import quota

COMPLETED = "completed"

# The set models.py documents against the ``status`` column. It is enforced here
# rather than left as a comment: any other string fits in the String(20) column,
# and a job holding one matches neither admin dashboard query (the
# ``status.in_(["submitted", "processing"])`` filter nor ``status="completed"``),
# so it disappears from both tables and all four stat counters while the
# student's quota stays spent.
ALLOWED_STATUSES = frozenset({"submitted", "processing", COMPLETED, "cancelled"})


class InvalidStatus(quota.ServiceError):
    """The requested status is not one of :data:`ALLOWED_STATUSES`."""

    def __init__(self, status):
        super().__init__(f"invalid status: {status!r}")
        self.status = status


def submit(db_session, student, num_clothes):
    """Validate, create the request row, deduct the quota and commit.

    Returns the persisted :class:`~models.LaundryRequest`. Raises
    :class:`~services.quota.InvalidQuantity` or
    :class:`~services.quota.QuotaExceeded` -- and leaves the session untouched
    -- when validation fails.

    The step order is load-bearing and matches the original inline code:
    validate, build the row, deduct, then a single commit.
    """
    quota.check(student, num_clothes)

    laundry_request = LaundryRequest(student_id=student.student_id, num_clothes=num_clothes)
    quota.deduct(student, num_clothes)

    db_session.add(laundry_request)
    db_session.commit()

    return laundry_request


def set_status(db_session, laundry_request, new_status, now=None):
    """Assign ``new_status`` to ``laundry_request`` and commit.

    ``new_status`` must be one of :data:`ALLOWED_STATUSES`; anything else --
    including ``None``, ``""`` and a differently-cased ``"COMPLETED"`` -- raises
    :class:`InvalidStatus` and leaves the row and the session untouched.

    ``completed_date`` tracks the status rather than merely accumulating:
    it is stamped on the transition *into* ``"completed"`` (so re-submitting
    ``"completed"`` preserves the original time) and cleared on any transition
    away from it (so a job reverted to ``"processing"`` cannot keep claiming a
    completion timestamp). ``now`` exists so tests can pin the stamp -- omitted,
    it is ``utcnow()``, which is what the route always used.

    Returns the same request object.
    """
    if new_status not in ALLOWED_STATUSES:
        raise InvalidStatus(new_status)

    was_completed = laundry_request.status == COMPLETED
    laundry_request.status = new_status

    if new_status != COMPLETED:
        laundry_request.completed_date = None
    elif not was_completed:
        laundry_request.completed_date = now if now is not None else datetime.utcnow()

    db_session.commit()

    return laundry_request
