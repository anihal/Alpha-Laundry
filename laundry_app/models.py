"""
Database models using SQLAlchemy
"""

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class Student(db.Model):
    """Student model - users who submit laundry requests"""

    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    remaining_quota = db.Column(db.Integer, default=30)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    laundry_requests = db.relationship("LaundryRequest", backref="student", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<Student {self.student_id}>"


class LaundryRequest(db.Model):
    """Laundry request model - tracks laundry jobs"""

    __tablename__ = "laundry_requests"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), db.ForeignKey("students.student_id"), nullable=False)
    num_clothes = db.Column(db.Integer, nullable=False)
    status = db.Column(
        db.String(20), default="submitted"
    )  # submitted, processing, completed, cancelled
    submission_date = db.Column(db.DateTime, default=datetime.utcnow)
    completed_date = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<LaundryRequest {self.id} - {self.status}>"


class Admin(db.Model):
    """Admin model - users who manage laundry operations"""

    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<Admin {self.username}>"
