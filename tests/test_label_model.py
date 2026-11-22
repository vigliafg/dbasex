"""Test del modello etichette (0.8 O7)."""

from __future__ import annotations

import pytest

from dbx.core.label_model import (
    DEFAULT_PRESET,
    LABEL_PRESETS,
    LabelSpec,
    default_template,
    preset_data,
    preset_labels,
)


def test_default_template_and_preset():
    spec = LabelSpec.create("et", "clienti", ["nome", "citta", "email", "note"])
    assert spec.template == "[nome]\n[citta]\n[email]"
    assert spec.page_size == "A4"
    assert spec.columns == 3
    assert spec.rows == 8
    assert spec.preset_key() == DEFAULT_PRESET
    assert spec.validate() == []


def test_preset_applies_geometry_and_margins():
    spec = LabelSpec(name="et", table="clienti")
    assert spec.apply_preset("avery5160") is True
    assert spec.page_size == "Letter"
    assert spec.columns == 3
    assert spec.rows == 10
    assert spec.gutter_x == pytest.approx(2.54)
    assert spec.margin("top") == pytest.approx(12.7)
    assert spec.margin("left") == pytest.approx(4.8)
    assert spec.validate() == []
    assert spec.apply_preset("inesistente") is False


def test_preset_catalog_and_data_are_copies():
    keys = [key for key, _label in preset_labels()]
    assert list(LABEL_PRESETS) == keys
    assert DEFAULT_PRESET in keys
    data = preset_data("avery5163")
    assert data is not None
    data["margins"]["top"] = 999
    assert preset_data("avery5163")["margins"]["top"] != 999


def test_round_trip_preserves_new_fields():
    spec = LabelSpec.create_for_query(
        "mail_merge", "clienti_attivi", ["codice", "nome"], title="Mail merge"
    )
    spec.filter = "citta = 'Roma'"
    spec.order = "nome desc"
    spec.font_size = 14
    spec.bold = True
    spec.align = "center"
    spec.border = True
    spec.start_offset = 3
    spec.color = "#333333"
    clone = LabelSpec.from_dict(spec.to_dict())
    assert clone.to_dict() == spec.to_dict()
    assert clone.source_type == "query"
    assert clone.query == "clienti_attivi"


def test_validation_reports_geometry_errors():
    spec = LabelSpec.create("et", "clienti", ["nome"])
    spec.label_width = 90
    assert any("larghezza" in error.lower() for error in spec.validate())
    spec = LabelSpec.create("et", "clienti", ["nome"])
    spec.label_height = 60
    assert any("altezza" in error.lower() for error in spec.validate())
    spec = LabelSpec.create("et", "clienti", ["nome"])
    spec.columns = 0
    assert any("almeno 1" in error for error in spec.validate())


def test_validation_reports_source_and_text_errors():
    spec = LabelSpec(name="et", source_type="table", table="")
    errors = spec.validate()
    assert any("tabella sorgente" in error for error in errors)
    spec = LabelSpec(name="et", source_type="query", query="")
    assert any("query sorgente" in error for error in spec.validate())
    spec = LabelSpec.create("et", "clienti", ["nome"])
    spec.align = "giustificato"
    assert any("Allineamento" in error for error in spec.validate())
    spec = LabelSpec.create("et", "clienti", ["nome"])
    spec.start_offset = -1
    assert any("saltare" in error for error in spec.validate())
    spec = LabelSpec.create("et", "clienti", ["nome"])
    spec.font_size = 2
    assert any("corpo" in error.lower() for error in spec.validate())


def test_landscape_page_dimensions():
    spec = LabelSpec.create("et", "clienti", ["nome"])
    spec.orientation = "landscape"
    width, height = spec.page_dimensions()
    assert width == pytest.approx(297.0)
    assert height == pytest.approx(210.0)


def test_default_template_skips_empty_names():
    assert default_template([]) == ""
    assert default_template(["", "nome"]) == "[nome]"
