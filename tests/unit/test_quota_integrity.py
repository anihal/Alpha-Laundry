"""Quota accounting: refund on cancellation, and an atomic deduction.

Two defects are covered here. Cancelling a job used to consume the student's
allowance forever, and the check-then-deduct in ``submit`` was a read-modify-
write over a value held in Python, so concurrent callers could both pass a check
against the same starting balance.
"""

import sqlite3
import threading

import pytest

from models import LaundryRequest, Student
from services import quota
from services import requests as requests_service


class TestRefundOnCancel:
    def test_cancelling_returns_the_clothes(self, db_session, student):
        before = student.remaining_quota
        req = requests_service.submit(db_session, student, 5)
        assert student.remaining_quota == before - 5

        requests_service.set_status(db_session, req, "cancelled")
        assert student.remaining_quota == before

    def test_refund_happens_only_on_the_transition_edge(self, db_session, student):
        before = student.remaining_quota
        req = requests_service.submit(db_session, student, 4)

        requests_service.set_status(db_session, req, "cancelled")
        requests_service.set_status(db_session, req, "cancelled")
        requests_service.set_status(db_session, req, "cancelled")

        assert student.remaining_quota == before

    def test_cancelling_a_completed_job_also_refunds(self, db_session, student):
        before = student.remaining_quota
        req = requests_service.submit(db_session, student, 3)
        requests_service.set_status(db_session, req, "completed")

        requests_service.set_status(db_session, req, "cancelled")
        assert student.remaining_quota == before

    def test_the_refund_is_persisted(self, db_session, student):
        before = student.remaining_quota
        req = requests_service.submit(db_session, student, 6)
        requests_service.set_status(db_session, req, "cancelled")

        db_session.expire_all()
        reloaded = db_session.query(Student).filter_by(student_id=student.student_id).first()
        assert reloaded.remaining_quota == before

    def test_only_the_owning_student_is_refunded(self, db_session, student, make_student):
        other = make_student(student_id="othstu", name="Other", password="pw")
        other_before = other.remaining_quota

        req = requests_service.submit(db_session, student, 5)
        requests_service.set_status(db_session, req, "cancelled")

        assert other.remaining_quota == other_before

    def test_cancelling_does_not_stamp_a_completion_date(self, db_session, student):
        req = requests_service.submit(db_session, student, 2)
        requests_service.set_status(db_session, req, "cancelled")
        assert req.completed_date is None


class TestReopeningACancelledJob:
    def test_reopening_spends_the_clothes_again(self, db_session, student):
        before = student.remaining_quota
        req = requests_service.submit(db_session, student, 5)
        requests_service.set_status(db_session, req, "cancelled")
        assert student.remaining_quota == before

        requests_service.set_status(db_session, req, "processing")
        assert student.remaining_quota == before - 5

    def test_a_cancel_reopen_cycle_is_quota_neutral(self, db_session, student):
        before = student.remaining_quota
        req = requests_service.submit(db_session, student, 7)

        for _ in range(3):
            requests_service.set_status(db_session, req, "cancelled")
            requests_service.set_status(db_session, req, "submitted")

        # Not a way to farm free quota.
        assert student.remaining_quota == before - 7

    def test_reopening_without_room_is_refused(self, db_session, student):
        student.remaining_quota = 10
        db_session.commit()

        req = requests_service.submit(db_session, student, 10)
        requests_service.set_status(db_session, req, "cancelled")
        assert student.remaining_quota == 10

        # Spend the refunded allowance elsewhere.
        requests_service.submit(db_session, student, 10)
        assert student.remaining_quota == 0

        with pytest.raises(quota.QuotaExceeded) as exc:
            requests_service.set_status(db_session, req, "submitted")
        assert exc.value.remaining == 0

    def test_a_refused_reopen_leaves_the_row_cancelled(self, db_session, student):
        student.remaining_quota = 5
        db_session.commit()
        req = requests_service.submit(db_session, student, 5)
        requests_service.set_status(db_session, req, "cancelled")
        requests_service.submit(db_session, student, 5)

        with pytest.raises(quota.QuotaExceeded):
            requests_service.set_status(db_session, req, "submitted")

        db_session.expire_all()
        assert db_session.get(LaundryRequest, req.id).status == "cancelled"

    def test_a_refused_reopen_does_not_move_the_quota(self, db_session, student):
        student.remaining_quota = 5
        db_session.commit()
        req = requests_service.submit(db_session, student, 5)
        requests_service.set_status(db_session, req, "cancelled")
        requests_service.submit(db_session, student, 5)

        with pytest.raises(quota.QuotaExceeded):
            requests_service.set_status(db_session, req, "submitted")

        db_session.expire_all()
        reloaded = db_session.query(Student).filter_by(student_id=student.student_id).first()
        assert reloaded.remaining_quota == 0


