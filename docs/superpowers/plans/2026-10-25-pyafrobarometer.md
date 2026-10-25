# pyafrobarometer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python package that discovers, downloads, caches, loads, searches, and harmonizes Afrobarometer survey data behind a small `Dataset` API.

**Architecture:** Runtime catalog resolution scrapes Afrobarometer index pages, caches a serialized catalog with a 7-day TTL, and falls back to a baked manifest. Downloads are streamed and cached per user. A `Dataset` wraps a DataFrame plus metadata and provenance. Harmonization is driven by curated YAML crosswalks. A CI job refreshes the baked manifest and validates links and mappings; it is never in the runtime path.

**Tech Stack:** Python >=3.10, pandas, pyreadstat, requests, platformdirs, beautifulsoup4. Optional: rapidfuzz, pypdf. Tests: pytest, respx.

**Spec:** `docs/superpowers/specs/2026-10-25-pyafrobarometer-design.md`

## Global Constraints

- Python `>=3.10`; package version `0.1.0`; src layout; license MIT.
- Core deps exactly: `pandas`, `pyreadstat`, `requests`, `platformdirs`, `beautifulsoup4`, `PyYAML`.
- Extras: `search=["rapidfuzz"]`, `codebook=["pypdf"]`, `dev=[pytest, pytest-cov, respx, ruff, mypy, rapidfuzz, pypdf, pandas-stubs]`.
- Never commit Afrobarometer microdata, codebooks, or downloaded archives. Only metadata JSON and HTML test fixtures.
- Cache root is `platformdirs.user_cache_dir("pyafrobarometer")`, overridable by `PYAFROBAROMETER_CACHE_DIR`.
- Catalog index TTL is `604800` seconds, overridable by `PYAFROBAROMETER_INDEX_TTL`; `PYAFROBAROMETER_OFFLINE=1` forbids network.
- All remote URLs must be HTTPS on `www.afrobarometer.org`.
- Canonical schema and question families cover merged rounds 1–10; a variable or family absent in a round is omitted, never guessed.
- User-Agent: `pyafrobarometer/<version> (+https://github.com/<repo>)`.
- No automatic fuzzy harmonization; fuzzy matching only suggests variables.
- No silent partial results: malformed/empty catalog parses raise `CatalogError`.

## Review Focus

1. **Malformed or empty HTML after a site redesign** — must raise `CatalogError` and use the cached/baked catalog, never return a partial catalog as success.
2. **Zip archives with path traversal or no `.sav` member** — must reject traversal, extract nothing outside the target directory, and fail clearly when no dataset is present.
3. **A requested question family missing for a round** — `strict=True` raises `HarmonizationError` naming available rounds; `strict=False` adds a NaN column and warns.
4. **Missing codes and encoded country values** — `8/9/97/98/997/998/999/-1` variants and numeric `COUNTRY` codes must be interpreted per variable metadata, not by a single global table.
5. **Concurrent and offline loads** — two callers must not duplicate or corrupt a download; offline mode must use cache or baked manifest without touching the network.

## Verified Crosswalk Data

Verified from Afrobarometer merged codebooks R1–R10 on 2026-10-25. These exact values go into `canonical.yaml` and `questions.yaml`.

Canonical (case-sensitive variable names):

| canonical | R1 | R2 | R3 | R4 | R5 | R6 | R7 | R8 | R9 | R10 |
|---|---|---|---|---|---|---|---|---|---|---|
| country | country | country | country | COUNTRY | COUNTRY_ALPHA | COUNTRY | COUNTRY | COUNTRY | COUNTRY | COUNTRY |
| respondent_id | refnumb | respno | respno | RESPNO | RESPNO | RESPNO | RESPNO | RESPNO | RESPNO | RESPNO |
| region | area | region | region | REGION | REGION | REGION | REGION | REGION | REGION | REGION |
| urban_rural | urbrur | urbrur | urbrur | URBRUR | URBRUR | URBRUR | URBRUR | URBRUR | URBRUR | URBRUR |
| age | age | Q80 | Q1 | Q1 | Q1 | Q1 | Q1 | Q1 | Q1 | Q1 |
| gender | gender | Q96 | Q101 | Q101 | Q101 | Q101 | Q101 | Q101 | Q100 | Q101 |
| education | educ | Q84 | Q90 | Q89 | Q97 | Q97 | Q97 | Q97 | Q94 | Q96 |
| interview_date | — | dateintr | dateintr | DATEINTR | DATEINTR | DATEINTR | DATEINTR | DATEINTR | DATEINTR | DATEINTR |
| weight | withinwt | withinwt | withinwt | Withinwt | withinwt | withinwt | withinwt | withinwt_ea | withinwt_ea | withinwt_ea |

`COUNTRY` is numeric with value labels for R4 and R6–R10; decode it to names. R1–R3 `country` is numeric with labels; R5 `COUNTRY_ALPHA` is already a string. `weight` prefers `withinwt_hh` when present, else the mapped variable.

Question families (`—` means the family is not available for that round):

| family | R1 | R2 | R3 | R4 | R5 | R6 | R7 | R8 | R9 | R10 |
|---|---|---|---|---|---|---|---|---|---|---|
| trust_president | trspre* | Q43A | Q55A | Q49A | Q59A | Q52A | Q43A | Q41A | Q37A | Q37A |
| trust_parliament | — | Q43B | Q55B | Q49B | Q59B | Q52B | Q43B | Q41B | Q37B | Q37B |
| trust_police | trspol* | Q43I | Q55H | Q49G | Q59H | Q52H | Q43G | Q41G | Q37G | Q37G |
| trust_courts | trscts* | Q43J | Q55I | Q49H | Q59J | Q52J | Q43I | Q41I | Q37I | Q37I |
| trust_electoral_commission | trsnec* | Q43C | Q55C | Q49C | Q59C | Q52C | Q43C | Q41C | Q37C | Q37C |
| trust_army | trsarm* | Q43H | Q55G | — | Q59I | Q52I | Q43H | Q41H | Q37H | Q37H |
| trust_ruling_party | — | Q43F | Q55E | Q49E | Q59F | Q52F | Q43E | Q41E | Q37E | Q37E |
| trust_opposition | — | Q43G | Q55F | Q49F | Q59G | Q52G | Q43F | Q41F | Q37F | Q37F |
| support_democracy | — | Q38 | Q37 | Q30 | Q32 | Q30 | Q28 | Q21 | Q23 | Q22 |
| reject_one_party_rule | — | Q35A | Q36A | Q29A | Q31A | Q28A | Q27A | Q20A | Q22A | Q21A |
| reject_military_rule | — | Q35C | Q36B | Q29B | Q31B | Q28B | Q27B | Q20B | Q22B | Q21B |
| reject_one_man_rule | — | Q35D | Q36C | Q29C | Q31C | Q28C | Q27C | Q20C | Q22C | Q21C |
| satisfaction_democracy | — | Q40 | Q47 | Q43 | Q43 | Q41 | Q36 | Q37 | Q31 | Q33 |
| corruption_president | — | Q51A | Q56A | Q50A | Q60A | Q53A | Q44A | Q42A | Q38A | Q38A |
| corruption_police | — | Q51D | Q56F | Q50E | Q60E | Q53E | Q44E | Q42E | Q38E | Q38E |
| corruption_judges | — | Q51F | Q56H | Q50G | Q60G | Q53G | Q44F | Q42F | Q38F | Q38F |
| bribe_police | — | — | — | — | — | Q55J | Q49T | Q44N | Q43E | Q45E |
| radio_news | — | Q26A | Q15A | Q12A | Q13A | Q12A | Q12A | Q55A | Q74A | Q65A |
| television_news | — | Q26B | Q15B | Q12B | Q13B | Q12B | Q12B | Q55B | Q74B | Q65B |
| newspaper_news | — | Q26C | Q15C | Q12C | Q13C | Q12C | Q12C | Q55C | Q74C | Q65C |
| internet_news | — | — | — | — | Q13D | Q12D | Q12D | Q55D | Q74D | Q65E |
| social_media_news | — | — | — | — | — | Q12E | Q12E | Q55E | Q74E | Q65D |
| internet_use | — | — | — | Q88C | Q91B | Q92B | Q91B | Q92I | Q90I | Q90J |
| econ_country_present | — | Q1A | Q4A | Q4A | Q3A | Q4A | Q4A | Q4A | Q4A | Q4A |
| econ_personal_present | — | Q1B | Q4B | Q4B | Q3B | Q4B | Q4B | Q4B | Q4B | Q4B |
| lived_poverty_food | — | Q9A | Q8A | Q8A | Q8A | Q8A | Q8A | Q7A | Q6A | Q7A |
| lived_poverty_water | — | Q9B | Q8B | Q8B | Q8B | Q8B | Q8B | Q7B | Q6B | Q7B |
| lived_poverty_medical | — | Q9C | Q8C | Q8C | Q8C | Q8C | Q8C | Q7C | Q6C | Q7C |
| lived_poverty_fuel | — | Q9E | Q8D | Q8D | Q8D | Q8D | Q8D | Q7D | Q6D | Q7D |
| free_to_say | — | — | — | Q15A | Q17A | Q15A | Q14 | Q10A | Q9A | Q10A |
| felt_unsafe_walking | — | — | — | — | Q9A | Q10A | Q10A | Q8A | Q7A | Q9 |
| neighbours_homosexuals | — | — | — | — | — | Q89C | Q87C | Q86C | Q87C | Q88C |

\* R1 trust uses 1–4; each mapping carries `recode: {1: 0, 2: 1, 3: 2, 4: 3}`.

Scales: trust `0–3`; rejection items `1–5`; corruption `0–3`; news, internet use, lived poverty, and safety `0–4`; support for democracy `1–3`; satisfaction with democracy `0–4`. Families whose scales drift (R1 news, R1 lived poverty, R1 satisfaction, R1 support/rejection) are excluded for R1 rather than silently merged.

