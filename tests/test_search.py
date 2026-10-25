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
