# pyafrobarometer — Design Specification

**Date:** 2026-10-25
**Status:** Draft for review
**Package:** `pyafrobarometer` (import as `import pyafrobarometer as ab`)

## 1. Purpose

Provide simple, intuitive, programmatic access to Afrobarometer survey data in Python:
discover what exists, download it, load it with metadata intact, and join comparable
variables across rounds and countries.

### Intended users

- Researchers and analysts using Python instead of R/SPSS.
- Data journalists and students exploring aggregate public opinion.
- Anyone who currently downloads `.sav` files manually and re-implements the same
  metadata handling each time.

### Success criteria

1. `pip install pyafrobarometer` then `ab.load(rounds=9)` returns a usable `Dataset`
   on a normal broadband connection.
2. A second load of the same round works offline from cache.
3. A two-round trend for one harmonized variable takes three lines of code.
4. Variable discovery works before downloading a 100+ MB dataset, via a shipped
   metadata index and fuzzy search.
5. Every downloaded artifact has provenance (source URL, retrieval time) and the
   required citation is available programmatically.
6. No Afrobarometer microdata or codebook PDFs are committed to the repository.

## 2. Constraints and facts

- Afrobarometer publishes SPSS `.sav` (sometimes zipped) datasets and PDF codebooks.
  There is **no public JSON API**.
- Downloads from `www.afrobarometer.org` are direct and unauthenticated (verified:
  HTTP 200, `content-type: application/zip` for Round 10).
- Merged rounds live at `/data/merged-data/`. Recent rounds link directly to files;
  older rounds link to `/survey-resource/...` pages that contain the actual links.
- Country datasets are listed at `/data/data-sets/`, also via `survey-resource` pages.
- Merged data exists for Rounds 1–10. Round 10 (38 countries, 2025) includes English
  and French merged files.
- Afrobarometer data are copyrighted but free to use under their access policy. The
  package must not redistribute the data; it downloads to a user-local cache.
- The package is unaffiliated with Afrobarometer.

### Supported rounds in v1

- **Verified:** merged Rounds 1–10 (1999–2025) and their codebooks. Canonical
  variables and question families are verified per round; variables a round lacks
  are omitted with a warning rather than guessed.
- Older rounds use different variable names and sometimes different response
  scales: R1 uses lowercase names (`country`, `area`, `age`, `gender`, `educ`,
  `refnumb`, `withinwt`) and a 1–4 trust scale that maps exactly to the modern
  0–3 scale. R2/R3 are lowercase, R4 is mixed case (`COUNTRY`, `Withinwt`).
- Country-level datasets: all entries discoverable from `/data/data-sets/`; if a
  country/round is not listed there, raise `NotFoundError` rather than guess a URL.
- Language: `"en"` (default) and `"fr"` where the catalog exposes variants.

## 3. Architecture

```
pyafrobarometer/
├── pyproject.toml
├── README.md
├── LICENSE
├── .github/workflows/update-catalog.yml
├── scripts/update_catalog.py
├── src/pyafrobarometer/
│   ├── __init__.py        # public surface
│   ├── api.py             # high-level functions composing the pieces
│   ├── catalog.py         # resolve website index + survey-resource pages
│   ├── fetch.py           # HTTP streaming, retries, atomic writes
│   ├── cache.py           # platformdirs cache, TTL, baked-manifest fallback
│   ├── io.py              # zip extraction + pyreadstat reads
│   ├── dataset.py         # Dataset wrapper, to_pandas, provenance, repr
│   ├── metadata.py        # variable/value-label metadata, missing codes
│   ├── search.py          # fuzzy search over shipped + live metadata
│   ├── codebook.py        # PDF download; optional text extraction
│   ├── errors.py          # exception hierarchy
│   ├── manifest.json      # baked fallback catalog
│   ├── metadata_index.json# baked metadata-only variable index
│   ├── crosswalk/
│   │   ├── canonical.yaml
│   │   └── questions.yaml
│   └── harmonize/
│       ├── canonical.py
│       ├── crosswalk.py
│       ├── normalize.py
│       └── panel.py
└── tests/
    ├── fixtures/          # HTML snapshots, synthetic .sav, metadata JSON
    └── test_*.py
```

Module boundaries:

