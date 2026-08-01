"""Tests for routes.py -- the admin blueprint (dashboard, update_status)."""

import re
from datetime import datetime, timedelta

import pytest
from models import LaundryRequest

# The admin template renders each job id as `>#123</td>`. Parsing the ids out
# properly matters: a naive `f"#{id}" in body` substring test would report job
# #1 as present whenever job #10 is rendered.
_JOB_ID_RE = re.compile(r">#(\d+)</td>")


def _job_ids_in(body, section):
    """Job ids rendered in the "running" or "completed" table, in page order."""
    running, _, completed = body.partition("Recently Completed")
    assert section in ("running", "completed")
    return [int(m) for m in _JOB_ID_RE.findall(running if section == "running" else completed)]


# ---------------------------------------------------------------------------
# Admin dashboard
# ---------------------------------------------------------------------------


class TestAdminDashboard:
    def test_renders_for_a_logged_in_admin(self, admin_client):
        resp = admin_client.get("/admin/dashboard")
        assert resp.status_code == 200
        assert "Admin Dashboard" in resp.get_data(as_text=True)

    def test_empty_states(self, admin_client):
        body = admin_client.get("/admin/dashboard").get_data(as_text=True)
        assert "No active jobs at the moment." in body
        assert "No completed jobs yet." in body

    def test_running_jobs_include_submitted_and_processing(
        self, admin_client, make_student, make_request
    ):
        make_student(student_id="STU001")
        submitted = make_request(student_id="STU001", num_clothes=1, status="submitted")
        processing = make_request(student_id="STU001", num_clothes=2, status="processing")
        body = admin_client.get("/admin/dashboard").get_data(as_text=True)
        assert set(_job_ids_in(body, "running")) == {submitted.id, processing.id}
        assert "No active jobs at the moment." not in body

    def test_running_jobs_exclude_completed_and_cancelled(
        self, admin_client, make_student, make_request, times
    ):
        make_student(student_id="STU001")
        active = make_request(student_id="STU001", num_clothes=1, status="submitted")
        completed = make_request(
            student_id="STU001", num_clothes=2, status="completed", completed_date=times[1]
        )
        cancelled = make_request(student_id="STU001", num_clothes=3, status="cancelled")

        body = admin_client.get("/admin/dashboard").get_data(as_text=True)
        running = _job_ids_in(body, "running")
        assert running == [active.id]
        assert completed.id not in running
        assert cancelled.id not in running

    def test_cancelled_jobs_are_invisible_everywhere(
        self, admin_client, make_student, make_request
    ):
        make_student(student_id="STU001")
        cancelled = make_request(student_id="STU001", num_clothes=3, status="cancelled")
        body = admin_client.get("/admin/dashboard").get_data(as_text=True)
        # BUG: routes.py:163-169 builds running_jobs from
        # {submitted, processing} and completed_jobs from {completed}, so a
        # "cancelled" job -- a status the admin UI itself offers in its dropdown
        # (templates/admin.html) -- disappears from the dashboard entirely with
        # no way to review or undo it. The stats dict (routes.py:172-177) has no
        # "cancelled" counter either. Correct behaviour: surface cancelled jobs
        # in their own section and count them.
        assert cancelled.id not in _job_ids_in(body, "running")
        assert cancelled.id not in _job_ids_in(body, "completed")
        assert "No active jobs at the moment." in body
        assert "No completed jobs yet." in body

    def test_running_jobs_are_ordered_newest_first(
        self, admin_client, make_student, make_request, times
    ):
        make_student(student_id="STU001")
        oldest = make_request(
            student_id="STU001", num_clothes=1, status="submitted", submission_date=times[0]
        )
        newest = make_request(
            student_id="STU001", num_clothes=2, status="processing", submission_date=times[5]
        )
        body = admin_client.get("/admin/dashboard").get_data(as_text=True)
        assert _job_ids_in(body, "running") == [newest.id, oldest.id]

    def test_completed_jobs_include_only_completed(
        self, admin_client, make_student, make_request, times
    ):
        make_student(student_id="STU001")
        done = make_request(
            student_id="STU001", num_clothes=1, status="completed", completed_date=times[1]
        )
        make_request(student_id="STU001", num_clothes=2, status="submitted")
        make_request(student_id="STU001", num_clothes=3, status="cancelled")

        body = admin_client.get("/admin/dashboard").get_data(as_text=True)
        assert _job_ids_in(body, "completed") == [done.id]
        assert "No completed jobs yet." not in body

    def test_completed_jobs_are_capped_at_20(self, admin_client, make_student, make_request):
        make_student(student_id="STU001")
        base = datetime(2026, 1, 1, 0, 0, 0)
        ids = []
        for i in range(25):
            req = make_request(
                student_id="STU001",
                num_clothes=1,
                status="completed",
                submission_date=base + timedelta(minutes=i),
                completed_date=base + timedelta(hours=i),
            )
            ids.append(req.id)

        body = admin_client.get("/admin/dashboard").get_data(as_text=True)
        shown = _job_ids_in(body, "completed")
        assert len(shown) == 20
        # The 20 most recently completed are the last 20 created (latest
        # completed_date), listed newest-first.
        assert shown == list(reversed(ids[5:]))

    def test_completed_jobs_ordered_by_completed_date_desc(
        self, admin_client, make_student, make_request, times
    ):
        make_student(student_id="STU001")
        early = make_request(
            student_id="STU001", num_clothes=1, status="completed", completed_date=times[1]
        )
        late = make_request(
            student_id="STU001", num_clothes=2, status="completed", completed_date=times[6]
        )
        body = admin_client.get("/admin/dashboard").get_data(as_text=True)
        assert _job_ids_in(body, "completed") == [late.id, early.id]

    def test_completed_job_without_a_completed_date_still_renders(
        self, admin_client, make_student, make_request
    ):
        """Rows marked completed directly in the DB have a NULL completed_date."""
        make_student(student_id="STU001")
        orphan = make_request(student_id="STU001", num_clothes=2, status="completed")
        body = admin_client.get("/admin/dashboard").get_data(as_text=True)
        assert _job_ids_in(body, "completed") == [orphan.id]
        assert orphan.completed_date is None

    def test_stats_counts_are_correct(self, admin_client, make_student, make_request, times):
        make_student(student_id="STU001", name="A")
        make_student(student_id="STU002", name="B")
        make_student(student_id="STU003", name="C")
        for _ in range(2):
            make_request(student_id="STU001", num_clothes=1, status="submitted")
        for _ in range(3):
            make_request(student_id="STU002", num_clothes=1, status="processing")
        for _ in range(4):
            make_request(
                student_id="STU003", num_clothes=1, status="completed", completed_date=times[1]
            )
        make_request(student_id="STU001", num_clothes=1, status="cancelled")

        resp = admin_client.get("/admin/dashboard")
        stats = _captured_stats(resp)
        assert stats == {
            "submitted": 2,
            "processing": 3,
            "completed": 4,
            "total_students": 3,
        }

    def test_stats_are_all_zero_on_an_empty_system(self, app, make_admin):
        make_admin(username="admin", password="admin123")
        client = app.test_client()
        client.post("/admin/login", data={"username": "admin", "password": "admin123"})
        stats = _captured_stats(client.get("/admin/dashboard"))
        assert stats == {"submitted": 0, "processing": 0, "completed": 0, "total_students": 0}

    def test_stats_total_students_counts_students_not_requests(
        self, admin_client, make_student, make_request
    ):
        make_student(student_id="STU001")
        for _ in range(5):
            make_request(student_id="STU001", num_clothes=1)
        assert _captured_stats(admin_client.get("/admin/dashboard"))["total_students"] == 1

    def test_dashboard_shows_jobs_from_every_student(
        self, admin_client, make_student, make_request
    ):
        make_student(student_id="STU001", name="A")
        make_student(student_id="STU002", name="B")
        a = make_request(student_id="STU001", num_clothes=1)
        b = make_request(student_id="STU002", num_clothes=2)
        body = admin_client.get("/admin/dashboard").get_data(as_text=True)
        assert set(_job_ids_in(body, "running")) == {a.id, b.id}
        assert "STU001" in body and "STU002" in body

    def test_anonymous_access_redirects(self, client):
        resp = client.get("/admin/dashboard")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/admin/login")

    def test_dashboard_rejects_post(self, admin_client):
        assert admin_client.post("/admin/dashboard").status_code == 405


