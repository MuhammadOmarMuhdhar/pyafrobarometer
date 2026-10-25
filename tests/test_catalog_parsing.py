import dataclasses
from pathlib import Path

import pytest

from pyafrobarometer import catalog
from pyafrobarometer.errors import CatalogError

BASE = "https://www.afrobarometer.org"


def read(name):
    return Path(f"tests/fixtures/{name}").read_text(encoding="utf-8")


def test_parse_merged_entries():
    entries = catalog.parse_merged_index(read("merged_data.html"), BASE)
    r10 = next(e for e in entries if e.round == 10 and e.language == "en")
    assert r10.kind == "merged" and r10.country is None and r10.year == 2025
    assert r10.data_url.endswith(".sav.zip") and r10.filename.endswith(".sav.zip")
    assert any(e.round == 10 and e.language == "fr" for e in entries)
    r9 = next(e for e in entries if e.round == 9)
    assert r9.data_url == BASE + "/survey-resource/merged-round-9-data-39-countries-2023/"
    assert r9.page_url == r9.data_url
    r5 = next(e for e in entries if e.round == 5)
    assert r5.year == 2011 and r5.data_url.endswith(
        "/merged-round-5-data-34-countries-2015/"
    )


def test_parse_country_entry():
    entries = catalog.parse_country_index(read("data_sets.html"), BASE)
    assert entries[0].kind == "country"
    assert entries[0].country == "South Africa" and entries[0].round == 10
    assert entries[0].year == 2026


def test_extract_resource_links():
    data, codebook = catalog.extract_resource_links(read("resource_page.html"), BASE)
    assert data.endswith("r7_merged_data_34ctry.release.sav")
    assert codebook.endswith(".pdf")


def test_empty_html_raises():
    with pytest.raises(CatalogError):
        catalog.parse_merged_index("<html></html>", BASE)


def test_validate_rejects_non_afrobarometer_urls():
    good = catalog.parse_merged_index(read("merged_data.html"), BASE)
    bad = dataclasses.replace(good[0], data_url="https://evil.test/x.sav")
    with pytest.raises(CatalogError):
        catalog.validate_catalog([bad])


def test_absolute_http_links_are_upgraded():
    html = (
        '<a href="http://www.afrobarometer.org/wp-content/uploads/x.sav">'
        "Merged Round 9 data (39 countries) (2023)</a>"
    )
    entries = catalog.parse_merged_index(html, BASE)
    assert entries[0].data_url.startswith("https://www.afrobarometer.org/")


def test_parse_live_country_card_text():
    html = (
        '<a href="/survey-resource/south-africa-round-10-data-2026/">'
        "Data set South Africa Round 10 data (2026) 25 Sep 2026 South Africa Round 10 data"
        "</a>"
    )
    entries = catalog.parse_country_index(html, BASE)
    assert entries and entries[0].country == "South Africa"
    assert entries[0].round == 10 and entries[0].year == 2026


def test_country_index_follows_pagination(monkeypatch):
    page1 = (
        '<li><a class="c-list-item__button" title="South Africa Round 10 data (2026)" '
        'href="/survey-resource/south-africa-round-10-data-2026/">Data set South Africa '
        "Round 10 data (2026)</a></li>"
        '<a href="/data/data-sets/?current-page=2#listing">2</a>'
    )
    page2 = (
        '<li><a class="c-list-item__button" title="Eswatini Round 10 data (2025)" '
        'href="/survey-resource/eswatini-round-10-data-2025/">Data set Eswatini '
        "Round 10 data (2025)</a></li>"
    )

    def fake_fetch(url, *args, **kwargs):
        return page2 if "current-page=2" in url else page1

    monkeypatch.setattr(catalog, "fetch_text", fake_fetch)
    entries = catalog._fetch_country_index()
    assert {entry.country for entry in entries} == {"South Africa", "Eswatini"}


def test_country_index_raises_when_cards_do_not_parse(monkeypatch):
    html = (
        '<a class="c-list-item__button" title="South Africa Round Ten data (2026)" '
        'href="/survey-resource/south-africa-round-10-data-2026/">Data set</a>'
    )
    monkeypatch.setattr(catalog, "fetch_text", lambda *a, **k: html)
    with pytest.raises(CatalogError):
        catalog._fetch_country_index()