---

### Task 1: Scaffolding, packaging, and errors

**Files:**
- Create: `pyproject.toml`, `LICENSE`, `.gitignore`, `README.md`
- Create: `src/pyafrobarometer/__init__.py`, `src/pyafrobarometer/errors.py`
- Test: `tests/test_package.py`, `tests/test_errors.py`

**Interfaces:**
- Produces: `pyafrobarometer.__version__ == "0.1.0"`; exception classes `AfrobarometerError`, `CatalogError`, `DownloadError`, `CacheError`, `NotFoundError`, `HarmonizationError`, `CodebookError`, all exported from `pyafrobarometer`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_package.py
import pyafrobarometer as ab

def test_version():
    assert ab.__version__ == "0.1.0"

def test_public_errors_are_exported():
    for name in ["AfrobarometerError", "CatalogError", "DownloadError", "CacheError",
                 "NotFoundError", "HarmonizationError", "CodebookError"]:
        assert hasattr(ab, name)
```

```python
# tests/test_errors.py
import pyafrobarometer as ab

def test_error_hierarchy():
    for exc in [ab.CatalogError, ab.DownloadError, ab.CacheError,
                ab.NotFoundError, ab.HarmonizationError, ab.CodebookError]:
        assert issubclass(exc, ab.AfrobarometerError)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_package.py tests/test_errors.py -v`
Expected: FAIL (`ModuleNotFoundError: pyafrobarometer`).

- [ ] **Step 3: Implement packaging and errors**

Create `pyproject.toml` with hatchling, the exact core deps/extras from Global Constraints, `[tool.pytest.ini_options] markers = ["network: hits afrobarometer.org"]`, `addopts = "-m 'not network'"`, ruff `line-length = 100`, and mypy `strict = true`. Create `errors.py` with the hierarchy, and `__init__.py` exporting `__version__` and the errors. `.gitignore` must ignore `*.sav`, `*.zip`, `*.pdf`, `__pycache__/`, `.pytest_cache/`, `dist/`, `.venv/`.

- [ ] **Step 4: Run tests and tooling**

Run: `pip install -e ".[dev]" && pytest tests/test_package.py tests/test_errors.py -v && ruff check .`
Expected: PASS; ruff clean.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml LICENSE .gitignore README.md src/pyafrobarometer tests
git commit -m "chore: scaffold pyafrobarometer package and error hierarchy"
```

---

### Task 2: Cache, state, TTL, and locks

**Files:**
- Create: `src/pyafrobarometer/cache.py`
- Test: `tests/test_cache.py`

**Interfaces:**
- Produces:
  - `DEFAULT_TTL_SECONDS: int = 604800`
  - `cache_root() -> pathlib.Path`
  - `cache_file(relative: str) -> pathlib.Path` (creates parent dirs)
  - `read_state() -> dict[str, Any]`, `write_state(state: Mapping[str, Any]) -> None`
  - `is_fresh(fetched_at: float, *, ttl: int = DEFAULT_TTL_SECONDS, now: float | None = None) -> bool`
  - `url_lock(url: str, *, timeout: float = 300.0) -> ContextManager[None]`
  - `clear_cache(round_number: int | None = None) -> None`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cache.py
import time, threading
import pytest
from pyafrobarometer import cache
from pyafrobarometer.errors import CacheError

def test_cache_root_respects_env(tmp_path, monkeypatch):
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path))
    assert cache.cache_root() == tmp_path

def test_is_fresh_boundaries():
    now = 1_000_000.0
    assert cache.is_fresh(now - 10, ttl=60, now=now)
    assert not cache.is_fresh(now - 60, ttl=60, now=now)

def test_state_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path))
    cache.write_state({"index_fetched_at": 1.0, "files": {}})
    assert cache.read_state()["index_fetched_at"] == 1.0

def test_lock_is_exclusive(tmp_path, monkeypatch):
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path))
    started = threading.Event()
    release = threading.Event()
    def holder():
        with cache.url_lock("https://example.test/a"):
            started.set()
            release.wait(2)
    thread = threading.Thread(target=holder)
    thread.start(); started.wait(2)
    with pytest.raises(CacheError):
        with cache.url_lock("https://example.test/a", timeout=0.05):
            pass
    release.set(); thread.join()

def test_clear_cache_by_round(tmp_path, monkeypatch):
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path))
    f = cache.cache_file("files/abc-round-9.sav"); f.write_bytes(b"x")
    m = cache.cache_file("metadata/round-9.json"); m.write_text("{}")
    cache.write_state({"files": {"u": {"path": str(f), "round": 9}}})
    cache.clear_cache(9)
    assert not f.exists() and not m.exists()
    assert cache.read_state()["files"] == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cache.py -v`
Expected: FAIL (`ModuleNotFoundError` / missing functions).

- [ ] **Step 3: Implement `cache.py`**

Use `platformdirs.user_cache_dir("pyafrobarometer")`; honor `PYAFROBAROMETER_CACHE_DIR`. Store `state.json` atomically via `tempfile.NamedTemporaryFile` in the same directory plus `os.replace`. Implement the lock with `os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)` and a 50 ms retry loop; on timeout raise `CacheError`. `clear_cache` removes files/metadata and prunes matching `state["files"]` entries.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_cache.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pyafrobarometer/cache.py tests/test_cache.py
git commit -m "feat: add cache, TTL, state, and download locks"
```

---

### Task 3: HTTP fetching and atomic downloads

**Files:**
- Create: `src/pyafrobarometer/fetch.py`
- Test: `tests/test_fetch.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) DownloadResult(path: Path, sha256: str, size: int, content_type: str)`
  - `http_get(url: str, *, timeout: float = 60.0, retries: int = 3) -> requests.Response`
  - `http_head(url: str, *, timeout: float = 30.0) -> requests.Response`
  - `fetch_text(url: str, *, timeout: float = 60.0) -> str`
  - `download(url: str, dest: Path, *, expected_types: tuple[str, ...] | None = None, timeout: float = 60.0, retries: int = 3) -> DownloadResult`
- Consumes: `cache.url_lock` for per-URL serialization.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_fetch.py
import hashlib
import respx, httpx, pytest
from pyafrobarometer import fetch
from pyafrobarometer.errors import DownloadError

@respx.mock
def test_download_writes_and_hashes(tmp_path):
    body = b"PK\x03\x04fake"
    respx.get("https://www.afrobarometer.org/a.zip").mock(
        return_value=httpx.Response(200, content=body, headers={"content-type": "application/zip"}))
    dest = tmp_path / "a.zip"
    result = fetch.download("https://www.afrobarometer.org/a.zip", dest, expected_types=("application/zip",))
    assert dest.read_bytes() == body
    assert result.sha256 == hashlib.sha256(body).hexdigest() and result.size == len(body)

@respx.mock
def test_download_retries_5xx(tmp_path):
    route = respx.get("https://www.afrobarometer.org/a.sav")
    route.side_effect = [httpx.Response(503), httpx.Response(200, content=b"x",
        headers={"content-type": "application/x-spss-sav"})]
    result = fetch.download("https://www.afrobarometer.org/a.sav", tmp_path / "a.sav")
    assert route.call_count == 2 and result.size == 1

@respx.mock
def test_download_rejects_wrong_content_type(tmp_path):
    respx.get("https://www.afrobarometer.org/x").mock(
        return_value=httpx.Response(200, content=b"<html>", headers={"content-type": "text/html"}))
    with pytest.raises(DownloadError):
        fetch.download("https://www.afrobarometer.org/x", tmp_path / "x", expected_types=("application/zip",))

def test_download_rejects_non_https(tmp_path):
    with pytest.raises(DownloadError):
        fetch.download("http://www.afrobarometer.org/a", tmp_path / "a")

@respx.mock
def test_http_head_returns_status():
    respx.head("https://www.afrobarometer.org/a.sav").mock(return_value=httpx.Response(200))
    assert fetch.http_head("https://www.afrobarometer.org/a.sav").status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_fetch.py -v`
Expected: FAIL (missing module/functions).

- [ ] **Step 3: Implement `fetch.py`**

Use a `requests.Session` with the required UA, `stream=True`, and `raise_for_status`. Retry on `ConnectionError`, `Timeout`, and 5xx up to `retries` with exponential backoff; honor `Retry-After` on 429/503. Reject non-HTTPS URLs and redirects whose final URL is not HTTPS. Stream chunks to `dest.with_suffix(dest.suffix + ".part")` inside the URL lock, hash while writing, validate `Content-Type` against `expected_types` (default: `application/zip`, `application/x-spss-sav`, `application/octet-stream`, `application/pdf`), then `os.replace`. On failure delete the `.part` file and raise `DownloadError` with the URL.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_fetch.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pyafrobarometer/fetch.py tests/test_fetch.py
git commit -m "feat: add retrying atomic downloads"
```

---

### Task 4: SPSS/ZIP I/O with traversal protection

**Files:**
- Create: `src/pyafrobarometer/io.py`
- Test: `tests/test_io.py`

**Interfaces:**
- Produces:
  - `safe_extract_sav(archive: Path, dest_dir: Path) -> Path` (returns the single `.sav` path)
  - `read_metadata(path: Path) -> dict[str, Any]`
  - `read_frame(path: Path, *, usecols: Sequence[str] | None = None, apply_value_labels: bool = False) -> tuple[pd.DataFrame, dict[str, Any]]`
- Consumes: nothing from earlier tasks except `CacheError`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_io.py
import zipfile
import pandas as pd, pyreadstat, pytest
from pyafrobarometer import io
from pyafrobarometer.errors import CacheError

def make_sav(path):
    df = pd.DataFrame({"COUNTRY": [3, 14], "Q37A": [0, 9]})
    pyreadstat.write_sav(df, str(path), column_labels=["Country", "Trust president"],
        variable_value_labels={"COUNTRY": {3: "Benin", 14: "Ghana"},
                               "Q37A": {0: "Not at all", 3: "A lot", 9: "Don't know"}})

