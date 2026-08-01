"""
URL endpoints

Handlers here are deliberately thin: read the form, call into ``services``,
then translate the result (or the domain error) into a flash message and a
redirect. The rules themselves live in ``laundry_app/services/``.
"""

from functools import wraps

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from sqlalchemy import func

from models import Admin, LaundryRequest, Student, db
from services import quota as quota_service
from services import requests as requests_service

# Create blueprints
main = Blueprint("main", __name__)
auth = Blueprint("auth", __name__)
student = Blueprint("student", __name__, url_prefix="/student")
admin = Blueprint("admin", __name__, url_prefix="/admin")


# =====================================================
# DECORATORS
# =====================================================


def login_required(f):
    """Require a session that resolves to a real Student.

    The session id is authorization-critical, so it is never trusted on its own:
    the Student row is loaded from the database. A session with no student
    identity redirects to the login; one that names a student who no longer
    exists is cleared first (fail closed) so a stale cookie cannot linger. The
    resolved Student is stashed on ``flask.g`` for the view to use, which keeps
    the gate and the view from ever disagreeing about who is logged in.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        if user_id is None:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login"))

        current_student = db.session.get(Student, user_id)
        if current_student is None:
            session.clear()
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login"))

        g.student = current_student
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """Require a session that resolves to a real Admin.

    Same contract as :func:`login_required`: the ``admin_id`` in the session is
    resolved against the database, a missing row clears the session, and the
    loaded Admin is stashed on ``flask.g``.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin_id = session.get("admin_id")
        if admin_id is None:
            flash("Admin access required.", "warning")
            return redirect(url_for("auth.admin_login"))

        current_admin = db.session.get(Admin, admin_id)
        if current_admin is None:
            session.clear()
            flash("Admin access required.", "warning")
            return redirect(url_for("auth.admin_login"))

        g.admin = current_admin
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
            # Start from a clean session: this prevents session fixation and
            # makes the student/admin roles mutually exclusive (a browser can
            # never hold both identities at once).
            session.clear()
            session.permanent = True
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
            # Clean session first: prevents fixation and guarantees the admin
            # and student roles stay mutually exclusive.
            session.clear()
            session.permanent = True
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
    student = g.student
    requests = (
        LaundryRequest.query.filter_by(student_id=student.student_id)
        .order_by(LaundryRequest.submission_date.desc())
        .all()
    )

    return render_template("dashboard.html", student=student, requests=requests)


@student.route("/submit", methods=["POST"])
@login_required
def submit_request():
    """Submit a new laundry request"""
    student = g.student

    try:
        # Parsing lives inside the try because a value the browser will happily
        # post -- "" for a blank number field -- is an InvalidQuantity, and it
        # deserves the same flash as a zero or a negative rather than an
        # unhandled exception. The ``min``/``max`` attributes on the input in
        # dashboard.html are a convenience, not a control; every check that
        # matters happens here.
        num_clothes = quota_service.parse_quantity(request.form.get("num_clothes", 0))
        requests_service.submit(db.session, student, num_clothes)
    except quota_service.InvalidQuantity:
        flash("Please enter a valid number of clothes.", "error")
        return redirect(url_for("student.dashboard"))
    except quota_service.QuotaExceeded as exc:
        flash(f"You only have {exc.remaining} clothes remaining in your quota.", "error")
        return redirect(url_for("student.dashboard"))

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


@admin.route("/students")
@admin_required
def students():
    """Directory of enrolled students, with their laundry activity."""
    # One grouped query for the per-student counts instead of two queries per
    # row. `outerjoin` keeps students who have never submitted anything.
    rows = (
        db.session.query(
            Student,
            func.count(LaundryRequest.id).label("total_requests"),
            func.coalesce(func.sum(LaundryRequest.num_clothes), 0).label("total_clothes"),
        )
        .outerjoin(LaundryRequest, LaundryRequest.student_id == Student.student_id)
        .group_by(Student.id)
        .order_by(Student.name)
        .all()
    )

    students_list = [
        {
            "student": student,
            "total_requests": total_requests,
            "total_clothes": total_clothes,
        }
        for student, total_requests, total_clothes in rows
    ]

    return render_template("students.html", students=students_list)


@admin.route("/update-status/<int:request_id>", methods=["POST"])
@admin_required
def update_status(request_id):
    """Update job status"""
    new_status = request.form.get("status")

    laundry_request = LaundryRequest.query.get_or_404(request_id)

    try:
        requests_service.set_status(db.session, laundry_request, new_status)
    except requests_service.InvalidStatus:
        # Deliberately does not echo the rejected value back into the page.
        flash("Invalid status. Choose submitted, processing, completed or cancelled.", "error")
        return redirect(url_for("admin.dashboard"))

    flash(f"Job #{request_id} status updated to {new_status}.", "success")
    return redirect(url_for("admin.dashboard"))
