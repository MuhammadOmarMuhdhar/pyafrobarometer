# Functions

All functions are available from the top-level package:

```python
import pyafrobarometer as ab
```

## rounds

```python
ab.rounds(refresh: bool = False) -> pandas.DataFrame
```

Return the merged rounds in the catalog.

**Parameters**

- `refresh` — ignore the cached catalog index and fetch a fresh one.

**Returns** a DataFrame with the columns `round`, `year`, `countries`,
`data_url`, `codebook_url`, and `language`, sorted by round and language.

**Raises** `CatalogError` if neither the catalog nor the baked manifest can be
read.

```python
print(ab.rounds()[["round", "year", "language"]])
```

## countries

```python
ab.countries(round: int | None = None, *, refresh: bool = False) -> list[str]
```

Return country names.

**Parameters**

- `round` — restrict to countries present in this round.
- `refresh` — ignore the cached catalog index when falling back to the catalog.

**Returns** a list of country names. Names are read from value labels in the
shipped metadata index; the catalog's country entries are used as a fallback.

**Raises** `NotFoundError` if no names can be determined.

```python
print(ab.countries(round=9))
```

## questions

```python
ab.questions() -> pandas.DataFrame
```

Describe every reviewed question concept in the master codebook.

**Returns** a DataFrame with the columns `name`, `description`, `kind`, `rounds`
(a sorted list of available round numbers), `variables` (a mapping of round
number to source variable), and `values` (target value labels; empty for `text`
concepts).

**Raises** `HarmonizationError` if the shipped crosswalk is invalid.

```python
print(ab.questions()[["name", "kind", "rounds"]].head())
```

## question

```python
ab.question(name: str) -> pandas.DataFrame
```

Return the authoritative per-round view of one concept.

**Returns** a DataFrame with one row per round and the columns `round`, `var`,
`label`, `recode`, `missing`, `excluded`, and `reason`.

**Raises** `HarmonizationError` if the name is not a known concept.

```python
print(ab.question("trust_president"))
```

## families