def test_read_metadata_and_frame(tmp_path):
    p = tmp_path / "x.sav"; make_sav(p)
    meta = io.read_metadata(p)
    assert meta["column_names"] == ["COUNTRY", "Q37A"]
    assert meta["variable_value_labels"]["COUNTRY"][3.0] == "Benin"
    df, _ = io.read_frame(p, usecols=["Q37A"])
    assert list(df.columns) == ["Q37A"]

def test_extract_rejects_traversal(tmp_path):
    archive = tmp_path / "x.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("../evil.sav", b"x")
        z.writestr("data.sav", b"y")
    out = io.safe_extract_sav(archive, tmp_path / "out")
    assert out.name == "data.sav"
    assert not (tmp_path / "evil.sav").exists()

def test_extract_requires_a_sav(tmp_path):
    archive = tmp_path / "x.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("readme.txt", b"x")
    with pytest.raises(CacheError):
        io.safe_extract_sav(archive, tmp_path / "out")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_io.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `io.py`**

`read_metadata` calls `pyreadstat.read_sav(str(path), metadataonly=True)` and returns the second element (the first may be `None` or an empty DataFrame). `read_frame` calls `pyreadstat.read_sav(str(path), usecols=list(usecols) if usecols else None, apply_value_labels=apply_value_labels)`. `safe_extract_sav` resolves each member path and verifies it stays under `dest_dir`; extract only `.sav` members (case-insensitive); raise `CacheError` if zero or more than one `.sav` is found.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_io.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pyafrobarometer/io.py tests/test_io.py
git commit -m "feat: add SPSS and zip I/O with traversal protection"
```

---

### Task 5: Catalog parsing

**Files:**
- Create: `src/pyafrobarometer/catalog.py`
- Create: `tests/fixtures/merged_data.html`, `tests/fixtures/data_sets.html`, `tests/fixtures/resource_page.html`
- Test: `tests/test_catalog_parsing.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) CatalogEntry(kind, round, country, year, language, data_url, codebook_url, page_url, filename, size_bytes)`
  - `parse_merged_index(html: str, base_url: str) -> list[CatalogEntry]`
  - `parse_country_index(html: str, base_url: str) -> list[CatalogEntry]`
  - `extract_resource_links(html: str, base_url: str) -> tuple[str | None, str | None]`
  - `validate_catalog(entries: Sequence[CatalogEntry]) -> None`
- Consumes: nothing.

- [ ] **Step 1: Create fixtures and write the failing tests**

`tests/fixtures/merged_data.html` must contain anchors with these hrefs and texts:
`/wp-content/uploads/2026/10/AB_R10.Merge-Dataset_25Feb26.38ctry.release.sav.zip` ("Merged Round 10 data (38 countries) (2025)"), `/wp-content/uploads/2026/10/AB_R10.Merge-Dataset_25Feb26.38ctry.release.Fr_.sav.zip` ("Données fusionnées de la Série 10 (38 pays) (2025)"), `/survey-resource/merged-round-9-data-39-countries-2023/` ("Merged Round 9 data (39 countries) (2023)"), and `/survey-resource/merged-round-5-data-34-countries-2015/` ("Merged Round 5 data (34 countries) (2011-2013) (last update: July 2015)").

`tests/fixtures/data_sets.html` must contain `/survey-resource/south-africa-round-10-data-2026/` ("South Africa Round 10 data (2026)").

`tests/fixtures/resource_page.html` must contain `/wp-content/uploads/2022/02/r7_merged_data_34ctry.release.sav` and `/wp-content/uploads/2023/02/r7_merged.codebook_final_14dec20-1-1.pdf`.

```python
# tests/test_catalog_parsing.py
import dataclasses
import pytest
from pyafrobarometer import catalog
from pyafrobarometer.errors import CatalogError

BASE = "https://www.afrobarometer.org"

def read(name):
    return open(f"tests/fixtures/{name}", encoding="utf-8").read()

def test_parse_merged_entries():
    entries = catalog.parse_merged_index(read("merged_data.html"), BASE)
    r10 = next(e for e in entries if e.round == 10 and e.language == "en")
    assert r10.kind == "merged" and r10.country is None and r10.year == 2025
    assert r10.data_url.endswith(".sav.zip") and r10.filename.endswith(".sav.zip")
    assert any(e.round == 10 and e.language == "fr" for e in entries)
    r9 = next(e for e in entries if e.round == 9)
    assert r9.data_url == BASE + "/survey-resource/merged-round-9-data-39-countries-2023/"
    assert r9.page_url == r9.data_url
    r5 = next(e for e in entries if e.round == 5)
    assert r5.year == 2011 and r5.data_url.endswith("/merged-round-5-data-34-countries-2015/")

def test_parse_country_entry():
    entries = catalog.parse_country_index(read("data_sets.html"), BASE)
    assert entries[0].kind == "country"
    assert entries[0].country == "South Africa" and entries[0].round == 10 and entries[0].year == 2026

def test_extract_resource_links():
    data, codebook = catalog.extract_resource_links(read("resource_page.html"), BASE)
    assert data.endswith("r7_merged_data_34ctry.release.sav")
    assert codebook.endswith(".pdf")

def test_empty_html_raises():
    with pytest.raises(CatalogError):
        catalog.parse_merged_index("<html></html>", BASE)

def test_validate_rejects_non_afrobarometer_urls():
    good = catalog.parse_merged_index(read("merged_data.html"), BASE)
    bad = dataclasses.replace(good[0], data_url="https://evil.test/x.sav")
    with pytest.raises(CatalogError):
        catalog.validate_catalog([bad])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_catalog_parsing.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement parsing**

Use BeautifulSoup with selectors defined in one `SELECTORS` table at module top. Detect merged titles with `Merged Round (?P<round>\d+) data \((\d+) countries?\) \((?P<year>\d{4})(?:-\d{4})?\)` and French titles with `Série (?P<round>\d+)` / "Données fusionnées"; for English merged titles use the year in the countries parenthetical (R5 is `(2011-2013)`, taking 2011), and for French titles use the final `(YYYY)`. Detect French by a French title or a filename containing `.Fr_`/`French`; otherwise `"en"`. Detect country titles with `^(?P<country>.+?) Round (?P<round>\d+) data \((?P<year>\d{4})\)$`. Join relative hrefs with the page URL using `urllib.parse.urljoin`. A file href is one ending in `.sav`, `.sav.zip`, or `.dta`; otherwise it is a resource page. `extract_resource_links` returns the first data link and first PDF link. `validate_catalog` raises `CatalogError` when the list is empty, has no merged entry, or any URL is not HTTPS on `www.afrobarometer.org`.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_catalog_parsing.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pyafrobarometer/catalog.py tests/test_catalog_parsing.py tests/fixtures
git commit -m "feat: parse merged, country, and resource catalog pages"
```

---

### Task 6: Catalog resolution with cache and baked manifest

**Files:**
- Modify: `src/pyafrobarometer/catalog.py`
- Create: `src/pyafrobarometer/manifest.json`
- Test: `tests/test_catalog_resolution.py`

**Interfaces:**
- Produces:
  - `MERGED_INDEX_URL`, `DATASETS_INDEX_URL`, `MANIFEST_PATH`
  - `load_baked_manifest() -> list[CatalogEntry]`
  - `resolve_catalog(*, refresh: bool = False) -> list[CatalogEntry]`
- Consumes: `cache.is_fresh`, `cache.read_state`, `cache.write_state`, `cache.cache_file`; `fetch.fetch_text`; all parsing functions from Task 5.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_catalog_resolution.py
import dataclasses, time
import pytest
from pyafrobarometer import cache, catalog
from pyafrobarometer.errors import CatalogError

BASE = "https://www.afrobarometer.org"

def entries_html():
    return ('<a href="/wp-content/uploads/2026/10/AB_R10.Merge-Dataset_25Feb26.38ctry.release.sav.zip">'
            'Merged Round 10 data (38 countries) (2025)</a>')

def resource_html():
    return ('<a href="/wp-content/uploads/2022/02/r7_merged_data_34ctry.release.sav">Data</a>'
            '<a href="/wp-content/uploads/2023/02/r7_merged.codebook_final_14dec20-1-1.pdf">Codebook</a>')

def write_index(entries, fetched_at):
    import json
    cache.cache_file("index/catalog.json").write_text(
        json.dumps({"fetched_at": fetched_at, "entries": entries}))

def test_fresh_cache_skips_network(tmp_path, monkeypatch):
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path))
    entry = dataclasses.asdict(catalog.parse_merged_index(entries_html(), BASE)[0])
    write_index([entry], time.time())
    monkeypatch.setattr(catalog, "fetch_text", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network")))
    assert catalog.resolve_catalog()[0].round == 10

def test_stale_cache_refreshes_and_saves(tmp_path, monkeypatch):
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path))
    write_index([], 0)
    html = entries_html() + '<a href="/survey-resource/merged-round-9-data-39-countries-2023/">Merged Round 9 data (39 countries) (2023)</a>'
    monkeypatch.setattr(catalog, "fetch_text", lambda *a, **k: html)
    out = catalog.resolve_catalog()
    assert {e.round for e in out} == {9, 10}
    assert cache.read_state()["index_source"] == "live"

def test_resource_page_is_followed(tmp_path, monkeypatch):
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path))
    write_index([], 0)
    merged = '<a href="/survey-resource/merged-round-7-data-34-countries-2019/">Merged Round 7 data (34 countries) (2019)</a>'
    def fake_fetch(url, *a, **k):
        if "merged-data" in url:
            return merged
        if "data-sets" in url:
            return "<html></html>"
        if "survey-resource" in url:
            return resource_html()
        raise AssertionError(url)
    monkeypatch.setattr(catalog, "fetch_text", fake_fetch)
    entry = catalog.resolve_catalog()[0]
    assert entry.data_url.endswith("r7_merged_data_34ctry.release.sav")
    assert entry.codebook_url.endswith(".pdf")

def test_refresh_failure_uses_stale_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path))
    entry = dataclasses.asdict(catalog.parse_merged_index(entries_html(), BASE)[0])
    write_index([entry], 0)
    monkeypatch.setattr(catalog, "fetch_text", lambda *a, **k: (_ for _ in ()).throw(CatalogError("down")))
    with pytest.warns(UserWarning):
        assert catalog.resolve_catalog()[0].round == 10

def test_no_cache_failure_uses_baked_manifest(tmp_path, monkeypatch):
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(catalog, "fetch_text", lambda *a, **k: (_ for _ in ()).throw(CatalogError("down")))
    out = catalog.resolve_catalog()
    assert out and all(e.kind == "merged" for e in out)

def test_empty_parse_falls_back(tmp_path, monkeypatch):
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(catalog, "fetch_text", lambda *a, **k: "<html></html>")
    assert catalog.resolve_catalog()

def test_offline_uses_baked_manifest_without_network(tmp_path, monkeypatch):
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("PYAFROBAROMETER_OFFLINE", "1")
    monkeypatch.setattr(catalog, "fetch_text", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network")))
    assert catalog.resolve_catalog()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_catalog_resolution.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement resolution and seed manifest**

`resolve_catalog` reads `index/catalog.json` with keys `fetched_at` (float) and `entries` (list of entry dicts); if `fetched_at` is fresh and not `refresh`, reconstruct entries and return. Otherwise fetch both index pages with `fetch_text`, parse and merge, then follow one resource-page level for entries whose `data_url` is not a file; validate; write `index/catalog.json` atomically and set `state["index_source"] = "live"`; return. On any fetch/parse/validation failure, use stale entries with `warnings.warn(...)`; if none, use `load_baked_manifest()`. When `PYAFROBAROMETER_OFFLINE=1`, skip network entirely. Seed `manifest.json` with `{"version": 1, "generated_at": "2026-10-25", "entries": [R8_entry, R9_entry, R10_entry]}` where those are the three entries below (Task 12 regenerates the full file):
- R8: data `https://www.afrobarometer.org/wp-content/uploads/2023/03/afrobarometer_release-dataset_merge-34ctry_r8_en_2023-03-01.sav`, codebook `https://www.afrobarometer.org/wp-content/uploads/2025/07/R8_Merge-Codebook_28May24.final_.pdf`, year 2022.
- R9: data `https://www.afrobarometer.org/wp-content/uploads/2025/06/R9.Merge_39ctry.20Nov23.final_.release_Updated.4Jun25-3.sav`, codebook `https://www.afrobarometer.org/wp-content/uploads/2025/07/AB_R9.MergeCodebook_25Jun24.final_.pdf`, year 2023.
- R10: data `https://www.afrobarometer.org/wp-content/uploads/2026/10/AB_R10.Merge-Dataset_25Feb26.38ctry.release.sav.zip`, codebook `https://www.afrobarometer.org/wp-content/uploads/2026/10/Merge_Round_10_Codebook_09.09.26.pdf`, year 2025.

