"""Test della ricerca guidata e della sostituzione (0.6)."""

from __future__ import annotations

import pytest

from dbx.core import types as T
from dbx.core.db import Database
from dbx.core.ddl import apply_migration
from dbx.core.metadata import Field, Table
from dbx.core.search import (
    SearchCriterion,
    SearchError,
    SearchRequest,
    build_where,
    count_matches,
    delete_find,
    replace_in_rowset,
    replace_text,
    save_find,
    saved_finds,
    validate_request,
)
from dbx.runtime.rowset import Rowset


@pytest.fixture()
def rowset():
    db = Database(":memory:")
    table = Table(
        name="contatti",
        fields=[
            Field("nome", T.TEXT, required=True),
            Field("email", T.TEXT),
            Field("anni", T.INTEGER),
            Field("nato", T.DATE),
            Field("note", T.MEMO),
        ],
    )
    apply_migration(db.con, table, None)
    data = Rowset(db, table)
    data.insert({"nome": "Ada Lovelace", "email": "ada@example.it", "anni": 36, "nato": "1815-12-10", "note": "Matematica"})
    data.insert({"nome": "Bob Stone", "email": "bob@example.it", "anni": 40, "nato": "1980-01-02", "note": "Vendite"})
    data.insert({"nome": "Carla Bianchi", "email": "", "anni": 28, "nato": "1996-05-06", "note": ""})
    data.open()
    return data


def _where(rowset, request):
    where, params = build_where(rowset.table, request)
    return rowset, where, params


def test_contains_is_case_insensitive_and_multi_field(rowset):
    request = SearchRequest([SearchCriterion("nome", "contains", "ada")])
    where, params = build_where(rowset.table, request)
    assert "LIKE" in where
    matched = rowset.open(where=where, params=params)
    assert matched.count() == 1
    assert matched.current["nome"] == "Ada Lovelace"


def test_and_or_and_omit(rowset):
    request = SearchRequest(
        [
            SearchCriterion("anni", "ge", "30"),
            SearchCriterion("nome", "contains", "ada"),
        ],
        match="all",
    )
    where, params = build_where(rowset.table, request)
    assert rowset.open(where=where, params=params).count() == 1

    request.match = "any"
    where, params = build_where(rowset.table, request)
    assert rowset.open(where=where, params=params).count() == 2

    omitted = SearchRequest(
        [
            SearchCriterion("anni", "ge", "30"),
            SearchCriterion("nome", "contains", "ada", omit=True),
        ]
    )
    where, params = build_where(rowset.table, omitted)
    rows = rowset.open(where=where, params=params).rows()
    assert [row["nome"] for row in rows] == ["Bob Stone"]


def test_blank_notblank_and_dates(rowset):
    blank = SearchRequest([SearchCriterion("email", "blank")])
    where, params = build_where(rowset.table, blank)
    assert rowset.open(where=where, params=params).count() == 1

    nulls = SearchRequest([SearchCriterion("email", "notblank")])
    where, params = build_where(rowset.table, nulls)
    assert rowset.open(where=where, params=params).count() == 2

    dates = SearchRequest([SearchCriterion("nato", "ge", "1990-01-01")])
    where, params = build_where(rowset.table, dates)
    assert rowset.open(where=where, params=params).count() == 1


def test_like_wildcards_are_literal(rowset):
    request = SearchRequest([SearchCriterion("note", "contains", "100%")])
    where, params = build_where(rowset.table, request)
    assert rowset.open(where=where, params=params).count() == 0
    where, params = build_where(
        rowset.table, SearchRequest([SearchCriterion("note", "contains", "Vendite")])
    )
    assert count_matches(rowset.db, rowset.table, SearchRequest([SearchCriterion("note", "contains", "Vendite")])) == 1


def test_invalid_field_and_number_are_reported(rowset):
    bad = SearchRequest([SearchCriterion("inesistente", "eq", "x")])
    assert validate_request(rowset.table, bad)
    with pytest.raises(SearchError):
        build_where(rowset.table, bad)
    with pytest.raises(SearchError):
        build_where(rowset.table, SearchRequest([SearchCriterion("anni", "gt", "abc")]))


def test_empty_request_is_inactive(rowset):
    request = SearchRequest([SearchCriterion("", "contains", "")])
    assert request.is_empty()
    assert not request
    assert build_where(rowset.table, request) == ("", ())


def test_request_round_trip():
    request = SearchRequest(
        [SearchCriterion("nome", "starts", "A", omit=True)], match="any"
    )
    restored = SearchRequest.from_dict(request.to_dict())
    assert restored.match == "any"
    assert restored.criteria[0].field == "nome"
    assert restored.criteria[0].omit is True


def test_replace_text_case_and_whole_word():
    assert replace_text("Ada ada ADAm", "ada", "Eva") == "Eva Eva Evam"
    assert replace_text("Ada ada", "ada", "Eva", match_case=True) == "Ada Eva"
    assert replace_text("Ada Adam", "Ada", "Eva", whole_word=True) == "Eva Adam"
    assert replace_text(None, "x", "y") == ""


def test_replace_in_rowset_updates_matching_rows(rowset):
    changed = replace_in_rowset(rowset, "example.it", "example.org")
    assert changed == 2
    rowset.refresh()
    assert all(
        row["email"].endswith("example.org")
        for row in rowset.rows()
        if row["email"]
    )
    assert rowset.count() == 3


def test_saved_finds_on_project(demo_project):
    request = SearchRequest([SearchCriterion("citta", "eq", "Roma")])
    save_find(demo_project, "clienti", "Roma", request)
    stored = saved_finds(demo_project, "clienti")
    assert "Roma" in stored
    assert stored["Roma"]["criteria"][0]["value"] == "Roma"
    assert delete_find(demo_project, "clienti", "Roma") is True
    assert "Roma" not in saved_finds(demo_project, "clienti")
