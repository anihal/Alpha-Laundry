"""Tests for models.py -- Student, LaundryRequest and Admin."""
from datetime import datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from models import db, Student, Admin, LaundryRequest


# ---------------------------------------------------------------------------
# Student password handling
# ---------------------------------------------------------------------------

class TestStudentPassword:
    def test_check_password_accepts_correct_password(self, make_student):
        student = make_student(password="s3cret")
        assert student.check_password("s3cret") is True

    def test_check_password_rejects_wrong_password(self, make_student):
        student = make_student(password="s3cret")
        assert student.check_password("wrong") is False

    def test_check_password_rejects_empty_password(self, make_student):
        student = make_student(password="s3cret")
        assert student.check_password("") is False

    def test_empty_password_can_be_set_and_verified(self, make_student):
        # An empty string is accepted by set_password and round-trips.
        # BUG: models.py:25-26 Student.set_password performs no validation, so a
        # student can be created with an empty password. There is also no
        # minimum-length or complexity check anywhere in the app. Correct
        # behaviour would be to reject empty/blank passwords (raise ValueError)
        # or to enforce a minimum length before hashing.
        student = make_student(student_id="STU-EMPTY", password="")
        assert student.check_password("") is True
        assert student.check_password("anything") is False

    def test_password_hash_is_not_the_plaintext(self, make_student):
        student = make_student(password="password123")
        assert student.password_hash != "password123"
        assert "password123" not in student.password_hash
        # werkzeug's default in this environment is scrypt; assert the shape
        # rather than the exact algorithm so the test survives a werkzeug bump.
        assert "$" in student.password_hash
        assert len(student.password_hash) > 30

    def test_set_password_twice_produces_a_different_hash(self, make_student):
        """Salting means the same plaintext must not hash to the same value."""
        student = make_student(password="password123")
        first = student.password_hash
        student.set_password("password123")
        assert student.password_hash != first
        assert student.check_password("password123") is True

    def test_check_password_with_none_raises(self, make_student):
        student = make_student(password="password123")
        # BUG: models.py:28-29 Student.check_password passes the argument
        # straight to werkzeug's check_password_hash, which calls
        # ``password.encode()``. A None password therefore raises
        # AttributeError instead of returning False. This is reachable from the
        # login route (see test_routes_auth.py) whenever the form field is
        # absent. Correct behaviour: return False for a None/non-string password.
        with pytest.raises(AttributeError):
            student.check_password(None)


# ---------------------------------------------------------------------------
# Admin password handling
# ---------------------------------------------------------------------------

class TestAdminPassword:
    def test_check_password_accepts_correct_password(self, make_admin):
        admin = make_admin(password="admin123")
        assert admin.check_password("admin123") is True

    def test_check_password_rejects_wrong_password(self, make_admin):
        admin = make_admin(password="admin123")
        assert admin.check_password("nope") is False

    def test_check_password_rejects_empty_password(self, make_admin):
        admin = make_admin(password="admin123")
        assert admin.check_password("") is False

    def test_password_hash_is_not_the_plaintext(self, make_admin):
        admin = make_admin(password="admin123")
        assert admin.password_hash != "admin123"
        assert "admin123" not in admin.password_hash

    def test_check_password_with_none_raises(self, make_admin):
        admin = make_admin(password="admin123")
        # BUG: models.py:62-63 -- identical flaw to Student.check_password.
        # Reachable from /admin/login when the password field is missing.
        with pytest.raises(AttributeError):
            admin.check_password(None)


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

class TestDefaults:
    def test_student_remaining_quota_defaults_to_30(self, make_student):
        student = make_student(remaining_quota=None)
        assert student.remaining_quota == 30

    def test_student_explicit_quota_overrides_default(self, make_student):
        student = make_student(remaining_quota=7)
        assert student.remaining_quota == 7

    def test_student_created_at_is_set_on_insert(self, make_student):
        before = datetime.utcnow() - timedelta(seconds=5)
        student = make_student()
        after = datetime.utcnow() + timedelta(seconds=5)
        assert student.created_at is not None
        assert before <= student.created_at <= after

    def test_admin_created_at_is_set_on_insert(self, make_admin):
        before = datetime.utcnow() - timedelta(seconds=5)
        admin = make_admin()
        after = datetime.utcnow() + timedelta(seconds=5)
        assert admin.created_at is not None
        assert before <= admin.created_at <= after

    def test_laundry_request_status_defaults_to_submitted(self, make_student, make_request):
        make_student(student_id="STU001")
        req = make_request(student_id="STU001", status=None)
        assert req.status == "submitted"

    def test_laundry_request_submission_date_is_set_on_insert(self, make_student, make_request):
        make_student(student_id="STU001")
        before = datetime.utcnow() - timedelta(seconds=5)
        req = make_request(student_id="STU001", submission_date=None)
        after = datetime.utcnow() + timedelta(seconds=5)
        assert req.submission_date is not None
        assert before <= req.submission_date <= after

    def test_laundry_request_completed_date_defaults_to_none(self, make_student, make_request):
        make_student(student_id="STU001")
        req = make_request(student_id="STU001")
        assert req.completed_date is None


# ---------------------------------------------------------------------------
# __repr__
# ---------------------------------------------------------------------------

