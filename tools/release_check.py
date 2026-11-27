"""Verifica che il repository sia pronto per una release.

Controlla che la versione dichiarata in ``pyproject.toml`` coincida con quella del
pacchetto, che il changelog contenga la sezione della versione e che esistano le note
di rilascio usate dal workflow ``.github/workflows/release.yml``.

Uso::

    python tools/release_check.py
    python tools/release_check.py --tag v0.10.0
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def declared_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def package_version() -> str:
    from dbx import __version__

    return __version__


def check(tag: str | None = None) -> list[str]:
    problems: list[str] = []
    version = declared_version()
    package = package_version()

    if version != package:
        problems.append(
            f"versione disallineata: pyproject.toml={version}, dbx.__version__={package}"
        )

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## [{version}]" not in changelog:
        problems.append(f"CHANGELOG.md non contiene la sezione '## [{version}]'")

    notes = ROOT / "docs" / f"release-{version}.md"
    if not notes.is_file():
        problems.append(f"mancano le note di rilascio: docs/release-{version}.md")

    if tag is not None:
        normalized = tag[1:] if tag.startswith("v") else tag
        if normalized != version:
            problems.append(f"il tag {tag!r} non corrisponde alla versione {version}")

    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verifica la prontezza della release")
    parser.add_argument("--tag", help="Tag da pubblicare, ad esempio v0.10.0")
    args = parser.parse_args(argv)

    problems = check(args.tag)
    version = declared_version()
    if problems:
        print(f"Release {version} NON pronta:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    target = f" (tag {args.tag})" if args.tag else ""
    print(f"Release {version}{target} pronta: versione, changelog e note coerenti.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
