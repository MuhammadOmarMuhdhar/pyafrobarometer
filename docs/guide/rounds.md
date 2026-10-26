# Rounds and the catalog

`rounds()` lists the merged rounds known to the package.

```python
import pyafrobarometer as ab

print(ab.rounds()[["round", "year", "countries", "language", "data_url"]])
```

## Columns

| Column | Meaning |
| --- | --- |
| `round` | Afrobarometer round number |
| `year` | Survey year recorded in the catalog |
| `countries` | Number of countries in the merged file, when known |
| `data_url` | Direct URL of the merged data file |
| `codebook_url` | Direct URL of the merged codebook, when known |
| `language` | `en` or `fr` |

Rows are sorted by round and language. Only merged entries appear; country-level
entries are used internally for `countries=` filtering.

## Refresh

The catalog index is cached for seven days. Force a refresh with:

```python
ab.rounds(refresh=True)
```

`refresh=True` ignores the cached index and fetches a fresh one. If the fetch
fails, the package warns and falls back to the cached index or the baked
manifest.

## Catalog sources

The catalog is resolved in this order:

1. A cached live index younger than the TTL.
2. A freshly fetched live index, unless `PYAFROBAROMETER_OFFLINE=1`.
3. The baked `manifest.json` shipped with the package.

The live index is written to the cache after a successful fetch. The baked
manifest is the guaranteed fallback, so the package works offline out of the box.

## Languages

Merged datasets exist in English and sometimes French:

```python
print(ab.rounds()[ab.rounds()["language"] == "fr"])
```

Pass `language="fr"` to [`load()`](../reference/functions.md#load) to load the
French merged file.

## Which rounds are supported?

The baked manifest and crosswalks cover merged rounds 1–10. A round number that
is not in the catalog raises `NotFoundError` when you try to load it.

## Catalog refresh in CI

A weekly GitHub Actions job refreshes `manifest.json` and `metadata_index.json`,
validates links and crosswalk coverage, and opens a pull request when they
change. This is a maintenance detail; runtime behavior is unchanged. See
[Development](../development.md).

## See also

- [Countries and coverage](countries.md)
- [Question families](families.md)
- [Caching, TTL, and offline mode](caching-and-offline.md)
- [`rounds()`](../reference/functions.md#rounds)
