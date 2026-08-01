"""
URL endpoints and business logic
"""

from datetime import datetime
from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from models import Admin, LaundryRequest, Student, db

# Create blueprints
main = Blueprint("main", __name__)
auth = Blueprint("auth", __name__)
student = Blueprint("student", __name__, url_prefix="/student")
admin = Blueprint("admin", __name__, url_prefix="/admin")


# =====================================================
# DECORATORS
# =====================================================


def login_required(f):
    """Decorator to require login"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """Decorator to require admin login"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "admin_id" not in session:
            flash("Admin access required.", "warning")
            return redirect(url_for("auth.admin_login"))
        return f(*args, **kwargs)

    return decorated_function


# =====================================================
# MAIN ROUTES
# =====================================================


@main.route("/")
def index():
    """Landing page"""
    return render_template("login.html")


# =====================================================
# AUTH ROUTES
# =====================================================


@auth.route("/login", methods=["GET", "POST"])
def login():
    """Student login"""
    if request.method == "POST":
        student_id = request.form.get("student_id")
        password = request.form.get("password")

        student = Student.query.filter_by(student_id=student_id).first()

        if student and student.check_password(password):
            session["user_id"] = student.id
            session["student_id"] = student.student_id
            session["user_name"] = student.name
            flash("Welcome back!", "success")
            return redirect(url_for("student.dashboard"))

        flash("Invalid student ID or password.", "error")

    return render_template("login.html")


@auth.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Admin login"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        admin = Admin.query.filter_by(username=username).first()

        if admin and admin.check_password(password):
            session["admin_id"] = admin.id
            session["admin_username"] = admin.username
            flash("Welcome, Admin!", "success")
            return redirect(url_for("admin.dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("admin_login.html")


@auth.route("/logout")
def logout():
    """Logout user or admin"""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


# =====================================================
# STUDENT ROUTES
# =====================================================


@student.route("/dashboard")
@login_required
def dashboard():
    """Student dashboard - view remaining quota and history"""
    student = Student.query.filter_by(student_id=session["student_id"]).first()
    requests = (
        LaundryRequest.query.filter_by(student_id=session["student_id"])
        .order_by(LaundryRequest.submission_date.desc())
        .all()
    )

    return render_template("dashboard.html", student=student, requests=requests)


@student.route("/submit", methods=["POST"])
@login_required
def submit_request():
    """Submit a new laundry request"""
    num_clothes = int(request.form.get("num_clothes", 0))

    student = Student.query.filter_by(student_id=session["student_id"]).first()

    if num_clothes <= 0:
        flash("Please enter a valid number of clothes.", "error")
        return redirect(url_for("student.dashboard"))

    if num_clothes > student.remaining_quota:
        flash(f"You only have {student.remaining_quota} clothes remaining in your quota.", "error")
        return redirect(url_for("student.dashboard"))

    # Create new laundry request
    new_request = LaundryRequest(student_id=student.student_id, num_clothes=num_clothes)

    # Deduct from quota
    student.remaining_quota -= num_clothes

    db.session.add(new_request)
    db.session.commit()

    flash(f"Request submitted for {num_clothes} clothes!", "success")
    return redirect(url_for("student.dashboard"))


# =====================================================
# ADMIN ROUTES
# =====================================================


@admin.route("/dashboard")
@admin_required
def dashboard():
    """Admin dashboard - view all running jobs"""
    # Get jobs grouped by status
    running_jobs = (
        LaundryRequest.query.filter(LaundryRequest.status.in_(["submitted", "processing"]))
        .order_by(LaundryRequest.submission_date.desc())
        .all()
    )

    completed_jobs = (
        LaundryRequest.query.filter_by(status="completed")
        .order_by(LaundryRequest.completed_date.desc())
        .limit(20)
        .all()
    )

    # Stats
    stats = {
        "submitted": LaundryRequest.query.filter_by(status="submitted").count(),
        "processing": LaundryRequest.query.filter_by(status="processing").count(),
        "completed": LaundryRequest.query.filter_by(status="completed").count(),
        "total_students": Student.query.count(),
    }

    return render_template(
        "admin.html", running_jobs=running_jobs, completed_jobs=completed_jobs, stats=stats
    )


@admin.route("/update-status/<int:request_id>", methods=["POST"])
@admin_required
def update_status(request_id):
    """Update job status"""
    new_status = request.form.get("status")

    laundry_request = LaundryRequest.query.get_or_404(request_id)
    laundry_request.status = new_status

    if new_status == "completed":
        laundry_request.completed_date = datetime.utcnow()

    db.session.commit()

    flash(f"Job #{request_id} status updated to {new_status}.", "success")
    return redirect(url_for("admin.dashboard"))
