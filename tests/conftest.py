"""
Shared pytest fixtures for the Alpha Laundry test suite.

The application modules use bare imports (``from config import Config``), so
``pytest.ini`` adds ``laundry_app`` to ``pythonpath``; that makes ``app``,
``config``, ``models`` and ``routes`` importable as top-level modules here.

No application file is modified by these tests. The only thing the fixtures do
to make the app testable is monkeypatch the *class attributes* on
``config.Config`` before calling ``create_app()`` -- ``create_app()`` reads
``Config.DATABASE_URL`` / ``Config.SECRET_KEY`` at call time, and
Flask-SQLAlchemy binds the URI during ``init_app``, so patching after
construction would be too late for the database URL.
"""

from datetime import datetime, timedelta

import pytest
from app import create_app
from config import Config
from models import Admin, LaundryRequest, Student
from models import db as _db

TEST_SECRET_KEY = "test-secret-key-do-not-use-in-production"


@pytest.fixture
def app(monkeypatch):
    """A Flask app wired to a throwaway in-memory SQLite database.

    Flask-SQLAlchemy 3.x automatically applies a ``StaticPool`` for
    ``sqlite:///:memory:``, so every connection in a test sees the same
    database. The fixture is function-scoped, which is what gives each test a
    completely clean schema (no cross-test leakage) and guarantees the real
    ``laundry_app/instance/laundry.db`` is never touched.
    """
    monkeypatch.setattr(Config, "DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setattr(Config, "SECRET_KEY", TEST_SECRET_KEY)

    application = create_app()
    application.config.update(TESTING=True)

    with application.app_context():
        _db.create_all()
        try:
            yield application
        finally:
            _db.session.remove()
            _db.drop_all()
            # Dispose the engine so the underlying sqlite3 connection is closed
            # deterministically instead of at GC time (which otherwise floods
            # the run with ResourceWarnings).
            for engine in _db.engines.values():
                engine.dispose()


@pytest.fixture
def client(app):
    """Anonymous test client."""
    return app.test_client()


@pytest.fixture
def db_session(app):
    """The active SQLAlchemy session for the current app context."""
    return _db.session


# ---------------------------------------------------------------------------
# Factory fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def make_student(db_session):
    """Create and persist a Student.

    ``remaining_quota=None`` means "don't pass the column at all", so the
    model-level default (30) is exercised.
    """

    def _make(
        student_id="STU001", name="Test Student", password="password123", remaining_quota=None
    ):
        kwargs = {"student_id": student_id, "name": name}
        if remaining_quota is not None:
            kwargs["remaining_quota"] = remaining_quota
        student = Student(**kwargs)
        student.set_password(password)
        db_session.add(student)
        db_session.commit()
        return student

    return _make


@pytest.fixture
def make_admin(db_session):
    """Create and persist an Admin."""

    def _make(username="admin", password="admin123"):
        admin = Admin(username=username)
        admin.set_password(password)
        db_session.add(admin)
        db_session.commit()
        return admin

    return _make


@pytest.fixture
def make_request(db_session):
    """Create and persist a LaundryRequest.

    ``status``/``submission_date`` default to None here so that omitting them
    exercises the column defaults declared on the model.
    """

    def _make(
        student_id="STU001", num_clothes=5, status=None, submission_date=None, completed_date=None
    ):
        kwargs = {"student_id": student_id, "num_clothes": num_clothes}
        if status is not None:
            kwargs["status"] = status
        if submission_date is not None:
            kwargs["submission_date"] = submission_date
        if completed_date is not None:
            kwargs["completed_date"] = completed_date
        req = LaundryRequest(**kwargs)
        db_session.add(req)
        db_session.commit()
        return req

    return _make


@pytest.fixture
def times():
    """A small ladder of increasing datetimes for ordering assertions."""
    base = datetime(2026, 1, 1, 12, 0, 0)
    return [base + timedelta(hours=i) for i in range(10)]


# ---------------------------------------------------------------------------
# Authenticated client helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def student_user(make_student):
    """A concrete student used by the logged-in-student fixtures."""
    return make_student(
        student_id="STU001", name="John Doe", password="password123", remaining_quota=30
    )


@pytest.fixture
def admin_user(make_admin):
    """A concrete admin used by the logged-in-admin fixtures."""
    return make_admin(username="admin", password="admin123")


@pytest.fixture
def student_client(app, student_user):
    """Client with a real student session, established via a genuine login POST."""
    client = app.test_client()
    resp = client.post(
        "/login",
        data={"student_id": student_user.student_id, "password": "password123"},
    )
    assert resp.status_code == 302, "student login fixture failed to authenticate"
    return client


@pytest.fixture
def admin_client(app, admin_user):
    """Client with a real admin session, established via a genuine login POST."""
    client = app.test_client()
    resp = client.post(
        "/admin/login",
        data={"username": admin_user.username, "password": "admin123"},
    )
    assert resp.status_code == 302, "admin login fixture failed to authenticate"
    return client


@pytest.fixture
def session_student_client(app, student_user):
    """Same as ``student_client`` but built with ``session_transaction``.

    Useful for constructing *malformed* or cross-role sessions that a real
    login could never produce.
    """
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = student_user.id
        sess["student_id"] = student_user.student_id
        sess["user_name"] = student_user.name
    return client
