# Errors

Every exception raised by the package derives from `AfrobarometerError`.

```
AfrobarometerError
├── CatalogError
├── DownloadError
├── CacheError
├── NotFoundError
├── HarmonizationError
└── CodebookError
```

All of them are exported from the top-level package:

```python
import pyafrobarometer as ab

try:
    ab.load(rounds=99)
except ab.NotFoundError as exc:
    print(f"No such round: {exc}")
```

Catch `ab.AfrobarometerError` to handle any package-specific failure.

## AfrobarometerError

Base class for every error raised by pyafrobarometer. Catch this when you want a
single handler for all package errors.

## CatalogError

The Afrobarometer catalog could not be fetched or parsed, the baked manifest
could not be read, or the metadata index is invalid.

## DownloadError

A remote artifact could not be downloaded or validated. Causes include a
non-HTTPS URL, a host other than `www.afrobarometer.org`, an unexpected content
type, a retryable HTTP status that persisted, or an empty response. In offline
mode, any attempted download raises `DownloadError`.

## CacheError

The local cache could not be read, written, or locked. This includes corrupt
state files, unwritable cache directories, and lock timeouts. A zip archive that
does not contain exactly one SAV file also raises `CacheError`.

## NotFoundError

The requested round, country, variable, or artifact is unavailable. Examples:

- A round number that is not in the catalog.
- A country filter that matches no rows.
- A codebook that does not exist for the round.
- A country page that only offers CSV data.

## HarmonizationError

A canonical variable or question concept cannot be harmonized. Examples:

- A requested concept is unavailable in the round and `strict=True`.
- A requested name is unknown and `strict=True`.
- Harmonization is requested for a local source without `rounds=`.
- Country filtering is requested but no country column exists.
- A panel variable is missing from one or more rounds.

## CodebookError

A codebook could not be downloaded or read. This includes a missing PDF link,
a failed download, and text extraction without the `[codebook]` extra.

## See also

- [Functions](functions.md)
- [`Dataset`](dataset.md)
- [Troubleshooting patterns](../guide/loading.md)
