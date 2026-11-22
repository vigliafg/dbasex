from dbx.runtime.report_engine import (
    Control,
    ReportSpec,
    ReportRenderer,
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
