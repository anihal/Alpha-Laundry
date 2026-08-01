"""
Alpha Laundry - Main Application Entry Point
A modern, modular Flask application for laundry management
"""

import secrets
from datetime import timedelta

from flask import Flask

from config import INSECURE_SECRET_KEYS, Config
from models import Admin, Student, db
from routes import admin, auth, main, student

# How long a signed-in session stays valid before the cookie expires.
SESSION_LIFETIME = timedelta(hours=12)


def resolve_secret_key(secret_key, debug):
    """Return a usable session-signing key or fail closed.

    Flask signs session cookies with this key, so a guessable value makes every
    session forgeable. Rules:

    * A real value from the environment is used as-is.
    * When it is missing, blank, or a known placeholder we refuse to run with a
      guessable key. In DEBUG we mint a random *ephemeral* key so local dev and
      the test suite still work (sessions simply do not survive a restart).
    * Otherwise -- a production start with no SECRET_KEY -- we raise, so the
      deployment fails loudly instead of silently accepting forged cookies.
    """
    key = (secret_key or "").strip()
    if key and key not in INSECURE_SECRET_KEYS:
        return key
    if debug:
        return secrets.token_hex(32)
    raise RuntimeError(
        "SECRET_KEY is unset or left at an insecure placeholder. Flask signs "
        "session cookies with it, so refusing to start: set a strong SECRET_KEY "
        "in the environment. Generate one with "
        '`python -c "import secrets; print(secrets.token_hex(32))"`. '
        "For local development set DEBUG=true to allow an ephemeral key."
    )


def create_app():
    """Application factory"""
    app = Flask(__name__)

    # Load configuration
    app.config["SQLALCHEMY_DATABASE_URI"] = Config.DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = resolve_secret_key(Config.SECRET_KEY, Config.DEBUG)

    # Harden the session cookie.
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    # Secure cookies are only sent over HTTPS. That is required in production but
    # would drop the cookie on local plain-HTTP dev (breaking login), so it is
    # tied to DEBUG: on in production, off for local development.
    app.config["SESSION_COOKIE_SECURE"] = not Config.DEBUG
    app.config["PERMANENT_SESSION_LIFETIME"] = SESSION_LIFETIME

    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(student)
    app.register_blueprint(admin)

    return app


def init_db(app):
    """Initialize the database with sample data"""
    with app.app_context():
        db.create_all()

        # Create sample student if none exists
        if not Student.query.first():
            sample_student = Student(student_id="STU001", name="John Doe", remaining_quota=30)
            sample_student.set_password("password123")
            db.session.add(sample_student)

            sample_student2 = Student(student_id="STU002", name="Jane Smith", remaining_quota=25)
            sample_student2.set_password("password123")
            db.session.add(sample_student2)

        # Create admin if none exists
        if not Admin.query.first():
            admin = Admin(username="admin")
            admin.set_password("admin123")
            db.session.add(admin)

        db.session.commit()
        print("Database initialized with sample data!")


if __name__ == "__main__":
    app = create_app()
    init_db(app)
    app.run(debug=Config.DEBUG, host="0.0.0.0", port=5001)
