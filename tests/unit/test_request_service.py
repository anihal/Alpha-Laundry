"""Tests for services/requests.py -- creating requests and moving their status.

Persistence matters here, so these run against a plain SQLAlchemy session over
in-memory SQLite (``tests/unit/conftest.py``). There is still no Flask
application, no request context and no HTTP.
"""

import pathlib
from datetime import datetime, timedelta

import pytest

from models import LaundryRequest, Student
from services import requests as request_service
from services.quota import InvalidQuantity, QuotaExceeded, ServiceError

# ---------------------------------------------------------------------------
# submit -- happy path
# ---------------------------------------------------------------------------


class TestSubmitHappyPath:
    def test_creates_exactly_one_row(self, db_session, student):
        request_service.submit(db_session, student, 5)
        assert db_session.query(LaundryRequest).count() == 1

    def test_the_row_carries_the_students_id(self, db_session, student):
        created = request_service.submit(db_session, student, 5)
        assert created.student_id == "STU001"

    def test_the_row_carries_the_requested_amount(self, db_session, student):
        created = request_service.submit(db_session, student, 5)
        assert created.num_clothes == 5

    def test_the_row_starts_as_submitted(self, db_session, student):
        created = request_service.submit(db_session, student, 5)
        assert created.status == "submitted"

    def test_the_row_has_no_completed_date(self, db_session, student):
        created = request_service.submit(db_session, student, 5)
        assert created.completed_date is None

    def test_the_row_is_stamped_with_a_submission_date(self, db_session, student):
        created = request_service.submit(db_session, student, 5)
        assert created.submission_date is not None

    def test_returns_the_persisted_request(self, db_session, student):
        created = request_service.submit(db_session, student, 5)
        assert created.id is not None
        assert db_session.get(LaundryRequest, created.id) is created

    def test_deducts_exactly_the_requested_amount(self, db_session, student):
        request_service.submit(db_session, student, 5)
        assert student.remaining_quota == 25

    def test_the_deduction_is_committed(self, db_session, student):
        request_service.submit(db_session, student, 5)
        db_session.expunge_all()
        reloaded = db_session.query(Student).filter_by(student_id="STU001").one()
        assert reloaded.remaining_quota == 25

    def test_the_request_is_committed(self, db_session, student):
        created = request_service.submit(db_session, student, 5)
        request_id = created.id
        db_session.expunge_all()
        assert db_session.get(LaundryRequest, request_id) is not None

    def test_submitting_a_single_clothe_works(self, db_session, student):
        request_service.submit(db_session, student, 1)
        assert student.remaining_quota == 29

    def test_exactly_the_remaining_quota_succeeds_and_zeroes_it(self, db_session, student):
        request_service.submit(db_session, student, 30)
        assert db_session.query(LaundryRequest).count() == 1
        assert student.remaining_quota == 0

    def test_repeated_submissions_accumulate(self, db_session, student):
        for _ in range(3):
            request_service.submit(db_session, student, 4)
        assert db_session.query(LaundryRequest).count() == 3
        assert student.remaining_quota == 18

    def test_each_submission_gets_its_own_id(self, db_session, student):
        first = request_service.submit(db_session, student, 4)
        second = request_service.submit(db_session, student, 4)
        assert first.id != second.id

    def test_the_backref_resolves_to_the_owning_student(self, db_session, student):
        created = request_service.submit(db_session, student, 5)
        assert created.student is student

    def test_two_students_do_not_share_a_quota(self, db_session, make_student):
        alice = make_student(student_id="STU001", name="Alice", remaining_quota=30)
        bob = make_student(student_id="STU002", name="Bob", remaining_quota=30)
        request_service.submit(db_session, alice, 10)
        assert alice.remaining_quota == 20
        assert bob.remaining_quota == 30


# ---------------------------------------------------------------------------
# submit -- rejections
# ---------------------------------------------------------------------------


