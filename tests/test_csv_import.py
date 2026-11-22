"""Test dell'importazione CSV guidata (0.6)."""

from __future__ import annotations

import pytest

from dbx.io.csv_io import (
    CsvError,
    read_table,
    records_from_table,
    suggest_mapping,
)


def _write(tmp_path, text: str, encoding: str = "utf-8", name: str = "dati.csv"):
    path = tmp_path / name
    path.write_text(text, encoding=encoding)
    return path


def test_read_table_detects_semicolon_and_header(tmp_path):
    path = _write(tmp_path, "nome;citta\nAda;Roma\nBob;Milano\n")
    delimiter, encoding, rows = read_table(path)
    assert delimiter == ";"
    assert encoding == "utf-8-sig"
    assert rows[0] == ["nome", "citta"]
    assert rows[2] == ["Bob", "Milano"]


def test_read_table_detects_tab_and_latin1(tmp_path):
    path = _write(tmp_path, "nome\tcitta\nRenè\tRoma\n", encoding="latin-1")
    delimiter, encoding, rows = read_table(path)
    assert delimiter == "\t"
    assert encoding == "latin-1"
    assert rows[1][0] == "Renè"


def test_read_table_rejects_empty_file(tmp_path):
    path = _write(tmp_path, "")
    with pytest.raises(CsvError):
        read_table(path)


def test_suggest_mapping_by_name_and_caption(demo_project):
    table = demo_project.require_table("clienti")
    mapping = suggest_mapping(["Codice", "Nome", "Citta", "Email", "Sconosciuta"], table)
    assert mapping == ["codice", "nome", "citta", "email", None]


def test_records_from_table_converts_types(demo_project):
    table = demo_project.require_table("clienti")
    rows = [
        ["codice", "nome", "attivo"],
        ["C01", "Ada", "Sì"],
        ["C02", "Bob", "No"],
    ]
    records = records_from_table(rows, table, ["codice", "nome", "attivo"], True)
    assert records[0]["codice"] == "C01"
    assert records[0]["attivo"] == 1
    assert records[1]["attivo"] == 0


def test_import_wizard_inserts_records(qapp, demo_project, tmp_path, monkeypatch):
    from PyQt6.QtWidgets import QMessageBox

    from dbx.ui.import_wizard import ImportCsvDialog

    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: None)
    path = _write(tmp_path, "codice;nome;citta\nC90;Test Uno;Roma\nC91;Test Due;Milano\n")
    dialog = ImportCsvDialog(demo_project, "clienti")
    dialog.path_edit.setText(str(path))
    dialog.reload_preview()
    assert dialog.mapping_table.rowCount() == 3
    assert dialog.current_mapping()[:3] == ["codice", "nome", "citta"]
    dialog.run_import()
    assert dialog.imported == 2
    table = demo_project.require_table("clienti")
    assert demo_project.db.scalar(
        'SELECT COUNT(*) FROM "clienti" WHERE "codice" IN (?, ?)', ("C90", "C91")
    ) == 2
    dialog.close()


def test_import_wizard_reports_bad_row(qapp, demo_project, tmp_path, monkeypatch):
    from PyQt6.QtWidgets import QMessageBox

    from dbx.ui.import_wizard import ImportCsvDialog

    warnings: list[str] = []
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: warnings.append(args[2]))
    path = _write(tmp_path, "codice;nome\nC92;Test\n;Senza codice\n")
    dialog = ImportCsvDialog(demo_project, "clienti")
    dialog.path_edit.setText(str(path))
    dialog.reload_preview()
    dialog.run_import()
    assert dialog.imported == 0
    assert warnings and "Riga 3" in warnings[0]
    dialog.close()
