"""Programmatic access to Afrobarometer survey data."""

from __future__ import annotations

__version__ = "0.1.0"

from pyafrobarometer.api import (
    cache_dir,
    citation,
    clear_cache,
    codebook,
    countries,
    families,
    load,
    panel,
    rounds,
    search_variables,
)
from pyafrobarometer.dataset import Dataset, Provenance
from pyafrobarometer.errors import (
    AfrobarometerError,
    CacheError,
    CatalogError,
    CodebookError,
    DownloadError,
    HarmonizationError,
    NotFoundError,
)

__all__ = [
    "AfrobarometerError",
    "CacheError",
    "CatalogError",
    "CodebookError",
    "Dataset",
    "DownloadError",
    "HarmonizationError",
    "NotFoundError",
    "Provenance",
    "__version__",
    "cache_dir",
    "citation",
    "clear_cache",
    "codebook",
    "countries",
    "families",
    "load",
    "panel",
    "rounds",
    "search_variables",
]
