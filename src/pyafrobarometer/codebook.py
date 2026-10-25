"""Codebook download and optional PDF text extraction."""

from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

from pyafrobarometer import cache, catalog, fetch
from pyafrobarometer.catalog import CatalogEntry
from pyafrobarometer.errors import CodebookError, DownloadError


def _resolve_url(entry: CatalogEntry) -> str:
    if entry.codebook_url:
        return entry.codebook_url
    if entry.page_url:
        html = fetch.fetch_text(entry.page_url)
        _, codebook_url = catalog.extract_resource_links(html, entry.page_url)
        if codebook_url:
            return codebook_url
    raise CodebookError(f"No codebook is available for round {entry.round}")


def get_codebook(entry: CatalogEntry) -> Path:
    url = _resolve_url(entry)
    filename = PurePosixPath(urlparse(url).path).name or "codebook.pdf"
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    dest = cache.cache_file(f"files/{digest}-{filename}")
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    try:
        fetch.download(url, dest, expected_types=("application/pdf",))
    except DownloadError as exc:
        raise CodebookError(f"Could not download codebook {url}: {exc}") from exc
    return dest


def extract_text(path: Path) -> str:
    try:
        import pypdf
    except ImportError as exc:
        raise CodebookError(
            "pypdf is required to extract codebook text; "
            "pip install pyafrobarometer[codebook]"
        ) from exc
    reader: Any = pypdf.PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)