- `catalog.py` is the only scraper. It returns `CatalogEntry` objects and never
  downloads datasets.
- `fetch.py` is the only HTTP client. It never parses HTML.
- `cache.py` owns paths, TTL, locking, and fallback selection.
- `harmonize/` is pure transformation over a `Dataset` and metadata.
- `api.py` composes the above; it contains no scraping, I/O, or mapping logic.

## 4. Public API

```python
import pyafrobarometer as ab

ab.rounds(refresh=False)                     # DataFrame: round, year, countries, data_url, codebook_url
ab.countries(round=None)                     # list[str]
ab.load(rounds=None, countries=None, variables=None,
        labels=False, normalize_missing=False, harmonize=False,
        language="en", source=None, refresh=False, strict=True) -> Dataset
ab.search_variables(query, rounds=None, limit=20, fuzzy=True) -> DataFrame
ab.families()                                # DataFrame: family, description, rounds, variables
ab.codebook(round, country=None, extract_text=False) -> Path
ab.panel(rounds, variables, countries=None, labels=False, strict=True) -> Dataset
ab.citation(rounds=None, countries=None) -> str
ab.cache_dir() -> Path
ab.clear_cache(round=None) -> None
```

Parameter semantics:

- `rounds`: int or iterable of ints. `None` means "all merged rounds".
- `countries`: case-insensitive names; `None` means all countries in the selection.
- `variables`: source variable names when `harmonize=False`; canonical/family names
  when `harmonize=True`. Accepts str or iterable.
- `labels`: return decoded value labels (`Categorical`) instead of numeric codes.
- `normalize_missing`: replace declared missing codes with `pd.NA`.
- `harmonize`: add canonical columns and requested question-family columns.
- `source`: local path, URL, or iterable of either; bypasses catalog resolution.
- `refresh`: force re-fetch of the catalog index.
- `strict`: raise when a requested round/variable/family is unavailable instead of
  returning a NaN column with a warning.

## 5. Dataset object

```python
ds = ab.load(rounds=9, harmonize=True)
ds.rounds            # [9]
ds.countries         # ['Benin', ...]
ds.variables()       # DataFrame: name, label, value_labels, missing_codes, source_var
ds.to_pandas()                        # numeric codes
ds.to_pandas(labels=True)             # decoded categories
ds.to_pandas(normalize_missing=True)  # declared missings -> pd.NA
ds.codebook()                         # Path
ds.citation()                         # required citation string
ds.subset(countries=["Ghana"])        # -> Dataset
```

Rules:

- `Dataset` wraps one pandas DataFrame in `_df` and delegates attribute access to it
  (`ds.head()`, `ds["Q14"]`, `ds.shape` work).
- `isinstance(ds, pd.DataFrame)` is deliberately `False`.
- `to_pandas()` always returns a new frame; mutating it never mutates the `Dataset`.
- Provenance (`source_urls`, `retrieved_at`, `rounds`, `countries`, `language`) is
  stored on the object and exposed via `ds.provenance`.
- `__repr__` shows rounds, countries, row/column counts, and harmonization status.
- `Dataset` is picklable and supports `len()` and iteration over column names.

## 6. Catalog resolution

`catalog.py` produces `CatalogEntry` records:

```python
@dataclass(frozen=True)
class CatalogEntry:
    kind: Literal["merged", "country"]
    round: int
    country: str | None
    year: int | None
    language: str
    data_url: str
    codebook_url: str | None
    page_url: str
    filename: str
    size_bytes: int | None
```

Resolution flow:

1. Fetch `/data/merged-data/` and `/data/data-sets/` and build the catalog index
   (the serialized index, not raw HTML, is cached and governed by the TTL).
2. For entries whose link is a `survey-resource` page rather than a file, fetch that
   page (one level only) and extract `.sav`, `.sav.zip`, `.dta`, and `.pdf` links.
3. Prefer `.sav`/`.sav.zip`; never treat a codebook PDF as data.
4. Normalize titles into `round`, `country`, `year`, `language`. Country names are
   canonicalized (e.g. "Côte d'Ivoire", "Sao Tome and Principe").
