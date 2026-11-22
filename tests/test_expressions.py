import datetime

import pytest

from dbx.core.expressions import Expression, ExpressionError, evaluate, rewrite


def test_field_and_literal_arithmetic():
    expr = Expression("[prezzo] * [quantita]")
    assert expr.evaluate({"prezzo": 2.5, "quantita": 4}) == 10.0
    assert expr.fields == {"prezzo", "quantita"}


def test_qualified_field_prefers_table():
    expr = Expression("[clienti.nome] + ' ' + [clienti.cognome]")
    record = {"clienti.nome": "Ada", "clienti.cognome": "Lovelace", "nome": "sbagliato"}
    assert expr.evaluate(record, table="clienti") == "Ada Lovelace"


def test_dbase_boolean_and_comparison_operators():
    expr = Expression("([eta] >= 18) .AND. ([eta] < 65) .AND. .NOT. [bloccato]")
    assert expr.evaluate({"eta": 30, "bloccato": False}) is True
    assert expr.evaluate({"eta": 70, "bloccato": False}) is False
    assert Expression("[stato] <> 'chiuso'").evaluate({"stato": "aperto"}) is True


def test_iif_and_string_functions():
    expr = Expression("IIF([sesso] = 'F', 'Sig.ra ' + UPPER([nome]), 'Sig. ' + UPPER([nome]))")
    assert expr.evaluate({"sesso": "F", "nome": "ada"}) == "Sig.ra ADA"
    assert Expression("SUBSTR([codice], 2, 3)").evaluate({"codice": "XABCZ"}) == "ABC"
    assert Expression("LEN(ALLTRIM([t]))").evaluate({"t": "  abc  "}) == 3


def test_date_functions():
    expr = Expression("YEAR([data])")
    assert expr.evaluate({"data": "2024-03-05"}) == 2024
    assert Expression("DATEADD([data], 10)").evaluate({"data": "2024-03-05"}) == datetime.date(2024, 3, 15)
    assert Expression("TODAY() <= TODAY()").evaluate({}) is True


def test_variables():
    expr = Expression(":aliquota * [imponibile]")
    assert expr.evaluate({"imponibile": 100}, {"aliquota": 0.22}) == pytest.approx(22)
    with pytest.raises(ExpressionError):
        Expression(":mancante + 1").evaluate({})


def test_missing_field_yields_none_instead_of_crashing():
    assert Expression("[non_esiste]").evaluate({}) is None


def test_rejects_arbitrary_python():
    with pytest.raises(ExpressionError):
        Expression("__import__('os').system('ls')")
    with pytest.raises(ExpressionError):
        Expression("[x].__class__")


def test_unterminated_field_is_reported():
    with pytest.raises(ExpressionError):
        Expression("[campo")


def test_rewrite_preserves_string_literals():
    python_source, fields, variables = rewrite("'a [b] :c' + [x]")
    assert fields == {"x"}
    assert variables == set()
    assert "'a [b] :c'" in python_source


def test_evaluate_helper():
    assert evaluate("1 + 2") == 3
    assert evaluate("IIF(EMPTY([v]), 'vuoto', 'pieno')", {"v": ""}) == "vuoto"


def test_ampercent_is_concatenation():
    assert Expression("[a] & '-' & [b]").evaluate({"a": "x", "b": "y"}) == "x-y"


def test_division_by_zero_is_reported():
    with pytest.raises(ExpressionError):
        Expression("1 / 0").evaluate({})
