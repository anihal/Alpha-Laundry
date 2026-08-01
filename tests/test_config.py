"""Tests for config.py.

``config.Config`` reads ``os.getenv`` at *class body execution* time, i.e. once
at import. To observe different environments we monkeypatch the environment and
then ``importlib.reload`` the module.

Reloading rebinds ``config.Config`` to a brand new class object; the reference
that ``app.py`` and ``tests/conftest.py`` captured at their own import time
still points at the original class, so these tests cannot disturb the rest of
the suite. The ``reload_config`` fixture nonetheless restores the module to a
pristine state afterwards.
"""

import importlib
import os

import config as config_module
import pytest

ENV_KEYS = ("DATABASE_URL", "SECRET_KEY", "DEBUG")


@pytest.fixture
def reload_config(monkeypatch):
    """Reload config.py under a controlled environment.

    Usage: ``cfg = reload_config(DEBUG="true")``. Any key not passed is deleted
    from the environment first, so "absent" really means absent.
    """

    def _reload(**env):
        for key in ENV_KEYS:
            monkeypatch.delenv(key, raising=False)
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        # Reloading re-executes `from dotenv import load_dotenv`, so patch the
        # attribute on the dotenv package itself rather than on config. Without
        # this, a developer's real laundry_app/.env repopulates os.environ and
        # "absent" stops meaning absent -- these tests would then pass in CI's
        # clean checkout but fail on any machine that has a .env.
        monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: False)
        return importlib.reload(config_module).Config

    yield _reload

    # Restore the module to the ambient environment for anything that imports
    # it later in the session.
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    importlib.reload(config_module)


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


class TestDefaults:
    def test_database_url_default(self, reload_config):
        assert reload_config().DATABASE_URL == "sqlite:///laundry.db"

    def test_secret_key_has_no_insecure_default(self, reload_config):
        # config.py no longer injects a guessable fallback: an unset SECRET_KEY
        # yields None (not the old "change-me-in-production" literal). The
        # fail-closed decision then lives in app.resolve_secret_key, which
        # raises at startup outside DEBUG. This is what stops a deployment that
        # forgets SECRET_KEY from silently signing cookies with a public key.
        assert reload_config().SECRET_KEY is None

    def test_debug_default_is_false(self, reload_config):
        assert reload_config().DEBUG is False

    def test_all_three_defaults_together(self, reload_config):
        cfg = reload_config()
        assert cfg.DATABASE_URL == "sqlite:///laundry.db"
        assert cfg.SECRET_KEY is None
        assert cfg.DEBUG is False


# ---------------------------------------------------------------------------
# Environment override
# ---------------------------------------------------------------------------


class TestEnvironmentOverride:
    def test_database_url_from_env(self, reload_config):
        cfg = reload_config(DATABASE_URL="postgresql://user:pw@localhost/laundry")
        assert cfg.DATABASE_URL == "postgresql://user:pw@localhost/laundry"

    def test_secret_key_from_env(self, reload_config):
        cfg = reload_config(SECRET_KEY="a-real-secret")
        assert cfg.SECRET_KEY == "a-real-secret"

    def test_empty_env_var_is_taken_literally(self, reload_config):
        """An empty string is a *set* variable, so os.getenv returns ""."""
        # config.py reads the raw value, so an empty `SECRET_KEY=` still surfaces
        # as "" here -- but app.resolve_secret_key now treats "" as insecure and
        # fails closed at startup (see tests/test_app.py::TestResolveSecretKey),
        # so an empty signing key can no longer reach Flask. `DATABASE_URL=`
        # still yields an unusable URI; validating it is a separate concern.
        cfg = reload_config(SECRET_KEY="", DATABASE_URL="")
        assert cfg.SECRET_KEY == ""
        assert cfg.DATABASE_URL == ""

    def test_all_three_from_env(self, reload_config):
        cfg = reload_config(
            DATABASE_URL="sqlite:///other.db",
            SECRET_KEY="k",
            DEBUG="true",
        )
        assert cfg.DATABASE_URL == "sqlite:///other.db"
        assert cfg.SECRET_KEY == "k"
        assert cfg.DEBUG is True


# ---------------------------------------------------------------------------
# DEBUG string -> bool parsing
# ---------------------------------------------------------------------------


class TestDebugParsing:
    @pytest.mark.parametrize("raw", ["true", "True", "TRUE", "TrUe", "  true  ".strip()])
    def test_truthy_spellings(self, reload_config, raw):
        assert reload_config(DEBUG=raw).DEBUG is True

    @pytest.mark.parametrize(
        "raw",
        ["false", "False", "FALSE", "0", "1", "yes", "Yes", "on", "y", "garbage", ""],
    )
    def test_everything_else_is_false(self, reload_config, raw):
        # Note "1", "yes" and "on" -- conventional truthy spellings accepted by
        # most config parsers -- all evaluate to False here.
        # BUG: config.py:21 only recognises the exact (case-insensitive) string
        # "true". DEBUG=1 or DEBUG=yes silently disables debug mode with no
        # warning. Correct behaviour: accept the usual truthy set
        # {"1","true","yes","on"} and reject unrecognised values loudly.
        assert reload_config(DEBUG=raw).DEBUG is False

    def test_whitespace_padding_is_not_stripped(self, reload_config):
        # BUG: config.py:21 does not .strip() the value, so a trailing space in
        # a .env file ("DEBUG=true ") turns debug off. Correct behaviour: strip
        # before comparing.
        assert reload_config(DEBUG=" true").DEBUG is False
        assert reload_config(DEBUG="true ").DEBUG is False

    def test_debug_is_a_real_bool_not_a_string(self, reload_config):
        cfg = reload_config(DEBUG="true")
        assert isinstance(cfg.DEBUG, bool)


# ---------------------------------------------------------------------------
# Module shape
# ---------------------------------------------------------------------------


def test_config_exposes_the_expected_attributes():
    for attr in ("DATABASE_URL", "SECRET_KEY", "DEBUG"):
        assert hasattr(config_module.Config, attr)


def test_load_dotenv_is_imported_and_called_at_module_scope():
    """config.py wires python-dotenv so a .env file is honoured.

    A spy cannot be used here: ``importlib.reload`` re-executes
    ``from dotenv import load_dotenv``, which rebinds the name back to the real
    function before the call happens. Assert on the module contract instead.
    """
    assert callable(config_module.load_dotenv)
    with open(config_module.__file__, encoding="utf-8") as fh:
        source = fh.read()
    assert "load_dotenv()" in source
    assert os is not None  # os is used by the module under test
