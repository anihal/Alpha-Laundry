"""Populate the database with demo accounts for manual testing.

Deliberately NOT wired into ``app.py``: seeding is opt-in, so a real deployment
never silently ships accounts with a known password. Run it explicitly:

    python seed_demo.py

Idempotent per row -- rerunning adds only what is missing, and never touches an
existing student's quota or history. (``init_db`` guards its whole seed block
with ``if not Student.query.first()``, so a partially deleted seed set can never
be repaired; this does not repeat that mistake.)
"""

import random
import re
import unicodedata
from datetime import UTC, datetime, timedelta

from app import create_app
from models import LaundryRequest, Student, db

DEMO_PASSWORD = "password123"

# Laundry is the family business. Names are fictional characters, used here
# purely as recognisable demo data.
DEMO_STUDENTS = [
    ("Tony Soprano", 30),
    ("Carmela Soprano", 30),
    ("Christopher Moltisanti", 24),
    ("Paulie Gualtieri", 18),
    ("Silvio Dante", 30),
    ("Junior Soprano", 12),
    ("Bobby Baccalieri", 27),
    ("Adriana La Cerva", 21),
    ("Henry Hill", 15),
    ("Jimmy Conway", 30),
    ("Tommy DeVito", 9),
    ("Karen Hill", 26),
    ("Vito Corleone", 30),
    ("Michael Corleone", 28),
    ("Sonny Corleone", 6),
    ("Tom Hagen", 30),
    ("Sam Rothstein", 22),
    ("Nicky Santoro", 11),
    ("Nucky Thompson", 30),
    ("Thomas Shelby", 19),
]

# A spread of statuses so the admin dashboard has something to manage.
_STATUS_MIX = ["submitted"] * 4 + ["processing"] * 3 + ["completed"] * 6 + ["cancelled"] * 1


def _ascii_letters(text):
    """Strip accents and anything that is not a letter: 'La Cerva' -> 'lacerva'."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"[^a-z]", "", stripped.lower())


def derive_username(full_name, taken=()):
    """Build a readable login handle: 'Tony Soprano' -> 'tonsop'.

    Three letters of the given name plus three of the family name. Names with
    particles collapse ('Adriana La Cerva' -> 'adrlac'), and a single-word name
    just uses its first six letters. A numeric suffix breaks ties, so two people
    who compress to the same handle still get distinct logins.
    """
    parts = [p for p in (_ascii_letters(p) for p in full_name.split()) if p]
    if not parts:
        raise ValueError(f"cannot derive a username from {full_name!r}")

    if len(parts) == 1:
        base = parts[0][:6]
    else:
        base = parts[0][:3] + "".join(parts[1:])[:3]

    candidate, suffix = base, 2
    while candidate in taken:
        candidate = f"{base}{suffix}"
        suffix += 1
    return candidate


def _make_history(rng, student_id, now):
    """Build a plausible request history for one student."""
    requests = []
    for _ in range(rng.randint(0, 4)):
        status = rng.choice(_STATUS_MIX)
        submitted = now - timedelta(days=rng.randint(0, 45), hours=rng.randint(0, 23))
        completed = None
        if status == "completed":
            completed = submitted + timedelta(hours=rng.randint(6, 72))
        requests.append(
            LaundryRequest(
                student_id=student_id,
                num_clothes=rng.randint(1, 9),
                status=status,
                submission_date=submitted,
                completed_date=completed,
            )
        )
    return requests


def seed(app):
    rng = random.Random(1926)  # deterministic, so reruns look the same
    # Naive UTC, matching the columns in models.py. Taken via the non-deprecated
    # path rather than datetime.utcnow().
    now = datetime.now(UTC).replace(tzinfo=None)

    with app.app_context():
        db.create_all()

        taken = {s.student_id for s in Student.query.all()}
        added, skipped, requests_added = 0, 0, 0

        for name, quota in DEMO_STUDENTS:
            username = derive_username(name, taken)
            if Student.query.filter_by(name=name).first():
                skipped += 1
                continue

            taken.add(username)
            student = Student(student_id=username, name=name, remaining_quota=quota)
            student.set_password(DEMO_PASSWORD)
            db.session.add(student)

            history = _make_history(rng, username, now)
            db.session.add_all(history)
            requests_added += len(history)
            added += 1

        db.session.commit()

    print(f"Added {added} demo students ({skipped} already present).")
    print(f"Added {requests_added} laundry requests.")
    print(f"All demo accounts use the password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    seed(create_app())
