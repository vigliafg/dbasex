from dbx.runtime.report_engine import (
    BAND_NAMES,
    Control,
    ReportSpec,
    ReportRenderer,
    field_display_name,
    format_number,
    render_report,
    wrap_text,
)


def make_spec(**overrides):
    spec = ReportSpec(name="fatture", title="Fatture", table="fatture")
    spec.bands = {
        "title": [Control("t", "text", x=0, y=0, w=170, h=12, text="Elenco fatture", font_size=16, bold=True)],
        "page_header": [Control("h", "text", x=0, y=0, w=170, h=6, text="dBX", font_size=8)],
        "group_header": [Control("gh", "text", x=0, y=0, w=170, h=6, text="Gruppo", font_size=11, bold=True)],
        "detail": [
            Control("c", "field", x=0, y=0, w=100, h=6, expr="cliente"),
            Control("i", "expr", x=100, y=0, w=40, h=6, expr="[importo]", align="right"),
        ],
        "group_footer": [
            Control("tg", "total", x=100, y=0, w=40, h=6, expr="[importo]", func="sum", label="Totale: ", align="right")
        ],
        "page_footer": [Control("p", "text", x=0, y=0, w=170, h=6, text="Pagina {PAGINA} di {PAGINE}", align="right")],
        "summary": [Control("ts", "total", x=100, y=0, w=40, h=8, expr="[importo]", func="sum", label="Totale generale: ")],
    }
    for key, value in overrides.items():
        setattr(spec, key, value)
    return spec


ROWS = [
    {"cliente": "Alfa", "importo": 100},
    {"cliente": "Alfa", "importo": 50},
    {"cliente": "Beta", "importo": 25},
]


def texts(pages):
    return [op.text for page in pages for op in page.ops]


def test_wrap_text_and_format():
    lines = wrap_text("parola " * 30, 40, 10)
    assert len(lines) > 1
    assert all(len(line) <= 45 for line in lines)
    assert format_number(1500.0) == "1.500"
    assert format_number(12.5) == "12,50"


def test_layout_contains_title_details_and_totals():
    pages = render_report(make_spec(group_by="cliente"), ROWS)
    assert len(pages) == 1
    all_text = texts(pages)
    assert "Elenco fatture" in all_text
    assert "Alfa" in all_text and "Beta" in all_text
    assert any("Totale: 150" in t for t in all_text)
    assert any("Totale generale: 175" in t for t in all_text)


def test_ungrouped_report_has_no_group_footer():
    pages = render_report(make_spec(), ROWS)
    all_text = texts(pages)
    assert not any(t.startswith("Totale: ") for t in all_text)
    assert any("Totale generale: 175" in t for t in all_text)


def test_group_by_produces_group_headers_and_footers():
    spec = make_spec(group_by="cliente")
    pages = render_report(spec, ROWS)
    all_text = texts(pages)
    assert all_text.count("Alfa") >= 1
    assert any(t.startswith("Totale: 150") for t in all_text)
    assert any(t.startswith("Totale: 25") for t in all_text)


def test_pagination_repeats_page_header_and_footer():
    spec = make_spec(page_size="A4")
    spec.bands["detail"] = [Control("c", "field", x=0, y=0, w=100, h=40, expr="cliente")]
    rows = [{"cliente": f"Cliente {i}", "importo": i} for i in range(40)]
    pages = render_report(spec, rows)
    assert len(pages) > 1
    for page in pages:
        assert any(op.text == "dBX" for op in page.ops)
        assert any("{PAGINA}" not in op.text and op.text.startswith("Pagina") for op in page.ops)
    assert any("di %d" % len(pages) in op.text for page in pages for op in page.ops)


def test_empty_rows_still_produce_a_page():
    pages = render_report(make_spec(), [])
    assert len(pages) == 1
    assert any(op.text == "Elenco fatture" for op in pages[0].ops)


def test_validation_rejects_missing_expression():
    spec = make_spec()
    spec.bands["detail"] = [Control("x", "expr", expr="")]
    try:
        ReportRenderer(spec, [])
    except ValueError as exc:
        assert "espressione" in str(exc).lower()
    else:  # pragma: no cover
        raise AssertionError("atteso errore di validazione")


def test_roundtrip_spec_json():
    spec = make_spec(group_by="cliente", orientation="landscape")
    clone = ReportSpec.from_dict(spec.to_dict())
    assert clone.to_dict() == spec.to_dict()
    assert clone.page_dimensions()[0] > clone.page_dimensions()[1]


def test_band_order_heights_and_visibility_roundtrip():
    spec = make_spec()
    spec.band_order = ["summary", "title", "page_header", "detail"]
    spec.band_heights = {"detail": 12.5, "summary": 9}
    spec.band_visible = {"page_footer": False}
    spec.sort_fields = [{"field": "cliente", "direction": "desc"}]
    spec.groups = [{"field": "cliente", "label": "Cliente"}]
    clone = ReportSpec.from_dict(spec.to_dict())
    assert clone.to_dict() == spec.to_dict()
    assert clone.effective_band_order()[0] == "summary"
    assert set(clone.effective_band_order()) == set(
        ["title", "page_header", "group_header", "detail", "group_footer", "page_footer", "summary"]
    )
    assert clone.band_height("detail") >= 12.5
    assert clone.is_visible("page_footer") is False
    assert clone.is_visible("detail") is True
    assert clone.effective_groups() == [{"field": "cliente", "label": "Cliente"}]


