"""Integration: the admin dashboard, status updates, and the full round trip.

Status-transition semantics live in ``tests/unit/test_request_service.py``.
What is asserted here is the admin blueprint's own wiring -- the queries that
feed the template, the authorization gate, and the one journey that proves the
two roles actually meet in the same database.
"""

import re
from datetime import datetime

import pytest

from models import LaundryRequest

PROTECTED_ROUTES = [("GET", "/admin/dashboard"), ("POST", "/admin/update-status/1")]

# admin.html renders each job id as `>#123</td>`.
_JOB_ID_RE = re.compile(r">#(\d+)</td>")
_STAT_RE = re.compile(
    r'text-gray-500">(Submitted|Processing|Completed|Total Students)</p>\s*<p class="[^"]*">(\d+)</p>'
)


def _job_ids_in(body, section):
    """Job ids rendered in the "running" or "completed" table, in page order."""
    running, _, completed = body.partition("Recently Completed")
    return [int(m) for m in _JOB_ID_RE.findall(running if section == "running" else completed)]


def _stats_in(body):
    """The four stat-card numbers, recovered from the rendered page."""
    pairs = _STAT_RE.findall(body)
    assert len(pairs) == 4, f"could not parse the stat cards, got {pairs}"
    labels = {
        "Submitted": "submitted",
        "Processing": "processing",
        "Completed": "completed",
        "Total Students": "total_students",
    }
    return {labels[label]: int(value) for label, value in pairs}


def test_every_admin_route_redirects_an_anonymous_visitor(client):
    for method, path in PROTECTED_ROUTES:
        resp = client.open(path, method=method)
        assert resp.status_code == 302, path
        assert resp.headers["Location"].endswith("/admin/login"), path

        followed = client.open(path, method=method, follow_redirects=True)
        assert "Admin access required." in followed.get_data(as_text=True), path


def test_a_student_session_does_not_satisfy_admin_required(
    student_client, make_request, db_session
):
    """Cross-role: a logged-in student is anonymous as far as /admin is concerned."""
    job = make_request(student_id="STU001", num_clothes=5, status="submitted")

    for method, path in [("GET", "/admin/dashboard"), ("POST", f"/admin/update-status/{job.id}")]:
        resp = student_client.open(path, method=method, data={"status": "completed"})
        assert resp.status_code == 302, path
        assert resp.headers["Location"].endswith("/admin/login"), path

    assert db_session.get(LaundryRequest, job.id).status == "submitted"


def test_the_dashboard_renders_running_jobs_completed_jobs_and_stats(
    admin_client, make_student, make_request
):
    make_student(student_id="STU001", name="Alice")
    make_student(student_id="STU002", name="Bob")
    submitted = make_request(student_id="STU001", num_clothes=1, status="submitted")
    processing = make_request(student_id="STU002", num_clothes=2, status="processing")
    done = make_request(
        student_id="STU001",
        num_clothes=3,
        status="completed",
        completed_date=datetime(2026, 1, 1),
    )

    body = admin_client.get("/admin/dashboard").get_data(as_text=True)

    assert "Admin Dashboard" in body
    assert set(_job_ids_in(body, "running")) == {submitted.id, processing.id}
    assert _job_ids_in(body, "completed") == [done.id]
    assert "STU001" in body and "STU002" in body
    assert _stats_in(body) == {
        "submitted": 1,
        "processing": 1,
        "completed": 1,
        "total_students": 2,
    }


def test_an_empty_dashboard_renders_its_empty_states(admin_client):
    body = admin_client.get("/admin/dashboard").get_data(as_text=True)
    assert "No active jobs at the moment." in body
    assert "No completed jobs yet." in body
    assert _stats_in(body) == {
        "submitted": 0,
        "processing": 0,
        "completed": 0,
        "total_students": 0,
    }


def test_updating_a_job_persists_and_flashes_a_confirmation(admin_client, make_request, db_session):
    job = make_request(student_id="STU001", num_clothes=5, status="submitted")

    resp = admin_client.post(f"/admin/update-status/{job.id}", data={"status": "completed"})
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/admin/dashboard")

    stored = db_session.get(LaundryRequest, job.id)
    assert stored.status == "completed"
    assert stored.completed_date is not None

    body = admin_client.get("/admin/dashboard").get_data(as_text=True)
    assert f"Job #{job.id} status updated to completed." in body
    assert "bg-green-50" in body, "the confirmation flash must render in the success category"


def test_updating_an_unknown_job_is_a_404(admin_client):
    assert (
        admin_client.post("/admin/update-status/999999", data={"status": "completed"}).status_code
        == 404
    )


# ---------------------------------------------------------------------------
# Status allowlist
#
# A status outside {submitted, processing, completed, cancelled} used to be
# stored verbatim. The job then matched neither dashboard query -- the
# ``status.in_(["submitted", "processing"])`` filter nor
# ``filter_by(status="completed")`` -- so it disappeared from both tables and
# all four stat counters permanently, while the student's quota stayed spent.
# ---------------------------------------------------------------------------

DISALLOWED_STATUSES = ["banana", "", "COMPLETED", "deleted", "submitted ", "<script>x</script>"]


@pytest.mark.parametrize("status", DISALLOWED_STATUSES)
def test_a_disallowed_status_is_rejected_and_the_job_is_unchanged(
    admin_client, make_request, db_session, status
):
    job = make_request(student_id="STU001", num_clothes=5, status="submitted")

    resp = admin_client.post(f"/admin/update-status/{job.id}", data={"status": status})
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/admin/dashboard")

    stored = db_session.get(LaundryRequest, job.id)
    assert stored.status == "submitted"
    assert stored.completed_date is None


