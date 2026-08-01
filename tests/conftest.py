"""Root test configuration.

The suite is split in two, and the split is enforced by directory rather than
by a marker written at the top of every file -- a file can be added to
``tests/unit/`` without anyone remembering to tag it, and a mis-tagged file is
impossible.

``tests/unit/``
    The bulk of the suite. No Flask application, no ``test_client``, no HTTP.
    Where persistence is genuinely needed these tests talk to a plain
    SQLAlchemy session over in-memory SQLite (see ``tests/unit/conftest.py``).

``tests/integration/``
    Deliberately few. Only what needs the whole stack: the app factory, the
    blueprints, the session cookie, the templates.

Application modules use bare imports (``from config import Config``), so
``pytest.ini`` adds ``laundry_app`` to ``pythonpath``; that makes ``app``,
``config``, ``models``, ``routes`` and ``services`` importable as top-level
names from either directory.
"""

import pathlib

import pytest

_TESTS_ROOT = pathlib.Path(__file__).parent

# Directory name -> marker applied to everything collected beneath it.
_MARKER_BY_DIRECTORY = {"unit": "unit", "integration": "integration"}


def pytest_collection_modifyitems(items):
    """Tag every test with ``unit`` or ``integration`` based on its directory."""
    for item in items:
        try:
            relative = pathlib.Path(item.fspath).relative_to(_TESTS_ROOT)
        except ValueError:  # pragma: no cover - defensive, tests live under tests/
            continue
        marker = _MARKER_BY_DIRECTORY.get(relative.parts[0])
        if marker is not None:
            item.add_marker(getattr(pytest.mark, marker))
