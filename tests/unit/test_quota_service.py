"""Tests for services/quota.py -- quantity parsing, validation and deduction.

These used to be route tests: every case here was previously expressed as a
``POST /student/submit`` through Flask's test client. Calling the service
directly removes the app, the session cookie, the template render and the
redirect from cases that were never about any of those things.
"""

import pytest

from services import quota
from services.quota import InvalidQuantity, QuotaExceeded, ServiceError

# ---------------------------------------------------------------------------
# parse_quantity
# ---------------------------------------------------------------------------


class TestParseQuantity:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("1", 1),
            ("5", 5),
            ("30", 30),
            ("0", 0),
            ("-5", -5),
            ("1000000", 1000000),
            (0, 0),
            (7, 7),
        ],
    )
    def test_parses_integer_literals(self, raw, expected):
        assert quota.parse_quantity(raw) == expected

    def test_returns_a_real_int(self):
        assert isinstance(quota.parse_quantity("5"), int)

    @pytest.mark.parametrize("raw", [" +5 ", "5 ", " 5", "\t5\n", "+5"])
    def test_a_sign_and_surrounding_whitespace_are_accepted(self, raw):
        """Trimming is deliberate: it is what the old ``int()`` did too."""
        assert quota.parse_quantity(raw) == 5

    @pytest.mark.parametrize("raw,expected", [("007", 7), ("-0", 0), ("00", 0)])
    def test_ascii_digits_with_leading_zeros_still_parse(self, raw, expected):
        assert quota.parse_quantity(raw) == expected

    def test_the_routes_missing_field_default_parses_to_zero(self):
        """The route passes ``request.form.get("num_clothes", 0)``.

        An absent field therefore arrives as the int 0, not as a string, and
        parses to 0 -- which the validation below then rejects.
        """
        assert quota.parse_quantity(0) == 0

    @pytest.mark.parametrize(
        "raw",
        [
            "abc",
            "",  # what a browser posts for a blank number input
            "1.5",
            "5e3",
            "0x10",
            "  ",
            "5,000",
            "12abc",
            "\t",
            "1_0",  # int("1_0") is 10; the underscore separator is not form input
            "1 2",
            "+-5",
            "--5",
            "5%",
            "٣٤",
        ],
    )
    def test_non_integer_input_is_rejected_as_a_domain_error(self, raw):
        """Unparseable input is a domain error, not an escaping builtin.

        A bare ``int()`` raised ``ValueError`` here, which nothing caught: every
        one of these values was an unhandled exception, i.e. HTTP 500. They now
        raise InvalidQuantity so the route can flash "Please enter a valid
        number of clothes." exactly as it does for the ``<= 0`` case.
        """
        with pytest.raises(InvalidQuantity):
            quota.parse_quantity(raw)

    @pytest.mark.parametrize("raw", ["abc", "", "1.5", "  "])
    def test_a_parse_failure_is_not_a_builtin_error(self, raw):
        """Explicitly: callers never have to catch ValueError or TypeError."""
        with pytest.raises(ServiceError):
            quota.parse_quantity(raw)

    def test_the_parse_error_carries_the_offending_value(self):
        with pytest.raises(InvalidQuantity) as excinfo:
            quota.parse_quantity("abc")
        assert excinfo.value.num_clothes == "abc"

    def test_none_is_rejected_as_a_domain_error(self):
        """A None used to surface as TypeError, indistinguishable from a crash."""
        with pytest.raises(InvalidQuantity):
            quota.parse_quantity(None)

    # Arabic-Indic, Bengali, Thai, and (escaped, so the linter's
    # ambiguous-character rule does not fire on the very thing under test)
    # FULLWIDTH DIGIT THREE. int() accepts every one of them.
    @pytest.mark.parametrize("raw", ["٣", "١٢", "৩", "๓", "\uff13"])
    def test_non_ascii_digits_are_rejected(self, raw):
        """The ASCII-digit policy is chosen, not inherited from ``int()``.

        ``int("٣")`` (Arabic-Indic three) is 3, so the value used to create a
        real 3-item request. The form field is a plain HTML number input, so
        ASCII is the whole of the legitimate domain.
        """
        with pytest.raises(InvalidQuantity):
            quota.parse_quantity(raw)

    @pytest.mark.parametrize("raw", [1.9, 5.0, -2.5])
    def test_a_float_argument_is_rejected_not_truncated(self, raw):
        """``int(1.9)`` silently dropped the fraction; now it is refused."""
        with pytest.raises(InvalidQuantity):
            quota.parse_quantity(raw)

    @pytest.mark.parametrize("raw", [True, False])
    def test_a_bool_is_not_a_quantity(self, raw):
        """``bool`` is an ``int`` subclass by history, not a number of clothes."""
        with pytest.raises(InvalidQuantity):
            quota.parse_quantity(raw)

    @pytest.mark.parametrize("raw", [[5], {"n": 5}, (5,), object()])
    def test_other_types_are_rejected(self, raw):
        with pytest.raises(InvalidQuantity):
            quota.parse_quantity(raw)


