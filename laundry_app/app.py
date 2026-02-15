"""
Alpha Laundry - Main Application Entry Point
A modern, modular Flask application for laundry management
"""
from flask import Flask
from config import Config
from models import db, Student, Admin
from routes import main, auth, student, admin


def create_app():
    """Application factory"""
    app = Flask(__name__)

    # Load configuration
    app.config["SQLALCHEMY_DATABASE_URI"] = Config.DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = Config.SECRET_KEY

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
            sample_student = Student(
                student_id="STU001",
                name="John Doe",
                remaining_quota=30
            )
            sample_student.set_password("password123")
            db.session.add(sample_student)

            sample_student2 = Student(
                student_id="STU002",
                name="Jane Smith",
                remaining_quota=25
            )
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