`load_baked_manifest` validates and returns these entries.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_catalog_resolution.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pyafrobarometer/catalog.py src/pyafrobarometer/manifest.json tests/test_catalog_resolution.py
git commit -m "feat: resolve catalog with TTL cache and baked fallback"
```

---

### Task 7: Metadata and the Dataset object

**Files:**
- Create: `src/pyafrobarometer/metadata.py`, `src/pyafrobarometer/dataset.py`
- Test: `tests/test_metadata.py`, `tests/test_dataset.py`

**Interfaces:**
- Produces:
  - `variable_info(meta: Mapping[str, Any]) -> pd.DataFrame` with columns `name`, `label`, `value_labels`, `missing_codes`.
  - `missing_codes(meta, column) -> list[int]`, `value_labels(meta, column) -> dict[int, str]`, `decode_column(series, labels) -> pd.Series`, `normalize_missing(df, meta, columns=None) -> pd.DataFrame`.
  - `@dataclass(frozen=True) Provenance(source_urls, retrieved_at, rounds, countries, language, years=(), codebook_path=None)`
  - `Dataset(df, *, variables, provenance, meta, source_map=None, harmonized=False)` with `rounds`, `countries`, `provenance`, `variables()`, `to_pandas(labels=False, normalize_missing=False)`, `subset(countries=None, columns=None)`, `citation()`, `codebook()`, `__getattr__`, `__getitem__`, `__len__`, `__iter__`, `__repr__`, and pickle support. `source_map` maps output columns (canonical/family names) to their source variable for metadata lookups.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_metadata.py
import pandas as pd
from pyafrobarometer import metadata

META = {
    "column_names": ["COUNTRY", "Q37A", "Q1"],
    "column_labels": ["Country", "Trust president", "Age"],
    "variable_value_labels": {"COUNTRY": {3.0: "Benin", 9.0: "Côte d'Ivoire"},
                              "Q37A": {0.0: "Not at all", 3.0: "A lot", 8.0: "Refused",
                                       9.0: "Don't know", -1.0: "Missing"}},
    "missing_ranges": {"Q37A": {"lo": 8.0, "hi": 9.0}},
}

def test_variable_info():
    info = metadata.variable_info(META)
    assert list(info.columns) == ["name", "label", "value_labels", "missing_codes"]
    assert info.loc[info.name == "Q37A", "label"].item() == "Trust president"

def test_missing_codes_merges_metadata_and_fallback():
    codes = metadata.missing_codes(META, "Q37A")
    assert {8, 9, -1}.issubset(codes)
    assert 0 not in codes and 3 not in codes

def test_normalize_missing():
    df = pd.DataFrame({"Q37A": [0, 8, 9, -1]})
    out = metadata.normalize_missing(df, META, ["Q37A"])
    assert out["Q37A"].isna().tolist() == [False, True, True, True]

def test_decode_column_keeps_unknown_codes():
    out = metadata.decode_column(pd.Series([3, 9]), META["variable_value_labels"]["COUNTRY"])
    assert out.tolist() == ["Benin", "Côte d'Ivoire"]
```

```python
# tests/test_dataset.py
import pickle
import pandas as pd, pytest
from pyafrobarometer.dataset import Dataset, Provenance
from pyafrobarometer import metadata

META = {"column_names": ["COUNTRY", "Q37A"], "column_labels": ["Country", "Trust"],
        "variable_value_labels": {"COUNTRY": {3.0: "Benin"}, "Q37A": {0.0: "No", 9.0: "DK"}},
        "missing_ranges": {}}

def make():
    df = pd.DataFrame({"COUNTRY": [3, 3], "Q37A": [0, 9]})
    prov = Provenance(("https://www.afrobarometer.org/x.sav",), "2026-10-25T00:00:00Z", (9,), ("Benin",), "en")
    return Dataset(df, variables=metadata.variable_info(META), provenance=prov, meta=META)

def test_delegation_and_getitem():
    ds = make()
    assert list(ds.columns) == ["COUNTRY", "Q37A"]
    assert len(ds) == 2 and ds["Q37A"].tolist() == [0, 9]
    assert ds.head(1).shape == (1, 2)

def test_to_pandas_modes():
    ds = make()
    assert ds.to_pandas()["Q37A"].tolist() == [0, 9]
    assert ds.to_pandas(normalize_missing=True)["Q37A"].isna().tolist() == [False, True]
    labelled = ds.to_pandas(labels=True)
    assert labelled["Q37A"].astype(str).tolist() == ["No", "DK"]

def test_source_map_applies_metadata_to_a_family_column():
    df = pd.DataFrame({"Q37A": [0, 9], "trust_president": [0, 9]})
    prov = Provenance(("https://www.afrobarometer.org/x.sav",), "2026-10-25T00:00:00Z", (9,), ("Benin",), "en")
    ds = Dataset(df, variables=metadata.variable_info(META), provenance=prov, meta=META,
                 source_map={"Q37A": "Q37A", "trust_president": "Q37A"})
    out = ds.to_pandas(normalize_missing=True, labels=True)
    assert out["trust_president"].astype(str).tolist() == ["No", "<NA>"]

def test_subset_and_pickle():
    ds = make()
    assert ds.subset(countries=["Benin"], columns=["Q37A"]).to_pandas().shape == (2, 1)
    assert pickle.loads(pickle.dumps(ds)).to_pandas().equals(ds.to_pandas())

def test_variables_frame_available():
    assert set(make().variables()["name"]) == {"COUNTRY", "Q37A"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_metadata.py tests/test_dataset.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement metadata and Dataset**

`missing_codes` unions declared `missing_ranges` (`lo`..`hi`) plus user-missing values if present in the meta dict (`missing_user_values`, keyed by column) plus the fallback set `{8, 9, 97, 98, 99, 997, 998, 999, -1}` only when that code appears in the column's value-label keys or the column's observed values are unavailable; to stay deterministic in tests, union fallback codes that are present in `variable_value_labels[column]` or listed in `missing_ranges`. `normalize_missing` replaces those codes with `pd.NA` using `Series.where`. `decode_column` maps known codes to labels, leaves unknown codes unchanged, and returns an `object`/`category` series.

`Dataset.to_pandas` copies `_df`; for each column it resolves metadata through `source_map.get(column, column)`, applies `normalize_missing` first when requested, then labels. Add a test in this task that a column named `trust_president` with a `source_map={"trust_president": "Q37A"}` normalizes `9` to `pd.NA` and labels `0` as `"No"`. `__getattr__` delegates only non-underscore names to `_df` and raises `AttributeError` otherwise. `countries` returns `provenance.countries`; `subset` filters by the canonical `country` column when present, otherwise raises `HarmonizationError` with a message telling the caller to load with `harmonize=True`. `codebook()` raises `CodebookError` when `provenance.codebook_path` is `None`.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_metadata.py tests/test_dataset.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pyafrobarometer/metadata.py src/pyafrobarometer/dataset.py tests/test_metadata.py tests/test_dataset.py
git commit -m "feat: add metadata helpers and Dataset wrapper"
```

