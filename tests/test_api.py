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


def test_countries_falls_back_to_catalog_country_entries(monkeypatch):
    empty = pd.DataFrame(
        columns=[
            "name",
            "label",
            "round",
            "kind",
            "family",
            "source_var",
            "value_labels",
        ]
    )
    monkeypatch.setattr("pyafrobarometer.search.load_index", lambda: empty)
    monkeypatch.setattr(
        "pyafrobarometer.api.resolve_catalog",
        lambda **kw: [
            _entry(kind="country", country="Ghana", round=9),
            _entry(kind="country", country="Benin", round=9),
        ],
    )
    assert ab.countries(9) == ["Benin", "Ghana"]


def test_country_load_with_only_csv_raises(monkeypatch):
    entry = _entry(
        kind="country",
        country="South Africa",
        data_url="https://www.afrobarometer.org/survey-resource/south-africa-round-10-data-2026/",
        page_url="https://www.afrobarometer.org/survey-resource/south-africa-round-10-data-2026/",
        filename="south-africa-round-10-data-2026",
    )
    html = (
        '<a href="https://www.afrobarometer.org/wp-content/uploads/SAF_R10.csv">'
        "Download CSV</a>"
    )
    monkeypatch.setattr("pyafrobarometer.fetch.fetch_text", lambda *a, **k: html)
    with pytest.raises(ab.NotFoundError, match="CSV"):
        api._download_entry(entry)


def test_zip_extraction_uses_a_lock(monkeypatch, tmp_path):
    from pyafrobarometer.fetch import DownloadResult

    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path / "cache"))
    entry = _entry(
        data_url="https://www.afrobarometer.org/wp-content/uploads/r10.sav.zip",
        filename="r10.sav.zip",
    )
    locks = []
    original = api.cache.url_lock

    def spy(url, **kwargs):
        locks.append(url)
        return original(url, **kwargs)

    def fake_download(url, dest, **kwargs):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"PK")
        return DownloadResult(dest, "abc", 2, "application/zip")

    def fake_extract(archive, dest_dir):
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / "data.sav"
        path.write_bytes(b"x")
        return path

    monkeypatch.setattr(api.cache, "url_lock", spy)
    monkeypatch.setattr(api.fetch, "download", fake_download)
    monkeypatch.setattr(api.io, "safe_extract_sav", fake_extract)
    path = api._download_entry(entry)
    assert path.name == "data.sav"
    assert any(url.endswith("#extract") for url in locks)


def test_rounds_populates_country_count(monkeypatch):
    monkeypatch.setattr(
        "pyafrobarometer.api.resolve_catalog",
        lambda **kw: [_entry(countries_count=38)],
    )
    assert ab.rounds()["countries"].iloc[0] == 38


def test_citation_includes_years(monkeypatch):
    monkeypatch.setattr(
        "pyafrobarometer.api.resolve_catalog",
        lambda **kw: [_entry(round=9, year=2023)],
    )
    assert "2023" in ab.citation(rounds=[9])


def test_load_uses_usecols(monkeypatch, tmp_path):
    p = tmp_path / "r9.sav"
    write_sav(p)
    captured = {}
    original = api.io.read_frame

    def spy(path, **kwargs):
        captured["usecols"] = kwargs.get("usecols")
        return original(path, **kwargs)

    monkeypatch.setattr(api.io, "read_frame", spy)
    ab.load(rounds=9, source=p, variables=["Q37A"])
    assert captured["usecols"] is not None
    assert "Q37A" in captured["usecols"] and "COUNTRY" in captured["usecols"]
    assert "Q100" not in captured["usecols"]


def test_metadata_is_cached_by_sha(monkeypatch, tmp_path):
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path / "cache"))
    p = tmp_path / "r9.sav"
    write_sav(p)
    calls = []
    original = api.io.read_metadata

    def spy(path):
        calls.append(path)
        return original(path)

    monkeypatch.setattr(api.io, "read_metadata", spy)
    ab.load(rounds=9, source=p)
    ab.load(rounds=9, source=p)
    assert len(calls) == 1


def test_country_alias_matches(monkeypatch, tmp_path):
    p = tmp_path / "r9.sav"
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
        str(p),
        column_labels=list(df.columns),
        variable_value_labels={"COUNTRY": {3: "Côte d'Ivoire", 14: "Ghana"}},
    )
    ds = ab.load(rounds=9, countries=["Cote d Ivoire"], source=p, harmonize=True)
    assert ds.to_pandas()["country"].tolist() == ["Côte d'Ivoire"]


def test_country_filter_uses_merged_entry(monkeypatch, tmp_path):
    p = tmp_path / "r9.sav"
    write_sav(p)
    merged = _entry()
    country = _entry(kind="country", country="Ghana")
    monkeypatch.setattr("pyafrobarometer.api.resolve_catalog", lambda **kw: [merged, country])
    seen = []

    def fake_download(entry):
        seen.append(entry)
        return p

    monkeypatch.setattr("pyafrobarometer.api._download_entry", fake_download)
    ds = ab.load(rounds=9, countries=["Ghana"], harmonize=True)
    assert seen and seen[0].kind == "merged"
    assert ds.countries == ["Ghana"]