class TestSubmitRejections:
    @pytest.mark.parametrize("num_clothes", [0, -1, -5])
    def test_non_positive_amounts_raise_invalid_quantity(self, db_session, student, num_clothes):
        with pytest.raises(InvalidQuantity):
            request_service.submit(db_session, student, num_clothes)

    @pytest.mark.parametrize("num_clothes", [31, 100, 1000000])
    def test_over_quota_amounts_raise_quota_exceeded(self, db_session, student, num_clothes):
        with pytest.raises(QuotaExceeded):
            request_service.submit(db_session, student, num_clothes)

    def test_one_over_the_quota_is_rejected(self, db_session, make_student):
        student = make_student(student_id="STU001", remaining_quota=10)
        with pytest.raises(QuotaExceeded) as excinfo:
            request_service.submit(db_session, student, 11)
        assert excinfo.value.remaining == 10

    @pytest.mark.parametrize("num_clothes", [0, -5, 31])
    def test_a_rejected_submission_creates_no_row(self, db_session, student, num_clothes):
        with pytest.raises(ServiceError):
            request_service.submit(db_session, student, num_clothes)
        assert db_session.query(LaundryRequest).count() == 0

    @pytest.mark.parametrize("num_clothes", [0, -5, 31])
    def test_a_rejected_submission_leaves_the_quota_untouched(
        self, db_session, student, num_clothes
    ):
        with pytest.raises(ServiceError):
            request_service.submit(db_session, student, num_clothes)
        assert student.remaining_quota == 30

    def test_a_negative_submission_does_not_inflate_the_quota(self, db_session, student):
        """Guard against the classic `quota -= -5` bug."""
        with pytest.raises(InvalidQuantity):
            request_service.submit(db_session, student, -5)
        assert student.remaining_quota == 30

    def test_submission_after_the_quota_is_exhausted_is_rejected(self, db_session, student):
        request_service.submit(db_session, student, 30)
        with pytest.raises(QuotaExceeded) as excinfo:
            request_service.submit(db_session, student, 1)
        assert excinfo.value.remaining == 0
        assert db_session.query(LaundryRequest).count() == 1

    def test_a_missing_student_raises_attributeerror_on_a_valid_quantity(self, db_session):
        # BUG: services/requests.submit never checks that the student it was
        # handed is real, because routes.py never did -- the route assigns
        # ``student = Student.query...first()`` and passes the result straight
        # through, so a live session naming a deleted student reaches
        # ``student.remaining_quota`` and raises AttributeError -> HTTP 500.
        # Correct behaviour: when the student is missing, clear the session and
        # redirect to the login page.
        with pytest.raises(AttributeError):
            request_service.submit(db_session, None, 5)

    def test_a_missing_student_is_still_rejected_cleanly_for_a_bad_quantity(self, db_session):
        """Ordering check: the quantity guard fires before the student is read."""
        with pytest.raises(InvalidQuantity):
            request_service.submit(db_session, None, 0)


# ---------------------------------------------------------------------------
# submit -- concurrency semantics
# ---------------------------------------------------------------------------


class TestSubmitConcurrencySemantics:
    def test_the_quota_check_and_the_deduction_are_not_atomic(self, db_session, make_student):
        """Sequentially the second request is correctly rejected.

        A real race needs threads; this documents the shape of the window.
        """
        student = make_student(student_id="STU001", remaining_quota=10)
        request_service.submit(db_session, student, 10)
        with pytest.raises(QuotaExceeded):
            request_service.submit(db_session, student, 10)
        assert db_session.query(LaundryRequest).count() == 1
        # BUG: submit() is a read-check-write with no row lock and no
        # CHECK (remaining_quota >= 0) constraint behind it, so under real
        # concurrency two callers can both pass quota.check before either
        # commits its deduction and drive the balance negative. Correct
        # behaviour: SELECT ... FOR UPDATE (or an atomic conditional UPDATE)
        # plus a non-negative database constraint.
        assert student.remaining_quota == 0


