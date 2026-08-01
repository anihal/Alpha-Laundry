"""Integration: the student dashboard and the submit route.

Quota arithmetic and validation are covered exhaustively by
``tests/unit/test_quota_service.py`` and ``tests/unit/test_request_service.py``.
What is asserted here is the translation layer -- that a domain outcome becomes
the right status code, redirect, flash category and rendered page.
"""

import re

from models import LaundryRequest, Student

PROTECTED_ROUTES = [("GET", "/student/dashboard"), ("POST", "/student/submit")]

# dashboard.html renders each request id as `>#123</td>`.
_REQUEST_ID_RE = re.compile(r">#(\d+)</td>")


def _request_ids_in(body):
    return [int(m) for m in _REQUEST_ID_RE.findall(body)]


def test_every_student_route_redirects_an_anonymous_visitor(client):
    for method, path in PROTECTED_ROUTES:
        resp = client.open(path, method=method)
        assert resp.status_code == 302, path
        assert resp.headers["Location"].endswith("/login"), path

        followed = client.open(path, method=method, follow_redirects=True)
        assert "Please log in to access this page." in followed.get_data(as_text=True), path


def test_an_admin_session_does_not_satisfy_login_required(admin_client):
    """Cross-role: ``admin_id`` in the session is not a student login."""
    for method, path in PROTECTED_ROUTES:
        resp = admin_client.open(path, method=method)
        assert resp.status_code == 302, path
        assert resp.headers["Location"].endswith("/login"), path


def test_the_dashboard_renders_the_students_name_quota_and_history(
    student_client, make_request, make_student
):
    mine = make_request(student_id="STU001", num_clothes=3)
    make_student(student_id="STU002", name="Jane")
    theirs = make_request(student_id="STU002", num_clothes=99)

    body = student_client.get("/student/dashboard").get_data(as_text=True)

    assert "Your Dashboard" in body
    assert "John Doe" in body
    assert "30" in body
    assert _request_ids_in(body) == [mine.id]
    assert theirs.id not in _request_ids_in(body)
    assert "No requests yet" not in body


def test_an_empty_dashboard_renders_its_empty_state(student_client):
    body = student_client.get("/student/dashboard").get_data(as_text=True)
    assert "No requests yet. Submit your first laundry request above!" in body


def test_submitting_within_quota_persists_and_shows_up_on_the_dashboard(student_client, db_session):
    resp = student_client.post("/student/submit", data={"num_clothes": "5"})

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/student/dashboard")

    created = db_session.query(LaundryRequest).one()
    assert created.student_id == "STU001"
    assert created.num_clothes == 5
    assert created.status == "submitted"
    assert db_session.query(Student).filter_by(student_id="STU001").one().remaining_quota == 25

    body = student_client.get("/student/dashboard").get_data(as_text=True)
    assert "Request submitted for 5 clothes!" in body
    assert "bg-green-50" in body, "the success flash must render in the success category"
    assert _request_ids_in(body) == [created.id]


def test_submitting_over_quota_is_rejected_with_the_remaining_count(student_client, db_session):
    resp = student_client.post("/student/submit", data={"num_clothes": "31"}, follow_redirects=True)
    body = resp.get_data(as_text=True)

    assert "You only have 30 clothes remaining in your quota." in body
    assert "bg-red-50" in body, "the rejection flash must render in the error category"
    assert db_session.query(LaundryRequest).count() == 0
    assert db_session.query(Student).filter_by(student_id="STU001").one().remaining_quota == 30


def test_submitting_a_non_positive_quantity_is_rejected(student_client, db_session):
    resp = student_client.post("/student/submit", data={"num_clothes": "0"}, follow_redirects=True)
    body = resp.get_data(as_text=True)

    assert "Please enter a valid number of clothes." in body
    assert "bg-red-50" in body
    assert db_session.query(LaundryRequest).count() == 0
    assert db_session.query(Student).filter_by(student_id="STU001").one().remaining_quota == 30
