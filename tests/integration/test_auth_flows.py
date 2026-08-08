"""Integration: logging in, logging out, and the seeded database.

Credential checking itself is covered by the model unit tests. What is asserted
here is the part that only exists once the stack is assembled -- that a POST to
the login route sets a signed session cookie, that the redirect goes where the
templates expect, and that the flash survives the redirect.
"""

from app import init_db
from models import Admin, Student


def test_the_landing_page_renders_the_student_login_form(client):
    """`/` renders login.html through Jinja, with no session required."""
    resp = client.get("/")
    body = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert "Welcome Back" in body
    assert 'name="student_id"' in body
    assert 'name="password"' in body
    with client.session_transaction() as sess:
        assert dict(sess) == {}


def test_student_login_sets_a_session_and_redirects_to_the_dashboard(client, student_user):
    resp = client.post("/login", data={"student_id": "STU001", "password": "password123"})

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/student/dashboard")
    with client.session_transaction() as sess:
        assert sess["user_id"] == student_user.id
        assert sess["student_id"] == "STU001"
        assert sess["user_name"] == "John Doe"
        assert "admin_id" not in sess

    followed = client.get("/student/dashboard")
    assert "Welcome back!" in followed.get_data(as_text=True)


def test_a_bad_student_password_rerenders_the_form_with_an_error(client, student_user):
    resp = client.post("/login", data={"student_id": "STU001", "password": "nope"})

    assert resp.status_code == 200
    assert "Invalid student ID or password." in resp.get_data(as_text=True)
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_admin_login_sets_a_session_and_redirects_to_the_admin_dashboard(client, admin_user):
    resp = client.post("/admin/login", data={"username": "admin", "password": "admin123"})

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/admin/dashboard")
    with client.session_transaction() as sess:
        assert sess["admin_id"] == admin_user.id
        assert sess["admin_username"] == "admin"
        assert "user_id" not in sess

    followed = client.get("/admin/dashboard")
    assert "Welcome, Admin!" in followed.get_data(as_text=True)


def test_a_bad_admin_password_rerenders_the_form_with_an_error(client, admin_user):
    resp = client.post("/admin/login", data={"username": "admin", "password": "x"})

    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Admin Portal" in body
    assert "Invalid username or password." in body
    with client.session_transaction() as sess:
        assert "admin_id" not in sess


# ---------------------------------------------------------------------------
# A missing password field
#
# ``check_password(None)`` raises inside werkzeug (it calls ``.encode()`` on the
# value), so a POST carrying a *valid* student_id with no password field at all
# used to be an HTTP 500 while an unknown id rendered a normal 200. That
# 500-vs-200 split enumerated valid student IDs and admin usernames with zero
# password guesses. A missing password must be indistinguishable from a wrong
# one -- same status, same flash, no session.
# ---------------------------------------------------------------------------


def test_a_student_login_without_a_password_field_matches_a_wrong_password(client, student_user):
    missing = client.post("/login", data={"student_id": "STU001"})
    wrong = client.post("/login", data={"student_id": "STU001", "password": "nope"})

    assert missing.status_code == wrong.status_code == 200
    assert "Invalid student ID or password." in missing.get_data(as_text=True)
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_a_student_login_without_a_password_field_is_not_an_id_oracle(client, student_user):
    """A valid id and an unknown id must be indistinguishable from outside."""
    known = client.post("/login", data={"student_id": "STU001"})
    unknown = client.post("/login", data={"student_id": "NO-SUCH-STUDENT"})

    assert known.status_code == unknown.status_code == 200
    assert known.get_data(as_text=True) == unknown.get_data(as_text=True)


def test_an_admin_login_without_a_password_field_matches_a_wrong_password(client, admin_user):
    missing = client.post("/admin/login", data={"username": "admin"})
    wrong = client.post("/admin/login", data={"username": "admin", "password": "nope"})

    assert missing.status_code == wrong.status_code == 200
    assert "Invalid username or password." in missing.get_data(as_text=True)
    with client.session_transaction() as sess:
        assert "admin_id" not in sess


def test_an_admin_login_without_a_password_field_is_not_a_username_oracle(client, admin_user):
    known = client.post("/admin/login", data={"username": "admin"})
    unknown = client.post("/admin/login", data={"username": "no-such-admin"})

    assert known.status_code == unknown.status_code == 200
    assert known.get_data(as_text=True) == unknown.get_data(as_text=True)


def test_an_empty_password_is_rejected_for_both_roles(client, student_user, admin_user):
    student = client.post("/login", data={"student_id": "STU001", "password": ""})
    assert student.status_code == 200
    assert "Invalid student ID or password." in student.get_data(as_text=True)

    admin = client.post("/admin/login", data={"username": "admin", "password": ""})
    assert admin.status_code == 200
    assert "Invalid username or password." in admin.get_data(as_text=True)

    with client.session_transaction() as sess:
        assert "user_id" not in sess
        assert "admin_id" not in sess


def test_a_login_post_with_no_fields_at_all_is_rejected(client, student_user, admin_user):
    assert client.post("/login", data={}).status_code == 200
    assert client.post("/admin/login", data={}).status_code == 200
    with client.session_transaction() as sess:
        assert dict(sess) == {}


def test_logout_clears_the_session_and_locks_the_dashboard_again(student_client):
    resp = student_client.get("/logout", follow_redirects=True)

    assert "You have been logged out." in resp.get_data(as_text=True)
    with student_client.session_transaction() as sess:
        assert "user_id" not in sess
        assert "student_id" not in sess

    locked = student_client.get("/student/dashboard")
    assert locked.status_code == 302
    assert locked.headers["Location"].endswith("/login")


def test_the_seeded_database_can_be_logged_into(bare_app):
    """``init_db`` creates the schema and seeds credentials that actually work.

    This is the one place the seeding path is exercised end to end: schema
    creation, the sample rows, and the hashes those rows carry all have to line
    up for these logins to succeed.
    """
    init_db(bare_app)

    with bare_app.app_context():
        assert sorted(s.student_id for s in Student.query.all()) == ["STU001", "STU002"]
        assert [a.username for a in Admin.query.all()] == ["admin"]

    student = bare_app.test_client()
    resp = student.post("/login", data={"student_id": "STU001", "password": "password123"})
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/student/dashboard")

    admin = bare_app.test_client()
    resp = admin.post("/admin/login", data={"username": "admin", "password": "admin123"})
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/admin/dashboard")
