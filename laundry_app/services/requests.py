"""Creating laundry requests and moving them between statuses.

Extracted verbatim from ``routes.submit_request`` and ``routes.update_status``.
Both functions take the SQLAlchemy session explicitly so they can run against a
plain ``sessionmaker()`` session with no Flask application in sight.
"""

from datetime import datetime

from models import LaundryRequest
from services import quota

COMPLETED = "completed"


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

    ``completed_date`` is stamped only when ``new_status`` is exactly
    ``"completed"``; the comparison is case-sensitive and there is no allowlist
    of valid statuses, both of which are the pre-existing behaviour. ``now``
    exists so tests can pin the timestamp -- omitted, it is ``utcnow()``, which
    is what the route always used.

    Returns the same request object.
    """
    laundry_request.status = new_status

    if new_status == COMPLETED:
        laundry_request.completed_date = now if now is not None else datetime.utcnow()

    db_session.commit()

    return laundry_request