---

### Task 8: Canonical crosswalk and missing-code normalization

**Files:**
- Create: `src/pyafrobarometer/crosswalk/canonical.yaml`
- Create: `src/pyafrobarometer/harmonize/__init__.py`, `canonical.py`, `crosswalk.py`, `normalize.py`
- Test: `tests/test_canonical.py`

**Interfaces:**
- Produces:
  - `SUPPORTED_ROUNDS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)`
  - `@dataclass(frozen=True) Mapping(var: str, decode_country: bool = False, recode: Mapping[int, int] | None = None)`
  - `canonical_map() -> dict[str, dict[int, Mapping]]`
  - `apply_canonical(df, *, round_number: int, meta) -> tuple[pd.DataFrame, dict[str, str]]`
- Consumes: `metadata.decode_column`, `metadata.normalize_missing`.

- [ ] **Step 1: Write `canonical.yaml` with the verified table**

```yaml
canonical:
  country:
    var: COUNTRY
    decode_country: true
    1: {var: country}
    2: {var: country}
    3: {var: country}
    5: {var: COUNTRY_ALPHA, decode_country: false}
  respondent_id: {var: RESPNO, 1: {var: refnumb}, 2: {var: respno}, 3: {var: respno}}
  region: {var: REGION, 1: {var: area}, 2: {var: region}, 3: {var: region}}
  urban_rural: {var: URBRUR, 1: {var: urbrur}, 2: {var: urbrur}, 3: {var: urbrur}}
  age: {var: Q1, 1: {var: age}, 2: {var: Q80}}
  gender: {var: Q101, 1: {var: gender}, 2: {var: Q96}, 9: {var: Q100}}
  education: {var: Q97, 1: {var: educ}, 2: {var: Q84}, 3: {var: Q90}, 4: {var: Q89}, 9: {var: Q94}, 10: {var: Q96}}
  interview_date: {var: DATEINTR, 1: null, 2: {var: dateintr}, 3: {var: dateintr}}
  weight: {var: withinwt, 4: {var: Withinwt}, 8: {var: withinwt_ea}, 9: {var: withinwt_ea}, 10: {var: withinwt_ea}}
```

The loader treats top-level keys `var`/`decode_country`/`recode` as defaults for all rounds, numeric keys as per-round overrides, and a `null` override as "not available in this round".

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_canonical.py
import pandas as pd, pytest
from pyafrobarometer.harmonize import canonical
from pyafrobarometer.harmonize.crosswalk import canonical_map

def meta_for(names):
    country_labels = {3.0: "Benin", 14.0: "Ghana"}
    return {"column_names": names, "column_labels": names,
            "variable_value_labels": {"COUNTRY": country_labels, "country": country_labels,
                                      "Q37A": {0.0: "No", 9.0: "DK"}},
            "missing_ranges": {}}

def test_crosswalk_verified_values():
    m = canonical_map()
    assert m["country"][1].var == "country" and m["country"][5].var == "COUNTRY_ALPHA"
    assert not m["country"][5].decode_country and m["country"][9].decode_country
    assert m["respondent_id"][1].var == "refnumb" and m["respondent_id"][2].var == "respno"
    assert m["weight"][4].var == "Withinwt" and m["weight"][8].var == "withinwt_ea"
    assert m["gender"][9].var == "Q100" and m["education"][4].var == "Q89"
    assert 1 not in m["interview_date"]

def test_apply_canonical_r1():
    df = pd.DataFrame({"country": [3, 14], "refnumb": ["A", "B"], "area": [1, 2],
                       "urbrur": [1, 2], "age": [30, 40], "gender": [1, 2],
                       "educ": [3, 4], "withinwt": [1.0, 2.0]})
    out, mapping = canonical.apply_canonical(df, round_number=1, meta=meta_for(list(df.columns)))
    assert out["country"].tolist() == ["Benin", "Ghana"]
    assert out["respondent_id"].tolist() == ["A", "B"]
    assert mapping["weight"] == "withinwt" and "interview_date" not in mapping

def test_apply_canonical_r9():
    df = pd.DataFrame({"COUNTRY": [3, 14], "RESPNO": ["A", "B"], "REGION": [1, 2],
                       "URBRUR": [1, 2], "Q1": [30, 40], "Q100": [1, 2],
                       "Q94": [3, 4], "DATEINTR": ["x", "y"], "withinwt_ea": [1.0, 2.0],
                       "Q37A": [0, 9]})
    out, mapping = canonical.apply_canonical(df, round_number=9, meta=meta_for(list(df.columns)))
    assert out["country"].tolist() == ["Benin", "Ghana"]
    assert out["gender"].tolist() == [1, 2]
    assert out["education"].tolist() == [3, 4]
    assert out["weight"].tolist() == [1.0, 2.0]
    assert mapping["education"] == "Q94"

def test_missing_mapping_is_omitted_with_warning():
    df = pd.DataFrame({"COUNTRY": [3]})
    with pytest.warns(UserWarning):
        out, mapping = canonical.apply_canonical(df, round_number=9, meta=meta_for(["COUNTRY"]))
    assert "age" not in out.columns and "age" not in mapping
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_canonical.py -v`
Expected: FAIL.

- [ ] **Step 4: Implement the crosswalk loader and canonical application**

Load YAML with `importlib.resources.files("pyafrobarometer").joinpath("crosswalk/canonical.yaml")` and `yaml.safe_load`. Expand top-level defaults across `SUPPORTED_ROUNDS` (1–10), apply numeric overrides, and skip rounds mapped to `null`. `apply_canonical` keeps all source columns, adds canonical columns, decodes country when requested, and returns a canonical→source mapping. When a mapped source variable is absent, emit a warning and omit that canonical column. For the canonical `weight` column, use `withinwt_hh` when present, otherwise the mapped variable, and record the chosen source in the mapping.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/test_canonical.py -v`
Expected: PASS.

```bash
git add src/pyafrobarometer/crosswalk/canonical.yaml src/pyafrobarometer/harmonize tests/test_canonical.py pyproject.toml
git commit -m "feat: add canonical schema crosswalk and application"
```

---

### Task 9: Question-family harmonization

**Files:**
- Create: `src/pyafrobarometer/crosswalk/questions.yaml`
- Modify: `src/pyafrobarometer/harmonize/crosswalk.py`, `src/pyafrobarometer/harmonize/canonical.py`
- Test: `tests/test_questions.py`

**Interfaces:**
- Produces:
  - `family_map() -> dict[str, dict[int, Mapping]]`
  - `family_rounds(family: str) -> list[int]`
  - `apply_families(df, *, round_number: int, families: Sequence[str], strict: bool = True) -> tuple[pd.DataFrame, dict[str, str]]`

- [ ] **Step 1: Write `questions.yaml` from the verified table**

