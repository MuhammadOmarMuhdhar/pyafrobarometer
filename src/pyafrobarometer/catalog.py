"""Parse Afrobarometer index and survey-resource pages into catalog entries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Literal
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from pyafrobarometer.errors import CatalogError

SELECTORS: dict[str, str] = {
    "anchors": "a[href]",
}

MERGED_TITLE = re.compile(
    r"Merged Round (?P<round>\d+) data \(\d+ countries?\) \((?P<year>\d{4})(?:-\d{4})?\)"
)
FRENCH_TITLE = re.compile(r"S[ée]rie (?P<round>\d+)")
COUNTRY_TITLE = re.compile(
    r"^(?P<country>.+?) Round (?P<round>\d+) data \((?P<year>\d{4})\)$"
)
DATA_SUFFIXES = (".sav", ".sav.zip", ".dta")
ALLOWED_HOST = "www.afrobarometer.org"


@dataclass(frozen=True)
class CatalogEntry:
    kind: Literal["merged", "country"]
    round: int
    country: str | None
    year: int | None
    language: str
    data_url: str
    codebook_url: str | None
    page_url: str
    filename: str
    size_bytes: int | None


def _anchors(html: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    found: list[tuple[str, str]] = []
    for anchor in soup.select(SELECTORS["anchors"]):
        href = anchor.get("href")
        if not isinstance(href, str) or not href:
            continue
        found.append((anchor.get_text(" ", strip=True), href))
    return found


def _filename(url: str) -> str:
    return PurePosixPath(urlparse(url).path).name


def _is_data_file(href: str) -> bool:
    path = urlparse(href).path.lower()
    return path.endswith(DATA_SUFFIXES)


def _is_french(text: str, href: str) -> bool:
    lowered = text.lower()
    target = href.lower()
    return (
        bool(FRENCH_TITLE.search(text))
        or "données fusionnées" in lowered
        or "donnees fusionnees" in lowered
        or ".fr_" in target
        or "french" in target
    )


def parse_merged_index(html: str, base_url: str) -> list[CatalogEntry]:
    entries: list[CatalogEntry] = []
    for text, href in _anchors(html):
        url = urljoin(base_url, href)
        filename = _filename(url)
        match = MERGED_TITLE.search(text)
        if match:
            round_number = int(match.group("round"))
            year = int(match.group("year"))
        else:
            french = FRENCH_TITLE.search(text)
            years = re.findall(r"\((\d{4})\)", text)
            if french is None or not years:
                continue
            round_number = int(french.group("round"))
            year = int(years[-1])
        entries.append(
            CatalogEntry(
                kind="merged",
                round=round_number,
                country=None,
                year=year,
                language="fr" if _is_french(text, href) else "en",
                data_url=url,
                codebook_url=None,
                page_url=url,
                filename=filename,
                size_bytes=None,
            )
        )
    if not entries:
        raise CatalogError(
            f"No merged-dataset entries found at {base_url}; the page layout may have changed"
        )
    return entries


def parse_country_index(html: str, base_url: str) -> list[CatalogEntry]:
    entries: list[CatalogEntry] = []
    for text, href in _anchors(html):
        match = COUNTRY_TITLE.match(text.strip())
        if match is None:
            continue
        url = urljoin(base_url, href)
        entries.append(
            CatalogEntry(
                kind="country",
                round=int(match.group("round")),
                country=match.group("country").strip(),
                year=int(match.group("year")),
                language="fr" if _is_french(text, href) else "en",
                data_url=url,
                codebook_url=None,
                page_url=url,
                filename=_filename(url),
                size_bytes=None,
            )
        )
    return entries


def extract_resource_links(html: str, base_url: str) -> tuple[str | None, str | None]:
    data_url: str | None = None
    codebook_url: str | None = None
    for _, href in _anchors(html):
        url = urljoin(base_url, href)
        if data_url is None and _is_data_file(href):
            data_url = url
        elif codebook_url is None and urlparse(href).path.lower().endswith(".pdf"):
            codebook_url = url
        if data_url is not None and codebook_url is not None:
            break
    return data_url, codebook_url


def validate_catalog(entries: list[CatalogEntry] | tuple[CatalogEntry, ...]) -> None:
    if not entries:
        raise CatalogError("Catalog is empty")
    if not any(entry.kind == "merged" for entry in entries):
        raise CatalogError("Catalog contains no merged-dataset entry")
    for entry in entries:
        if not entry.filename:
            raise CatalogError(f"Catalog entry for round {entry.round} has no filename")
        for label, url in (
            ("data", entry.data_url),
            ("codebook", entry.codebook_url),
            ("page", entry.page_url),
        ):
            if url is None:
                continue
            parsed = urlparse(url)
            if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
                raise CatalogError(
                    f"Catalog entry for round {entry.round} has an invalid {label} URL: {url}"
                )
