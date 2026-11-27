"""Coerenza della versione e dei materiali di release."""

from __future__ import annotations

import pathlib
import tomllib

from dbx import __version__

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _declared_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def test_versions_are_aligned() -> None:
    assert __version__ == _declared_version()


def test_changelog_contains_current_version() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{__version__}]" in changelog


def test_release_notes_exist() -> None:
    assert (ROOT / "docs" / f"release-{__version__}.md").is_file()


def test_release_check_accepts_matching_tag() -> None:
    from tools.release_check import check

    assert check(f"v{__version__}") == []


def test_release_check_rejects_wrong_tag() -> None:
    from tools.release_check import check

    problems = check("v0.0.0")
    assert any("tag" in problem for problem in problems)