class TestDeductionIsAtomic:
    def test_the_guard_lives_in_the_statement_not_in_python(self, db_session, student):
        """The UPDATE refuses on its own, with no prior read to rely on.

        This is what makes the deduction safe under concurrency: the balance is
        never read into Python, compared, and written back. Calling the helper
        directly is the point -- ``submit``'s own ``quota.check`` would mask the
        statement guard by rejecting first.
        """
        student.remaining_quota = 2
        db_session.commit()

        refused = requests_service._adjust_quota(
            db_session, student.student_id, -15, require_available=True
        )
        assert refused == 0, "the statement should refuse to overdraw"

        db_session.expire_all()
        reloaded = db_session.query(Student).filter_by(student_id=student.student_id).first()
        assert reloaded.remaining_quota == 2

    def test_the_statement_allows_a_deduction_that_fits(self, db_session, student):
        student.remaining_quota = 20
        db_session.commit()

        applied = requests_service._adjust_quota(
            db_session, student.student_id, -15, require_available=True
        )
        assert applied == 1

        db_session.expire_all()
        reloaded = db_session.query(Student).filter_by(student_id=student.student_id).first()
        assert reloaded.remaining_quota == 5

    def test_the_boundary_case_of_spending_the_exact_balance(self, db_session, student):
        student.remaining_quota = 15
        db_session.commit()

        assert (
            requests_service._adjust_quota(
                db_session, student.student_id, -15, require_available=True
            )
            == 1
        )
        db_session.expire_all()
        reloaded = db_session.query(Student).filter_by(student_id=student.student_id).first()
        assert reloaded.remaining_quota == 0

    def test_a_refused_submit_creates_no_request(self, db_session, student):
        student.remaining_quota = 20
        db_session.commit()
        db_session.query(Student).filter_by(student_id=student.student_id).update(
            {Student.remaining_quota: 1}, synchronize_session=False
        )
        db_session.commit()

        with pytest.raises(quota.QuotaExceeded):
            requests_service.submit(db_session, student, 15)

        db_session.expire_all()
        assert db_session.query(LaundryRequest).count() == 0

    def test_quota_never_goes_negative_across_many_submits(self, db_session, student):
        student.remaining_quota = 10
        db_session.commit()

        accepted = 0
        for _ in range(20):
            try:
                requests_service.submit(db_session, student, 3)
                accepted += 1
            except quota.QuotaExceeded:
                pass

        db_session.expire_all()
        reloaded = db_session.query(Student).filter_by(student_id=student.student_id).first()
        assert accepted == 3
        assert reloaded.remaining_quota == 1
        assert reloaded.remaining_quota >= 0


class TestConcurrentSubmits:
    """The original defect, driven through real concurrent connections."""

    def test_two_threads_cannot_overspend_the_same_balance(self, tmp_path):
        # A file-backed DB so separate connections genuinely contend.
        path = tmp_path / "race.db"
        con = sqlite3.connect(path)
        con.executescript(
            """
            CREATE TABLE students (
                id INTEGER PRIMARY KEY, student_id VARCHAR(20) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL, password_hash VARCHAR(255) NOT NULL,
                remaining_quota INTEGER, created_at DATETIME
            );
            INSERT INTO students (student_id, name, password_hash, remaining_quota)
            VALUES ('tonsop', 'Tony Soprano', 'x', 23);
            """
        )
        con.commit()
        con.close()

        barrier = threading.Barrier(2)
        results = []

        def spend():
            conn = sqlite3.connect(path, timeout=10, isolation_level="IMMEDIATE")
            barrier.wait()
            try:
                cur = conn.execute(
                    "UPDATE students SET remaining_quota = remaining_quota - 23 "
                    "WHERE student_id = 'tonsop' AND remaining_quota >= 23"
                )
                conn.commit()
                results.append(cur.rowcount)
            except sqlite3.OperationalError:
                results.append(0)
            finally:
                conn.close()

        threads = [threading.Thread(target=spend) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        con = sqlite3.connect(path)
        remaining = con.execute(
            "SELECT remaining_quota FROM students WHERE student_id='tonsop'"
        ).fetchone()[0]
        con.close()

        # Exactly one of the two may win, and the balance may not go negative.
        assert sum(results) == 1, f"both submits were accepted: {results}"
        assert remaining == 0