# ---------------------------------------------------------------------------
# check -- acceptance
# ---------------------------------------------------------------------------


class TestCheckAccepts:
    @pytest.mark.parametrize("num_clothes", [1, 2, 15, 29, 30])
    def test_any_positive_amount_within_the_quota(self, fake_student, num_clothes):
        assert quota.check(fake_student(30), num_clothes) is None

    def test_exactly_the_remaining_quota_is_allowed(self, fake_student):
        assert quota.check(fake_student(10), 10) is None

    def test_one_below_the_quota_is_allowed(self, fake_student):
        assert quota.check(fake_student(10), 9) is None

    def test_a_single_clothe_against_a_quota_of_one(self, fake_student):
        assert quota.check(fake_student(1), 1) is None

    def test_check_does_not_mutate_the_student(self, fake_student):
        student = fake_student(30)
        quota.check(student, 5)
        assert student.remaining_quota == 30


# ---------------------------------------------------------------------------
# check -- InvalidQuantity
# ---------------------------------------------------------------------------


class TestCheckRejectsInvalidQuantity:
    @pytest.mark.parametrize("num_clothes", [0, -1, -5, -1000])
    def test_non_positive_amounts_are_invalid(self, fake_student, num_clothes):
        with pytest.raises(InvalidQuantity):
            quota.check(fake_student(30), num_clothes)

    def test_the_error_carries_the_offending_quantity(self, fake_student):
        with pytest.raises(InvalidQuantity) as excinfo:
            quota.check(fake_student(30), -5)
        assert excinfo.value.num_clothes == -5

    def test_zero_is_invalid_even_when_the_quota_is_zero(self, fake_student):
        """The quantity check runs first, so it wins over the quota check."""
        with pytest.raises(InvalidQuantity):
            quota.check(fake_student(0), 0)

    def test_the_quantity_check_runs_before_the_student_is_touched(self):
        """A non-positive quantity is rejected without reading the student.

        This ordering is load-bearing: it is why the route raises
        AttributeError for a deleted student on a *valid* quantity but flashes
        an error on an invalid one.
        """

        class Exploding:
            @property
            def remaining_quota(self):
                raise AssertionError("remaining_quota must not be read")

        with pytest.raises(InvalidQuantity):
            quota.check(Exploding(), 0)

    def test_a_missing_student_still_reaches_the_quantity_check(self):
        with pytest.raises(InvalidQuantity):
            quota.check(None, 0)


# ---------------------------------------------------------------------------
# check -- QuotaExceeded
# ---------------------------------------------------------------------------


class TestCheckRejectsQuotaExceeded:
    def test_one_over_the_quota_is_rejected(self, fake_student):
        with pytest.raises(QuotaExceeded):
            quota.check(fake_student(10), 11)

    def test_wildly_over_the_quota_is_rejected(self, fake_student):
        with pytest.raises(QuotaExceeded):
            quota.check(fake_student(30), 1000000)

    def test_anything_at_all_is_rejected_once_the_quota_is_zero(self, fake_student):
        with pytest.raises(QuotaExceeded):
            quota.check(fake_student(0), 1)

    def test_the_error_carries_the_remaining_quota(self, fake_student):
        with pytest.raises(QuotaExceeded) as excinfo:
            quota.check(fake_student(7), 8)
        assert excinfo.value.remaining == 7

    def test_the_error_carries_the_requested_amount(self, fake_student):
        with pytest.raises(QuotaExceeded) as excinfo:
            quota.check(fake_student(7), 8)
        assert excinfo.value.num_clothes == 8

    def test_the_remaining_value_is_what_the_route_renders(self, fake_student):
        """The route builds its flash from ``exc.remaining``."""
        with pytest.raises(QuotaExceeded) as excinfo:
            quota.check(fake_student(0), 1)
        message = f"You only have {excinfo.value.remaining} clothes remaining in your quota."
        assert message == "You only have 0 clothes remaining in your quota."

    def test_rejection_does_not_mutate_the_student(self, fake_student):
        student = fake_student(10)
        with pytest.raises(QuotaExceeded):
            quota.check(student, 11)
        assert student.remaining_quota == 10

    def test_a_negative_quota_rejects_every_positive_amount(self, fake_student):
        """A quota below zero is unreachable through the UI but storable."""
        with pytest.raises(QuotaExceeded):
            quota.check(fake_student(-3), 1)

    def test_a_missing_student_raises_attributeerror_on_a_valid_quantity(self):
        # BUG: quota.check dereferences ``student.remaining_quota`` with no
        # guard, exactly as routes.py did inline. A live session naming a
        # deleted student therefore produces AttributeError -> HTTP 500.
        # Correct behaviour: the caller should resolve the student before
        # calling, and the service should reject None loudly rather than by
        # accident.
        with pytest.raises(AttributeError):
            quota.check(None, 5)


