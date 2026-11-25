"""Test delle regole di input: maiuscole e maschere (piano validazione)."""

from __future__ import annotations

import pytest

from dbx.core import types as T
from dbx.core.metadata import Field, MetadataError
from dbx.ui.input_rules import InputRules


def test_apply_case_modes():
    assert InputRules.apply_case("ciao mondo", "upper") == "CIAO MONDO"
    assert InputRules.apply_case("CIAO", "lower") == "ciao"
    assert InputRules.apply_case("ciao mondo", "title") == "Ciao Mondo"
    assert InputRules.apply_case("  ciao mondo", "sentence") == "  Ciao mondo"
    assert InputRules.apply_case("ciao", "") == "ciao"
    assert InputRules.apply_case("ciao", "sconosciuta") == "ciao"


def test_mask_slots_and_accepts():
    slots = InputRules.mask_slots("A9 9")
    assert slots == {0: "A", 1: "9", 2: " ", 3: "9"}
    assert InputRules.accepts("9", "7")
    assert not InputRules.accepts("9", "A")
    assert InputRules.accepts("A", "x")
    assert InputRules.accepts("a", "X")
    assert not InputRules.accepts("A", "1")
    assert InputRules.accepts(" ", " ")
    assert not InputRules.accepts(" ", "-")


def test_check_accepts_partial_and_normalizes_slots():
    assert InputRules.check("AA 999", "") == ""
    assert InputRules.check("AA 999", "ab") == "AB"
    assert InputRules.check("AA 999", "ab 123") == "AB 123"
    assert InputRules.check("aa 999", "AB 123") == "ab 123"


def test_check_rejects_invalid_character_and_overflow():
    with pytest.raises(ValueError):
        InputRules.check("AA 999", "a1")
    with pytest.raises(ValueError):
        InputRules.check("AA 999", "ab 1234")
    assert InputRules.fits("AA 999", "ab 123")
    assert not InputRules.fits("AA 999", "ab-123")


def test_shape_combines_case_and_mask():
    field = Field("targa", T.TEXT, mask="AA 999", case_mode="upper")
    assert InputRules.shape(field, "ab 123") == "AB 123"
    assert InputRules.shape(field, "ab") == "AB"
    plain = Field("nome", T.TEXT, case_mode="title")
    assert InputRules.shape(plain, "ada lovelace") == "Ada Lovelace"


def test_is_complete_uses_mask_or_size():
    masked = Field("targa", T.TEXT, mask="AA 999")
    assert not InputRules.is_complete(masked, "AB 12")
    assert InputRules.is_complete(masked, "AB 123")
    sized = Field("nome", T.TEXT, size=4)
    assert not InputRules.is_complete(sized, "Ada")
    assert InputRules.is_complete(sized, "Ada L")
    assert not InputRules.is_complete(Field("nome", T.TEXT), "Ada")


def test_input_schema_rules_and_roundtrip():
    field = Field("targa", T.TEXT, mask="AA 999", case_mode="upper")
    assert Field.from_dict(field.to_dict()) == field
    with pytest.raises(MetadataError):
        Field("targa", T.TEXT, mask="AA-999").validate()
    with pytest.raises(MetadataError):
        Field("nota", T.MEMO, mask="AAA").validate()
    with pytest.raises(MetadataError):
        Field("targa", T.TEXT, mask="AAA", case_mode="caps").validate()
    with pytest.raises(MetadataError):
        Field("totale", T.INTEGER, mask="999").validate()