5. Validate the resulting catalog before returning it: at least one merged entry,
   every entry has a data URL on an `https://www.afrobarometer.org/` host, and
   filenames are non-empty. A malformed or empty parse is a `CatalogError`, never a
   successful partial result.
6. On `CatalogError` or network failure, fall back to the cached index, then to the
   baked `manifest.json`, with a warning.

HTML parsing uses BeautifulSoup. Selectors are centralized in one table so a site
redesign is a localized fix.

## 7. Cache and TTL

Cache root comes from `platformdirs.user_cache_dir("pyafrobarometer")`, overridable
with `PYAFROBAROMETER_CACHE_DIR`.

```
<root>/
├── index/catalog.json       # serialized index + fetched_at
├── files/<sha256(url)>-<basename>
├── metadata/<round>.json    # extracted variable metadata
├── locks/                   # per-URL .lock files
├── tmp/                     # transient .part downloads
└── state.json               # timestamps, manifest source, file map
```

**TTL definition.** `TTL` (default 7 days) applies only to `index/catalog.json`.
On a catalog-dependent call:

1. If the index exists and `now - fetched_at < TTL`, use it; no network.
2. Otherwise attempt a re-fetch; on success, replace the index and timestamp.
3. On failure, use the stale index with a warning.
4. `refresh=True` always forces step 2.
5. `PYAFROBAROMETER_INDEX_TTL` (seconds) overrides the default.
6. `PYAFROBAROMETER_OFFLINE=1` skips all network access and uses cache/manifest only.

Downloaded data files have **no TTL**. They are content-addressed by URL hash and
persist until `clear_cache()` is called. Metadata is re-extracted if the file hash
changes. `clear_cache(round=9)` removes that round's files and metadata only.

## 8. Downloads

- HTTPS only; TLS verification on; redirects allowed but final scheme must be HTTPS.
- Stream to `tmp/*.part`, then `os.replace` to the final path.
- Per-URL file lock; concurrent callers wait rather than duplicate the fetch.
- Timeouts: 60 s connect/read. Retries: 3 attempts, exponential backoff, on timeouts,
  connection errors, and 5xx; honor `Retry-After` on 429/503.
- Validate `Content-Type` (`application/zip`, `application/x-spss-sav`,
  `application/octet-stream`, `application/pdf` as applicable) and a minimum size.
- Record SHA-256 and size in `state.json`.
- User-Agent: `pyafrobarometer/<version> (+https://github.com/<repo>)`.
- Zip extraction is guarded against path traversal; only `.sav` members are extracted.
  The archive is deleted after extraction unless `keep_archive=True`.

## 9. Canonical schema

Canonical names: `country, round, year, respondent_id, weight, region, urban_rural,
age, gender, education, interview_date`.

Verified source variables:

| canonical | R1 | R2 | R3 | R4 | R5–R8 | R9 | R10 |
|---|---|---|---|---|---|---|---|
| country | country | country | country | COUNTRY | COUNTRY (R5: COUNTRY_ALPHA) | COUNTRY | COUNTRY |
| respondent_id | refnumb | respno | respno | RESPNO | RESPNO | RESPNO | RESPNO |
| region | area | region | region | REGION | REGION | REGION | REGION |
| urban_rural | urbrur | urbrur | urbrur | URBRUR | URBRUR | URBRUR | URBRUR |
| age | age | Q80 | Q1 | Q1 | Q1 | Q1 | Q1 |
| gender | gender | Q96 | Q101 | Q101 | Q101 (R9: Q100) | Q100 | Q101 |
| education | educ | Q84 | Q90 | Q89 | Q97 (R9: Q94) | Q94 | Q96 |
| interview_date | — | dateintr | dateintr | DATEINTR | DATEINTR | DATEINTR | DATEINTR |
| weight | withinwt | withinwt | withinwt | Withinwt | withinwt (R8: withinwt_ea) | withinwt_ea | withinwt_ea |

- Source variable names are case-sensitive and recorded per round in
  `crosswalk/canonical.yaml`. If a mapping cannot be verified, that canonical
  variable is omitted for that round rather than guessed; tests assert coverage.
- `harmonize=True` adds canonical columns while preserving original source columns.
- `ds.variables()` includes a `source_var` mapping for every canonical/family column.
- `round` and `year` come from the catalog, not from the data file.
- Weights: expose the within-country weight as `weight` (`withinwt_hh` when present,
  otherwise `withinwt_ea`, otherwise `withinwt`); do not weight any statistics.

