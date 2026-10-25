"""Exception hierarchy for pyafrobarometer."""

from __future__ import annotations

__all__ = [
    "AfrobarometerError",
    "CacheError",
    "CatalogError",
    "CodebookError",
    "DownloadError",
    "HarmonizationError",
    "NotFoundError",
]


class AfrobarometerError(Exception):
    """Base class for every error raised by pyafrobarometer."""


class CatalogError(AfrobarometerError):
    """The Afrobarometer catalog could not be fetched or parsed."""


class DownloadError(AfrobarometerError):
    """A remote artifact could not be downloaded or validated."""


class CacheError(AfrobarometerError):
    """The local cache could not be read, written, or locked."""


class NotFoundError(AfrobarometerError):
    """The requested round, country, variable, or artifact is unavailable."""


class HarmonizationError(AfrobarometerError):
    """A canonical variable or question family cannot be harmonized."""


class CodebookError(AfrobarometerError):
    """A codebook could not be downloaded or read."""
