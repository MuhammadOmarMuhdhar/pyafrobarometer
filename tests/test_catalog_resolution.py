import dataclasses
import json
import time

import pytest

from pyafrobarometer import cache, catalog
from pyafrobarometer.errors import CatalogError

BASE = "https://www.afrobarometer.org"


def entries_html():
    return (
        '<a href="/wp-content/uploads/2026/10/AB_R10.Merge-Dataset_25Feb26.38ctry.release.sav.zip">'
        "Merged Round 10 data (38 countries) (2025)</a>"
    )


def resource_html():
    return (
        '<a href="/wp-content/uploads/2022/02/r7_merged_data_34ctry.release.sav">Data</a>'
        '<a href="/wp-content/uploads/2023/02/r7_merged.codebook_final_14dec20-1-1.pdf">Codebook</a>'
    )


def write_index(entries, fetched_at):
    cache.cache_file("index/catalog.json").write_text(
        json.dumps({"fetched_at": fetched_at, "entries": entries})
    )


def network_forbidden(*args, **kwargs):
    raise AssertionError("network")


def test_fresh_cache_skips_network(tmp_path, monkeypatch):
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path))
    entry = dataclasses.asdict(catalog.parse_merged_index(entries_html(), BASE)[0])
    write_index([entry], time.time())
    monkeypatch.setattr(catalog, "fetch_text", network_forbidden)
    assert catalog.resolve_catalog()[0].round == 10


def test_stale_cache_refreshes_and_saves(tmp_path, monkeypatch):
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path))
    write_index([], 0)
    html = (
        entries_html()
        + '<a href="/survey-resource/merged-round-9-data-39-countries-2023/">'
        "Merged Round 9 data (39 countries) (2023)</a>"
    )
    monkeypatch.setattr(catalog, "fetch_text", lambda *a, **k: html)
    out = catalog.resolve_catalog()
    assert {e.round for e in out} == {9, 10}
    assert cache.read_state()["index_source"] == "live"


def test_resource_page_is_followed(tmp_path, monkeypatch):
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path))
    write_index([], 0)
    merged = (
        '<a href="/survey-resource/merged-round-7-data-34-countries-2019/">'
        "Merged Round 7 data (34 countries) (2019)</a>"
    )

    def fake_fetch(url, *args, **kwargs):
        if "merged-data" in url:
            return merged
        if "data-sets" in url:
            return "<html></html>"
        if "survey-resource" in url:
            return resource_html()
        raise AssertionError(url)

    monkeypatch.setattr(catalog, "fetch_text", fake_fetch)
    entry = catalog.resolve_catalog()[0]
    assert entry.data_url.endswith("r7_merged_data_34ctry.release.sav")
    assert entry.codebook_url.endswith(".pdf")


def test_refresh_failure_uses_stale_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path))
    entry = dataclasses.asdict(catalog.parse_merged_index(entries_html(), BASE)[0])
    write_index([entry], 0)

    def fail(*args, **kwargs):
        raise CatalogError("down")

    monkeypatch.setattr(catalog, "fetch_text", fail)
    with pytest.warns(UserWarning):
        assert catalog.resolve_catalog()[0].round == 10


def test_no_cache_failure_uses_baked_manifest(tmp_path, monkeypatch):
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path))

    def fail(*args, **kwargs):
        raise CatalogError("down")

    monkeypatch.setattr(catalog, "fetch_text", fail)
    out = catalog.resolve_catalog()
    assert out and all(e.kind == "merged" for e in out)


def test_empty_parse_falls_back(tmp_path, monkeypatch):
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(catalog, "fetch_text", lambda *a, **k: "<html></html>")
    assert catalog.resolve_catalog()


def test_offline_uses_baked_manifest_without_network(tmp_path, monkeypatch):
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("PYAFROBAROMETER_OFFLINE", "1")
    monkeypatch.setattr(catalog, "fetch_text", network_forbidden)
    assert catalog.resolve_catalog()


def test_fresh_invalid_cache_falls_back(tmp_path, monkeypatch):
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path))
    write_index([], time.time())
    monkeypatch.setattr(catalog, "fetch_text", lambda *a, **k: "<html></html>")
    assert catalog.resolve_catalog()


def test_baked_manifest_covers_all_rounds():
    assert set(range(1, 11)) <= {e.round for e in catalog.load_baked_manifest()}


def test_fetch_catalog_attaches_codebooks(monkeypatch):
    merged = (
        '<a href="/wp-content/uploads/2026/10/AB_R10.Merge-Dataset_25Feb26.38ctry.release.sav.zip">'
        "Merged Round 10 data (38 countries) (2025)</a>"
        '<a href="/wp-content/uploads/2026/10/Merge_Round_10_Codebook_09.09.26.pdf">'
        "Merged Round 10 codebook (38 countries) (2025)</a>"
    )

    def fake_fetch(url, *args, **kwargs):
        if "merged-data" in url:
            return merged
        return "<html></html>"

    monkeypatch.setattr(catalog, "fetch_text", fake_fetch)
    entries = catalog._fetch_catalog()
    entry = next(item for item in entries if item.round == 10)
    assert entry.codebook_url.endswith("Merge_Round_10_Codebook_09.09.26.pdf")


def test_follow_resource_page_preserves_known_codebook(monkeypatch):
    from pyafrobarometer.catalog import CatalogEntry

    entry = CatalogEntry(
        kind="merged",
        round=5,
        country=None,
        year=2011,
        language="en",
        data_url="https://www.afrobarometer.org/survey-resource/merged-round-5-data/",
        codebook_url="https://www.afrobarometer.org/survey-resource/merged-round-5-codebook/",
        page_url="https://www.afrobarometer.org/survey-resource/merged-round-5-data/",
        filename="merged-round-5-data",
        size_bytes=None,
    )
    notes = (
        '<a href="https://www.afrobarometer.org/wp-content/uploads/2022/02/r5_data.sav">Data</a>'
        '<a href="https://www.afrobarometer.org/wp-content/uploads/2022/02/R5_notes.pdf">Notes</a>'
    )
    monkeypatch.setattr(catalog, "fetch_text", lambda *a, **k: notes)
    followed = catalog._follow_resource_page(entry)
    assert followed.codebook_url == entry.codebook_url
    assert followed.data_url.endswith("r5_data.sav")