def test_an_omitted_status_field_is_rejected(admin_client, make_request, db_session):
    """No ``status`` key at all: the route reads None, which used to be stored.

    A None status renders as the literal text "None" in the student's history.
    """
    job = make_request(student_id="STU001", num_clothes=5, status="submitted")

    resp = admin_client.post(f"/admin/update-status/{job.id}", data={})
    assert resp.status_code == 302
    assert db_session.get(LaundryRequest, job.id).status == "submitted"


def test_a_rejected_status_flashes_an_error_and_leaves_the_job_on_the_board(
    admin_client, make_student, make_request
):
    make_student(student_id="STU001", name="Alice")
    job = make_request(student_id="STU001", num_clothes=5, status="submitted")

    admin_client.post(f"/admin/update-status/{job.id}", data={"status": "banana"})

    body = admin_client.get("/admin/dashboard").get_data(as_text=True)
    assert "Invalid status. Choose submitted, processing, completed or cancelled." in body
    assert "bg-red-50" in body, "the rejection flash must render in the error category"
    assert _job_ids_in(body, "running") == [job.id], "the job must not vanish from the board"
    assert _stats_in(body)["submitted"] == 1


def test_the_rejection_flash_does_not_echo_the_submitted_value(admin_client, make_request):
    job = make_request(student_id="STU001", num_clothes=5, status="submitted")

    admin_client.post(f"/admin/update-status/{job.id}", data={"status": "<script>x</script>"})

    body = admin_client.get("/admin/dashboard").get_data(as_text=True)
    assert "<script>x</script>" not in body
    assert "Invalid status." in body


@pytest.mark.parametrize("status", ["submitted", "processing", "completed", "cancelled"])
def test_every_allowed_status_is_accepted(admin_client, make_request, db_session, status):
    job = make_request(student_id="STU001", num_clothes=5, status="submitted")

    admin_client.post(f"/admin/update-status/{job.id}", data={"status": status})

    assert db_session.get(LaundryRequest, job.id).status == status


# ---------------------------------------------------------------------------
# completed_date follows the status
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("reverted_to", ["submitted", "processing", "cancelled"])
def test_reverting_a_completed_job_clears_the_completion_timestamp(
    admin_client, make_request, db_session, reverted_to
):
    job = make_request(student_id="STU001", num_clothes=5, status="submitted")

    admin_client.post(f"/admin/update-status/{job.id}", data={"status": "completed"})
    assert db_session.get(LaundryRequest, job.id).completed_date is not None

    admin_client.post(f"/admin/update-status/{job.id}", data={"status": reverted_to})

    stored = db_session.get(LaundryRequest, job.id)
    assert stored.status == reverted_to
    assert stored.completed_date is None, "a reverted job must not keep a completion timestamp"


def test_a_reverted_job_returns_to_the_running_board(admin_client, make_student, make_request):
    make_student(student_id="STU001", name="Alice")
    job = make_request(student_id="STU001", num_clothes=5, status="submitted")

    admin_client.post(f"/admin/update-status/{job.id}", data={"status": "completed"})
    admin_client.post(f"/admin/update-status/{job.id}", data={"status": "processing"})

    body = admin_client.get("/admin/dashboard").get_data(as_text=True)
    assert _job_ids_in(body, "running") == [job.id]
    assert _job_ids_in(body, "completed") == []
    assert _stats_in(body) == {
        "submitted": 0,
        "processing": 1,
        "completed": 0,
        "total_students": 1,
    }


def test_recompleting_a_job_keeps_the_original_completion_time(
    admin_client, make_request, db_session
):
    job = make_request(student_id="STU001", num_clothes=5, status="submitted")

    admin_client.post(f"/admin/update-status/{job.id}", data={"status": "completed"})
    first = db_session.get(LaundryRequest, job.id).completed_date

    admin_client.post(f"/admin/update-status/{job.id}", data={"status": "completed"})

    assert db_session.get(LaundryRequest, job.id).completed_date == first


def test_a_student_submission_travels_all_the_way_to_an_admin_completion(
    app, student_client, admin_user, db_session
):
    """The journey the whole application exists for.

    Student submits -> the job appears on the admin's running board -> the
    admin completes it -> the student sees it as completed. Two independent
    clients, two session cookies, one database.
    """
    submitted = student_client.post("/student/submit", data={"num_clothes": "7"})
    assert submitted.status_code == 302
    job = db_session.query(LaundryRequest).one()

    admin_client = app.test_client()
    admin_client.post("/admin/login", data={"username": "admin", "password": "admin123"})

    board = admin_client.get("/admin/dashboard").get_data(as_text=True)
    assert _job_ids_in(board, "running") == [job.id]
    assert _stats_in(board)["submitted"] == 1

    admin_client.post(f"/admin/update-status/{job.id}", data={"status": "completed"})

    board = admin_client.get("/admin/dashboard").get_data(as_text=True)
    assert _job_ids_in(board, "running") == []
    assert _job_ids_in(board, "completed") == [job.id]
    assert _stats_in(board)["completed"] == 1

    student_view = student_client.get("/student/dashboard").get_data(as_text=True)
    assert f">#{job.id}</td>" in student_view
    assert "bg-green-100 text-green-800" in student_view, "the row must render as completed"
    assert "23" in student_view, "the quota stays spent -- completion is not a refund"
