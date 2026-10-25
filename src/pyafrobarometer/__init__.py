"""Programmatic access to Afrobarometer survey data."""

from __future__ import annotations

from pyafrobarometer.errors import (
    AfrobarometerError,
    CacheError,
    CatalogError,
    CodebookError,
    DownloadError,
    HarmonizationError,
    NotFoundError,
)

__version__ = "0.1.0"

__all__ = [
    "AfrobarometerError",
    "CacheError",
    "CatalogError",
    "CodebookError",
    "DownloadError",
    "HarmonizationError",
    "NotFoundError",
    "__version__",
]
