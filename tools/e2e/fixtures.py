"""Schemi e dati deterministici per gli scenari E2E."""

from __future__ import annotations

from datetime import date
from typing import Iterable

from dbx.core import types as T
from dbx.core.metadata import Field, ForeignKey, Index, Table
from dbx.core.project import Project
from dbx.runtime.rowset import Rowset


def clienti_table() -> Table:
    return Table(
        name="clienti",
        caption="Clienti",
        fields=[
            Field("codice", T.TEXT, size=8, required=True, pk=True),
            Field("nome", T.TEXT, size=60, required=True),
            Field("citta", T.TEXT, size=40),
            Field("attivo", T.BOOLEAN, default="1"),
            Field("saldo", T.DECIMAL, size=12, default="0"),
            Field("data_nascita", T.DATE),
            Field("note", T.MEMO),
            Field("nome_maiuscolo", T.TEXT, calculated="UPPER([nome])"),
        ],
        indexes=[Index(fields=["codice"], unique=True), Index(fields=["nome"])],
    )


def fatture_table(on_delete: str = "NO ACTION") -> Table:
    return Table(
        name="fatture",
        caption="Fatture",
        fields=[
            Field("numero", T.INTEGER, required=True, pk=True),
            Field("cliente", T.TEXT, size=8, required=True),
            Field("data", T.DATE),
            Field("importo", T.DECIMAL, size=12, default="0"),
            Field("pagata", T.BOOLEAN, default="0"),
            Field("descrizione", T.MEMO),
        ],
        indexes=[Index(fields=["cliente"]), Index(fields=["data"])],
        foreign_keys=[
            ForeignKey(
                columns=["cliente"],
                ref_table="clienti",
                ref_columns=["codice"],
                on_delete=on_delete,
            )
        ],
    )


def tutti_tipi_table() -> Table:
    return Table(
        name="tutti_tipi",
        caption="Tutti i tipi",
        fields=[
            Field("testo", T.TEXT, size=30),
            Field("intero", T.INTEGER),
            Field("decimale", T.DECIMAL, size=12, fmt="###,##0.00"),
            Field("data", T.DATE),
            Field("dataora", T.DATETIME),
            Field("booleano", T.BOOLEAN, default="0"),
            Field("lungo", T.MEMO),
            Field(
                "scelta",
                T.CHOICE,
                size=10,
                choices=[
                    {"value": "A", "label": "Attivo"},
                    {"value": "C", "label": "Chiuso"},
                ],
            ),
            Field("allegato", T.BLOB),
        ],
    )


def apply(project: Project, *tables: Table) -> None:
    for table in tables:
        project.apply_table(table, backup=False)


def seed_clienti(project: Project) -> list[int]:
    rows = Rowset(project.db, project.require_table("clienti"))
    ids: list[int] = []
    for record in (
        {
            "codice": "C001",
            "nome": "Alfa Srl",
            "citta": "Roma",
            "attivo": True,
            "saldo": 1200.5,
            "data_nascita": "2001-05-10",
        },
        {
            "codice": "C002",
            "nome": "Beta Studio",
            "citta": "Milano",
            "attivo": True,
            "saldo": 0,
            "data_nascita": "2010-01-20",
        },
        {
            "codice": "C003",
            "nome": "Gamma snc",
            "citta": "Torino",
            "attivo": False,
            "saldo": -50,
            "data_nascita": "1995-11-03",
        },
        {
            "codice": "C004",
            "nome": "Delta Spa",
            "citta": "Roma",
            "attivo": True,
            "saldo": 500,
            "data_nascita": "2018-07-01",
        },
        {
            "codice": "C005",
            "nome": "Epsilon",
            "citta": "Napoli",
            "attivo": False,
            "saldo": 75.25,
            "data_nascita": "2020-12-31",
        },
    ):
        ids.append(rows.insert(record))
    return ids


def seed_fatture(project: Project) -> list[int]:
    rows = Rowset(project.db, project.require_table("fatture"))
    ids: list[int] = []
    for record in (
        {"numero": 1, "cliente": "C001", "data": "2026-01-10", "importo": 100.0, "pagata": True},
        {"numero": 2, "cliente": "C001", "data": "2026-02-10", "importo": 200.0, "pagata": False},
        {"numero": 3, "cliente": "C002", "data": "2026-03-10", "importo": 300.0, "pagata": False},
        {"numero": 4, "cliente": "C004", "data": "2026-04-10", "importo": 150.5, "pagata": True},
    ):
        ids.append(rows.insert(record))
    return ids


def settled_project(project: Project) -> Project:
    """Crea lo schema 1:N più usato negli scenari E2E."""

    apply(project, clienti_table(), fatture_table())
    seed_clienti(project)
    seed_fatture(project)
    return project


def rows_values(project: Project, table_name: str, field: str) -> list:
    table = project.require_table(table_name)
    return [row.get(field) for row in Rowset(project.db, table).open().rows()]


def fixed_dates() -> list[date]:
    return [date(2026, 1, 10), date(2026, 2, 10), date(2026, 3, 10)]


__all__ = [
    "clienti_table",
    "fatture_table",
    "tutti_tipi_table",
    "apply",
    "seed_clienti",
    "seed_fatture",
    "settled_project",
    "rows_values",
    "fixed_dates",
]