# ---------------------------------------------------------------------------
# set_status -- the documented transitions
# ---------------------------------------------------------------------------


@pytest.fixture
def job(make_student, make_request):
    """A submitted job belonging to STU001."""
    make_student(student_id="STU001")
    return make_request(student_id="STU001", num_clothes=5, status="submitted")


class TestSetStatus:
    @pytest.mark.parametrize("new_status", ["submitted", "processing", "completed", "cancelled"])
    def test_every_documented_status_persists(self, db_session, job, new_status):
        request_service.set_status(db_session, job, new_status)
        assert job.status == new_status

    def test_the_change_is_committed(self, db_session, job):
        job_id = job.id
        request_service.set_status(db_session, job, "processing")
        db_session.expunge_all()
        assert db_session.get(LaundryRequest, job_id).status == "processing"

    def test_returns_the_same_request_object(self, db_session, job):
        assert request_service.set_status(db_session, job, "processing") is job

    def test_completing_stamps_the_completed_date(self, db_session, job):
        before = datetime.utcnow() - timedelta(seconds=5)
        request_service.set_status(db_session, job, "completed")
        after = datetime.utcnow() + timedelta(seconds=5)
        assert job.completed_date is not None
        assert before <= job.completed_date <= after

    def test_the_completed_date_can_be_pinned(self, db_session, job):
        pinned = datetime(2026, 3, 4, 5, 6, 7)
        request_service.set_status(db_session, job, "completed", now=pinned)
        assert job.completed_date == pinned

    def test_the_pinned_timestamp_is_ignored_for_other_statuses(self, db_session, job):
        request_service.set_status(db_session, job, "processing", now=datetime(2026, 3, 4))
        assert job.completed_date is None

    @pytest.mark.parametrize("new_status", ["submitted", "processing", "cancelled"])
    def test_non_completed_transitions_leave_the_completed_date_null(
        self, db_session, job, new_status
    ):
        request_service.set_status(db_session, job, new_status)
        assert job.completed_date is None

    def test_updating_one_job_does_not_touch_another(self, db_session, make_student, make_request):
        make_student(student_id="STU001")
        a = make_request(student_id="STU001", num_clothes=1, status="submitted")
        b = make_request(student_id="STU001", num_clothes=2, status="submitted")
        request_service.set_status(db_session, a, "completed")
        assert b.status == "submitted"
        assert b.completed_date is None

    def test_the_submitted_date_is_never_rewritten(self, db_session, job):
        original = job.submission_date
        request_service.set_status(db_session, job, "completed")
        assert job.submission_date == original

    def test_the_num_clothes_is_never_rewritten(self, db_session, job):
        request_service.set_status(db_session, job, "completed")
        assert job.num_clothes == 5

    def test_the_completed_constant_matches_the_string_it_compares(self):
        assert request_service.COMPLETED == "completed"


# ---------------------------------------------------------------------------
# set_status -- documented bugs
# ---------------------------------------------------------------------------