# ---------------------------------------------------------------------------
# deduct
# ---------------------------------------------------------------------------


class TestDeduct:
    def test_subtracts_exactly_the_requested_amount(self, fake_student):
        student = fake_student(30)
        quota.deduct(student, 5)
        assert student.remaining_quota == 25

    def test_returns_the_new_balance(self, fake_student):
        assert quota.deduct(fake_student(30), 5) == 25

    def test_deducting_the_whole_quota_zeroes_it(self, fake_student):
        student = fake_student(30)
        quota.deduct(student, 30)
        assert student.remaining_quota == 0

    def test_repeated_deductions_accumulate(self, fake_student):
        student = fake_student(30)
        for _ in range(3):
            quota.deduct(student, 4)
        assert student.remaining_quota == 18

    def test_deducting_one_leaves_the_rest(self, fake_student):
        student = fake_student(30)
        quota.deduct(student, 1)
        assert student.remaining_quota == 29

    def test_deduct_does_not_validate(self, fake_student):
        # BUG: deduct has no guard of its own -- it trusts that check() ran
        # first. Called directly with an over-quota amount it drives the
        # balance negative, and there is no CHECK (remaining_quota >= 0)
        # constraint in models.py to catch that at the database. This is the
        # same read-check-write gap the route has under concurrency: two
        # requests can both pass check() before either deducts. Correct
        # behaviour: an atomic conditional UPDATE plus a non-negative
        # constraint.
        student = fake_student(10)
        quota.deduct(student, 25)
        assert student.remaining_quota == -15

    def test_deducting_a_negative_amount_inflates_the_quota(self, fake_student):
        # BUG: the classic `quota -= -5`. Unreachable today because check()
        # rejects non-positive amounts first, but nothing in deduct itself
        # prevents it.
        student = fake_student(30)
        quota.deduct(student, -5)
        assert student.remaining_quota == 35

    def test_works_on_a_real_student_row(self, student):
        quota.deduct(student, 12)
        assert student.remaining_quota == 18

    def test_does_not_commit(self, student, db_session):
        """Persistence is the caller's job."""
        quota.deduct(student, 12)
        db_session.rollback()
        assert student.remaining_quota == 30


# ---------------------------------------------------------------------------
# The check -> deduct sequence
# ---------------------------------------------------------------------------


class TestCheckThenDeduct:
    def test_the_happy_path_leaves_the_expected_balance(self, fake_student):
        student = fake_student(30)
        quota.check(student, 5)
        quota.deduct(student, 5)
        assert student.remaining_quota == 25

    def test_a_rejected_request_leaves_the_balance_alone(self, fake_student):
        student = fake_student(30)
        with pytest.raises(QuotaExceeded):
            quota.check(student, 31)
        assert student.remaining_quota == 30

    def test_the_quota_can_be_spent_down_to_exactly_zero(self, fake_student):
        student = fake_student(30)
        for amount in (10, 10, 10):
            quota.check(student, amount)
            quota.deduct(student, amount)
        assert student.remaining_quota == 0
        with pytest.raises(QuotaExceeded):
            quota.check(student, 1)


# ---------------------------------------------------------------------------
# Error taxonomy
# ---------------------------------------------------------------------------


class TestErrorTaxonomy:
    @pytest.mark.parametrize("error", [InvalidQuantity, QuotaExceeded])
    def test_domain_errors_share_a_base_class(self, error):
        assert issubclass(error, ServiceError)

    def test_service_error_is_an_exception(self):
        assert issubclass(ServiceError, Exception)

    def test_invalid_quantity_and_quota_exceeded_are_distinguishable(self):
        assert not issubclass(InvalidQuantity, QuotaExceeded)
        assert not issubclass(QuotaExceeded, InvalidQuantity)

    def test_invalid_quantity_message_names_the_value(self):
        assert "-5" in str(InvalidQuantity(-5))

    def test_quota_exceeded_message_names_both_numbers(self):
        message = str(QuotaExceeded(8, 7))
        assert "8" in message
        assert "7" in message

    def test_the_package_re_exports_the_domain_errors(self):
        import services

        assert services.InvalidQuantity is InvalidQuantity
        assert services.QuotaExceeded is QuotaExceeded
        assert services.ServiceError is ServiceError


# ---------------------------------------------------------------------------
# Framework independence
# ---------------------------------------------------------------------------


PRESENTATION_HELPERS = {"flash", "redirect", "url_for", "render_template", "session", "request"}


def test_the_quota_module_imports_nothing_at_all(imported_roots):
    """The whole point of the extraction: pure arithmetic, zero dependencies."""
    assert imported_roots(quota) == set()


def test_the_quota_module_names_no_presentation_helpers(referenced_names):
    assert referenced_names(quota).isdisjoint(PRESENTATION_HELPERS)
