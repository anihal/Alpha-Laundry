"""Fixtures for the unit suite -- no Flask anywhere.

The models are declared through Flask-SQLAlchemy, but a Flask-SQLAlchemy model
is an ordinary declarative class: ``db.metadata`` describes the tables and any
``sqlalchemy.orm.Session`` can persist them. So these fixtures build an
in-memory engine directly and hand out a plain session.

That is the whole point of the split. Nothing here creates an application,
pushes an app context, or needs ``Model.query`` (which is the one part of
Flask-SQLAlchemy that *does* require a context). Queries use
``db_session.query(...)`` instead.
"""

import ast
import pathlib

import flask
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Admin, LaundryRequest, Student, db


@pytest.fixture(autouse=True)
def no_application_context():
    """Fail any unit test that pushes a Flask application context.

    The rule is easy to break by accident -- ``Model.query`` and ``db.session``
    both work fine as long as *something* earlier in the file pushed a context
    -- and the cost of breaking it is a unit suite that slowly turns back into
    the integration suite. Asserting it here makes the regression loud.
    """
    yield
    assert not flask.current_app, "a unit test left a Flask application context pushed"


@pytest.fixture
def engine():
    """A throwaway in-memory SQLite engine with the schema created."""
    eng = create_engine("sqlite:///:memory:")
    db.metadata.create_all(eng)
    try:
        yield eng
    finally:
        # Close the underlying sqlite3 connection deterministically rather than
        # at GC time, which otherwise floods the run with ResourceWarnings.
        eng.dispose()


@pytest.fixture
def db_session(engine):
    """A plain SQLAlchemy session bound to the throwaway engine."""
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Factories
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
def student(make_student):
    """A student with a 30-clothes quota -- the common starting point."""
    return make_student(
        student_id="STU001", name="John Doe", password="password123", remaining_quota=30
    )


class FakeStudent:
    """A stand-in for a Student that never touches a database.

    ``quota.check`` and ``quota.deduct`` only read and write
    ``remaining_quota``, so most of the quota tests need nothing more than
    this. Using it keeps those tests honest about the service's real dependency
    surface.
    """

    def __init__(self, remaining_quota, student_id="STU001"):
        self.remaining_quota = remaining_quota
        self.student_id = student_id


@pytest.fixture
def fake_student():
    """Factory for :class:`FakeStudent`."""
    return FakeStudent


# ---------------------------------------------------------------------------
# Source inspection
# ---------------------------------------------------------------------------
#
# "This module does not depend on Flask" is the contract that makes the unit
# suite possible, so it is asserted rather than assumed. Reading the AST catches
# a function-body import that an `import module; check sys.modules` probe would
# miss (by then the parent package has already pulled Flask in via models).


def _parse(module):
    return ast.parse(pathlib.Path(module.__file__).read_text(encoding="utf-8"))


@pytest.fixture
def imported_roots():
    """Callable: module -> the set of top-level packages it imports."""

    def _roots(module):
        roots = set()
        for node in ast.walk(_parse(module)):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".")[0])
        return roots

    return _roots


@pytest.fixture
def referenced_names():
    """Callable: module -> every bare name and attribute it mentions."""

    def _names(module):
        tree = _parse(module)
        return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {
            node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
        }

    return _names
