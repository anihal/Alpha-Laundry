"""Quota arithmetic and the validation that guards it.

Extracted from the body of ``routes.submit_request``. ``parse_quantity`` is the
one part that no longer behaves as it did inline: it validates its input instead
of handing it to a bare ``int()``.
"""


class ServiceError(Exception):
    """Base class for every error the service layer raises deliberately."""


class InvalidQuantity(ServiceError):
    """The submitted value is not a usable number of clothes.

    Covers both halves of "usable": input that is not an ASCII integer at all
    (raised by :func:`parse_quantity`) and an integer that is not positive
    (raised by :func:`check`).
    """

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

    Raises :class:`InvalidQuantity` -- never ``ValueError`` or ``TypeError`` --
    for anything that is not an ASCII integer, so the route has exactly one kind
    of failure to translate into a flash message. This is the guard that keeps
    ``""`` (what a browser posts for a blank number field), ``"abc"``, ``"1.5"``
    and friends from escaping as an unhandled exception, i.e. an HTTP 500.

    An ``int`` passes through untouched, because the route's own default for a
    missing field is the int ``0``. ``bool`` does not: it is an ``int`` subclass
    by accident of history, not a quantity. Surrounding whitespace is stripped,
    which keeps ``" +5 "`` working the way it always has.

    The accepted shape -- an optional sign then ASCII digits, nothing else -- is
    chosen here rather than inherited from ``int()``, which also accepts every
    Unicode decimal digit (``int("٣")`` is 3, and used to create a real 3-item
    request) and underscore separators (``int("1_0")`` is 10).
    """
    if isinstance(raw, int) and not isinstance(raw, bool):
        return raw

    if not isinstance(raw, str):
        raise InvalidQuantity(raw)

    text = raw.strip()
    digits = text[1:] if text[:1] in ("+", "-") else text
    if not digits.isascii() or not digits.isdigit():
        raise InvalidQuantity(raw)

    return int(text)


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
