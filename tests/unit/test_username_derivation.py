"""Tests for the readable login handles used by the demo seeder."""

import pytest
from seed_demo import derive_username


class TestDeriveUsername:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("Tony Soprano", "tonsop"),
            ("Carmela Soprano", "carsop"),
            ("Christopher Moltisanti", "chrmol"),
            ("Paulie Gualtieri", "paugua"),
            ("Tommy DeVito", "tomdev"),
            ("Tom Hagen", "tomhag"),
            ("Nucky Thompson", "nuctho"),
            ("Thomas Shelby", "thoshe"),
        ],
    )
    def test_three_plus_three(self, name, expected):
        assert derive_username(name) == expected

    def test_particles_collapse_into_the_family_name(self):
        # "Adriana La Cerva" -> adr + (la + cerva)[:3]
        assert derive_username("Adriana La Cerva") == "adrlac"

    def test_single_word_name_uses_first_six_letters(self):
        assert derive_username("Clemenza") == "clemen"

    def test_short_names_are_not_padded(self):
        assert derive_username("Al Bo") == "albo"

    def test_accents_are_stripped(self):
        assert derive_username("Renée Fàvreau") == "renfav"

    def test_punctuation_and_case_are_ignored(self):
        assert derive_username("D'Angelo O'Brien") == "danobr"

    def test_result_is_lowercase_ascii_letters_or_digits(self):
        handle = derive_username("Tony Soprano")
        assert handle.isascii()
        assert handle.isalnum()
        assert handle == handle.lower()

    def test_a_name_with_no_letters_is_rejected(self):
        with pytest.raises(ValueError, match="cannot derive"):
            derive_username("--- ???")


class TestCollisions:
    def test_a_taken_handle_gets_a_numeric_suffix(self):
        assert derive_username("Tony Soprano", taken={"tonsop"}) == "tonsop2"

    def test_suffixes_keep_climbing(self):
        taken = {"tonsop", "tonsop2", "tonsop3"}
        assert derive_username("Tony Soprano", taken=taken) == "tonsop4"

    def test_distinct_people_who_compress_alike_stay_distinct(self):
        taken = set()
        first = derive_username("Tony Soprano", taken)
        taken.add(first)
        second = derive_username("Tonya Sopranelli", taken)
        assert first != second

    def test_an_untaken_handle_is_unchanged(self):
        assert derive_username("Tony Soprano", taken={"henhil"}) == "tonsop"
