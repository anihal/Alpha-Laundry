"""Tests for routes.py -- the student blueprint (dashboard, submit_request)."""
import re

import pytest

from models import Student, LaundryRequest


# dashboard.html renders each request id as `>#123</td>`. Extract the ids
# properly rather than substring-testing, which would match #1 inside #10.
_REQ_ID_RE = re.compile(r">#(\d+)</td>")


def _request_ids_in(body):
    """Request ids listed in the history table, in page order."""
    return [int(m) for m in _REQ_ID_RE.findall(body)]


# ---------------------------------------------------------------------------
# Student dashboard
# ---------------------------------------------------------------------------

class TestStudentDashboard:
    def test_renders_for_a_logged_in_student(self, student_client):
        resp = student_client.get("/student/dashboard")
        assert resp.status_code == 200
        assert "Your Dashboard" in resp.get_data(as_text=True)

    def test_shows_the_remaining_quota(self, app, make_student):
        make_student(student_id="STU001", name="John Doe",
                     password="password123", remaining_quota=17)
        client = app.test_client()
        client.post("/login", data={"student_id": "STU001", "password": "password123"})
        assert "17" in client.get("/student/dashboard").get_data(as_text=True)

    def test_empty_state_with_zero_requests(self, student_client):
        body = student_client.get("/student/dashboard").get_data(as_text=True)
        assert "No requests yet. Submit your first laundry request above!" in body

    def test_lists_the_students_own_requests(self, student_client, make_request):
        a = make_request(student_id="STU001", num_clothes=3)
        b = make_request(student_id="STU001", num_clothes=4)
        body = student_client.get("/student/dashboard").get_data(as_text=True)
        assert "No requests yet" not in body
        assert set(_request_ids_in(body)) == {a.id, b.id}

    def test_excludes_other_students_requests(
        self, student_client, make_student, make_request
    ):
        make_student(student_id="STU002", name="Jane", password="pw")
        mine = make_request(student_id="STU001", num_clothes=3)
        theirs = make_request(student_id="STU002", num_clothes=99)
        body = student_client.get("/student/dashboard").get_data(as_text=True)
        assert _request_ids_in(body) == [mine.id]
        assert theirs.id not in _request_ids_in(body)
        assert "99" not in body

    def test_requests_are_ordered_newest_first(self, student_client, make_request, times):
        oldest = make_request(student_id="STU001", num_clothes=1, submission_date=times[0])
        middle = make_request(student_id="STU001", num_clothes=2, submission_date=times[1])
        newest = make_request(student_id="STU001", num_clothes=3, submission_date=times[2])

        body = student_client.get("/student/dashboard").get_data(as_text=True)
        assert _request_ids_in(body) == [newest.id, middle.id, oldest.id]

    def test_total_request_count_is_rendered(self, student_client, make_request):
        for _ in range(3):
            make_request(student_id="STU001", num_clothes=1)
        body = student_client.get("/student/dashboard").get_data(as_text=True)
        assert "Total Requests" in body

    def test_completed_requests_are_shown_too(self, student_client, make_request, times):
        make_request(student_id="STU001", num_clothes=2,
                     status="completed", completed_date=times[3])
        body = student_client.get("/student/dashboard").get_data(as_text=True)
        assert "Completed" in body

    def test_exhausted_quota_shows_the_warning(self, app, make_student):
        make_student(student_id="STU001", name="John Doe",
                     password="password123", remaining_quota=0)
        client = app.test_client()
        client.post("/login", data={"student_id": "STU001", "password": "password123"})
        body = client.get("/student/dashboard").get_data(as_text=True)
        assert "Your quota is exhausted. Please contact admin." in body

    def test_anonymous_access_redirects(self, client):
        resp = client.get("/student/dashboard")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/login")

    def test_dashboard_rejects_post(self, student_client):
        assert student_client.post("/student/dashboard").status_code == 405


# ---------------------------------------------------------------------------
# submit_request -- happy paths
# ---------------------------------------------------------------------------

