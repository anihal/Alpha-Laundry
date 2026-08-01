"""Tests for the application factory and the database seeder.

These live in the integration suite rather than tests/unit/ because they build
a real Flask application -- the unit suite's autouse ``no_application_context``
fixture forbids that by design. They do no HTTP, so they stay fast.
"""

import pytest
from flask import Flask

from app import create_app, init_db
from config import Config
from models import Admin, LaundryRequest, Student
from models import db as _db

pytestmark = pytest.mark.integration


class TestCreateApp:
    def test_returns_a_flask_app(self, app):
        assert isinstance(app, Flask)

    def test_database_uri_comes_from_config(self, app):
        assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"

    def test_secret_key_comes_from_config(self, app):
        assert app.config["SECRET_KEY"] == Config.SECRET_KEY

    def test_track_modifications_is_disabled(self, app):
        # Left on, SQLAlchemy emits change-tracking signals the app never uses
        # and pays memory for it.
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

    def test_two_apps_are_independent(self, app):
        second = create_app()
        assert second is not app


class TestInitDb:
    def test_creates_the_schema_and_seeds(self, bare_app):
        with bare_app.app_context():
            init_db(bare_app)
            assert Student.query.count() == 2
            assert Admin.query.count() == 1
            # Seeding must not invent laundry history.
            assert LaundryRequest.query.count() == 0

    def test_seeded_credentials_verify(self, bare_app):
        with bare_app.app_context():
            init_db(bare_app)
            for student_id in ("STU001", "STU002"):
                student = Student.query.filter_by(student_id=student_id).first()
                assert student.check_password("password123")
            assert Admin.query.filter_by(username="admin").first().check_password("admin123")

    def test_seeded_passwords_are_hashed_not_stored_plaintext(self, bare_app):
        with bare_app.app_context():
            init_db(bare_app)
            for student in Student.query.all():
                assert student.password_hash != "password123"
                assert "password123" not in student.password_hash

    def test_is_idempotent(self, bare_app):
        with bare_app.app_context():
            init_db(bare_app)
            init_db(bare_app)
            assert Student.query.count() == 2
            assert Admin.query.count() == 1

    def test_does_not_wipe_existing_user_data(self, bare_app):
        with bare_app.app_context():
            init_db(bare_app)
            student = Student.query.filter_by(student_id="STU001").first()
            student.remaining_quota = 3
            _db.session.commit()

            init_db(bare_app)
            assert Student.query.filter_by(student_id="STU001").first().remaining_quota == 3

    def test_a_deleted_seed_student_is_not_restored(self, bare_app):
        # BUG: app.py guards the whole seed block with
        # `if not Student.query.first()`. Because STU001 still exists the block
        # is skipped wholesale, so a deleted STU002 is never restored. Worse,
        # deleting STU001 instead would make the next run attempt to insert
        # both and fail with a UNIQUE constraint error on STU002. Correct
        # behaviour: check for and upsert each seed row individually.
        with bare_app.app_context():
            init_db(bare_app)
            _db.session.delete(Student.query.filter_by(student_id="STU002").first())
            _db.session.commit()

            init_db(bare_app)

            remaining = [s.student_id for s in Student.query.all()]
            assert remaining == ["STU001"]
            assert Student.query.filter_by(student_id="STU002").first() is None