!!! warning "Deprecated"

    `families()` is kept for compatibility with the original 32 names. Use
    [`questions()`](#questions) and [`question()`](#question) instead.

```python
ab.families() -> pandas.DataFrame
```

Describe the original 32 harmonized question families.

**Returns** a DataFrame with the columns `family`, `description`, `rounds`
(a sorted list of round numbers), and `variables` (a mapping of round number to
source variable). Emits `DeprecationWarning`.

```python
print(ab.families()[["family", "rounds"]])
```

## load

```python
ab.load(
    rounds=None,
    countries=None,
    variables=None,
    labels: bool = False,
    normalize_missing: bool = False,
    harmonize: bool = False,
    language: str = "en",
    source=None,
    refresh: bool = False,
    strict: bool = True,
) -> Dataset
```

Load one or more rounds into a [`Dataset`](dataset.md#dataset).

**Parameters**

- `rounds` — a round number or an iterable of round numbers. When omitted, every
  merged round in the catalog is loaded.
- `countries` — a country name or iterable of names. Matching is
  case-insensitive and alias-aware.
- `variables` — a variable name or iterable of names. With `harmonize=False`
  these are raw source columns; with `harmonize=True` they may be canonical
  variables, question concepts, or raw variables, in that precedence.
- `labels` — decode value labels. Harmonized coded concepts use their target
  labels; canonical and raw columns use per-round metadata.
- `normalize_missing` — replace declared missing codes with `pd.NA`. Harmonized
  concepts force their declared missing codes to `pd.NA` regardless of this flag.
- `harmonize` — add canonical columns and question concepts. Without
  `variables=`, only canonical columns plus the original 32 concept names are
  added.
- `language` — `"en"` (default) or `"fr"` for merged datasets.
- `source` — a local path, a URL on `www.afrobarometer.org`, or a sequence of
  either. `rounds=` is required when harmonizing a local source.
- `refresh` — ignore the cached catalog index.
- `strict` — raise on unavailable requested variables or concepts instead of
  warning.

**Returns** a `Dataset`. The frame always has `round` and `year` columns.

**Raises**

- `NotFoundError` — no data matches the request, or a country page only offers
  CSV.
- `HarmonizationError` — a requested variable or concept is unavailable and
  `strict=True`, or harmonization is requested without a round number for a
  local source.
- `CatalogError` — the catalog cannot be read.
- `DownloadError` — a data file cannot be downloaded.
- `CacheError` — the cache cannot be read or written.

```python
ds = ab.load(rounds=9, harmonize=True, variables=["trust_president", "age"])
print(ds.to_pandas().head())
```

## panel

```python
ab.panel(
    rounds,
    variables,
    countries=None,
    labels: bool = False,
    strict: bool = True,
) -> Dataset
```

Build a multi-round dataset for selected harmonized variables.

**Parameters**

- `rounds` — required round numbers.
- `variables` — required harmonized variable names.
- `countries` — optional country filter.
- `labels` — decode value labels per round.
- `strict` — raise when a requested concept is unavailable in a round.

**Returns** a `Dataset` with the keys `round`, `country`, and `year`, followed by
the requested variables.

**Raises** `HarmonizationError` if a requested variable is missing from any
round, and the same errors as [`load()`](#load).

```python
panel = ab.panel(rounds=[8, 9], variables=["trust_president"])
print(panel.to_pandas().groupby("round")["trust_president"].mean())
```

## search_variables

```python
ab.search_variables(
    query: str,
    rounds=None,
    limit: int = 20,
    fuzzy: bool = True,
) -> pandas.DataFrame
```

Search the shipped metadata index for merged rounds 1–10. This never downloads a
dataset.

**Parameters**

- `query` — text to match against names, labels, concepts, and families.
- `rounds` — a round number or iterable of round numbers.
- `limit` — maximum number of rows.
- `fuzzy` — use fuzzy matching when `rapidfuzz` is installed; otherwise use
  case-insensitive substring matching.

**Returns** a DataFrame with the columns `name`, `label`, `round`, `kind`,
`family`, `concept`, `source_var`, and `score`.

**Raises** `CatalogError` if the shipped metadata index cannot be read.

```python
print(ab.search_variables("trust president", rounds=9, limit=5))
```

## codebook

```python
ab.codebook(
    round: int,
    country: str | None = None,
    extract_text: bool = False,
) -> pathlib.Path
```

Download a codebook for a round.

**Parameters**

- `round` — round number.
- `country` — request a country-specific codebook instead of the merged one.
- `extract_text` — extract PDF text and return the path to a `.txt` file next to
  the PDF. Requires the `[codebook]` extra.

**Returns** the path to the cached PDF, or to the extracted text file when
`extract_text=True`.

**Raises** `NotFoundError` if no codebook exists, and `CodebookError` if the
download or extraction fails.

```python
path = ab.codebook(round=10, extract_text=True)
print(path)
```

## citation

```python
ab.citation(rounds=None, countries=None) -> str
```

Build the required Afrobarometer acknowledgment.

**Parameters**

- `rounds` — a round number or iterable of round numbers.
- `countries` — a country name or iterable of names.

**Returns** a citation string. Years are filled in from the catalog when
available; catalog failures do not prevent a citation from being returned.

```python
print(ab.citation(rounds=[8, 9], countries=["Ghana", "Benin"]))
```

## cache_dir

```python
ab.cache_dir() -> pathlib.Path
```

Return the cache directory. The value is controlled by
`PYAFROBAROMETER_CACHE_DIR` and otherwise uses the platform user cache directory.

```python
print(ab.cache_dir())
```

## clear_cache

```python
ab.clear_cache(round: int | None = None) -> None
```

Remove cached files.

**Parameters**

- `round` — when given, remove only that round's files and metadata. When
  omitted, remove the cache layout directories and the state file.

**Raises** `CacheError` if the cache state cannot be read or written.

```python
ab.clear_cache(round=9)
```
