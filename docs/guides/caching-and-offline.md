# Caching and offline use

Downloads and catalog indexes are cached locally so repeated analyses do not
re-fetch the same files.

## Cache location

```python
import pyafrobarometer as ab

print(ab.cache_dir())
```

The default is the platform user cache directory for `pyafrobarometer`
(for example `~/.cache/pyafrobarometer` on Linux or
`~/Library/Caches/pyafrobarometer` on macOS). Override it with an environment
variable:

```bash
export PYAFROBAROMETER_CACHE_DIR=/data/pyafrobarometer-cache
```

The cache contains:

| Directory | Contents |
| --- | --- |
| `files/` | Downloaded data archives, extracted SAV files, and codebook PDFs |
| `metadata/` | Parsed per-round metadata keyed by file hash |
| `index/` | The cached catalog index |
| `locks/` | Per-URL and state locks |
| `tmp/` | Temporary files |

## Catalog TTL

The catalog index is cached for seven days:

```python
ab.rounds(refresh=True)     # ignore the cached index and fetch a fresh one
```

Change the TTL in seconds with `PYAFROBAROMETER_INDEX_TTL`:

```bash
export PYAFROBAROMETER_INDEX_TTL=86400   # one day
```

If a refresh fails, the package warns and uses the cached index or the baked
manifest. A failed refresh never blocks a load.

## Offline mode

Set `PYAFROBAROMETER_OFFLINE=1` to forbid all network access:

```bash
export PYAFROBAROMETER_OFFLINE=1
```

In offline mode:

- The cached index is used if present; otherwise the baked manifest is used.
- Data downloads raise `DownloadError`.
- Already-cached data and codebooks keep working.

This is useful for reproducible analysis on a machine with no network.

## Data files

Data files have no TTL. They are reused by URL and content hash, so a file is
downloaded once and then served from the cache. Deleting the cache forces a
fresh download.

## Clearing the cache

```python
ab.clear_cache()          # remove everything
ab.clear_cache(round=9)   # remove only Round 9 files and metadata
```

`clear_cache()` with no argument removes the cache layout directories and the
state file. With a round number, it removes the files recorded for that round
and the round's cached metadata.

## Concurrency

Downloads and state updates use per-URL and state locks, so parallel processes do
not corrupt the cache. Locks left by a dead process are detected and recovered
automatically. A process that waits too long for a lock raises `CacheError`.

## See also

- [`cache_dir()`](../reference/functions.md#cache_dir)
- [`clear_cache()`](../reference/functions.md#clear_cache)
- [Discovery](discovery.md)