```yaml
families:
  trust_president:
    description: Trust in the President
    rounds:
      1: {var: trspre, recode: {1: 0, 2: 1, 3: 2, 4: 3}}
      2: Q43A
      3: Q55A
      4: Q49A
      5: Q59A
      6: Q52A
      7: Q43A
      8: Q41A
      9: Q37A
      10: Q37A
  trust_parliament:
    description: Trust in Parliament
    rounds: {2: Q43B, 3: Q55B, 4: Q49B, 5: Q59B, 6: Q52B, 7: Q43B, 8: Q41B, 9: Q37B, 10: Q37B}
  trust_police:
    description: Trust in the Police
    rounds:
      1: {var: trspol, recode: {1: 0, 2: 1, 3: 2, 4: 3}}
      2: Q43I
      3: Q55H
      4: Q49G
      5: Q59H
      6: Q52H
      7: Q43G
      8: Q41G
      9: Q37G
      10: Q37G
  trust_courts:
    description: Trust in Courts of Law
    rounds:
      1: {var: trscts, recode: {1: 0, 2: 1, 3: 2, 4: 3}}
      2: Q43J
      3: Q55I
      4: Q49H
      5: Q59J
      6: Q52J
      7: Q43I
      8: Q41I
      9: Q37I
      10: Q37I
  trust_electoral_commission:
    description: Trust in the Electoral Commission
    rounds:
      1: {var: trsnec, recode: {1: 0, 2: 1, 3: 2, 4: 3}}
      2: Q43C
      3: Q55C
      4: Q49C
      5: Q59C
      6: Q52C
      7: Q43C
      8: Q41C
      9: Q37C
      10: Q37C
  trust_army:
    description: Trust in the Army
    rounds:
      1: {var: trsarm, recode: {1: 0, 2: 1, 3: 2, 4: 3}}
      2: Q43H
      3: Q55G
      5: Q59I
      6: Q52I
      7: Q43H
      8: Q41H
      9: Q37H
      10: Q37H
  trust_ruling_party:
    description: Trust in the Ruling Party
    rounds: {2: Q43F, 3: Q55E, 4: Q49E, 5: Q59F, 6: Q52F, 7: Q43E, 8: Q41E, 9: Q37E, 10: Q37E}
  trust_opposition:
    description: Trust in Opposition Parties
    rounds: {2: Q43G, 3: Q55F, 4: Q49F, 5: Q59G, 6: Q52G, 7: Q43F, 8: Q41F, 9: Q37F, 10: Q37F}
  support_democracy:
    description: Support for Democracy
    rounds: {2: Q38, 3: Q37, 4: Q30, 5: Q32, 6: Q30, 7: Q28, 8: Q21, 9: Q23, 10: Q22}
  reject_one_party_rule:
    description: Reject One-Party Rule
    rounds: {2: Q35A, 3: Q36A, 4: Q29A, 5: Q31A, 6: Q28A, 7: Q27A, 8: Q20A, 9: Q22A, 10: Q21A}
  reject_military_rule:
    description: Reject Military Rule
    rounds: {2: Q35C, 3: Q36B, 4: Q29B, 5: Q31B, 6: Q28B, 7: Q27B, 8: Q20B, 9: Q22B, 10: Q21B}
  reject_one_man_rule:
    description: Reject One-Man Rule
    rounds: {2: Q35D, 3: Q36C, 4: Q29C, 5: Q31C, 6: Q28C, 7: Q27C, 8: Q20C, 9: Q22C, 10: Q21C}
  satisfaction_democracy:
    description: Satisfaction with Democracy
    rounds: {2: Q40, 3: Q47, 4: Q43, 5: Q43, 6: Q41, 7: Q36, 8: Q37, 9: Q31, 10: Q33}
  corruption_president:
    description: Corruption in the Presidency
    rounds: {2: Q51A, 3: Q56A, 4: Q50A, 5: Q60A, 6: Q53A, 7: Q44A, 8: Q42A, 9: Q38A, 10: Q38A}
  corruption_police:
    description: Corruption in the Police
    rounds: {2: Q51D, 3: Q56F, 4: Q50E, 5: Q60E, 6: Q53E, 7: Q44E, 8: Q42E, 9: Q38E, 10: Q38E}
  corruption_judges:
    description: Corruption among Judges and Magistrates
    rounds: {2: Q51F, 3: Q56H, 4: Q50G, 5: Q60G, 6: Q53G, 7: Q44F, 8: Q42F, 9: Q38F, 10: Q38F}
  bribe_police:
    description: Paid a Bribe to Avoid a Problem with the Police
    rounds: {6: Q55J, 7: Q49T, 8: Q44N, 9: Q43E, 10: Q45E}
  radio_news:
    description: Radio News Frequency
    rounds: {2: Q26A, 3: Q15A, 4: Q12A, 5: Q13A, 6: Q12A, 7: Q12A, 8: Q55A, 9: Q74A, 10: Q65A}
  television_news:
    description: Television News Frequency
    rounds: {2: Q26B, 3: Q15B, 4: Q12B, 5: Q13B, 6: Q12B, 7: Q12B, 8: Q55B, 9: Q74B, 10: Q65B}
  newspaper_news:
    description: Newspaper News Frequency
    rounds: {2: Q26C, 3: Q15C, 4: Q12C, 5: Q13C, 6: Q12C, 7: Q12C, 8: Q55C, 9: Q74C, 10: Q65C}
  internet_news:
    description: Internet News Frequency
    rounds: {5: Q13D, 6: Q12D, 7: Q12D, 8: Q55D, 9: Q74D, 10: Q65E}
  social_media_news:
    description: Social Media News Frequency
    rounds: {6: Q12E, 7: Q12E, 8: Q55E, 9: Q74E, 10: Q65D}
  internet_use:
    description: Internet Use Frequency
    rounds: {4: Q88C, 5: Q91B, 6: Q92B, 7: Q91B, 8: Q92I, 9: Q90I, 10: Q90J}
  econ_country_present:
    description: Country's Present Economic Condition
    rounds: {2: Q1A, 3: Q4A, 4: Q4A, 5: Q3A, 6: Q4A, 7: Q4A, 8: Q4A, 9: Q4A, 10: Q4A}
  econ_personal_present:
    description: Personal Present Living Conditions
    rounds: {2: Q1B, 3: Q4B, 4: Q4B, 5: Q3B, 6: Q4B, 7: Q4B, 8: Q4B, 9: Q4B, 10: Q4B}
  lived_poverty_food:
    description: Went Without Food
    rounds: {2: Q9A, 3: Q8A, 4: Q8A, 5: Q8A, 6: Q8A, 7: Q8A, 8: Q7A, 9: Q6A, 10: Q7A}
  lived_poverty_water:
    description: Went Without Water
    rounds: {2: Q9B, 3: Q8B, 4: Q8B, 5: Q8B, 6: Q8B, 7: Q8B, 8: Q7B, 9: Q6B, 10: Q7B}
  lived_poverty_medical:
    description: Went Without Medical Care
    rounds: {2: Q9C, 3: Q8C, 4: Q8C, 5: Q8C, 6: Q8C, 7: Q8C, 8: Q7C, 9: Q6C, 10: Q7C}
  lived_poverty_fuel:
    description: Went Without Cooking Fuel
    rounds: {2: Q9E, 3: Q8D, 4: Q8D, 5: Q8D, 6: Q8D, 7: Q8D, 8: Q7D, 9: Q6D, 10: Q7D}
  free_to_say:
    description: Freedom to Say What You Think
    rounds: {4: Q15A, 5: Q17A, 6: Q15A, 7: Q14, 8: Q10A, 9: Q9A, 10: Q10A}
  felt_unsafe_walking:
    description: Felt Unsafe Walking in the Neighbourhood
    rounds: {5: Q9A, 6: Q10A, 7: Q10A, 8: Q8A, 9: Q7A, 10: Q9}
  neighbours_homosexuals:
    description: Would Not Like Homosexual Neighbours
    rounds: {6: Q89C, 7: Q87C, 8: Q86C, 9: Q87C, 10: Q88C}
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_questions.py
import pandas as pd, pytest
from pyafrobarometer.harmonize import canonical
from pyafrobarometer.harmonize.crosswalk import family_map, family_rounds
from pyafrobarometer.errors import HarmonizationError

def test_verified_family_mappings():
    m = family_map()
    assert m["trust_president"][5].var == "Q59A"
    assert m["trust_president"][9].var == "Q37A"
    assert m["trust_president"][1].recode == {1: 0, 2: 1, 3: 2, 4: 3}
    assert m["trust_police"][7].var == "Q43G"
    assert m["satisfaction_democracy"][9].var == "Q31"
    assert m["social_media_news"][6].var == "Q12E"
    assert family_rounds("trust_courts") == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert family_rounds("trust_army") == [1, 2, 3, 5, 6, 7, 8, 9, 10]
    assert family_rounds("social_media_news") == [6, 7, 8, 9, 10]
    assert family_rounds("neighbours_homosexuals") == [6, 7, 8, 9, 10]

def test_apply_families():
    df = pd.DataFrame({"Q37A": [0, 3], "Q37B": [1, 2]})
    out, mapping = canonical.apply_families(df, round_number=9,
                                            families=["trust_president", "trust_parliament"])
    assert out.columns.tolist() == ["Q37A", "Q37B", "trust_president", "trust_parliament"]
    assert mapping == {"trust_president": "Q37A", "trust_parliament": "Q37B"}

def test_r1_trust_recode():
    df = pd.DataFrame({"trspre": [1, 2, 3, 4]})
    out, mapping = canonical.apply_families(df, round_number=1, families=["trust_president"])
    assert out["trust_president"].tolist() == [0, 1, 2, 3]
    assert mapping["trust_president"] == "trspre"

def test_missing_family_strict_raises_with_available_rounds():
    df = pd.DataFrame({"Q40": [0]})
    with pytest.raises(HarmonizationError, match="available in rounds"):
        canonical.apply_families(df, round_number=1, families=["satisfaction_democracy"])

def test_missing_family_non_strict_adds_nan():
    df = pd.DataFrame({"Q37A": [0]})
    with pytest.warns(UserWarning):
        out, mapping = canonical.apply_families(df, round_number=1,
                                                families=["social_media_news"], strict=False)
    assert out["social_media_news"].isna().all() and "social_media_news" not in mapping
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_questions.py -v`
Expected: FAIL.

- [ ] **Step 4: Implement family loading and application**

Parse `questions.yaml` so each round value may be a bare variable string or `{var, recode}`; build `Mapping(var=<source variable>, recode=<dict or None>)`. `apply_families` adds a column named after the family when the source var exists, applying `Series.map(lambda v: recode.get(v, v))` first when a recode is present. On missing var, `strict=True` raises `HarmonizationError` with the message `"<family> is available in rounds [..] but not round <n>"`, `strict=False` warns and adds a column of `pd.NA` without adding a mapping entry.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/test_questions.py -v`
Expected: PASS.

```bash
git add src/pyafrobarometer/crosswalk/questions.yaml src/pyafrobarometer/harmonize tests/test_questions.py
git commit -m "feat: add question-family harmonization"
```

---

### Task 10: Variable search and codebooks

**Files:**
- Create: `src/pyafrobarometer/search.py`, `src/pyafrobarometer/codebook.py`
- Create: `src/pyafrobarometer/metadata_index.json`
- Test: `tests/test_search.py`, `tests/test_codebook.py`

**Interfaces:**
- Produces:
  - `load_index() -> pd.DataFrame` with columns `name, label, round, kind, family, source_var, value_labels`.
  - `search_variables(query, *, rounds=None, limit=20, fuzzy=True, index=None) -> pd.DataFrame`
  - `get_codebook(entry: CatalogEntry) -> Path`
  - `extract_text(path: Path) -> str`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_search.py
import pandas as pd
from pyafrobarometer import search

INDEX = pd.DataFrame([
    {"name": "Q37A", "label": "Q37a. Trust president", "round": 9, "kind": "question",
     "family": "trust_president", "source_var": None, "value_labels": "{}"},
    {"name": "Q41A", "label": "Q41a. Trust president", "round": 8, "kind": "question",
     "family": "trust_president", "source_var": None, "value_labels": "{}"},
    {"name": "Q1", "label": "Q1. Age", "round": 9, "kind": "canonical",
     "family": None, "source_var": "Q1", "value_labels": "{}"},
])

def test_substring_search_filters_rounds():
    out = search.search_variables("trust pres", rounds=[8], index=INDEX, fuzzy=False)
    assert out["name"].tolist() == ["Q41A"]

def test_limit_and_sorting():
    out = search.search_variables("trust", limit=1, index=INDEX, fuzzy=False)
    assert len(out) == 1 and out.iloc[0]["name"] in {"Q37A", "Q41A"}

def test_no_match_returns_empty_frame():
    out = search.search_variables("zzzz", index=INDEX, fuzzy=False)
    assert out.empty and "name" in out.columns
```