class TestRepr:
    def test_student_repr(self, make_student):
        student = make_student(student_id="STU042")
        assert repr(student) == "<Student STU042>"

    def test_admin_repr(self, make_admin):
        admin = make_admin(username="root")
        assert repr(admin) == "<Admin root>"

    def test_laundry_request_repr(self, make_student, make_request):
        make_student(student_id="STU001")
        req = make_request(student_id="STU001", status="processing")
        assert repr(req) == f"<LaundryRequest {req.id} - processing>"

    def test_laundry_request_repr_on_unsaved_instance(self):
        """__repr__ must not explode before the row has an id."""
        req = LaundryRequest(student_id="STU001", num_clothes=3)
        assert repr(req) == "<LaundryRequest None - None>"


# ---------------------------------------------------------------------------
# Constraints
# ---------------------------------------------------------------------------

class TestConstraints:
    def test_duplicate_student_id_raises_integrity_error(self, make_student, db_session):
        make_student(student_id="STU001")
        dup = Student(student_id="STU001", name="Impostor")
        dup.set_password("x")
        db_session.add(dup)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_duplicate_admin_username_raises_integrity_error(self, make_admin, db_session):
        make_admin(username="admin")
        dup = Admin(username="admin")
        dup.set_password("x")
        db_session.add(dup)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_student_name_is_not_nullable(self, db_session):
        student = Student(student_id="STU-NONAME")
        student.set_password("x")
        db_session.add(student)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_student_password_hash_is_not_nullable(self, db_session):
        db_session.add(Student(student_id="STU-NOPW", name="No Password"))
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_student_id_is_not_nullable(self, db_session):
        student = Student(name="Anonymous")
        student.set_password("x")
        db_session.add(student)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_admin_username_is_not_nullable(self, db_session):
        admin = Admin()
        admin.set_password("x")
        db_session.add(admin)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_laundry_request_num_clothes_is_not_nullable(self, make_student, db_session):
        make_student(student_id="STU001")
        db_session.add(LaundryRequest(student_id="STU001"))
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_laundry_request_student_id_is_not_nullable(self, db_session):
        db_session.add(LaundryRequest(num_clothes=3))
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_orphan_laundry_request_is_accepted(self, db_session):
        """A request pointing at a non-existent student commits successfully."""
        # BUG: models.py:40 declares a ForeignKey to students.student_id, but
        # SQLite does not enforce foreign keys unless
        # ``PRAGMA foreign_keys=ON`` is issued per connection, and the app never
        # does that. An orphan row is therefore persisted silently. Correct
        # behaviour: enforce the FK (enable the pragma via a connect event, or
        # validate the student exists) so this raises IntegrityError.
        orphan = LaundryRequest(student_id="NO-SUCH-STUDENT", num_clothes=3)
        db_session.add(orphan)
        db_session.commit()
        assert orphan.id is not None
        assert orphan.student is None

    def test_negative_num_clothes_is_accepted_at_the_model_layer(self, make_student, db_session):
        make_student(student_id="STU001")
        # BUG: models.py:41 has no CHECK constraint on num_clothes, so a
        # negative quantity is storable. The route layer happens to guard
        # against it, but any other writer (a script, a future endpoint) could
        # persist nonsense. Correct behaviour: a CheckConstraint num_clothes > 0.
        req = LaundryRequest(student_id="STU001", num_clothes=-10)
        db_session.add(req)
        db_session.commit()
        assert req.num_clothes == -10


# ---------------------------------------------------------------------------
# Relationship / backref
# ---------------------------------------------------------------------------

class TestRelationship:
    def test_laundry_requests_starts_empty(self, make_student):
        student = make_student(student_id="STU001")
        assert student.laundry_requests == []

    def test_laundry_requests_collects_the_students_requests(
        self, make_student, make_request, db_session
    ):
        student = make_student(student_id="STU001")
        r1 = make_request(student_id="STU001", num_clothes=3)
        r2 = make_request(student_id="STU001", num_clothes=4)
        db_session.refresh(student)
        assert {r.id for r in student.laundry_requests} == {r1.id, r2.id}

    def test_laundry_requests_excludes_other_students_requests(
        self, make_student, make_request, db_session
    ):
        alice = make_student(student_id="STU001", name="Alice")
        make_student(student_id="STU002", name="Bob")
        mine = make_request(student_id="STU001", num_clothes=3)
        make_request(student_id="STU002", num_clothes=9)
        db_session.refresh(alice)
        assert [r.id for r in alice.laundry_requests] == [mine.id]

    def test_backref_resolves_to_the_owning_student(self, make_student, make_request):
        make_student(student_id="STU001", name="Alice")
        req = make_request(student_id="STU001")
        assert req.student is not None
        assert req.student.name == "Alice"
        assert req.student.student_id == "STU001"

    def test_appending_through_the_relationship_persists(self, make_student, db_session):
        student = make_student(student_id="STU001")
        student.laundry_requests.append(LaundryRequest(num_clothes=6))
        db_session.commit()
        stored = LaundryRequest.query.all()
        assert len(stored) == 1
        assert stored[0].student_id == "STU001"
        assert stored[0].num_clothes == 6


# ---------------------------------------------------------------------------
# Table wiring
# ---------------------------------------------------------------------------

def test_table_names(app):
    assert Student.__tablename__ == "students"
    assert Admin.__tablename__ == "admins"
    assert LaundryRequest.__tablename__ == "laundry_requests"
    assert set(db.metadata.tables) == {"students", "admins", "laundry_requests"}