class TestSubmitRequestHappyPath:
    def test_creates_the_row(self, student_client):
        student_client.post("/student/submit", data={"num_clothes": "5"})
        rows = LaundryRequest.query.all()
        assert len(rows) == 1
        assert rows[0].student_id == "STU001"
        assert rows[0].num_clothes == 5
        assert rows[0].status == "submitted"
        assert rows[0].completed_date is None

    def test_deducts_exactly_the_requested_amount(self, student_client):
        student_client.post("/student/submit", data={"num_clothes": "5"})
        assert Student.query.filter_by(student_id="STU001").one().remaining_quota == 25

    def test_redirects_to_the_dashboard(self, student_client):
        resp = student_client.post("/student/submit", data={"num_clothes": "5"})
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/student/dashboard")

    def test_flashes_a_success_message(self, student_client):
        resp = student_client.post(
            "/student/submit", data={"num_clothes": "5"}, follow_redirects=True
        )
        assert "Request submitted for 5 clothes!" in resp.get_data(as_text=True)

    def test_submitting_one_clothe_works(self, student_client):
        student_client.post("/student/submit", data={"num_clothes": "1"})
        assert LaundryRequest.query.count() == 1
        assert Student.query.filter_by(student_id="STU001").one().remaining_quota == 29

    def test_exactly_the_remaining_quota_succeeds_and_zeroes_it(self, student_client):
        student_client.post("/student/submit", data={"num_clothes": "30"})
        assert LaundryRequest.query.count() == 1
        assert Student.query.filter_by(student_id="STU001").one().remaining_quota == 0

    def test_repeated_submissions_accumulate(self, student_client):
        for _ in range(3):
            student_client.post("/student/submit", data={"num_clothes": "4"})
        assert LaundryRequest.query.count() == 3
        assert Student.query.filter_by(student_id="STU001").one().remaining_quota == 18

    def test_submission_after_quota_is_exhausted_is_rejected(self, student_client):
        student_client.post("/student/submit", data={"num_clothes": "30"})
        resp = student_client.post(
            "/student/submit", data={"num_clothes": "1"}, follow_redirects=True
        )
        assert "You only have 0 clothes remaining in your quota." in resp.get_data(as_text=True)
        assert LaundryRequest.query.count() == 1


# ---------------------------------------------------------------------------
# submit_request -- rejections
# ---------------------------------------------------------------------------

class TestSubmitRequestRejections:
    def test_zero_is_rejected(self, student_client):
        resp = student_client.post(
            "/student/submit", data={"num_clothes": "0"}, follow_redirects=True
        )
        assert "Please enter a valid number of clothes." in resp.get_data(as_text=True)
        assert LaundryRequest.query.count() == 0
        assert Student.query.filter_by(student_id="STU001").one().remaining_quota == 30

    def test_negative_is_rejected(self, student_client):
        resp = student_client.post(
            "/student/submit", data={"num_clothes": "-5"}, follow_redirects=True
        )
        assert "Please enter a valid number of clothes." in resp.get_data(as_text=True)
        assert LaundryRequest.query.count() == 0
        assert Student.query.filter_by(student_id="STU001").one().remaining_quota == 30

    def test_a_negative_submission_does_not_inflate_the_quota(self, student_client):
        """Guard against the classic `quota -= -5` bug."""
        student_client.post("/student/submit", data={"num_clothes": "-5"})
        assert Student.query.filter_by(student_id="STU001").one().remaining_quota == 30

    def test_missing_field_falls_back_to_zero_and_is_rejected(self, student_client):
        resp = student_client.post("/student/submit", data={}, follow_redirects=True)
        assert "Please enter a valid number of clothes." in resp.get_data(as_text=True)
        assert LaundryRequest.query.count() == 0

    def test_over_quota_is_rejected(self, student_client):
        resp = student_client.post(
            "/student/submit", data={"num_clothes": "31"}, follow_redirects=True
        )
        assert "You only have 30 clothes remaining in your quota." in resp.get_data(as_text=True)
        assert LaundryRequest.query.count() == 0
        assert Student.query.filter_by(student_id="STU001").one().remaining_quota == 30

    def test_one_over_quota_is_rejected(self, app, make_student):
        make_student(student_id="STU001", name="John Doe",
                     password="password123", remaining_quota=10)
        client = app.test_client()
        client.post("/login", data={"student_id": "STU001", "password": "password123"})
        resp = client.post(
            "/student/submit", data={"num_clothes": "11"}, follow_redirects=True
        )
        assert "You only have 10 clothes remaining in your quota." in resp.get_data(as_text=True)
        assert LaundryRequest.query.count() == 0

    def test_wildly_over_quota_is_rejected(self, student_client):
        student_client.post("/student/submit", data={"num_clothes": "1000000"})
        assert LaundryRequest.query.count() == 0
        assert Student.query.filter_by(student_id="STU001").one().remaining_quota == 30

    def test_anonymous_submission_redirects_and_creates_nothing(self, client, student_user):
        resp = client.post("/student/submit", data={"num_clothes": "5"})
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/login")
        assert LaundryRequest.query.count() == 0

    def test_submit_rejects_get(self, student_client):
        assert student_client.get("/student/submit").status_code == 405


# ---------------------------------------------------------------------------
# submit_request -- non-numeric input (documented bugs)
# ---------------------------------------------------------------------------