class TestSetStatusDocumentedBugs:
    @pytest.mark.parametrize(
        "garbage",
        ["banana", "COMPLETED", "deleted", "submitted ", "<script>x</script>", "0"],
    )
    def test_arbitrary_status_strings_are_persisted(self, db_session, job, garbage):
        # BUG: set_status assigns the caller's string to the column with no
        # allowlist check, exactly as routes.py did inline. The status field is
        # documented in models.py as one of
        # {submitted, processing, completed, cancelled}, yet any string fits in
        # the String(20) column and is committed. A job set to "banana"
        # vanishes from both admin dashboard queries (it matches neither the
        # running_jobs IN-clause nor status="completed") and becomes
        # unreachable through the UI. Correct behaviour: validate against the
        # allowed set and reject anything else.
        request_service.set_status(db_session, job, garbage)
        assert job.status == garbage[:20]

    def test_uppercase_completed_does_not_stamp_the_completed_date(self, db_session, job):
        # BUG: the comparison is `new_status == "completed"` exactly, so
        # "COMPLETED" stores the status but never stamps completed_date. The
        # row then reads as finished to a human and unfinished to every query.
        request_service.set_status(db_session, job, "COMPLETED")
        assert job.status == "COMPLETED"
        assert job.completed_date is None

    def test_a_none_status_is_persisted(self, db_session, job):
        # BUG: the route passes ``request.form.get("status")``, which is None
        # when the field is absent, and set_status writes that None straight to
        # a column models.py clearly intends to always hold a value. The job is
        # silently erased from every dashboard view. Correct behaviour: reject
        # a missing status instead of storing it.
        request_service.set_status(db_session, job, None)
        assert job.status is None

    def test_an_empty_status_is_persisted(self, db_session, job):
        # BUG: same missing validation; an empty string is stored as the
        # status.
        request_service.set_status(db_session, job, "")
        assert job.status == ""

    def test_moving_out_of_completed_leaves_a_stale_completed_date(self, db_session, job):
        request_service.set_status(db_session, job, "completed")
        stamped = job.completed_date
        assert stamped is not None

        request_service.set_status(db_session, job, "processing")
        # BUG: set_status only ever *sets* completed_date; nothing clears it.
        # Reverting a job to "processing" leaves it claiming a completion
        # timestamp, so the row reads as both in-progress and finished. Correct
        # behaviour: clear completed_date on any transition away from
        # "completed".
        assert job.status == "processing"
        assert job.completed_date == stamped

    def test_recompleting_overwrites_the_completed_date(self, db_session, job):
        first = datetime(2026, 1, 1, 0, 0, 0)
        second = datetime(2026, 6, 1, 0, 0, 0)
        request_service.set_status(db_session, job, "completed", now=first)
        request_service.set_status(db_session, job, "completed", now=second)
        # BUG: set_status re-stamps unconditionally, so the original completion
        # time is lost when an admin re-submits the same status. Correct
        # behaviour: stamp only on the transition *into* "completed".
        assert job.completed_date == second

    def test_cancelling_does_not_refund_the_quota(self, db_session, student):
        created = request_service.submit(db_session, student, 10)
        assert student.remaining_quota == 20

        request_service.set_status(db_session, created, "cancelled")

        # BUG: cancelling a job never returns the deducted clothes to the
        # student's quota -- submit() took them and nothing gives them back.
        # The student permanently loses 10 from their allowance for a job that
        # was never done. Correct behaviour: refund num_clothes to
        # remaining_quota on the transition to "cancelled".
        assert created.status == "cancelled"
        assert student.remaining_quota == 20

    def test_completing_does_not_refund_either(self, db_session, student):
        """For contrast: completion is the case where *not* refunding is right."""
        created = request_service.submit(db_session, student, 10)
        request_service.set_status(db_session, created, "completed")
        assert student.remaining_quota == 20


# ---------------------------------------------------------------------------
# Framework independence
# ---------------------------------------------------------------------------

PRESENTATION_HELPERS = {"flash", "redirect", "url_for", "render_template", "session", "request"}


def test_the_requests_module_imports_no_flask(imported_roots):
    roots = imported_roots(request_service)
    assert "flask" not in roots
    assert "flask_sqlalchemy" not in roots


def test_the_requests_module_names_no_presentation_helpers(referenced_names):
    assert referenced_names(request_service).isdisjoint(PRESENTATION_HELPERS)


def test_the_service_never_reaches_for_a_scoped_session():
    """It must use the session it was handed, not ``db.session``.

    ``db.session`` is a Flask-SQLAlchemy scoped session and raises outside an
    application context, so this is what makes the module usable from a plain
    script, a management command or these tests.
    """
    source = pathlib.Path(request_service.__file__).read_text(encoding="utf-8")
    assert "db.session" not in source
