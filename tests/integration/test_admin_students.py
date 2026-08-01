"""The admin student directory reached from the Total Students card."""

import pytest

pytestmark = pytest.mark.integration


class TestAccessControl:
    def test_anonymous_is_redirected_to_admin_login(self, client):
        response = client.get("/admin/students")
        assert response.status_code == 302
        assert "/admin/login" in response.headers["Location"]

    def test_a_student_session_cannot_reach_it(self, student_client):
        response = student_client.get("/admin/students")
        assert response.status_code == 302
        assert "/admin/login" in response.headers["Location"]

    def test_an_admin_can_reach_it(self, admin_client):
        assert admin_client.get("/admin/students").status_code == 200


class TestDirectoryContents:
    def test_lists_every_student(self, admin_client, make_student):
        make_student(student_id="tonsop", name="Tony Soprano", password="pw")
        make_student(student_id="henhil", name="Henry Hill", password="pw")

        body = admin_client.get("/admin/students").get_data(as_text=True)
        assert "Tony Soprano" in body
        assert "tonsop" in body
        assert "Henry Hill" in body
        assert "henhil" in body

    def test_shows_the_remaining_quota(self, admin_client, make_student):
        make_student(student_id="soncor", name="Sonny Corleone", password="pw", remaining_quota=6)
        assert "6 left" in admin_client.get("/admin/students").get_data(as_text=True)

    def test_counts_requests_and_clothes_per_student(
        self, admin_client, make_student, make_request
    ):
        make_student(student_id="tonsop", name="Tony Soprano", password="pw")
        make_request(student_id="tonsop", num_clothes=4)
        make_request(student_id="tonsop", num_clothes=5)

        body = admin_client.get("/admin/students").get_data(as_text=True)
        row = [line for line in body.splitlines() if "tonsop" in line]
        assert row, "expected the student's row to render"
        # 2 requests totalling 9 clothes.
        assert ">2<" in body
        assert ">9<" in body

    def test_a_student_with_no_requests_still_appears(self, admin_client, make_student):
        make_student(student_id="junsop", name="Junior Soprano", password="pw")
        body = admin_client.get("/admin/students").get_data(as_text=True)
        assert "Junior Soprano" in body
        assert ">0<" in body

    def test_one_students_requests_are_not_counted_for_another(
        self, admin_client, make_student, make_request
    ):
        make_student(student_id="tonsop", name="Tony Soprano", password="pw")
        make_student(student_id="junsop", name="Junior Soprano", password="pw")
        make_request(student_id="tonsop", num_clothes=7)

        body = admin_client.get("/admin/students").get_data(as_text=True)
        junior_row = next(line for line in body.splitlines() if "junsop" in line)
        assert "7" not in junior_row

    def test_students_are_ordered_by_name(self, admin_client, make_student):
        make_student(student_id="vitcor", name="Vito Corleone", password="pw")
        make_student(student_id="adrlac", name="Adriana La Cerva", password="pw")

        body = admin_client.get("/admin/students").get_data(as_text=True)
        assert body.index("Adriana La Cerva") < body.index("Vito Corleone")

    def test_empty_state_when_nobody_is_enrolled(self, admin_client):
        body = admin_client.get("/admin/students").get_data(as_text=True)
        assert "No students enrolled yet." in body


class TestDashboardLink:
    def test_the_total_students_card_links_to_the_directory(self, admin_client):
        body = admin_client.get("/admin/dashboard").get_data(as_text=True)
        assert 'href="/admin/students"' in body
