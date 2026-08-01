"""The opt-in demo seeder."""

import pytest
from seed_demo import DEMO_PASSWORD, DEMO_STUDENTS, seed

from models import LaundryRequest, Student

pytestmark = pytest.mark.integration


class TestSeeding:
    def test_creates_every_demo_student(self, bare_app):
        seed(bare_app)
        with bare_app.app_context():
            assert Student.query.count() == len(DEMO_STUDENTS)

    def test_handles_are_derived_from_names(self, bare_app):
        seed(bare_app)
        with bare_app.app_context():
            assert Student.query.filter_by(student_id="tonsop").first().name == "Tony Soprano"
            assert Student.query.filter_by(student_id="adrlac").first().name == "Adriana La Cerva"

    def test_handles_are_unique(self, bare_app):
        seed(bare_app)
        with bare_app.app_context():
            handles = [s.student_id for s in Student.query.all()]
            assert len(handles) == len(set(handles))

    def test_seeded_passwords_verify(self, bare_app):
        seed(bare_app)
        with bare_app.app_context():
            assert (
                Student.query.filter_by(student_id="tonsop").first().check_password(DEMO_PASSWORD)
            )

    def test_passwords_are_hashed(self, bare_app):
        seed(bare_app)
        with bare_app.app_context():
            for student in Student.query.all():
                assert student.password_hash != DEMO_PASSWORD

    def test_quotas_match_the_table(self, bare_app):
        seed(bare_app)
        with bare_app.app_context():
            assert Student.query.filter_by(student_id="soncor").first().remaining_quota == 6
            assert Student.query.filter_by(student_id="tonsop").first().remaining_quota == 30

    def test_generates_laundry_history(self, bare_app):
        seed(bare_app)
        with bare_app.app_context():
            assert LaundryRequest.query.count() > 0

    def test_every_request_belongs_to_a_seeded_student(self, bare_app):
        seed(bare_app)
        with bare_app.app_context():
            handles = {s.student_id for s in Student.query.all()}
            for req in LaundryRequest.query.all():
                assert req.student_id in handles

    def test_completed_requests_carry_a_completion_date(self, bare_app):
        seed(bare_app)
        with bare_app.app_context():
            for req in LaundryRequest.query.filter_by(status="completed"):
                assert req.completed_date is not None
                assert req.completed_date >= req.submission_date


class TestIdempotency:
    def test_rerunning_adds_nothing(self, bare_app):
        seed(bare_app)
        with bare_app.app_context():
            students, requests = Student.query.count(), LaundryRequest.query.count()

        seed(bare_app)
        with bare_app.app_context():
            assert Student.query.count() == students
            assert LaundryRequest.query.count() == requests

    def test_rerunning_does_not_reset_a_changed_quota(self, bare_app):
        seed(bare_app)
        with bare_app.app_context():
            from models import db

            student = Student.query.filter_by(student_id="tonsop").first()
            student.remaining_quota = 2
            db.session.commit()

        seed(bare_app)
        with bare_app.app_context():
            assert Student.query.filter_by(student_id="tonsop").first().remaining_quota == 2

    def test_a_deleted_demo_student_is_restored(self, bare_app):
        """Unlike init_db, the seeder repairs a partially deleted set."""
        seed(bare_app)
        with bare_app.app_context():
            from models import db

            # The student's requests have to go first. models.py declares the
            # relationship without a cascade, so deleting a Student makes the
            # default backref NULL out laundry_requests.student_id -- a column
            # that is nullable=False -- and the commit dies with an
            # IntegrityError. Deleting a student is therefore impossible through
            # the ORM today; see the FK rework in the backlog.
            LaundryRequest.query.filter_by(student_id="henhil").delete()
            db.session.delete(Student.query.filter_by(student_id="henhil").first())
            db.session.commit()
            assert Student.query.filter_by(student_id="henhil").first() is None

        seed(bare_app)
        with bare_app.app_context():
            assert Student.query.filter_by(student_id="henhil").first() is not None

    def test_deleting_a_student_with_history_is_currently_impossible(self, bare_app):
        # BUG: models.py declares `laundry_requests` with no cascade and
        # laundry_requests.student_id is nullable=False, so the default
        # "null out the child" behaviour violates the constraint. An admin can
        # never remove a student who has ever submitted laundry. Correct
        # behaviour: ondelete="RESTRICT" with passive_deletes, or an explicit
        # cascade, so the outcome is a deliberate choice rather than a crash.
        import sqlalchemy.exc

        from models import db

        seed(bare_app)
        with bare_app.app_context():
            student = Student.query.filter_by(student_id="tonsop").first()
            db.session.add(
                LaundryRequest(student_id=student.student_id, num_clothes=3, status="submitted")
            )
            db.session.commit()

            db.session.delete(student)
            with pytest.raises(sqlalchemy.exc.IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_output_is_reported(self, bare_app, capsys):
        seed(bare_app)
        assert "Added 20 demo students" in capsys.readouterr().out
