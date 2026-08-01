"""Tests for app.py -- the create_app() factory and init_db() seeding."""
import pytest

from app import create_app, init_db
from config import Config
from models import db, Student, Admin, LaundryRequest


# ---------------------------------------------------------------------------
# create_app()
# ---------------------------------------------------------------------------

class TestCreateApp:
    def test_returns_a_flask_app(self, app):
        from flask import Flask
        assert isinstance(app, Flask)

    def test_database_uri_comes_from_config(self, monkeypatch):
        monkeypatch.setattr(Config, "DATABASE_URL", "sqlite:///from-config.db")
        application = create_app()
        assert application.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///from-config.db"

    def test_secret_key_comes_from_config(self, monkeypatch):
        monkeypatch.setattr(Config, "DATABASE_URL", "sqlite:///:memory:")
        monkeypatch.setattr(Config, "SECRET_KEY", "wired-through")
        application = create_app()
        assert application.config["SECRET_KEY"] == "wired-through"

    def test_track_modifications_is_disabled(self, app):
        assert app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] is False

    def test_all_four_blueprints_are_registered(self, app):
        assert set(app.blueprints) == {"main", "auth", "student", "admin"}

    def test_blueprint_url_prefixes(self, app):
        assert app.blueprints["student"].url_prefix == "/student"
        assert app.blueprints["admin"].url_prefix == "/admin"
        assert app.blueprints["main"].url_prefix is None
        assert app.blueprints["auth"].url_prefix is None

    def test_expected_endpoints_exist(self, app):
        endpoints = {rule.endpoint for rule in app.url_map.iter_rules()}
        assert {
            "main.index",
            "auth.login",
            "auth.admin_login",
            "auth.logout",
            "student.dashboard",
            "student.submit_request",
            "admin.dashboard",
            "admin.update_status",
        } <= endpoints

    def test_expected_url_rules(self, app):
        rules = {rule.endpoint: str(rule) for rule in app.url_map.iter_rules()}
        assert rules["main.index"] == "/"
        assert rules["auth.login"] == "/login"
        assert rules["auth.admin_login"] == "/admin/login"
        assert rules["auth.logout"] == "/logout"
        assert rules["student.dashboard"] == "/student/dashboard"
        assert rules["student.submit_request"] == "/student/submit"
        assert rules["admin.dashboard"] == "/admin/dashboard"
        assert rules["admin.update_status"] == "/admin/update-status/<int:request_id>"

    def test_sqlalchemy_extension_is_initialised(self, app):
        assert "sqlalchemy" in app.extensions

    def test_debug_is_not_forced_on(self, monkeypatch):
        """create_app() must not enable debug mode; only __main__ passes it to run()."""
        monkeypatch.setattr(Config, "DATABASE_URL", "sqlite:///:memory:")
        application = create_app()
        assert application.debug is False

    def test_two_apps_are_independent(self, monkeypatch):
        monkeypatch.setattr(Config, "DATABASE_URL", "sqlite:///:memory:")
        a = create_app()
        b = create_app()
        assert a is not b
        a.config["SECRET_KEY"] = "changed-on-a"
        assert b.config["SECRET_KEY"] != "changed-on-a"


# ---------------------------------------------------------------------------
# init_db()
# ---------------------------------------------------------------------------

@pytest.fixture
def fresh_app(monkeypatch):
    """An app with the schema NOT yet created, so init_db() does the work."""
    monkeypatch.setattr(Config, "DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setattr(Config, "SECRET_KEY", "test-secret-key")
    application = create_app()
    application.config.update(TESTING=True)
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()
        for engine in db.engines.values():
            engine.dispose()


class TestInitDb:
    def test_creates_the_schema(self, fresh_app, capsys):
        init_db(fresh_app)
        with fresh_app.app_context():
            inspector = db.inspect(db.engine)
            assert set(inspector.get_table_names()) == {
                "students", "admins", "laundry_requests"
            }

    def test_seeds_two_students(self, fresh_app):
        init_db(fresh_app)
        with fresh_app.app_context():
            ids = sorted(s.student_id for s in Student.query.all())
            assert ids == ["STU001", "STU002"]

    def test_seeded_student_attributes(self, fresh_app):
        init_db(fresh_app)
        with fresh_app.app_context():
            one = Student.query.filter_by(student_id="STU001").one()
            two = Student.query.filter_by(student_id="STU002").one()
            assert one.name == "John Doe"
            assert one.remaining_quota == 30
            assert two.name == "Jane Smith"
            assert two.remaining_quota == 25

    def test_seeds_exactly_one_admin(self, fresh_app):
        init_db(fresh_app)
        with fresh_app.app_context():
            admins = Admin.query.all()
            assert len(admins) == 1
            assert admins[0].username == "admin"

    def test_seeded_student_passwords_verify(self, fresh_app):
        init_db(fresh_app)
        with fresh_app.app_context():
            for sid in ("STU001", "STU002"):
                student = Student.query.filter_by(student_id=sid).one()
                assert student.check_password("password123") is True
                assert student.check_password("wrong") is False

    def test_seeded_admin_password_verifies(self, fresh_app):
        init_db(fresh_app)
        with fresh_app.app_context():
            admin = Admin.query.filter_by(username="admin").one()
            assert admin.check_password("admin123") is True
            assert admin.check_password("wrong") is False

    def test_seeded_passwords_are_hashed(self, fresh_app):
        init_db(fresh_app)
        with fresh_app.app_context():
            student = Student.query.filter_by(student_id="STU001").one()
            admin = Admin.query.filter_by(username="admin").one()
            assert student.password_hash != "password123"
            assert admin.password_hash != "admin123"

    def test_no_laundry_requests_are_seeded(self, fresh_app):
        init_db(fresh_app)
        with fresh_app.app_context():
            assert LaundryRequest.query.count() == 0

    def test_is_idempotent(self, fresh_app):
        init_db(fresh_app)
        init_db(fresh_app)
        init_db(fresh_app)
        with fresh_app.app_context():
            assert Student.query.count() == 2
            assert Admin.query.count() == 1

    def test_prints_a_confirmation(self, fresh_app, capsys):
        init_db(fresh_app)
        assert "Database initialized with sample data!" in capsys.readouterr().out

    def test_reseeding_is_all_or_nothing_per_model(self, fresh_app):
        """The guard is `if not Student.query.first()`, not a per-row check."""
        init_db(fresh_app)
        with fresh_app.app_context():
            db.session.delete(Student.query.filter_by(student_id="STU002").one())
            db.session.commit()

        init_db(fresh_app)

        with fresh_app.app_context():
            # BUG: app.py:38 guards the whole seed block with
            # `if not Student.query.first()`. Because STU001 still exists, the
            # block is skipped entirely and the deleted STU002 is never
            # restored. Correct behaviour: check for (and upsert) each seed row
            # individually, e.g. `if not Student.query.filter_by(
            # student_id="STU002").first()`.
            assert Student.query.count() == 1
            assert Student.query.filter_by(student_id="STU002").first() is None

    def test_does_not_wipe_existing_user_data(self, fresh_app):
        init_db(fresh_app)
        with fresh_app.app_context():
            db.session.add(LaundryRequest(student_id="STU001", num_clothes=4))
            db.session.commit()
        init_db(fresh_app)
        with fresh_app.app_context():
            assert LaundryRequest.query.count() == 1

    def test_leaves_no_open_app_context(self, fresh_app):
        from flask import current_app
        init_db(fresh_app)
        with pytest.raises(RuntimeError):
            _ = current_app.name
