"""Quota arithmetic and the validation that guards it.

Extracted verbatim from the body of ``routes.submit_request``. The behaviour --
including its known defects -- is unchanged; only the location moved.
"""


class ServiceError(Exception):
    """Base class for every error the service layer raises deliberately."""


class InvalidQuantity(ServiceError):
    """The requested number of clothes is not a usable quantity (``<= 0``)."""

    def __init__(self, num_clothes):
        super().__init__(f"invalid quantity: {num_clothes!r}")
        self.num_clothes = num_clothes


class QuotaExceeded(ServiceError):
    """The request is larger than the student's remaining quota."""

    def __init__(self, num_clothes, remaining):
        super().__init__(f"requested {num_clothes}, only {remaining} remaining")
        self.num_clothes = num_clothes
        self.remaining = remaining


def parse_quantity(raw):
    """Coerce a raw form value into a number of clothes.

    A bare ``int()`` with no ``try``/``except``, exactly as it was inline in the
    route. Non-numeric input therefore raises ``ValueError`` (and ``None``
    raises ``TypeError``) rather than being rejected politely; callers see the
    same exceptions they saw before this function existed.
    """
    return int(raw)


def check(student, num_clothes):
    """Validate ``num_clothes`` against ``student``'s remaining quota.

    Raises :class:`InvalidQuantity` for a non-positive quantity and
    :class:`QuotaExceeded` when the request outruns the quota. The order of the
    two checks matters and is preserved: the quantity check runs first and does
    not touch ``student`` at all.
    """
    if num_clothes <= 0:
        raise InvalidQuantity(num_clothes)

    if num_clothes > student.remaining_quota:
        raise QuotaExceeded(num_clothes, student.remaining_quota)


def deduct(student, num_clothes):
    """Subtract ``num_clothes`` from the student's remaining quota (in memory).

    Persisting the change is the caller's responsibility -- this function never
    commits.
    """
    student.remaining_quota -= num_clothes
    return student.remaining_quota
