from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_frontend_sources_are_utf8_readable_on_windows():
    for relative in (
        "app/backend/api/app/static/index.html",
        "app/backend/api/app/static/styles.css",
        "app/backend/api/app/static/app.js",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert text


def test_frontend_tests_use_explicit_utf8_reads():
    tests_dir = Path(__file__).resolve().parent
    for path in tests_dir.glob("test_*.py"):
        source = path.read_text(encoding="utf-8")
        for line in source.splitlines():
            if ".read_text(" in line and "encoding=" not in line:
                # Helper calls such as _read(path) are fine; every direct Path.read_text
                # in this frontend test suite must pin UTF-8 for Windows.
                raise AssertionError(f"missing explicit UTF-8 encoding in {path.name}: {line.strip()}")