## 10. Question families

`crosswalk/questions.yaml` stores one entry per family per round. A family need not
exist in every round; `family_rounds()` and `ab.families()` report availability, and
`panel()` respects it.

v1 ships 32 families, all verified against the codebooks:

- **Democracy:** `support_democracy` (R2–R10), `reject_one_party_rule`,
  `reject_military_rule`, `reject_one_man_rule` (R2–R10),
  `satisfaction_democracy` (R2–R10).
- **Institutional trust:** `trust_president`, `trust_police`, `trust_courts` (R1–R10,
  R1 recoded), `trust_parliament`, `trust_ruling_party`, `trust_opposition`
  (R2–R10), `trust_electoral_commission` (R1–R10, R1 recoded), `trust_army`
  (R1, R2–R3, R5–R10; R1 recoded).
- **Corruption:** `corruption_president`, `corruption_police`, `corruption_judges`
  (R2–R10), `bribe_police` (R6–R10).
- **Media:** `radio_news`, `television_news`, `newspaper_news` (R2–R10),
  `internet_news` (R5–R10), `social_media_news` (R6–R10), `internet_use` (R4–R10).
- **Economy and wellbeing:** `econ_country_present`, `econ_personal_present`
  (R2–R10), `lived_poverty_food`, `lived_poverty_water`, `lived_poverty_medical`,
  `lived_poverty_fuel` (R2–R10).
- **Rights, safety, participation:** `free_to_say` (R4–R10),
  `felt_unsafe_walking` (R5–R10), `neighbours_homosexuals` (R6–R10).

Scale rules: trust is 0–3, rejection items 1–5, corruption 0–3, news and lived
poverty 0–4, support democracy 1–3, satisfaction with democracy 0–4. R1 trust is
1–4 and is recoded exactly to 0–3. Families whose scales drift (for example R1
satisfaction with democracy, R1 media frequency, R1 lived poverty) are excluded for
that round rather than silently merged.

- Value labels are read from the `.sav` metadata; `labels=True` applies them.
- `recode` is optional per round for exact scale mappings.
- No automatic fuzzy harmonization. Fuzzy matching is only a discovery aid in
  `search_variables()`.
- Missing/unavailable family for a requested round: `HarmonizationError` when
  `strict=True` (message lists available rounds), NaN column with warning otherwise.

## 11. Missing codes

- Declared missing values are read from pyreadstat metadata (`missing_ranges` and
  user-missing values), with a fallback table for common codes (`8`, `9`, `-1`,
  `98`, `99`) when metadata is absent.
- Default load preserves raw codes. `normalize_missing=True` converts declared
  missing codes to `pd.NA`. `ds.variables()` reports the codes that were applied.
- Refused / don't know / no answer are not distinguished in normalized form in v1.

## 12. Search and metadata index

- `metadata_index.json` is generated by `scripts/update_catalog.py` from codebook/data
  metadata. It contains only variable names, labels, value labels, round, and whether
  a canonical/family mapping exists — no respondent data.
- `search_variables()` searches the shipped index plus metadata from any cached round.
- Scoring uses `rapidfuzz` when installed (`[search]` extra), otherwise
  case-insensitive substring matching.
- Results: `name, label, round, kind, family, source_var, score`; sorted descending,
  limited by `limit`.

## 13. Panel helper

`ab.panel(rounds, variables, countries=None, labels=False, strict=True)`:

1. Resolve requested families/canonical variables per round.
2. Load only selected columns via pyreadstat `usecols`.
3. Rename to canonical names, add `round`, `country`, `year`.
4. Concatenate with `ignore_index=True` and consistent dtypes.
5. Return a `Dataset` whose provenance lists every source URL.

## 14. Errors and logging

```
AfrobarometerError
├── CatalogError
├── DownloadError
├── CacheError
├── NotFoundError
├── HarmonizationError
└── CodebookError
```

- Messages state what failed, the URL or round involved, and a suggested action.
- Logging uses the `pyafrobarometer` logger; non-fatal fallbacks use `warnings.warn`.
- No silent partial results.

