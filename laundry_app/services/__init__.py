"""Framework-free business logic for Alpha Laundry.

Everything in this package is importable and callable without a Flask
application, an application context or a request context. Functions take plain
arguments -- a ``Student``, a SQLAlchemy session, ints, strings -- and either
return a value or raise a domain error.

Nothing here touches ``flash``, ``redirect``, ``session`` or ``request``:
translating a domain error into an HTTP response is the route layer's job.
"""

from services.quota import InvalidQuantity, QuotaExceeded, ServiceError
from services.requests import InvalidStatus

__all__ = ["InvalidQuantity", "InvalidStatus", "QuotaExceeded", "ServiceError"]