class TestSubmitRequestNonNumericInput:
    """routes.py:126 does `int(request.form.get("num_clothes", 0))` with no
    try/except. Anything that is not a base-10 integer literal raises
    ValueError before any validation runs."""

    @pytest.mark.parametrize("raw", ["abc", "", "1.5", "5e3", "0x10", "  ", "5,000", "12abc"])
    def test_non_integer_input_raises_valueerror(self, student_client, raw):
        # BUG: routes.py:126 -- `int(...)` on unvalidated form input. Every one
        # of these values escapes as an unhandled ValueError, i.e. HTTP 500 in
        # production (here TESTING=True propagates it to the caller). Note that
        # "" is what a browser sends when the number input is submitted blank,
        # so this is trivially reachable, not just an attacker path. Correct
        # behaviour: wrap the conversion in try/except ValueError and flash
        # "Please enter a valid number of clothes." exactly like the <= 0 case.
        with pytest.raises(ValueError):
            student_client.post("/student/submit", data={"num_clothes": raw})

    @pytest.mark.parametrize("raw", ["abc", "", "1.5"])
    def test_no_row_is_created_and_the_quota_is_untouched(self, student_client, raw):
        with pytest.raises(ValueError):
            student_client.post("/student/submit", data={"num_clothes": raw})
        assert LaundryRequest.query.count() == 0
        assert Student.query.filter_by(student_id="STU001").one().remaining_quota == 30

    def test_none_input_raises_typeerror(self, student_client):
        # BUG: routes.py:126 -- when the field is present but has no value at
        # all in a multi-valued sense, or when a client sends a raw None, the
        # same unguarded int() is the culprit. Here a whitespace-only string is
        # used as the closest reachable analogue.
        with pytest.raises(ValueError):
            student_client.post("/student/submit", data={"num_clothes": "\t"})

    def test_leading_plus_and_whitespace_are_accepted_by_int(self, student_client):
        """int() tolerates " +5 ", so this one actually succeeds."""
        resp = student_client.post("/student/submit", data={"num_clothes": " +5 "})
        assert resp.status_code == 302
        assert LaundryRequest.query.count() == 1
        assert Student.query.filter_by(student_id="STU001").one().remaining_quota == 25

    def test_non_ascii_digits_are_silently_accepted(self, student_client):
        """int() parses any Unicode decimal digit, e.g. Arabic-Indic U+0663."""
        # BUG: routes.py:126 relies on int()'s Unicode-aware parsing, so the
        # form value "٣" is quietly interpreted as 3 and a real request is
        # created. Whatever the desired policy, the app never decides it --
        # this is an accident of using bare int() on untrusted input. Correct
        # behaviour: validate the input against an explicit ASCII-digit pattern
        # before converting.
        resp = student_client.post("/student/submit", data={"num_clothes": "٣"})
        assert resp.status_code == 302
        assert LaundryRequest.query.one().num_clothes == 3
        assert Student.query.filter_by(student_id="STU001").one().remaining_quota == 27

    def test_deleted_student_with_live_session_raises(self, app, make_student, db_session):
        """submit_request never checks that the student lookup succeeded."""
        student = make_student(student_id="STU001", name="John Doe",
                               password="password123", remaining_quota=30)
        client = app.test_client()
        client.post("/login", data={"student_id": "STU001", "password": "password123"})
        db_session.delete(student)
        db_session.commit()
        # BUG: routes.py:128 assigns `student = Student.query...first()` which
        # can be None, then routes.py:134 reads `student.remaining_quota`
        # unguarded -> AttributeError / HTTP 500. Correct behaviour: if the
        # student is missing, clear the session and redirect to the login page.
        with pytest.raises(AttributeError):
            client.post("/student/submit", data={"num_clothes": "5"})


# ---------------------------------------------------------------------------
# Cross-cutting behaviour
# ---------------------------------------------------------------------------

class TestSubmitRequestConcurrencySemantics:
    def test_quota_check_and_deduction_are_not_atomic(self, app, make_student):
        """Two clients sharing one session can both pass the quota check.

        This drives the two requests sequentially (a real race needs threads),
        but it documents that the read-check-write in routes.py:134-148 runs
        without any row lock or DB-level constraint.
        """
        make_student(student_id="STU001", name="John Doe",
                     password="password123", remaining_quota=10)
        c1 = app.test_client()
        c1.post("/login", data={"student_id": "STU001", "password": "password123"})
        c2 = app.test_client()
        c2.post("/login", data={"student_id": "STU001", "password": "password123"})

        c1.post("/student/submit", data={"num_clothes": "10"})
        c2.post("/student/submit", data={"num_clothes": "10"})

        # Sequentially the second one is correctly rejected...
        assert LaundryRequest.query.count() == 1
        # BUG: ...but routes.py:134-148 is a read-check-write with no row lock
        # and no CHECK (remaining_quota >= 0) constraint, so under real
        # concurrency both requests could pass the check and drive the quota
        # negative. Correct behaviour: use SELECT ... FOR UPDATE (or an atomic
        # conditional UPDATE) plus a non-negative DB constraint.
        assert Student.query.filter_by(student_id="STU001").one().remaining_quota == 0