## 15. CI maintenance job

Purpose: keep the baked fallback manifest and metadata index fresh, validate links and
mappings, and surface breakage before users see it. CI is **not** in the runtime path.

`.github/workflows/update-catalog.yml`:

- Triggers: weekly cron (Monday 06:00 UTC), `workflow_dispatch`, and changes to
  `catalog.py`, `scripts/update_catalog.py`, or the crosswalk files.
- Permissions: `contents: write`, `pull-requests: write`; no secrets.
- Steps: checkout, setup Python, install `.[dev]`, run
  `python scripts/update_catalog.py --write --validate`, run `pytest -m "not network"`,
  then open a PR via `peter-evans/create-pull-request` when files changed.
- Validation performed: every data/codebook URL responds with an allowed content type
  and plausible size; newest merged round opens with pyreadstat; canonical/family
  mappings exist for every claimed round. Any broken expected URL fails the job.
- The job may download datasets to the runner for validation, but never commits them
  or their contents to git; only generated JSON is committed.
- Mitigations documented in README: manual dispatch when cron is delayed; commits on
  change keep the repository active; a failed job is an alert, not a user-facing error.

`scripts/update_catalog.py` reuses `catalog.py` and `metadata.py` so CI and runtime
cannot diverge in parsing logic.

## 16. Testing

- `pytest`, src layout, `tests/fixtures/`.
- Catalog parsing: HTML snapshots of merged-data, data-sets, and one survey-resource
  page; assertions on round/country/year/URL extraction and malformed-input handling.
- Data loading: synthetic `.sav` files written at test time with pyreadstat (no
  copyrighted data committed); tests for labels, missing codes, column selection.
- Cache: TTL expiry, stale fallback, offline mode, content-addressed reuse, lock
  behavior, guarded zip extraction.
- Harmonization: canonical and family coverage per supported round using metadata
  fixtures; strict and non-strict behavior.
- Dataset contract: delegation, `to_pandas` modes, provenance, pickling, repr.
- Network tests marked `@pytest.mark.network`, excluded by default; CI may run a
  smoke test against the real site.
- `ruff` and `mypy` clean.

Commands: `pytest`, `ruff check .`, `mypy src`.

## 17. Packaging

- `pyproject.toml` with hatchling, src layout.
- Python `>=3.10`.
- Core dependencies: `pandas`, `pyreadstat`, `requests`, `platformdirs`,
  `beautifulsoup4`, `PyYAML`.
- Extras: `search = ["rapidfuzz"]`, `codebook = ["pypdf"]`,
  `dev = ["pytest", "pytest-cov", "respx", "ruff", "mypy"]`.
- Version `0.1.0`. Semantic versioning for the public API.

## 18. Licensing and data policy

- Code: MIT.
- Afrobarometer data and codebooks are never redistributed or committed; they live in
  the user-local cache.
- `ab.citation(rounds, countries)` returns the required acknowledgment:
  "Afrobarometer Data, [Country(ies)], [Round(s)], [Year(s)], available at
  http://www.afrobarometer.org."
- README states the package is unaffiliated, links the access policy, and asks users to
  cite Afrobarometer in publications.
- Requests are polite: one catalog fetch per TTL, descriptive UA, no parallel flooding.

## 19. Non-goals for v1

- Geocoded or restricted datasets (application required).
- The Online Data Analysis (ODA) tool or any undocumented API.
- Statistical weighting or estimation (the weight variable is exposed only).
- GUI, notebook widgets, or CLI.
- Harmonizing all 400+ variables.
- Languages other than selecting an EN/FR file variant.

## 20. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Site redesign breaks scraping | Selectors centralized; CI detects; baked manifest fallback; malformed parse = error |
| Dead or moved URLs | CI validates weekly; runtime falls back to cached/baked manifest |
| Crosswalk drift across releases | CI validates mappings against real files; unmapped vars omitted, never guessed |
| pyreadstat wheel unavailable | Supported Python versions tracked in CI matrix; documented build requirement |
| Large downloads | Streaming, size checks, `usecols` on load, cache reuse |
| Copyright/redistribution | No data in repo; user-local cache; citation helper |
| GitHub cron delays/disablement | Manual dispatch; commits on change; README note |
