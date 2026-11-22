"""Test UI dei parametri script e dell'esecuzione parametrizzata (0.9 O10)."""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QMessageBox

from dbx.runtime.script_engine import new_step


def test_arguments_dialog_prefills_defaults_and_returns_values(qapp) -> None:
    from dbx.ui.script_params import ScriptArgumentsDialog

    dialog = ScriptArgumentsDialog(
        [
            {"name": "soglia", "label": "Importo minimo", "default": "1000"},
            {"name": "anno", "label": "Anno", "default": ""},
        ],
        name="prova",
    )
    try:
        assert dialog.windowTitle() == "Esegui script — prova"
        assert dialog.values() == {"soglia": "1000", "anno": ""}
        dialog._edits["soglia"].setText("250")
        dialog._edits["anno"].setText("2026")
        assert dialog.values() == {"soglia": "250", "anno": "2026"}
    finally:
        dialog.close()


def test_parameters_dialog_roundtrip(qapp) -> None:
    from dbx.ui.script_params import ScriptParametersDialog

    dialog = ScriptParametersDialog(
        [{"name": "soglia", "label": "Importo minimo", "default": "1000"}],
        name="prova",
    )
    try:
        assert dialog.table.rowCount() == 1
        assert dialog.parameters() == [
            {"name": "soglia", "label": "Importo minimo", "default": "1000"}
        ]
        dialog.add_row("anno", "Anno", "2026")
        assert [entry["name"] for entry in dialog.parameters()] == ["soglia", "anno"]
        dialog.table.selectRow(0)
        dialog.remove_row()
        assert [entry["name"] for entry in dialog.parameters()] == ["anno"]
    finally:
        dialog.close()


def test_parameters_dialog_rejects_invalid_name(qapp, monkeypatch) -> None:
    from dbx.ui.script_params import ScriptParametersDialog

    warnings: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *args, **kwargs: warnings.append(str(args[2]))
    )
    dialog = ScriptParametersDialog()
    try:
        dialog.table.item(0, 0).setText("nome non valido")
        dialog.accept()
        assert warnings and "parametro" in warnings[0].lower()
        assert dialog.result() == QDialog.DialogCode.Rejected
    finally:
        dialog.close()


def test_designer_edits_parameters_and_saves_them(qapp, demo_project, monkeypatch) -> None:
    from dbx.designers.script_builder import ScriptBuilderWidget
    from dbx.ui.script_params import ScriptParametersDialog

    artifact = {
        "name": "con_parametri",
        "steps": [new_step("message", text=":soglia")],
    }
    editor = ScriptBuilderWidget(demo_project, artifact)
    try:
        monkeypatch.setattr(
            ScriptParametersDialog,
            "exec",
            lambda self: QDialog.DialogCode.Accepted,
        )
        monkeypatch.setattr(
            ScriptParametersDialog,
            "parameters",
            lambda self: [
                {"name": "soglia", "label": "Soglia", "default": "100"}
            ],
        )
        assert editor.is_dirty() is False
        editor.edit_parameters()
        assert editor.params == [
            {"name": "soglia", "label": "Soglia", "default": "100"}
        ]
        assert editor.is_dirty() is True
        assert editor.save() is True
        assert editor.is_dirty() is False
        saved = demo_project.artifact("scripts", "con_parametri")
        assert saved["params"] == [
            {"name": "soglia", "label": "Soglia", "default": "100"}
        ]

        editor.edit_parameters()
        assert editor.status_label.text() in ("Pronto", "Sorgente modificata: applica le modifiche o rigenera")
    finally:
        editor.close()


def test_designer_runs_script_with_parameter_defaults(
    qapp, demo_project, monkeypatch
) -> None:
    from dbx.designers.script_builder import ScriptBuilderWidget

    messages: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "information", lambda *args, **kwargs: messages.append(str(args[2]))
    )
    artifact = demo_project.artifact("scripts", "fatture_sopra_soglia")
    editor = ScriptBuilderWidget(demo_project, artifact)
    try:
        editor.run_script()
        text = editor.log.toPlainText()
        assert "Fatture sopra 1000" in text
    finally:
        editor.close()


def test_main_window_asks_parameters_before_running(qapp, demo_project, monkeypatch) -> None:
    from dbx.ui.main_window import MainWindow
    from dbx.ui.script_params import ScriptArgumentsDialog

    seen: list[dict[str, str]] = []
    messages: list[str] = []
    monkeypatch.setattr(
        ScriptArgumentsDialog, "exec", lambda self: QDialog.DialogCode.Accepted
    )
    original_values = ScriptArgumentsDialog.values

    def values(self):
        data = original_values(self)
        seen.append(dict(data))
        return {"soglia": "500"}

    monkeypatch.setattr(ScriptArgumentsDialog, "values", values)
    monkeypatch.setattr(
        QMessageBox, "information", lambda *args, **kwargs: messages.append(str(args[2]))
    )
    window = MainWindow(demo_project)
    try:
        window.show()
        window.run_object("scripts", "fatture_sopra_soglia")
        qapp.processEvents()
        assert seen and seen[0]["soglia"] == "1000"
        assert messages and "500" in messages[-1]
        assert demo_project.globals.get("ultima_soglia") == "500"
    finally:
        window.close()


def test_project_runner_asks_parameters_before_running(
    qapp, demo_project, monkeypatch
) -> None:
    from dbx.ui.project_runner import ProjectRunner
    from dbx.ui.script_params import ScriptArgumentsDialog

    seen: list[dict[str, str]] = []
    monkeypatch.setattr(
        ScriptArgumentsDialog, "exec", lambda self: QDialog.DialogCode.Accepted
    )
    original_values = ScriptArgumentsDialog.values

    def values(self):
        data = original_values(self)
        seen.append(dict(data))
        return {"soglia": "1500"}

    monkeypatch.setattr(ScriptArgumentsDialog, "values", values)
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)
    runner = ProjectRunner(demo_project)
    try:
        runner._dispatch("run_script", "fatture_sopra_soglia")
        assert seen and seen[0]["soglia"] == "1000"
        assert demo_project.globals.get("ultima_soglia") == "1500"
    finally:
        runner.close()


def test_main_window_can_cancel_parameter_prompt(qapp, demo_project, monkeypatch) -> None:
    from dbx.ui.main_window import MainWindow
    from dbx.ui.script_params import ScriptArgumentsDialog

    calls: list[str] = []
    monkeypatch.setattr(
        ScriptArgumentsDialog, "exec", lambda self: QDialog.DialogCode.Rejected
    )
    monkeypatch.setattr(
        QMessageBox, "information", lambda *args, **kwargs: calls.append("info")
    )
    window = MainWindow(demo_project)
    try:
        window.show()
        window.run_object("scripts", "fatture_sopra_soglia")
        qapp.processEvents()
        assert calls == []
        assert "ultima_soglia" not in demo_project.globals
    finally:
        window.close()
