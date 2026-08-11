"""Cancelling and reopening a job through the admin dashboard, end to end."""

import pytest

from models import Student

pytestmark = pytest.mark.integration


def _quota(app, student_id):
    with app.app_context():
        return Student.query.filter_by(student_id=student_id).first().remaining_quota


class TestCancelRefundsThroughTheDashboard:
    def test_cancelling_returns_the_clothes_to_the_student(
        self, app, admin_client, make_student, make_request
    ):
        make_student(student_id="tonsop", name="Tony Soprano", password="pw", remaining_quota=20)
        job = make_request(student_id="tonsop", num_clothes=8, status="submitted")

        response = admin_client.post(f"/admin/update-status/{job.id}", data={"status": "cancelled"})

        assert response.status_code == 302
        assert _quota(app, "tonsop") == 28

    def test_the_student_sees_the_restored_quota(
        self, app, admin_client, make_student, make_request
    ):
        make_student(student_id="tonsop", name="Tony Soprano", password="pw", remaining_quota=20)
        job = make_request(student_id="tonsop", num_clothes=8, status="submitted")
        admin_client.post(f"/admin/update-status/{job.id}", data={"status": "cancelled"})

        client = app.test_client()
        client.post("/login", data={"student_id": "tonsop", "password": "pw"})
        body = client.get("/student/dashboard").get_data(as_text=True)
        assert "28" in body

    def test_completing_does_not_refund(self, app, admin_client, make_student, make_request):
        make_student(student_id="tonsop", name="Tony Soprano", password="pw", remaining_quota=20)
        job = make_request(student_id="tonsop", num_clothes=8, status="submitted")

        admin_client.post(f"/admin/update-status/{job.id}", data={"status": "completed"})
        assert _quota(app, "tonsop") == 20


class TestReopeningThroughTheDashboard:
    def test_reopening_spends_the_clothes_again(
        self, app, admin_client, make_student, make_request
    ):
        make_student(student_id="tonsop", name="Tony Soprano", password="pw", remaining_quota=20)
        job = make_request(student_id="tonsop", num_clothes=8, status="cancelled")

        admin_client.post(f"/admin/update-status/{job.id}", data={"status": "processing"})
        assert _quota(app, "tonsop") == 12

    def test_reopening_without_room_is_refused_with_a_flash(
        self, app, admin_client, make_student, make_request
    ):
        make_student(student_id="soncor", name="Sonny Corleone", password="pw", remaining_quota=2)
        job = make_request(student_id="soncor", num_clothes=9, status="cancelled")

        response = admin_client.post(
            f"/admin/update-status/{job.id}", data={"status": "submitted"}, follow_redirects=True
        )

        body = response.get_data(as_text=True)
        assert "Cannot reopen" in body
        assert "only 2 clothes left" in body

    def test_a_refused_reopen_changes_nothing(self, app, admin_client, make_student, make_request):
        make_student(student_id="soncor", name="Sonny Corleone", password="pw", remaining_quota=2)
        job = make_request(student_id="soncor", num_clothes=9, status="cancelled")

        admin_client.post(f"/admin/update-status/{job.id}", data={"status": "submitted"})

        assert _quota(app, "soncor") == 2
        with app.app_context():
            from models import LaundryRequest

            assert LaundryRequest.query.get(job.id).status == "cancelled"
