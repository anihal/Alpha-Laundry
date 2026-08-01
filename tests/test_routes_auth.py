"""Tests for routes.py -- index, student login, admin login, logout and the
login_required / admin_required decorators."""

import pytest

# ---------------------------------------------------------------------------
# Landing page
# ---------------------------------------------------------------------------


class TestIndex:
    def test_get_root_renders_the_login_page(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Welcome Back" in body
        assert "Sign in to your student account" in body
        assert 'name="student_id"' in body

    def test_root_does_not_require_a_session(self, client):
        assert client.get("/").status_code == 200

    def test_root_sets_no_session_keys(self, client):
        client.get("/")
        with client.session_transaction() as sess:
            assert dict(sess) == {}


# ---------------------------------------------------------------------------
# Student login
# ---------------------------------------------------------------------------


class TestStudentLogin:
    def test_get_renders_the_form(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200
        assert 'action="/login"' in resp.get_data(as_text=True)

    def test_valid_credentials_redirect_to_the_dashboard(self, client, student_user):
        resp = client.post("/login", data={"student_id": "STU001", "password": "password123"})
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/student/dashboard")

    def test_valid_credentials_set_the_session_keys(self, client, student_user):
        client.post("/login", data={"student_id": "STU001", "password": "password123"})
        with client.session_transaction() as sess:
            assert sess["user_id"] == student_user.id
            assert sess["student_id"] == "STU001"
            assert sess["user_name"] == "John Doe"
            assert "admin_id" not in sess

    def test_valid_credentials_flash_a_welcome(self, client, student_user):
        resp = client.post(
            "/login",
            data={"student_id": "STU001", "password": "password123"},
            follow_redirects=True,
        )
        assert "Welcome back!" in resp.get_data(as_text=True)

    def test_wrong_password_rerenders_with_an_error(self, client, student_user):
        resp = client.post("/login", data={"student_id": "STU001", "password": "nope"})
        assert resp.status_code == 200
        assert "Invalid student ID or password." in resp.get_data(as_text=True)

    def test_wrong_password_sets_no_session(self, client, student_user):
        client.post("/login", data={"student_id": "STU001", "password": "nope"})
        with client.session_transaction() as sess:
            assert "user_id" not in sess
            assert "student_id" not in sess

    def test_unknown_student_id_rerenders_with_an_error(self, client, student_user):
        resp = client.post("/login", data={"student_id": "NOPE999", "password": "password123"})
        assert resp.status_code == 200
        assert "Invalid student ID or password." in resp.get_data(as_text=True)

    def test_unknown_student_id_sets_no_session(self, client, student_user):
        client.post("/login", data={"student_id": "NOPE999", "password": "password123"})
        with client.session_transaction() as sess:
            assert "user_id" not in sess

    def test_empty_student_id_is_rejected(self, client, student_user):
        resp = client.post("/login", data={"student_id": "", "password": "password123"})
        assert resp.status_code == 200
        assert "Invalid student ID or password." in resp.get_data(as_text=True)
        with client.session_transaction() as sess:
            assert "user_id" not in sess

    def test_empty_password_is_rejected(self, client, student_user):
        resp = client.post("/login", data={"student_id": "STU001", "password": ""})
        assert resp.status_code == 200
        assert "Invalid student ID or password." in resp.get_data(as_text=True)
        with client.session_transaction() as sess:
            assert "user_id" not in sess

    def test_both_fields_empty_is_rejected(self, client, student_user):
        resp = client.post("/login", data={"student_id": "", "password": ""})
        assert resp.status_code == 200
        assert "Invalid student ID or password." in resp.get_data(as_text=True)

    def test_completely_empty_form_is_rejected(self, client, student_user):
        """No form fields at all: student_id is None so the lookup misses."""
        resp = client.post("/login", data={})
        assert resp.status_code == 200
        assert "Invalid student ID or password." in resp.get_data(as_text=True)

    def test_missing_password_field_for_a_real_student_raises(self, client, student_user):
        """A valid student_id with the password field entirely absent."""
        # BUG: routes.py:62 does `password = request.form.get("password")`,
        # which yields None when the field is absent, and routes.py:66 then
        # calls student.check_password(None). werkzeug's check_password_hash
        # does `password.encode()` -> AttributeError, i.e. an unhandled 500 on
        # a request an attacker fully controls. (With TESTING=True the
        # exception propagates to the caller, which is what this asserts;
        # in production it surfaces as HTTP 500.) Correct behaviour: treat a
        # missing password as a failed login and re-render with the flash.
        with pytest.raises(AttributeError):
            client.post("/login", data={"student_id": "STU001"})

    def test_student_id_lookup_is_case_sensitive(self, client, student_user):
        # BUG: routes.py:64 filters on the raw form value, so "stu001" does not
        # match the stored "STU001". Whether that is desired is a product call,
        # but it is undocumented and surprising -- a student who types their ID
        # in lower case is told their credentials are invalid. Correct
        # behaviour: normalise case (and strip whitespace) on both sides.
        resp = client.post("/login", data={"student_id": "stu001", "password": "password123"})
        assert resp.status_code == 200
        assert "Invalid student ID or password." in resp.get_data(as_text=True)

    def test_surrounding_whitespace_is_not_stripped(self, client, student_user):
        # BUG: routes.py:61 -- " STU001 " does not match "STU001".
        resp = client.post("/login", data={"student_id": " STU001 ", "password": "password123"})
        assert resp.status_code == 200
        assert "Invalid student ID or password." in resp.get_data(as_text=True)

    def test_correct_student_matched_among_several(self, client, make_student):
        make_student(student_id="STU001", name="Alice", password="alice-pw")
        make_student(student_id="STU002", name="Bob", password="bob-pw")
        client.post("/login", data={"student_id": "STU002", "password": "bob-pw"})
        with client.session_transaction() as sess:
            assert sess["student_id"] == "STU002"
            assert sess["user_name"] == "Bob"

    def test_one_students_password_does_not_unlock_another(self, client, make_student):
        make_student(student_id="STU001", name="Alice", password="alice-pw")
        make_student(student_id="STU002", name="Bob", password="bob-pw")
        resp = client.post("/login", data={"student_id": "STU002", "password": "alice-pw"})
        assert resp.status_code == 200
        with client.session_transaction() as sess:
            assert "user_id" not in sess

    def test_login_does_not_grant_admin_access(self, student_client):
        resp = student_client.get("/admin/dashboard")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/admin/login")


# ---------------------------------------------------------------------------
# Admin login
# ---------------------------------------------------------------------------


class TestAdminLogin:
    def test_get_renders_the_form(self, client):
        resp = client.get("/admin/login")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Admin Portal" in body
        assert 'name="username"' in body

    def test_valid_credentials_redirect_to_the_admin_dashboard(self, client, admin_user):
        resp = client.post("/admin/login", data={"username": "admin", "password": "admin123"})
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/admin/dashboard")

    def test_valid_credentials_set_the_session_keys(self, client, admin_user):
        client.post("/admin/login", data={"username": "admin", "password": "admin123"})
        with client.session_transaction() as sess:
            assert sess["admin_id"] == admin_user.id
            assert sess["admin_username"] == "admin"
            assert "user_id" not in sess

    def test_valid_credentials_flash_a_welcome(self, client, admin_user):
        resp = client.post(
            "/admin/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=True,
        )
        assert "Welcome, Admin!" in resp.get_data(as_text=True)

    def test_wrong_password_rerenders_with_an_error(self, client, admin_user):
        resp = client.post("/admin/login", data={"username": "admin", "password": "x"})
        assert resp.status_code == 200
        assert "Invalid username or password." in resp.get_data(as_text=True)

    def test_wrong_password_sets_no_session(self, client, admin_user):
        client.post("/admin/login", data={"username": "admin", "password": "x"})
        with client.session_transaction() as sess:
            assert "admin_id" not in sess

    def test_unknown_username_rerenders_with_an_error(self, client, admin_user):
        resp = client.post("/admin/login", data={"username": "ghost", "password": "admin123"})
        assert resp.status_code == 200
        assert "Invalid username or password." in resp.get_data(as_text=True)
        with client.session_transaction() as sess:
            assert "admin_id" not in sess

    def test_empty_username_is_rejected(self, client, admin_user):
        resp = client.post("/admin/login", data={"username": "", "password": "admin123"})
        assert resp.status_code == 200
        assert "Invalid username or password." in resp.get_data(as_text=True)

    def test_empty_password_is_rejected(self, client, admin_user):
        resp = client.post("/admin/login", data={"username": "admin", "password": ""})
        assert resp.status_code == 200
        assert "Invalid username or password." in resp.get_data(as_text=True)
        with client.session_transaction() as sess:
            assert "admin_id" not in sess

    def test_completely_empty_form_is_rejected(self, client, admin_user):
        resp = client.post("/admin/login", data={})
        assert resp.status_code == 200
        assert "Invalid username or password." in resp.get_data(as_text=True)

    def test_missing_password_field_for_a_real_admin_raises(self, client, admin_user):
        # BUG: routes.py:83/87 -- same unhandled-None flaw as the student login.
        # An absent password field reaches Admin.check_password(None) and blows
        # up with AttributeError (HTTP 500 in production) instead of failing the
        # login cleanly.
        with pytest.raises(AttributeError):
            client.post("/admin/login", data={"username": "admin"})

    def test_student_credentials_do_not_work_on_the_admin_login(self, client, student_user):
        resp = client.post("/admin/login", data={"username": "STU001", "password": "password123"})
        assert resp.status_code == 200
        assert "Invalid username or password." in resp.get_data(as_text=True)
        with client.session_transaction() as sess:
            assert "admin_id" not in sess

    def test_admin_login_does_not_grant_student_access(self, admin_client):
        resp = admin_client.get("/student/dashboard")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/login")


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


class TestLogout:
    def test_clears_a_student_session(self, student_client):
        student_client.get("/logout")
        with student_client.session_transaction() as sess:
            assert "user_id" not in sess
            assert "student_id" not in sess
            assert "user_name" not in sess

    def test_clears_an_admin_session(self, admin_client):
        admin_client.get("/logout")
        with admin_client.session_transaction() as sess:
            assert "admin_id" not in sess
            assert "admin_username" not in sess

    def test_redirects_to_the_student_login(self, student_client):
        resp = student_client.get("/logout")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/login")

    def test_admin_is_also_redirected_to_the_student_login(self, admin_client):
        # BUG: routes.py:103 always redirects to auth.login. An admin who logs
        # out lands on the *student* login page rather than /admin/login.
        # Correct behaviour: branch on which session keys were present and send
        # the admin back to the admin login.
        resp = admin_client.get("/logout")
        assert resp.headers["Location"].endswith("/login")
        assert not resp.headers["Location"].endswith("/admin/login")

    def test_flashes_a_confirmation(self, student_client):
        resp = student_client.get("/logout", follow_redirects=True)
        assert "You have been logged out." in resp.get_data(as_text=True)

    def test_works_when_not_logged_in(self, client):
        resp = client.get("/logout")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/login")

    def test_is_idempotent(self, student_client):
        student_client.get("/logout")
        resp = student_client.get("/logout")
        assert resp.status_code == 302

    def test_after_logout_protected_routes_redirect(self, student_client):
        student_client.get("/logout")
        resp = student_client.get("/student/dashboard")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/login")

    def test_logout_accepts_get(self, client):
        # BUG: routes.py:98 registers /logout for GET only. A state-changing
        # action reachable by GET is CSRF-prone (any <img src="/logout"> logs
        # the user out) -- correct behaviour is POST with a CSRF token.
        assert client.get("/logout").status_code == 302
        assert client.post("/logout").status_code == 405


# ---------------------------------------------------------------------------
# Access-control decorators
# ---------------------------------------------------------------------------

PROTECTED_STUDENT_ROUTES = [
    ("GET", "/student/dashboard"),
    ("POST", "/student/submit"),
]

PROTECTED_ADMIN_ROUTES = [
    ("GET", "/admin/dashboard"),
    ("POST", "/admin/update-status/1"),
]


class TestLoginRequired:
    @pytest.mark.parametrize("method,path", PROTECTED_STUDENT_ROUTES)
    def test_anonymous_is_redirected_to_the_student_login(self, client, method, path):
        resp = client.open(path, method=method)
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/login")

    @pytest.mark.parametrize("method,path", PROTECTED_STUDENT_ROUTES)
    def test_anonymous_gets_a_warning_flash(self, client, method, path):
        resp = client.open(path, method=method, follow_redirects=True)
        assert "Please log in to access this page." in resp.get_data(as_text=True)

    @pytest.mark.parametrize("method,path", PROTECTED_STUDENT_ROUTES)
    def test_an_admin_session_is_treated_as_anonymous(self, admin_client, method, path):
        """Cross-role: admin_id in session does not satisfy login_required."""
        resp = admin_client.open(path, method=method)
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/login")

    def test_user_id_alone_resolves_the_student(self, app, student_user):
        """login_required loads the Student by its primary key, so a session
        carrying only ``user_id`` (no ``student_id``) still resolves correctly
        instead of blowing up when the view needs the student."""
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = student_user.id  # deliberately no student_id
        resp = client.get("/student/dashboard")
        # The decorator resolves the student from the DB and stashes it on
        # flask.g; the view reads g.student rather than session["student_id"],
        # so the two can never disagree and no KeyError is raised.
        assert resp.status_code == 200
        assert "Your Dashboard" in resp.get_data(as_text=True)

    def test_session_naming_a_missing_student_is_rejected(self, app):
        """A session naming a student who no longer exists is rejected, not served."""
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = 999
            sess["student_id"] = "GHOST"
            sess["user_name"] = "Ghost"

        resp = client.get("/student/dashboard")

        # The decorator loads the user and, on a miss, clears the session and
        # redirects to the login rather than rendering a silently broken page.
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/login")
        with client.session_transaction() as sess:
            assert "user_id" not in sess
            assert "student_id" not in sess
            assert "user_name" not in sess


class TestAdminRequired:
    @pytest.mark.parametrize("method,path", PROTECTED_ADMIN_ROUTES)
    def test_anonymous_is_redirected_to_the_admin_login(self, client, method, path):
        resp = client.open(path, method=method)
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/admin/login")

    @pytest.mark.parametrize("method,path", PROTECTED_ADMIN_ROUTES)
    def test_anonymous_gets_a_warning_flash(self, client, method, path):
        resp = client.open(path, method=method, follow_redirects=True)
        assert "Admin access required." in resp.get_data(as_text=True)

    @pytest.mark.parametrize("method,path", PROTECTED_ADMIN_ROUTES)
    def test_a_student_session_is_treated_as_anonymous(self, student_client, method, path):
        """Cross-role: user_id in session does not satisfy admin_required."""
        resp = student_client.open(path, method=method)
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/admin/login")

    def test_session_naming_a_missing_admin_is_rejected(self, app):
        """admin_required resolves the admin row and rejects a missing one."""
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["admin_id"] = 4242  # no such admin
        # A session referencing a deleted/nonexistent admin must not retain
        # admin access: the decorator loads the Admin row, and on a miss clears
        # the session and redirects to the admin login.
        resp = client.get("/admin/dashboard")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/admin/login")
        with client.session_transaction() as sess:
            assert "admin_id" not in sess
            assert "admin_username" not in sess

    def test_decorators_preserve_the_wrapped_function_name(self, app):
        """functools.wraps keeps __name__, which is what Flask uses as the
        endpoint name -- without it every decorated view would collide on the
        endpoint "decorated_function"."""
        endpoints = {rule.endpoint for rule in app.url_map.iter_rules()}
        assert "student.dashboard" in endpoints
        assert "student.submit_request" in endpoints
        assert "admin.dashboard" in endpoints
        assert "admin.update_status" in endpoints
        assert not any("decorated_function" in e for e in endpoints)
