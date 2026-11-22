"""Verifiche di prestazione dichiarate nel piano della release 0.2."""

from __future__ import annotations

import time
from pathlib import Path

from dbx.core.form_model import FormControl, FormPage, FormSpec
from dbx.core.project import Project
from dbx.runtime.form_runtime import FormRuntime
from dbx.samples import create_demo_project

PROJECT_BUDGET = 2.0
FORM_BUDGET = 2.0


def test_demo_project_opens_within_budget(tmp_path: Path) -> None:
    started = time.perf_counter()
    project = create_demo_project(tmp_path / "Rubrica")
    created = time.perf_counter() - started
    project.close()

    started = time.perf_counter()
    reopened = Project.open(tmp_path / "Rubrica")
    opened = time.perf_counter() - started
    try:
        assert len(reopened.tables()) == 2
    finally:
        reopened.close()
    assert created < PROJECT_BUDGET
    assert opened < PROJECT_BUDGET


def test_form_with_hundred_controls_is_fluid(qapp, demo_project) -> None:
    page = FormPage(caption="Cento campi")
    for index in range(100):
        page.controls.append(
            FormControl(
                id=f"c{index}",
                kind="field",
                field="nome",
                x=(index % 3) * 190,
                y=(index // 3) * 26,
                w=180,
                h=20,
            )
        )
    spec = FormSpec(
        name="form_cento",
        caption="Cento campi",
        table="clienti",
        width=600,
        height=900,
        pages=[page],
    )
    started = time.perf_counter()
    runtime = FormRuntime(demo_project, spec)
    elapsed = time.perf_counter() - started
    try:
        assert len(runtime.binders) == 100
        assert runtime.load_current() is None
        assert elapsed < FORM_BUDGET
    finally:
        runtime.deleteLater()