def test_legacy_json_without_new_keys_keeps_defaults():
    legacy = {
        "name": "vecchio",
        "title": "Vecchio",
        "table": "fatture",
        "bands": {"detail": [{"id": "c", "kind": "field", "expr": "cliente", "w": 80, "h": 6}]},
    }
    spec = ReportSpec.from_dict(legacy)
    assert spec.band_order == []
    assert spec.band_heights == {}
    assert spec.band_visible == {}
    assert spec.sort_fields == []
    assert spec.groups == []
    assert spec.effective_band_order() == list(BAND_NAMES)
    assert spec.effective_groups() == []


def test_sort_fields_change_row_order():
    spec = make_spec()
    spec.bands["detail"] = [Control("c", "field", x=0, y=0, w=100, h=6, expr="cliente")]
    spec.sort_fields = [{"field": "cliente", "direction": "desc"}]
    pages = render_report(spec, ROWS)
    detail_texts = [op.text for op in pages[0].ops if op.text in ("Alfa", "Beta")]
    assert detail_texts == ["Beta", "Alfa", "Alfa"]


def test_sort_fields_numeric_and_multiple_keys():
    spec = make_spec()
    spec.bands["detail"] = [Control("c", "field", x=0, y=0, w=100, h=6, expr="cliente")]
    spec.sort_fields = [
        {"field": "cliente", "direction": "asc"},
        {"field": "importo", "direction": "desc"},
    ]
    rows = [
        {"cliente": "Beta", "importo": 1},
        {"cliente": "Alfa", "importo": 10},
        {"cliente": "Alfa", "importo": 200},
    ]
    pages = render_report(spec, rows)
    assert [op.text for op in pages[0].ops if op.text in ("Alfa", "Beta")] == [
        "Alfa",
        "Alfa",
        "Beta",
    ]


def test_hidden_band_is_not_rendered():
    spec = make_spec()
    spec.band_visible = {"title": False, "page_footer": False}
    pages = render_report(spec, ROWS)
    all_text = texts(pages)
    assert "Elenco fatture" not in all_text
    assert not any("Pagina" in text for text in all_text)
    assert "Alfa" in all_text


def test_band_height_adds_vertical_space():
    spec = make_spec()
    spec.bands["detail"] = [Control("c", "field", x=0, y=0, w=100, h=6, expr="cliente")]
    spec.band_heights = {"detail": 30}
    rows = [{"cliente": f"Cliente {i}", "importo": i} for i in range(4)]
    pages = render_report(spec, rows)
    detail_ops = [op for op in pages[0].ops if op.text.startswith("Cliente")]
    assert len(detail_ops) == 4
    assert detail_ops[1].y - detail_ops[0].y >= 30


def test_multiple_groups_emit_headers_and_totals():
    spec = make_spec()
    spec.groups = [
        {"field": "cliente", "label": "Cliente"},
        {"field": "pagata", "label": "Pagata"},
    ]
    rows = [
        {"cliente": "Alfa", "importo": 100, "pagata": 1},
        {"cliente": "Alfa", "importo": 20, "pagata": 1},
        {"cliente": "Alfa", "importo": 5, "pagata": 0},
        {"cliente": "Beta", "importo": 7, "pagata": 1},
    ]
    pages = render_report(spec, rows)
    all_text = texts(pages)
    assert all_text.count("Gruppo") == 5
    assert any(t.startswith("Totale: 120") for t in all_text)
    assert any(t.startswith("Totale: 5") for t in all_text)


def test_underline_roundtrip():
    control = Control("x", "text", text="sottolineato", underline=True)
    clone = Control.from_dict(control.to_dict())
    assert clone.underline is True
    assert clone.to_dict() == control.to_dict()


def test_field_display_name_uses_table_and_field():
    assert field_display_name("fatture", "cliente") == "fatture->cliente"
    assert field_display_name("", "cliente") == "cliente"


def test_text_control_interpolates_bracketed_fields():
    spec = make_spec()
    spec.bands["group_header"] = [
        Control("gh", "text", x=0, y=0, w=170, h=6, text="Cliente: [cliente]")
    ]
    spec.groups = [{"field": "cliente", "label": "Cliente"}]
    pages = render_report(spec, ROWS)
    values = [op.text for op in pages[0].ops if op.text.startswith("Cliente: ")]
    assert values == ["Cliente: Alfa", "Cliente: Beta"]


def test_total_accepts_bare_field_name_and_counts_text_values():
    spec = make_spec()
    spec.bands["detail"] = [Control("c", "field", x=0, y=0, w=100, h=6, expr="cliente")]
    spec.bands["summary"] = [
        Control("n", "total", x=0, y=0, w=60, h=6, expr="cliente", func="count", label="Clienti: ")
    ]
    pages = render_report(spec, ROWS)
    all_text = texts(pages)
    assert "Clienti: 3" in all_text
