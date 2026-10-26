# Local and remote sources

Use `source=` to load a file you already have or a URL you want to fetch
directly.

## Local files

```python
import pyafrobarometer as ab

ds = ab.load(
    source="AB_R9_merged.sav",
    rounds=9,
    harmonize=True,
    variables=["trust_president"],
)
```

`rounds=` is required when harmonizing a local source, because the crosswalk is
round-specific. Without harmonization, a local source can be loaded without a
round number, but the result has no `year`.

## Remote URLs

```python
ds = ab.load(
    source="https://www.afrobarometer.org/wp-content/uploads/.../AB_R9_merged.sav",
    rounds=9,
)
```

Remote URLs must use HTTPS and the host `www.afrobarometer.org`. Other hosts and
plain HTTP are rejected with `DownloadError`.

## Multiple sources

`source` accepts a list. If `rounds` is also a list, entries are paired by
position:

```python
ds = ab.load(
    source=["ghana_r9.sav", "kenya_r9.sav"],
    rounds=[9, 9],
    harmonize=True,
)
```

If `rounds` contains a single round, it applies to every source.

## Supported formats

- `.sav` — SPSS
- `.sav.zip` — zipped SPSS
- `.dta` — Stata

CSV is not supported.

## Caching remote files

Remote downloads go through the same cache as catalog downloads. Reusing the
same URL reuses the cached file. See
[Caching, TTL, and offline mode](caching-and-offline.md).

## Errors

| Situation | Error |
| --- | --- |
| Non-HTTPS URL | `DownloadError` |
| Host other than `www.afrobarometer.org` | `DownloadError` |
| Offline mode with a remote URL | `DownloadError` |
| Harmonization without `rounds=` | `HarmonizationError` |
| Unreadable or unsupported file | `CacheError` or a pandas/pyreadstat error |

## See also

- [Loading a round](loading.md)
- [Caching, TTL, and offline mode](caching-and-offline.md)
- [`load()`](../reference/functions.md#load)
