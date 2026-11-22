"""Fixture condivise per i test UI headless."""

from __future__ import annotations

import os
import tempfile

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DBX_CONFIG_DIR", tempfile.mkdtemp(prefix="dbx-test-config-"))


@pytest.fixture(scope="session")
def qapp():
    from PyQt6.QtWidgets import QApplication

    from dbx.ui.app import create_application

    app = QApplication.instance() or create_application(["dbx-tests"], "silver")
    return app


@pytest.fixture()
def demo_project(tmp_path):
    from dbx.samples import create_demo_project

    project = create_demo_project(tmp_path / "Rubrica")
    try:
        yield project
    finally:
        project.close()
