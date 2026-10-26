import pandas as pd

from pyafrobarometer import search

INDEX = pd.DataFrame(
    [
        {
            "name": "Q37A",
            "label": "Q37a. Trust president",
            "round": 9,
            "kind": "question",
            "family": "trust_president",
            "source_var": None,
            "value_labels": "{}",
        },
        {
            "name": "Q41A",
            "label": "Q41a. Trust president",
            "round": 8,
            "kind": "question",
            "family": "trust_president",
            "source_var": None,
            "value_labels": "{}",
        },
        {
            "name": "Q1",
            "label": "Q1. Age",
            "round": 9,
            "kind": "canonical",
            "family": None,
            "source_var": "Q1",
            "value_labels": "{}",
        },
    ]
)


def test_result_columns_include_concept():
    out = search.search_variables("trust", index=INDEX, fuzzy=False)
    assert "concept" in out.columns


def test_load_index_fills_missing_optional_columns(monkeypatch):
    old = pd.DataFrame([{"name": "Q37A", "label": "Trust", "round": 9}])
    monkeypatch.setattr(search, "_read_index_payload", lambda: old.to_dict("records"))
    out = search.load_index()
    assert "concept" in out.columns and "missing_codes" in out.columns


def test_substring_search_filters_rounds():
    out = search.search_variables("trust pres", rounds=[8], index=INDEX, fuzzy=False)
    assert out["name"].tolist() == ["Q41A"]


def test_limit_and_sorting():
    out = search.search_variables("trust", limit=1, index=INDEX, fuzzy=False)
    assert len(out) == 1 and out.iloc[0]["name"] in {"Q37A", "Q41A"}


def test_no_match_returns_empty_frame():
    out = search.search_variables("zzzz", index=INDEX, fuzzy=False)
    assert out.empty and "name" in out.columns


def test_shipped_index_is_populated():
    assert not search.load_index().empty


def test_search_finds_known_variable():
    out = search.search_variables("trust president", rounds=[9], fuzzy=False)
    assert "Q37A" in set(out["name"])


def test_search_matches_family_and_rejects_nonpositive_limit():
    out = search.search_variables("trust_president", limit=5, index=INDEX, fuzzy=False)
    assert "Q37A" in set(out["name"])
    assert search.search_variables("trust", limit=0, index=INDEX, fuzzy=False).empty