```python
# tests/test_codebook.py
from pathlib import Path
import pytest
from pyafrobarometer import codebook
from pyafrobarometer.errors import CodebookError

def test_extract_text_without_dependency(monkeypatch):
    import builtins
    real_import = builtins.__import__
    def fake_import(name, *a, **k):
        if name == "pypdf":
            raise ImportError
        return real_import(name, *a, **k)
    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(CodebookError, match="pip install pyafrobarometer\\[codebook\\]"):
        codebook.extract_text(Path("x.pdf"))

def test_extract_text_uses_pypdf(monkeypatch):
    class Page:
        def extract_text(self): return "hello"
    class Reader:
        def __init__(self, path): self.pages = [Page()]
    import pypdf
    monkeypatch.setattr(pypdf, "PdfReader", Reader)
    assert codebook.extract_text(Path("x.pdf")) == "hello"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_search.py tests/test_codebook.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement search and codebook**

`load_index` reads `metadata_index.json` via `importlib.resources` and returns a DataFrame. `search_variables` filters by round, scores with `rapidfuzz.fuzz.WRatio` when `fuzzy=True` and installed, else case-insensitive substring; sort by `score` descending then `round` descending; return the documented columns. `get_codebook` resolves the catalog entry (following a resource page if needed), downloads to `cache_file(f"files/{sha256(url)}-{filename}")` via `fetch.download`, and returns the path. `extract_text` imports `pypdf`, raises `CodebookError` with the install hint on ImportError, and joins page text with `"\n"`.

Seed `metadata_index.json` with `{"version": 1, "variables": []}`; Task 12 regenerates it.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_search.py tests/test_codebook.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pyafrobarometer/search.py src/pyafrobarometer/codebook.py src/pyafrobarometer/metadata_index.json tests/test_search.py tests/test_codebook.py
git commit -m "feat: add variable search and codebook access"
```

---

### Task 11: Panel building and the public API

**Files:**
- Create: `src/pyafrobarometer/harmonize/panel.py`, `src/pyafrobarometer/api.py`
- Modify: `src/pyafrobarometer/__init__.py`
- Test: `tests/test_panel.py`, `tests/test_api.py`

**Interfaces:**
- Produces:
  - `select_entries(entries: Sequence[CatalogEntry], *, rounds, countries=None) -> list[CatalogEntry]`
  - `concat_frames(frames: Sequence[pd.DataFrame], *, variables: Sequence[str]) -> pd.DataFrame`
  - `rounds(refresh=False) -> pd.DataFrame`
  - `countries(round=None, *, refresh=False) -> list[str]`
  - `load(rounds=None, countries=None, variables=None, labels=False, normalize_missing=False, harmonize=False, language="en", source=None, refresh=False, strict=True) -> Dataset`
  - `search_variables(query, rounds=None, limit=20, fuzzy=True) -> pd.DataFrame`
  - `families() -> pd.DataFrame` with columns `family, description, rounds, variables`
  - `codebook(round, country=None, extract_text=False) -> Path`
  - `panel(rounds, variables, countries=None, labels=False, strict=True) -> Dataset`
  - `citation(rounds=None, countries=None) -> str`
  - `cache_dir() -> Path`, `clear_cache(round=None) -> None`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_panel.py
import pandas as pd
from pyafrobarometer.harmonize.panel import concat_frames

def test_concat_preserves_order_and_adds_round_country():
    a = pd.DataFrame({"round": [8], "country": ["Ghana"], "year": [2022], "trust_president": [2]})
    b = pd.DataFrame({"round": [9], "country": ["Benin"], "year": [2023], "trust_president": [1]})
    out = concat_frames([a, b], variables=["trust_president"])
    assert out["round"].tolist() == [8, 9]
    assert out["trust_president"].tolist() == [2, 1]

def test_concat_missing_column_raises():
    import pytest
    from pyafrobarometer.errors import HarmonizationError
    with pytest.raises(HarmonizationError):
        concat_frames([pd.DataFrame({"round": [9]})], variables=["trust_president"])
```

```python
# tests/test_api.py
import pandas as pd, pyreadstat, pytest
import pyafrobarometer as ab
from pyafrobarometer import api, catalog

def write_sav(path):
    df = pd.DataFrame({"COUNTRY": [3, 14], "RESPNO": ["A", "B"], "REGION": [1, 2],
                       "URBRUR": [1, 2], "Q1": [30, 40], "Q100": [1, 2], "Q94": [3, 4],
                       "DATEINTR": [1, 2], "Q37A": [0, 9], "withinwt_ea": [1.0, 2.0]})
    pyreadstat.write_sav(df, str(path),
        column_labels=list(df.columns),
        variable_value_labels={"COUNTRY": {3: "Benin", 14: "Ghana"},
                               "Q37A": {0: "Not at all", 3: "A lot", 8: "Refused", 9: "Don't know", -1: "Missing"}})

def _entry(**kw):
    base = dict(kind="merged", round=9, country=None, year=2023, language="en",
                data_url="https://www.afrobarometer.org/wp-content/uploads/x.sav",
                codebook_url=None, page_url="https://www.afrobarometer.org/p",
                filename="x.sav", size_bytes=None)
    base.update(kw)
    return catalog.CatalogEntry(**base)

def test_load_from_local_source_end_to_end(tmp_path):
    p = tmp_path / "r9.sav"; write_sav(p)
    ds = ab.load(rounds=9, source=p, harmonize=True)
    assert ds.rounds == [9] and ds.countries == ["Benin", "Ghana"]
    out = ds.to_pandas(normalize_missing=True)
    assert out["country"].tolist() == ["Benin", "Ghana"]
    assert out["trust_president"].tolist() == [0, pd.NA]
    assert "Q37A" in out.columns

def test_load_filters_countries(tmp_path):
    p = tmp_path / "r9.sav"; write_sav(p)
    ds = ab.load(rounds=9, countries=["Ghana"], source=p, harmonize=True)
    assert ds.to_pandas()["country"].tolist() == ["Ghana"]

def test_variables_include_harmonized_rows(tmp_path):
    p = tmp_path / "r9.sav"; write_sav(p)
    ds = ab.load(rounds=9, source=p, harmonize=True)
    variables = ds.variables()
    row = variables.loc[variables["name"] == "trust_president"].iloc[0]
    assert row["source_var"] == "Q37A"

def test_citation_contains_required_text(tmp_path):
    p = tmp_path / "r9.sav"; write_sav(p)
    ds = ab.load(rounds=9, source=p)
    assert ds.citation().startswith("Afrobarometer Data,")

def test_source_without_rounds_requires_round_for_harmonize(tmp_path):
    p = tmp_path / "r9.sav"; write_sav(p)
    with pytest.raises(ab.HarmonizationError):
        ab.load(source=p, harmonize=True, rounds=None)

def test_missing_source_variable_strict_and_non_strict(tmp_path):
    p = tmp_path / "r9.sav"; write_sav(p)
    with pytest.raises(ab.HarmonizationError):
        ab.load(rounds=9, source=p, variables=["NOPE"])
    with pytest.warns(UserWarning):
        ds = ab.load(rounds=9, source=p, variables=["NOPE"], strict=False)
    assert "NOPE" not in ds.to_pandas().columns

def test_select_entries_prefers_country_files():
    merged = _entry()
    ghana = _entry(kind="country", country="Ghana")
    benin = _entry(kind="country", country="Benin")
    assert api.select_entries([merged, ghana, benin], rounds=[9], countries=["Ghana"]) == [ghana]
    assert api.select_entries([merged, ghana, benin], rounds=[9]) == [merged]

def test_rounds_and_countries_from_catalog(monkeypatch, tmp_path):
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr("pyafrobarometer.api.resolve_catalog", lambda **kw: [_entry()])
    index = pd.DataFrame([{"name": "COUNTRY", "label": "Country", "round": 9,
                           "kind": "canonical", "family": None, "source_var": "COUNTRY",
                           "value_labels": "{\"3\": \"Benin\"}"}])
    monkeypatch.setattr("pyafrobarometer.search.load_index", lambda: index)
    assert list(ab.rounds().columns) == ["round", "year", "countries", "data_url", "codebook_url", "language"]
    assert ab.countries(9) == ["Benin"]

def test_families_lists_sparse_availability():
    out = ab.families()
    row = out.loc[out["family"] == "social_media_news"].iloc[0]
    assert row["rounds"] == [6, 7, 8, 9, 10]
    assert "Q12E" in row["variables"].values()
    army = out.loc[out["family"] == "trust_army"].iloc[0]
    assert army["rounds"] == [1, 2, 3, 5, 6, 7, 8, 9, 10]

def test_second_load_reuses_cached_download(monkeypatch, tmp_path):
    from pyafrobarometer.fetch import DownloadResult
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path / "cache"))
    p = tmp_path / "r9.sav"; write_sav(p)
    e = _entry(data_url="https://www.afrobarometer.org/wp-content/uploads/r9.sav", filename="r9.sav")
    monkeypatch.setattr("pyafrobarometer.api.resolve_catalog", lambda **kw: [e])
    calls = []
    def fake_download(url, dest, **kwargs):
        calls.append(url); dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(p.read_bytes())
        return DownloadResult(dest, "abc", dest.stat().st_size, "application/x-spss-sav")
    monkeypatch.setattr("pyafrobarometer.fetch.download", fake_download)
    ab.load(rounds=9, harmonize=True)
    ab.load(rounds=9, harmonize=True)
    assert calls == [e.data_url]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_panel.py tests/test_api.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement panel and API**

`concat_frames` validates that every requested variable exists in every frame, raises `HarmonizationError` listing missing ones, selects `round, country, year` plus requested variables, and concatenates with `ignore_index=True`.

