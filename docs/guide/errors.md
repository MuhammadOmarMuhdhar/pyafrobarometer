# Errors

Every package exception derives from `AfrobarometerError`.

```text
AfrobarometerError
├── CatalogError
├── DownloadError
├── CacheError
├── NotFoundError
├── HarmonizationError
└── CodebookError
```

## Catching errors

```python
import pyafrobarometer as ab

try:
    ab.load(rounds=99)
except ab.NotFoundError as exc:
    print(f"No such round: {exc}")
```

Catch `ab.AfrobarometerError` to handle any package-specific failure.

## Common cases

| Error | Typical cause |
| --- | --- |
| `CatalogError` | Catalog or metadata index cannot be read or parsed |
| `DownloadError` | Non-HTTPS URL, wrong host, bad content type, failed download, offline mode |
| `CacheError` | Corrupt state, unwritable cache, lock timeout, bad zip contents |
| `NotFoundError` | Unknown round, empty country filter, missing codebook, CSV-only page |
| `HarmonizationError` | Unavailable concept with `strict=True`, unknown name, missing country column, panel variable missing |
| `CodebookError` | Missing PDF link, failed download, extraction without `pypdf` |

## Handling harmonization failures

```python
try:
    ds = ab.load(rounds=4, harmonize=True, variables=["trust_army"])
except ab.HarmonizationError as exc:
    print(f"Unavailable: {exc}")
```

Use `strict=False` when you want a warning and a `pd.NA` column instead:

```python
ds = ab.load(rounds=4, harmonize=True, variables=["trust_army"], strict=False)
```

## Handling offline failures

```python
import os

os.environ["PYAFROBAROMETER_OFFLINE"] = "1"

try:
    ds = ab.load(rounds=9)
except ab.DownloadError:
    print("Round 9 is not cached; run once online first")
```

## Inspecting an error message

Messages name the round, variable, concept, or URL involved. Print the exception
to see the details.

## See also

- [Errors reference](../reference/errors.md)
- [Caching, TTL, and offline mode](caching-and-offline.md)
- [Question harmonization](family-harmonization.md)
- [Local and remote sources](sources.md)
