"""Creating laundry requests and moving them between statuses.

Extracted verbatim from ``routes.submit_request`` and ``routes.update_status``.
Both functions take the SQLAlchemy session explicitly so they can run against a
plain ``sessionmaker()`` session with no Flask application in sight.
"""

from datetime import datetime

from models import LaundryRequest, Student
from services import quota

COMPLETED = "completed"
CANCELLED = "cancelled"

# The set models.py documents against the ``status`` column. It is enforced here
# rather than left as a comment: any other string fits in the String(20) column,
# and a job holding one matches neither admin dashboard query (the
# ``status.in_(["submitted", "processing"])`` filter nor ``status="completed"``),
# so it disappears from both tables and all four stat counters while the
# student's quota stays spent.
ALLOWED_STATUSES = frozenset({"submitted", "processing", COMPLETED, CANCELLED})


class InvalidStatus(quota.ServiceError):
    """The requested status is not one of :data:`ALLOWED_STATUSES`."""

    def __init__(self, status):
        super().__init__(f"invalid status: {status!r}")
        self.status = status


def _adjust_quota(db_session, student_id, delta, require_available=False):
    """Move a student's remaining quota by ``delta`` in a single statement.

    The arithmetic happens in the database (``remaining_quota + delta``) rather
    than in Python, so two concurrent callers cannot both read the same starting
    balance and write back conflicting totals.

    With ``require_available`` the statement also carries its own guard --
    ``remaining_quota >= -delta`` -- so the check and the write are one atomic
    operation. Returns the number of rows updated: 0 means the guard refused,
    which is the caller's signal that the balance was insufficient.
    """
    query = db_session.query(Student).filter(Student.student_id == student_id)
    if require_available:
        query = query.filter(Student.remaining_quota >= -delta)

    return query.update(
        {Student.remaining_quota: Student.remaining_quota + delta},
        synchronize_session="fetch",
    )


def submit(db_session, student, num_clothes):
    """Validate, create the request row, deduct the quota and commit.

    Returns the persisted :class:`~models.LaundryRequest`. Raises
    :class:`~services.quota.InvalidQuantity` or
    :class:`~services.quota.QuotaExceeded` -- and leaves the session untouched
    -- when validation fails.

    The deduction is atomic. ``quota.check`` still runs first, because it is
    what produces the precise error the route flashes, but it is no longer the
    thing enforcing the limit: the UPDATE carries its own
    ``remaining_quota >= num_clothes`` guard, and a row count of 0 means another
    transaction spent the balance in between. Previously the check and the write
    were separate steps over a value read into Python, so two concurrent submits
    could both pass a check against the same starting balance -- verified, with
    a student on a quota of 23 getting 46 items accepted.
    """
    quota.check(student, num_clothes)

    if _adjust_quota(db_session, student.student_id, -num_clothes, require_available=True) != 1:
        db_session.rollback()
        db_session.refresh(student)
        raise quota.QuotaExceeded(num_clothes, student.remaining_quota)

    laundry_request = LaundryRequest(student_id=student.student_id, num_clothes=num_clothes)
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

    Quota follows the cancellation. Moving *into* ``"cancelled"`` returns the
    request's clothes to the student, and moving back *out* of it spends them
    again; both happen only on the transition edge, so saving the same status
    repeatedly cannot refund twice. The invariant is that a cancelled request
    never counts against a quota -- previously cancelling consumed the allowance
    forever, with no admin control to give it back.

    Un-cancelling is guarded: if the student no longer has room for the request,
    :class:`~services.quota.QuotaExceeded` is raised and the row is left
    untouched, rather than driving the balance negative (which would defeat the
    dashboard's ``remaining_quota == 0`` guard and re-enable submission).

    Returns the same request object.
    """
    if new_status not in ALLOWED_STATUSES:
        raise InvalidStatus(new_status)

    was_completed = laundry_request.status == COMPLETED
    was_cancelled = laundry_request.status == CANCELLED
    becomes_cancelled = new_status == CANCELLED

    if was_cancelled and not becomes_cancelled:
        spent = _adjust_quota(
            db_session,
            laundry_request.student_id,
            -laundry_request.num_clothes,
            require_available=True,
        )
        if spent != 1:
            db_session.rollback()
            owner = (
                db_session.query(Student)
                .filter(Student.student_id == laundry_request.student_id)
                .first()
            )
            raise quota.QuotaExceeded(
                laundry_request.num_clothes,
                owner.remaining_quota if owner else 0,
            )
    elif becomes_cancelled and not was_cancelled:
        _adjust_quota(db_session, laundry_request.student_id, laundry_request.num_clothes)

    laundry_request.status = new_status

    if new_status != COMPLETED:
        laundry_request.completed_date = None
    elif not was_completed:
        laundry_request.completed_date = now if now is not None else datetime.utcnow()

    db_session.commit()

    return laundry_request