`select_entries` chooses one entry per requested round: with `countries=None`, the merged entry for the requested language; with `countries`, the matching country entries when all are available, otherwise the merged entry for that round (filtering happens after load). It raises `NotFoundError` when a round has no entry.

`load` algorithm:
1. Resolve source paths: `source` may be a path, URL, or iterable; URLs download via `fetch.download`.
2. Without `source`, call `resolve_catalog(refresh=refresh)`, filter `language`, then call `select_entries`.
3. Download each selected file to a URL-addressed cache path. Reuse `state["files"][url]["path"]` when it exists and its size matches; otherwise download, extract zips with `safe_extract_sav`, and update `state["files"]` with path, SHA-256, size, and round. Cache extracted metadata at `metadata/round-<round>.json` keyed by the file SHA-256 so a changed release re-extracts metadata.
4. Determine requested columns: source variable names, or canonical/family names when `harmonize=True`. A missing requested variable raises `HarmonizationError` when `strict=True`, otherwise warns and is skipped. Map names to source vars and pass them via `usecols` plus the variables needed for filtering and harmonization.
5. Filter rows by decoded country when `countries` is set.
6. Apply canonical and family mappings when requested; build `source_map` (output column → source variable) and a variables DataFrame that adds a row per canonical/family column (name, label/value labels/missing codes from the source variable, `source_var`). Preserve source columns.
7. Apply `normalize_missing`, then labels, using `source_map` for canonical/family columns.
8. Add `round`/`country`/`year`; build `Provenance` from entries (URLs, UTC timestamp, rounds, decoded countries, language, years, codebook path) and return `Dataset` with `source_map`.

`rounds()` resolves the catalog, keeps merged entries, and returns columns `round, year, countries, data_url, codebook_url, language`; `countries` is the comma-joined count from the title when known. `countries(round)` reads the `COUNTRY` variable's `value_labels` from the metadata index (a JSON object string), else uses country catalog entries, else raises `NotFoundError` with guidance. `families()` returns one row per curated family with `family`, `description`, sorted `rounds`, and a `variables` dict of round→source variable, read from `questions.yaml`. `citation` formats exactly `Afrobarometer Data, {countries}, Round {rounds}, {years}, available at http://www.afrobarometer.org.` with "All Countries" when countries are unknown. `codebook(round, country=None, extract_text=False)` resolves the matching entry, downloads the PDF, and returns its path; when `extract_text=True` it also writes `<pdf>.txt` and returns that text path. `panel` loads each round with `harmonize=True`, selects the requested families/canonical columns, calls `concat_frames`, and returns a `Dataset`.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_panel.py tests/test_api.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pyafrobarometer/harmonize/panel.py src/pyafrobarometer/api.py src/pyafrobarometer/__init__.py tests/test_panel.py tests/test_api.py
git commit -m "feat: add panel builder and public API"
```

---

### Task 12: Manifest/index generator and CI maintenance job

**Files:**
- Create: `scripts/update_catalog.py`
- Create: `.github/workflows/update-catalog.yml`
- Test: `tests/test_update_catalog.py`

**Interfaces:**
- Produces in `scripts/update_catalog.py`:
  - `manifest_payload(entries: Sequence[CatalogEntry]) -> dict[str, Any]`
  - `merge_metadata_index(existing: Mapping[str, Any], new: Sequence[Mapping[str, Any]]) -> dict[str, Any]`
  - `validate_links(entries, *, head=None) -> list[str]` (returns problems; empty means valid; `head` defaults to `fetch.http_head`)
  - `validate_crosswalk(meta: Mapping[str, Any], round_number: int) -> list[str]` (returns missing mapped variables)
  - CLI: `python scripts/update_catalog.py --write --validate [--metadata-rounds 10]`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_update_catalog.py
import importlib.util, pathlib
from pyafrobarometer.catalog import CatalogEntry

spec = importlib.util.spec_from_file_location("update_catalog", "scripts/update_catalog.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def entry(**kw):
    base = dict(kind="merged", round=10, country=None, year=2025, language="en",
                data_url="https://www.afrobarometer.org/x.sav", codebook_url=None,
                page_url="https://www.afrobarometer.org/p", filename="x.sav", size_bytes=None)
    base.update(kw); return CatalogEntry(**base)

def test_manifest_payload_roundtrip():
    payload = mod.manifest_payload([entry()])
    assert payload["version"] == 1 and payload["entries"][0]["round"] == 10

def test_merge_metadata_index_replaces_same_round():
    existing = {"version": 1, "variables": [{"name": "Q1", "round": 9}]}
    new = [{"name": "Q1", "round": 10}, {"name": "Q2", "round": 10}]
    out = mod.merge_metadata_index(existing, new)
    assert [v["round"] for v in out["variables"]] == [9, 10, 10]

def test_validate_links_reports_non_200(monkeypatch):
    class R: status_code = 404
    problems = mod.validate_links([entry()], head=lambda *a, **k: R())
    assert problems and "404" in problems[0]

def test_validate_crosswalk_reports_missing_variable():
    meta = {"column_names": ["COUNTRY_ALPHA", "RESPNO", "REGION", "URBRUR", "Q1",
                             "Q101", "Q97", "DATEINTR", "withinwt",
                             "Q59A", "Q59B", "Q59H", "Q59J", "Q3A", "Q3B", "Q43"]}
    assert mod.validate_crosswalk(meta, 5) == []
    meta["column_names"].remove("Q59A")
    assert any("trust_president" in p for p in mod.validate_crosswalk(meta, 5))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_update_catalog.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement the script and workflow**

The script calls `catalog.resolve_catalog(refresh=True)`, builds the manifest payload, downloads metadata for `--metadata-rounds` (default: latest merged round; accepts `all` or a comma-separated list) using the same `io`/`fetch` path, builds index records from `metadata.variable_info` plus family mapping, merges with the existing index, writes `src/pyafrobarometer/manifest.json` and `metadata_index.json` atomically, and prints a summary. `--validate` checks each URL with a HEAD request and allowed content type, runs `validate_crosswalk` against each downloaded metadata round, reports failures, and exits non-zero. `manifest_payload` sorts entries by `(round, kind, country or "", language)`.

Workflow `update-catalog.yml`:
```yaml
name: update-catalog
on:
  schedule: [{cron: "0 6 * * 1"}]
  workflow_dispatch:
  push:
    paths: ["src/pyafrobarometer/catalog.py", "scripts/update_catalog.py", "src/pyafrobarometer/crosswalk/**"]
permissions: {contents: write, pull-requests: write}
jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12"}
      - uses: actions/cache@v4
        with:
          path: ~/.cache/pyafrobarometer
          key: ab-data-${{ github.run_id }}
          restore-keys: ab-data-
      - run: pip install -e ".[dev]"
      - run: python scripts/update_catalog.py --write --validate --metadata-rounds all
      - run: pytest -m "not network"
      - uses: peter-evans/create-pull-request@v6
        with:
          commit-message: "chore: refresh Afrobarometer catalog"
          title: "chore: refresh Afrobarometer catalog"
          branch: automation/update-catalog
          delete-branch: true
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_update_catalog.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/update_catalog.py .github/workflows/update-catalog.yml tests/test_update_catalog.py
git commit -m "feat: add catalog refresh script and weekly CI job"
```

---

### Task 13: Documentation and live verification

**Files:**
- Modify: `README.md`
- Create: `tests/test_crosswalk_live.py`
- Test: all

**Interfaces:**
- Consumes: the full public API.

- [ ] **Step 1: Write the live crosswalk test (network-marked)**

```python
# tests/test_crosswalk_live.py
import pytest
import pyafrobarometer as ab
from pyafrobarometer import catalog, io, fetch
from pyafrobarometer.harmonize.crosswalk import canonical_map, family_map

pytestmark = pytest.mark.network

@pytest.mark.parametrize("round_number", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
def test_every_mapping_exists_in_real_data(round_number, tmp_path):
    entries = [e for e in catalog.resolve_catalog(refresh=True)
               if e.kind == "merged" and e.round == round_number and e.language == "en"]
    assert entries, f"no merged entry for round {round_number}"
    e = entries[0]
    dest = tmp_path / e.filename
    fetch.download(e.data_url, dest)
    path = io.safe_extract_sav(dest, tmp_path) if dest.suffix == ".zip" else dest
    meta = io.read_metadata(path)
    names = set(meta["column_names"])
    for mapping in canonical_map().values():
        if round_number in mapping:
            assert mapping[round_number].var in names
    for family, rounds in family_map().items():
        if round_number in rounds:
            assert rounds[round_number].var in names, f"{family} missing in R{round_number}"
```

- [ ] **Step 2: Write README**

Include install (`pip install pyafrobarometer` and extras), quickstart (`ab.rounds()`, `ab.families()`, `ab.load(rounds=9)`, `ab.panel([8, 9], ["trust_president"])`), an availability note explaining that families such as `social_media_news` start in R6, caching/TTL, offline/env vars, search, codebooks, citation and access-policy link, unaffiliated statement, and a "Data is never redistributed" note.

- [ ] **Step 3: Run the full offline suite and static checks**

Run: `pytest`, `ruff check .`, `mypy src`
Expected: all PASS; no lint or type errors.

- [ ] **Step 4: Run the live verification**

Run: `pytest -m network -o addopts="" tests/test_crosswalk_live.py -v`
Expected: PASS for all six rounds (downloads several hundred MB total; run sparingly).

- [ ] **Step 5: Commit**

```bash
git add README.md tests/test_crosswalk_live.py
git commit -m "docs: document usage and add live crosswalk verification"
```

---

## Execution Notes

- If pyreadstat returns `metadataonly` as `None`, treat it as an empty frame; never assume a type.
- Cache files are content-addressed by URL SHA-256; never overwrite a file from a different URL.
- CI must only commit generated JSON, never `.sav`, `.zip`, or `.pdf` files.
- If a real codebook disagrees with the verified table, fix the YAML and the table together; do not make the test match the code.
