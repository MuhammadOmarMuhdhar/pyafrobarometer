import pandas as pd
import pyreadstat
import pytest

import pyafrobarometer as ab
from pyafrobarometer import api, catalog


def write_sav(path):
    df = pd.DataFrame(
        {
            "COUNTRY": [3, 14],
            "RESPNO": ["A", "B"],
            "REGION": [1, 2],
            "URBRUR": [1, 2],
            "Q1": [30, 40],
            "Q100": [1, 2],
            "Q94": [3, 4],
            "DATEINTR": [1, 2],
            "Q37A": [0, 9],
            "withinwt_ea": [1.0, 2.0],
        }
    )
    pyreadstat.write_sav(
        df,
        str(path),
        column_labels=list(df.columns),
        variable_value_labels={
            "COUNTRY": {3: "Benin", 14: "Ghana"},
            "Q37A": {
                0: "Not at all",
                3: "A lot",
                8: "Refused",
                9: "Don't know",
                -1: "Missing",
            },
        },
    )


def _entry(**kw):
    base = {
        "kind": "merged",
        "round": 9,
        "country": None,
        "year": 2023,
        "language": "en",
        "data_url": "https://www.afrobarometer.org/wp-content/uploads/x.sav",
        "codebook_url": None,
        "page_url": "https://www.afrobarometer.org/p",
        "filename": "x.sav",
        "size_bytes": None,
    }
    base.update(kw)
    return catalog.CatalogEntry(**base)


def test_load_from_local_source_end_to_end(tmp_path):
    p = tmp_path / "r9.sav"
    write_sav(p)
    ds = ab.load(rounds=9, source=p, harmonize=True)
    assert ds.rounds == [9] and ds.countries == ["Benin", "Ghana"]
    out = ds.to_pandas(normalize_missing=True)
    assert out["country"].tolist() == ["Benin", "Ghana"]
    values = out["trust_president"].tolist()
    assert values[0] == 0 and pd.isna(values[1])
    assert "Q37A" in out.columns


def test_load_filters_countries(tmp_path):
    p = tmp_path / "r9.sav"
    write_sav(p)
    ds = ab.load(rounds=9, countries=["Ghana"], source=p, harmonize=True)
    assert ds.to_pandas()["country"].tolist() == ["Ghana"]


def test_variables_include_harmonized_rows(tmp_path):
    p = tmp_path / "r9.sav"
    write_sav(p)
    ds = ab.load(rounds=9, source=p, harmonize=True)
    variables = ds.variables()
    row = variables.loc[variables["name"] == "trust_president"].iloc[0]
    assert row["source_var"] == "Q37A"


def test_citation_contains_required_text(tmp_path):
    p = tmp_path / "r9.sav"
    write_sav(p)
    ds = ab.load(rounds=9, source=p)
    assert ds.citation().startswith("Afrobarometer Data,")


def test_source_without_rounds_requires_round_for_harmonize(tmp_path):
    p = tmp_path / "r9.sav"
    write_sav(p)
    with pytest.raises(ab.HarmonizationError):
        ab.load(source=p, harmonize=True, rounds=None)


def test_missing_source_variable_strict_and_non_strict(tmp_path):
    p = tmp_path / "r9.sav"
    write_sav(p)
    with pytest.raises(ab.HarmonizationError):
        ab.load(rounds=9, source=p, variables=["NOPE"])
    with pytest.warns(UserWarning):
        ds = ab.load(rounds=9, source=p, variables=["NOPE"], strict=False)
    assert "NOPE" not in ds.to_pandas().columns


def test_select_entries_prefers_country_files():
    merged = _entry()
    ghana = _entry(kind="country", country="Ghana")
    benin = _entry(kind="country", country="Benin")
    assert api.select_entries([merged, ghana, benin], rounds=[9], countries=["Ghana"]) == [
        ghana
    ]
    assert api.select_entries([merged, ghana, benin], rounds=[9]) == [merged]


def test_rounds_and_countries_from_catalog(monkeypatch, tmp_path):
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr("pyafrobarometer.api.resolve_catalog", lambda **kw: [_entry()])
    index = pd.DataFrame(
        [
            {
                "name": "COUNTRY",
                "label": "Country",
                "round": 9,
                "kind": "canonical",
                "family": None,
                "source_var": "COUNTRY",
                "value_labels": '{"3": "Benin"}',
            }
        ]
    )
    monkeypatch.setattr("pyafrobarometer.search.load_index", lambda: index)
    assert list(ab.rounds().columns) == [
        "round",
        "year",
        "countries",
        "data_url",
        "codebook_url",
        "language",
    ]
    assert ab.countries(9) == ["Benin"]


def test_families_lists_sparse_availability():
    out = ab.families()
    row = out.loc[out["family"] == "social_media_news"].iloc[0]
    assert row["rounds"] == [6, 7, 8, 9, 10]
    assert "Q12E" in row["variables"].values()
    army = out.loc[out["family"] == "trust_army"].iloc[0]
    assert army["rounds"] == [1, 2, 3, 5, 6, 7, 8, 9, 10]


def test_second_load_reuses_cached_download(monkeypatch, tmp_path):
    from pyafrobarometer.fetch import DownloadResult

    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path / "cache"))
    p = tmp_path / "r9.sav"
    write_sav(p)
    e = _entry(
        data_url="https://www.afrobarometer.org/wp-content/uploads/r9.sav",
        filename="r9.sav",
    )
    monkeypatch.setattr("pyafrobarometer.api.resolve_catalog", lambda **kw: [e])
    calls = []

    def fake_download(url, dest, **kwargs):
        calls.append(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(p.read_bytes())
        return DownloadResult(dest, "abc", dest.stat().st_size, "application/x-spss-sav")

    monkeypatch.setattr("pyafrobarometer.fetch.download", fake_download)
    ab.load(rounds=9, harmonize=True)
    ab.load(rounds=9, harmonize=True)
    assert calls == [e.data_url]


def test_filtered_load_reports_filtered_countries(tmp_path):
    p = tmp_path / "r9.sav"
    write_sav(p)
    ds = ab.load(rounds=9, countries=["Ghana"], source=p, harmonize=True)
    assert ds.countries == ["Ghana"]


def test_unknown_country_raises(tmp_path):
    p = tmp_path / "r9.sav"
    write_sav(p)
    with pytest.raises(ab.NotFoundError):
        ab.load(rounds=9, countries=["Atlantis"], source=p, harmonize=True)
