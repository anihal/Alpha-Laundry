"""Startup-time security configuration: the SECRET_KEY gate and cookie flags.

Ported from the pre-split tests/test_app.py so the fail-closed behaviour keeps
its coverage after the unit/integration reorganisation. These build a real Flask
app, so they belong here rather than in tests/unit/.
"""

import pytest

from app import SESSION_LIFETIME, create_app, resolve_secret_key
from config import Config

pytestmark = pytest.mark.integration


class TestResolveSecretKey:
    def test_a_real_key_is_returned_unchanged(self):
        assert resolve_secret_key("a-genuinely-random-key", debug=False) == (
            "a-genuinely-random-key"
        )

    def test_surrounding_whitespace_is_stripped(self):
        assert resolve_secret_key("  padded-key  ", debug=False) == "padded-key"

    @pytest.mark.parametrize(
        "insecure",
        [None, "", "   ", "change-me-in-production", "your-secret-key"],
    )
    def test_missing_or_placeholder_key_raises_outside_debug(self, insecure):
        """A production start without a real key must fail loudly."""
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            resolve_secret_key(insecure, debug=False)

    @pytest.mark.parametrize("insecure", [None, "", "change-me-in-production"])
    def test_debug_mints_an_ephemeral_key_instead_of_raising(self, insecure):
        key = resolve_secret_key(insecure, debug=True)
        assert key
        assert key not in ("change-me-in-production", "")
        # 32 random bytes, hex-encoded.
        assert len(key) == 64

    def test_ephemeral_keys_are_random_per_call(self):
        assert resolve_secret_key(None, debug=True) != resolve_secret_key(None, debug=True)


class TestCreateAppFailsClosed:
    def test_missing_key_makes_create_app_fail_closed(self, monkeypatch):
        monkeypatch.setattr(Config, "DATABASE_URL", "sqlite:///:memory:")
        monkeypatch.setattr(Config, "SECRET_KEY", None)
        monkeypatch.setattr(Config, "DEBUG", False)
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            create_app()

    def test_insecure_default_makes_create_app_fail_closed(self, monkeypatch):
        monkeypatch.setattr(Config, "DATABASE_URL", "sqlite:///:memory:")
        monkeypatch.setattr(Config, "SECRET_KEY", "change-me-in-production")
        monkeypatch.setattr(Config, "DEBUG", False)
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            create_app()

    def test_debug_lets_create_app_start_without_a_key(self, monkeypatch):
        monkeypatch.setattr(Config, "DATABASE_URL", "sqlite:///:memory:")
        monkeypatch.setattr(Config, "SECRET_KEY", None)
        monkeypatch.setattr(Config, "DEBUG", True)
        assert create_app().config["SECRET_KEY"]


class TestSessionCookieHardening:
    def test_cookie_is_httponly_and_lax(self, app):
        assert app.config["SESSION_COOKIE_HTTPONLY"] is True
        assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"

    def test_lifetime_is_finite(self, app):
        assert app.config["PERMANENT_SESSION_LIFETIME"] == SESSION_LIFETIME

    def test_secure_is_on_in_production(self, monkeypatch):
        monkeypatch.setattr(Config, "DATABASE_URL", "sqlite:///:memory:")
        monkeypatch.setattr(Config, "SECRET_KEY", "a-real-secret-key")
        monkeypatch.setattr(Config, "DEBUG", False)
        assert create_app().config["SESSION_COOKIE_SECURE"] is True

    def test_secure_is_off_in_debug(self, monkeypatch):
        """Local HTTP dev cannot use Secure cookies or login breaks."""
        monkeypatch.setattr(Config, "DATABASE_URL", "sqlite:///:memory:")
        monkeypatch.setattr(Config, "SECRET_KEY", "a-real-secret-key")
        monkeypatch.setattr(Config, "DEBUG", True)
        assert create_app().config["SESSION_COOKIE_SECURE"] is False


class TestStaleStudentSessionIsRejected:
    def test_session_naming_a_deleted_student_is_cleared(self, app, make_student, db_session):
        """login_required must resolve the id against the DB, not trust it."""
        student = make_student(student_id="STU777", password="pw")
        student_pk = student.id
        db_session.delete(student)
        db_session.commit()

        client = app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = student_pk
            sess["student_id"] = "STU777"

        response = client.get("/student/dashboard")
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")

        with client.session_transaction() as sess:
            assert "user_id" not in sess