def _captured_stats(resp):
    """Recover the four stat numbers from the rendered admin dashboard."""
    import re

    body = resp.get_data(as_text=True)
    pairs = re.findall(
        r'text-gray-500">(Submitted|Processing|Completed|Total Students)</p>\s*'
        r'<p class="[^"]*">(\d+)</p>',
        body,
    )
    mapping = {
        "Submitted": "submitted",
        "Processing": "processing",
        "Completed": "completed",
        "Total Students": "total_students",
    }
    assert len(pairs) == 4, f"could not parse stats cards, got {pairs}"
    return {mapping[label]: int(value) for label, value in pairs}


# ---------------------------------------------------------------------------
# update_status
# ---------------------------------------------------------------------------


class TestUpdateStatus:
    @pytest.fixture
    def job(self, make_student, make_request):
        make_student(student_id="STU001")
        return make_request(student_id="STU001", num_clothes=5, status="submitted")

    def test_submitted_to_processing_persists(self, admin_client, job):
        admin_client.post(f"/admin/update-status/{job.id}", data={"status": "processing"})
        assert LaundryRequest.query.get(job.id).status == "processing"

    def test_processing_to_completed_persists(self, admin_client, make_student, make_request):
        make_student(student_id="STU001")
        req = make_request(student_id="STU001", num_clothes=5, status="processing")
        admin_client.post(f"/admin/update-status/{req.id}", data={"status": "completed"})
        assert LaundryRequest.query.get(req.id).status == "completed"

    def test_to_cancelled_persists(self, admin_client, job):
        admin_client.post(f"/admin/update-status/{job.id}", data={"status": "cancelled"})
        assert LaundryRequest.query.get(job.id).status == "cancelled"

    def test_completing_sets_completed_date(self, admin_client, job):
        before = datetime.utcnow() - timedelta(seconds=5)
        admin_client.post(f"/admin/update-status/{job.id}", data={"status": "completed"})
        after = datetime.utcnow() + timedelta(seconds=5)
        stored = LaundryRequest.query.get(job.id)
        assert stored.completed_date is not None
        assert before <= stored.completed_date <= after

    def test_non_completed_transitions_leave_completed_date_null(self, admin_client, job):
        admin_client.post(f"/admin/update-status/{job.id}", data={"status": "processing"})
        assert LaundryRequest.query.get(job.id).completed_date is None

    def test_redirects_to_the_admin_dashboard(self, admin_client, job):
        resp = admin_client.post(f"/admin/update-status/{job.id}", data={"status": "processing"})
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/admin/dashboard")

    def test_flashes_a_confirmation(self, admin_client, job):
        resp = admin_client.post(
            f"/admin/update-status/{job.id}",
            data={"status": "processing"},
            follow_redirects=True,
        )
        assert f"Job #{job.id} status updated to processing." in resp.get_data(as_text=True)

    def test_updating_one_job_does_not_touch_another(
        self, admin_client, make_student, make_request
    ):
        make_student(student_id="STU001")
        a = make_request(student_id="STU001", num_clothes=1, status="submitted")
        b = make_request(student_id="STU001", num_clothes=2, status="submitted")
        admin_client.post(f"/admin/update-status/{a.id}", data={"status": "completed"})
        assert LaundryRequest.query.get(b.id).status == "submitted"
        assert LaundryRequest.query.get(b.id).completed_date is None

    def test_nonexistent_request_id_returns_404(self, admin_client, job):
        resp = admin_client.post("/admin/update-status/999999", data={"status": "completed"})
        assert resp.status_code == 404

    def test_non_integer_request_id_returns_404(self, admin_client):
        """The <int:request_id> converter refuses to match a non-integer."""
        assert (
            admin_client.post("/admin/update-status/abc", data={"status": "completed"}).status_code
            == 404
        )

    def test_anonymous_cannot_update(self, client, make_student, make_request):
        make_student(student_id="STU001")
        req = make_request(student_id="STU001", num_clothes=5, status="submitted")
        resp = client.post(f"/admin/update-status/{req.id}", data={"status": "completed"})
        assert resp.status_code == 302
        assert LaundryRequest.query.get(req.id).status == "submitted"

    def test_a_student_cannot_update(self, student_client, make_request):
        req = make_request(student_id="STU001", num_clothes=5, status="submitted")
        resp = student_client.post(f"/admin/update-status/{req.id}", data={"status": "completed"})
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/admin/login")
        assert LaundryRequest.query.get(req.id).status == "submitted"

    def test_update_rejects_get(self, admin_client, job):
        assert admin_client.get(f"/admin/update-status/{job.id}").status_code == 405

    # -- documented bugs ---------------------------------------------------

    @pytest.mark.parametrize(
        "garbage",
        ["banana", "COMPLETED", "deleted", "submitted ", "<script>x</script>", "0"],
    )
    def test_arbitrary_status_strings_are_persisted(self, admin_client, job, garbage):
        # BUG: routes.py:187-190 takes request.form["status"] verbatim and
        # assigns it to the column with no whitelist check. The status field is
        # documented in models.py:42 as one of
        # {submitted, processing, completed, cancelled}, yet any string fits in
        # the String(20) column and is committed. A job set to "banana"
        # vanishes from both dashboard queries (it matches neither the
        # running_jobs IN-clause nor status="completed") and becomes
        # unreachable through the UI. Note "COMPLETED" also fails to trigger
        # the completed_date branch at routes.py:192 because the comparison is
        # case-sensitive. Correct behaviour: validate against the allowed set
        # and return 400 / flash an error otherwise.
        admin_client.post(f"/admin/update-status/{job.id}", data={"status": garbage})
        assert LaundryRequest.query.get(job.id).status == garbage[:20]

    def test_uppercase_completed_does_not_set_completed_date(self, admin_client, job):
        # BUG: routes.py:192 compares `new_status == "completed"` exactly, so
        # "COMPLETED" stores the status but never stamps completed_date.
        admin_client.post(f"/admin/update-status/{job.id}", data={"status": "COMPLETED"})
        stored = LaundryRequest.query.get(job.id)
        assert stored.status == "COMPLETED"
        assert stored.completed_date is None

    def test_missing_status_field_sets_status_to_none(self, admin_client, job):
        # BUG: routes.py:187 -- `request.form.get("status")` returns None when
        # the field is absent, and routes.py:188 writes that None straight to a
        # column that models.py:42 clearly intends to always hold a value. The
        # job is silently erased from every dashboard view. Correct behaviour:
        # reject the request with 400 when status is missing.
        admin_client.post(f"/admin/update-status/{job.id}", data={})
        assert LaundryRequest.query.get(job.id).status is None

    def test_empty_status_is_persisted(self, admin_client, job):
        # BUG: routes.py:187-188 -- same missing validation; an empty string is
        # stored as the status.
        admin_client.post(f"/admin/update-status/{job.id}", data={"status": ""})
        assert LaundryRequest.query.get(job.id).status == ""

    def test_moving_out_of_completed_leaves_a_stale_completed_date(self, admin_client, job):
        admin_client.post(f"/admin/update-status/{job.id}", data={"status": "completed"})
        stamped = LaundryRequest.query.get(job.id).completed_date
        assert stamped is not None

        admin_client.post(f"/admin/update-status/{job.id}", data={"status": "processing"})
        stored = LaundryRequest.query.get(job.id)
        # BUG: routes.py:192-193 only ever *sets* completed_date; nothing clears
        # it. Reverting a job to "processing" leaves it claiming a completion
        # timestamp, so the row reads as both in-progress and finished.
        # Correct behaviour: set completed_date = None on any transition away
        # from "completed".
        assert stored.status == "processing"
        assert stored.completed_date == stamped

    def test_recompleting_overwrites_the_completed_date(self, admin_client, job):
        admin_client.post(f"/admin/update-status/{job.id}", data={"status": "completed"})
        first = LaundryRequest.query.get(job.id).completed_date
        admin_client.post(f"/admin/update-status/{job.id}", data={"status": "completed"})
        second = LaundryRequest.query.get(job.id).completed_date
        # BUG: routes.py:192-193 re-stamps unconditionally, so the original
        # completion time is lost when an admin re-submits the same status.
        # Correct behaviour: only stamp on the transition into "completed".
        assert second >= first

    def test_cancelling_does_not_refund_the_quota(
        self, app, make_student, make_admin, make_request
    ):
        make_student(
            student_id="STU001", name="John Doe", password="password123", remaining_quota=30
        )
        make_admin(username="admin", password="admin123")

        student = app.test_client()
        student.post("/login", data={"student_id": "STU001", "password": "password123"})
        student.post("/student/submit", data={"num_clothes": "10"})
        req = LaundryRequest.query.one()

        admin = app.test_client()
        admin.post("/admin/login", data={"username": "admin", "password": "admin123"})
        admin.post(f"/admin/update-status/{req.id}", data={"status": "cancelled"})

        from models import Student

        # BUG: routes.py:185-198 -- cancelling a job never returns the deducted
        # clothes to the student's quota (routes.py:145 deducted them on
        # submission). The student permanently loses 10 from their allowance for
        # a job that was never done. Correct behaviour: refund
        # num_clothes to remaining_quota when transitioning to "cancelled".
        assert Student.query.filter_by(student_id="STU001").one().remaining_quota == 20
