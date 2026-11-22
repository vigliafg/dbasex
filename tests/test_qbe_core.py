"""Test della grammatica delle celle QBE (0.4/O4)."""

from __future__ import annotations

import pytest

from dbx.core import types as T
from dbx.core.qbe import (
    QbeCell,
    QbeError,
    example_name,
    format_cell,
    is_example_element,
    parse_cell,
)


def test_empty_cell_has_no_condition() -> None:
    assert parse_cell("") is None
    assert parse_cell("   ") is None


def test_plain_value_is_equality() -> None:
    assert parse_cell("Roma", T.TEXT) == QbeCell("eq", "Roma")


def test_comparison_operators() -> None:
    assert parse_cell(">1000", T.DECIMAL) == QbeCell("gt", "1000")
    assert parse_cell(">= 10", T.INTEGER) == QbeCell("ge", "10")
    assert parse_cell("<>0", T.INTEGER) == QbeCell("ne", "0")
    assert parse_cell("!=0", T.INTEGER) == QbeCell("ne", "0")
    assert parse_cell("<2026-01-01", T.DATE) == QbeCell("lt", "2026-01-01")
    assert parse_cell("<=5", T.INTEGER) == QbeCell("le", "5")


def test_range_for_numbers_and_dates() -> None:
    assert parse_cell("100..500", T.DECIMAL) == QbeCell("between", "100", "500")
    assert parse_cell("2026-01-01..2026-12-31", T.DATE) == QbeCell(
        "between", "2026-01-01", "2026-12-31"
    )


def test_range_rejects_text_and_incomplete() -> None:
    with pytest.raises(QbeError, match="numeri e date"):
        parse_cell("a..z", T.TEXT)
    with pytest.raises(QbeError, match="incompleto"):
        parse_cell("10..", T.INTEGER)
    with pytest.raises(QbeError, match="non valido"):
        parse_cell("x..10", T.INTEGER)


def test_wildcards_are_like_for_text_only() -> None:
    assert parse_cell("Al*", T.TEXT) == QbeCell("like", "Al*")
    assert parse_cell("?eta", T.TEXT) == QbeCell("like", "?eta")
    assert parse_cell("=Al*", T.TEXT) == QbeCell("like", "Al*")
    with pytest.raises(QbeError, match="solo per il testo"):
        parse_cell("1*", T.INTEGER)


def test_blank_aliases() -> None:
    assert parse_cell("blank", T.TEXT) == QbeCell("null")
    assert parse_cell("vuoto", T.TEXT) == QbeCell("null")
    assert parse_cell("not blank", T.TEXT) == QbeCell("notnull")
    assert parse_cell("non vuoto", T.TEXT) == QbeCell("notnull")


def test_example_elements() -> None:
    assert is_example_element("_cliente")
    assert example_name("_cliente") == "cliente"
    assert not is_example_element("cliente")
    assert not is_example_element("_")
    with pytest.raises(QbeError, match="example element"):
        parse_cell("_cliente", T.TEXT)


@pytest.mark.parametrize(
    "cell",
    [
        QbeCell("eq", "Roma"),
        QbeCell("ne", "0"),
        QbeCell("gt", "10"),
        QbeCell("ge", "10"),
        QbeCell("lt", "10"),
        QbeCell("le", "10"),
        QbeCell("between", "10", "20"),
        QbeCell("like", "Al*"),
        QbeCell("null"),
        QbeCell("notnull"),
    ],
)
def test_format_roundtrip(cell: QbeCell) -> None:
    text = format_cell(cell)
    assert parse_cell(text, T.TEXT if cell.op == "like" else T.INTEGER) == cell


def test_comparison_requires_value() -> None:
    with pytest.raises(QbeError, match="valore mancante"):
        parse_cell(">", T.INTEGER)
