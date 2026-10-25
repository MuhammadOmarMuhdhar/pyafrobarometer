"""Parse Afrobarometer index and survey-resource pages into catalog entries."""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
import warnings
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path, PurePosixPath
from typing import Any, Literal
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from pyafrobarometer import cache
from pyafrobarometer.errors import CatalogError, DownloadError
from pyafrobarometer.fetch import fetch_text

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


def _resolve_url(base_url: str, href: str) -> str:
    url = urljoin(base_url, href)
    parsed = urlparse(url)
    if parsed.scheme == "http" and parsed.hostname in (
        "afrobarometer.org",
        "www.afrobarometer.org",
    ):
        url = parsed._replace(scheme="https", netloc="www.afrobarometer.org").geturl()
    return url


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
        url = _resolve_url(base_url, href)
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
        url = _resolve_url(base_url, href)
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
        url = _resolve_url(base_url, href)
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


MANIFEST_PATH = Path(__file__).with_name("manifest.json")
MERGED_INDEX_URL = "https://www.afrobarometer.org/data/merged-data/"
DATASETS_INDEX_URL = "https://www.afrobarometer.org/data/data-sets/"
INDEX_PATH = "index/catalog.json"


def _entries_from_payload(payload: Mapping[str, Any]) -> list[CatalogEntry]:
    raw = payload.get("entries")
    if not isinstance(raw, list):
        raise CatalogError("Catalog payload has no entries list")
    entries: list[CatalogEntry] = []
    for item in raw:
        if not isinstance(item, dict):
            raise CatalogError("Catalog entry is not an object")
        try:
            entries.append(CatalogEntry(**item))
        except TypeError as exc:
            raise CatalogError(f"Malformed catalog entry: {exc}") from exc
    return entries


def load_baked_manifest() -> list[CatalogEntry]:
    try:
        payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogError(f"Could not read baked manifest at {MANIFEST_PATH}: {exc}") from exc
    if not isinstance(payload, dict):
        raise CatalogError(f"Baked manifest at {MANIFEST_PATH} is not a JSON object")
    entries = _entries_from_payload(payload)
    validate_catalog(entries)
    return entries


def _read_cached_index() -> tuple[float, list[CatalogEntry]] | None:
    path = cache.cache_file(INDEX_PATH)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    try:
        fetched_at = float(payload["fetched_at"])
    except (KeyError, TypeError, ValueError):
        return None
    try:
        entries = _entries_from_payload(payload)
    except CatalogError:
        return None
    return fetched_at, entries


def _write_cached_index(entries: Sequence[CatalogEntry], fetched_at: float) -> None:
    path = cache.cache_file(INDEX_PATH)
    payload = {
        "fetched_at": fetched_at,
        "entries": [asdict(entry) for entry in entries],
    }
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".catalog-", suffix=".json")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp, path)
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        raise CatalogError(f"Could not write catalog cache at {path}: {exc}") from exc


def _follow_resource_page(entry: CatalogEntry) -> CatalogEntry:
    if _is_data_file(entry.data_url):
        return entry
    html = fetch_text(entry.page_url)
    data_url, codebook_url = extract_resource_links(html, entry.page_url)
    if data_url is None:
        return entry
    return replace(
        entry,
        data_url=data_url,
        codebook_url=codebook_url or entry.codebook_url,
        filename=_filename(data_url),
    )


def _fetch_catalog() -> list[CatalogEntry]:
    merged_html = fetch_text(MERGED_INDEX_URL)
    country_html = fetch_text(DATASETS_INDEX_URL)
    entries = parse_merged_index(merged_html, MERGED_INDEX_URL)
    entries.extend(parse_country_index(country_html, DATASETS_INDEX_URL))
    entries = [
        _follow_resource_page(entry) if entry.kind == "merged" else entry
        for entry in entries
    ]
    validate_catalog(entries)
    return entries


def resolve_catalog(*, refresh: bool = False) -> list[CatalogEntry]:
    offline = os.environ.get("PYAFROBAROMETER_OFFLINE") == "1"
    cached = _read_cached_index()
    if cached is not None:
        fetched_at, cached_entries = cached
        if not refresh and cache.is_fresh(fetched_at):
            return cached_entries

    if not offline:
        try:
            entries = _fetch_catalog()
        except (CatalogError, DownloadError, OSError, TypeError, ValueError) as exc:
            if cached is not None:
                warnings.warn(
                    f"Could not refresh the Afrobarometer catalog ({exc}); using cached index",
                    UserWarning,
                    stacklevel=2,
                )
                return cached[1]
            warnings.warn(
                f"Could not refresh the Afrobarometer catalog ({exc}); using baked manifest",
                UserWarning,
                stacklevel=2,
            )
            return load_baked_manifest()
        _write_cached_index(entries, time.time())
        state = cache.read_state()
        state["index_source"] = "live"
        cache.write_state(state)
        return entries

    if cached is not None:
        return cached[1]
    return load_baked_manifest()
