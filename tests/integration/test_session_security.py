"""Regression tests for the forgeable-session fix.

Each test here fails against the pre-fix code:

* a session cookie forged with the published default SECRET_KEY was accepted;
* a validly signed cookie naming a nonexistent admin/student was served;
* logging in as a student and then as an admin left *both* identities live.
"""

import hashlib

from flask.sessions import TaggedJSONSerializer
from itsdangerous import TimestampSigner, URLSafeTimedSerializer

# The literal that shipped in config.py's history and is therefore public.
PUBLISHED_DEFAULT_KEY = "change-me-in-production"


def mint_session_cookie(secret_key, payload):
    """Forge a Flask session cookie exactly the way Flask signs its own.

    Uses itsdangerous ``URLSafeTimedSerializer`` with salt ``"cookie-session"``,
    Flask's ``TaggedJSONSerializer`` payload, and hmac/sha1 key derivation --
    the default Flask session signing scheme -- so a cookie minted here is
    byte-for-byte one Flask would accept if the key matched.
    """
    serializer = URLSafeTimedSerializer(
        secret_key,
        salt="cookie-session",
        serializer=TaggedJSONSerializer(),
        signer=TimestampSigner,
        signer_kwargs={"key_derivation": "hmac", "digest_method": hashlib.sha1},
    )
    return serializer.dumps(payload)


class TestForgedCookieRejected:
    def test_forged_admin_cookie_with_default_key_is_rejected(self, app, admin_user):
        """The exploit: forge {"admin_id": ...} with the public default key."""
        client = app.test_client()
        forged = mint_session_cookie(PUBLISHED_DEFAULT_KEY, {"admin_id": admin_user.id})
        client.set_cookie("session", forged, domain="localhost")

        resp = client.get("/admin/dashboard")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/admin/login")

    def test_forged_admin_cookie_naming_nonexistent_admin_is_rejected(self, app):
        client = app.test_client()
        forged = mint_session_cookie(PUBLISHED_DEFAULT_KEY, {"admin_id": 99999})
        client.set_cookie("session", forged, domain="localhost")

        resp = client.get("/admin/dashboard")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/admin/login")

    def test_forged_student_cookie_with_default_key_is_rejected(self, app, student_user):
        client = app.test_client()
        forged = mint_session_cookie(
            PUBLISHED_DEFAULT_KEY,
            {"user_id": student_user.id, "student_id": student_user.student_id},
        )
        client.set_cookie("session", forged, domain="localhost")

        resp = client.get("/student/dashboard")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/login")

    def test_cookie_validly_signed_but_naming_a_ghost_admin_is_rejected(self, app):
        """Second layer: even a correctly signed cookie is checked against the DB."""
        client = app.test_client()
        real_key = app.config["SECRET_KEY"]
        valid_but_bogus = mint_session_cookie(real_key, {"admin_id": 99999})
        client.set_cookie("session", valid_but_bogus, domain="localhost")

        resp = client.get("/admin/dashboard")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/admin/login")


class TestRolesAreMutuallyExclusive:
    def test_student_then_admin_leaves_only_admin(self, app, student_user, admin_user):
        client = app.test_client()
        client.post("/login", data={"student_id": "STU001", "password": "password123"})
        client.post("/admin/login", data={"username": "admin", "password": "admin123"})

        with client.session_transaction() as sess:
            assert "admin_id" in sess
            assert "user_id" not in sess
            assert "student_id" not in sess
            assert "user_name" not in sess

        # And the student routes now treat this client as unauthenticated.
        resp = client.get("/student/dashboard")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/login")

    def test_admin_then_student_leaves_only_student(self, app, student_user, admin_user):
        client = app.test_client()
        client.post("/admin/login", data={"username": "admin", "password": "admin123"})
        client.post("/login", data={"student_id": "STU001", "password": "password123"})

        with client.session_transaction() as sess:
            assert "user_id" in sess
            assert "admin_id" not in sess
            assert "admin_username" not in sess

        resp = client.get("/admin/dashboard")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/admin/login")

    def test_one_client_cannot_hold_both_dashboards(self, app, student_user, admin_user):
        """The pre-fix code let a single client load 200/200 on both dashboards."""
        client = app.test_client()
        client.post("/login", data={"student_id": "STU001", "password": "password123"})
        assert client.get("/student/dashboard").status_code == 200
        assert client.get("/admin/dashboard").status_code == 302

        client.post("/admin/login", data={"username": "admin", "password": "admin123"})
        assert client.get("/admin/dashboard").status_code == 200
        assert client.get("/student/dashboard").status_code == 302


class TestSessionFixationAndHardening:
    def test_login_clears_a_preexisting_session(self, app, student_user):
        """A value planted before login must not survive it (fixation guard)."""
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["planted"] = "attacker-value"

        client.post("/login", data={"student_id": "STU001", "password": "password123"})
        with client.session_transaction() as sess:
            assert "planted" not in sess
            assert sess["user_id"] == student_user.id

    def test_admin_login_clears_a_preexisting_session(self, app, admin_user):
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["planted"] = "attacker-value"

        client.post("/admin/login", data={"username": "admin", "password": "admin123"})
        with client.session_transaction() as sess:
            assert "planted" not in sess
            assert sess["admin_id"] == admin_user.id

    def test_student_login_marks_the_session_permanent(self, app, student_user):
        client = app.test_client()
        client.post("/login", data={"student_id": "STU001", "password": "password123"})
        with client.session_transaction() as sess:
            assert sess.permanent is True

    def test_admin_login_marks_the_session_permanent(self, app, admin_user):
        client = app.test_client()
        client.post("/admin/login", data={"username": "admin", "password": "admin123"})
        with client.session_transaction() as sess:
            assert sess.permanent is True
