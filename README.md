# pyafrobarometer

Programmatic access to [Afrobarometer](https://www.afrobarometer.org/) survey data
in Python: discover what exists, download it into a local cache, load it with
metadata intact, and harmonize comparable variables across rounds and countries.

> **Unofficial.** This package is not affiliated with or endorsed by
> Afrobarometer. Afrobarometer data are free to use under their
> [access policy](https://www.afrobarometer.org/data/), but remain copyrighted.
> This package does not redistribute microdata or codebooks; it downloads them
> to a user-local cache. Please cite Afrobarometer in publications.

## Installation

```bash
pip install pyafrobarometer
```

Optional extras:

```bash
pip install "pyafrobarometer[search]"    # fuzzy variable search with rapidfuzz
pip install "pyafrobarometer[codebook]"  # PDF codebook text extraction with pypdf
```

Requires Python 3.10 or newer.

## Quickstart

```python
import pyafrobarometer as ab

# Which merged rounds exist?
print(ab.rounds()[["round", "year", "language", "data_url"]])

# Which comparative question families are shipped?
print(ab.families()[["family", "rounds"]])

# Load one round with metadata intact.
ds = ab.load(rounds=9)
print(ds)
print(ds.variables().head())
print(ds.to_pandas(normalize_missing=True).head())

# Add canonical columns and harmonized question families.
ds = ab.load(rounds=9, harmonize=True)
print(ds.to_pandas()[["country", "age", "trust_president"]].head())

# A two-round trend takes three lines.
panel = ab.panel(rounds=[8, 9], variables=["trust_president"])
trend = panel.to_pandas(normalize_missing=True)
print(trend.groupby("round")["trust_president"].mean())
```

`Dataset` wraps a DataFrame and delegates attribute access, so `ds.head()`,
`ds["Q37A"]`, `ds.shape`, and `len(ds)` work as expected. `ds.to_pandas()` always
returns a copy; mutating it never mutates the dataset.

## Rounds, countries, and availability

- Merged rounds 1–10 are supported, and the baked manifest covers all ten.
  Country-level discovery reads every data-sets listing page and supports
  `.sav`/`.zip`/`.dta` links. CSV-only country pages raise a clear
  `NotFoundError` because CSV is not supported in v1.
- Canonical variables (`country`, `respondent_id`, `weight`, `region`,
  `urban_rural`, `age`, `gender`, `education`, `interview_date`) are mapped per
  round from a curated YAML crosswalk. A mapping that cannot be verified is
  omitted with a warning, never guessed.
- Question families are sparse by design. For example, `social_media_news` is
  available from Round 6, `trust_army` is missing in Round 4, and Round 1
  institutional-trust items are recoded from the 1–4 scale to 0–3.
- `ab.families()` reports each family's available rounds and source variables.
  `strict=True` (the default) raises `HarmonizationError` when a requested family
  is unavailable; `strict=False` adds a missing column of `pd.NA` and warns.

## Value labels and missing codes

`ds.to_pandas(labels=True)` decodes value labels from the SPSS metadata.
`ds.to_pandas(normalize_missing=True)` replaces declared missing codes (`8`, `9`,
`97`, `98`, `99`, `-1`, and their metadata variants) with `pd.NA`. Default loads
keep the raw numeric codes.

## Caching, TTL, and offline use

- Downloaded data and codebooks live in the platform cache reported by
  `ab.cache_dir()`. Set `PYAFROBAROMETER_CACHE_DIR` to override it.
- The catalog index is cached for seven days. Set `PYAFROBAROMETER_INDEX_TTL`
  (seconds) to change the TTL, or call `ab.rounds(refresh=True)` to force a
  refresh.
- Set `PYAFROBAROMETER_OFFLINE=1` to forbid all network access; the cached index
  or the baked manifest is used instead.
- Data files have no TTL and are reused by URL and content hash. `ab.clear_cache()`
  removes everything; `ab.clear_cache(round=9)` removes only that round.

## Variable search

```python
ab.search_variables("trust president", rounds=[8, 9], limit=10)
```

With `rapidfuzz` installed (`[search]` extra), matching is fuzzy; otherwise it is
case-insensitive substring matching. Search reads the shipped
`metadata_index.json`, populated for merged rounds 1–10 and refreshed by the
weekly catalog job. Search never downloads a dataset.

## Codebooks

```python
path = ab.codebook(round=10)                 # downloaded PDF
text = ab.codebook(round=10, extract_text=True)  # .txt next to the PDF
ds = ab.load(rounds=10)
print(ds.codebook())                         # codebook for a loaded dataset
```

Text extraction needs the `[codebook]` extra.

## Citation

```python
print(ab.citation(rounds=[8, 9], countries=["Ghana", "Benin"]))
print(ab.load(rounds=9).citation())
```

The required acknowledgment is:

> Afrobarometer Data, [Country(ies)], [Round(s)], [Year(s)], available at
> http://www.afrobarometer.org.

## Data policy

- Data and codebooks are stored only in the local cache reported by
  `ab.cache_dir()`.
- No Afrobarometer microdata, codebooks, or archives are committed to this
  repository. Downloads use HTTPS from `www.afrobarometer.org` only.
- Please cite Afrobarometer in publications and follow their
  [access policy](https://www.afrobarometer.org/data/).

## Development

```bash
pip install -e ".[dev]"
pytest            # offline suite; network tests are excluded by default
pytest -m network # live catalog/crosswalk verification (large downloads)
ruff check .
mypy src
```

A weekly GitHub Actions job refreshes `manifest.json` and `metadata_index.json`,
validates links and crosswalk coverage, and opens a pull request when they
change. CI is never in the runtime path: a failed refresh only means the package
keeps using its cached or baked catalog.

## License

Code is released under the MIT License. See [LICENSE](LICENSE).
