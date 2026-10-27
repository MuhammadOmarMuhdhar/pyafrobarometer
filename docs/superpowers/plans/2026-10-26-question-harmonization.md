# Cross-round Question Harmonization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every repeated Afrobarometer variable a reviewed, stable concept name and make cross-round values comparable with explicit, YAML-driven normalization.

**Architecture:** `questions.yaml` is the master codebook and only runtime truth. A developer-only generator proposes entries from the metadata index; the reviewed YAML is parsed by a shared schema module, applied to frames by the harmonization layer, and used to derive the search index.

**Tech Stack:** Python 3.10+, pandas, pyreadstat, PyYAML, pytest, rapidfuzz (dev only), hatchling.

**Spec:** `docs/superpowers/specs/2026-10-26-question-harmonization-design.md`

## Global Constraints

- Target release: `0.1.2`.
- Python `>=3.10`.
- No new runtime dependencies. `rapidfuzz` is dev-only.
- `questions.yaml` is the only source of truth. There is no `status` field.
- The original 32 names are canonical and must not be renamed.
- `harmonize=True` with `variables=None` adds canonical variables plus only the legacy 32 concepts.
- Harmonized question columns force `missing` and `recode: null` to `pd.NA`.
- Variable lookup is case-insensitive.
- `metadata_index.json` covers all rounds 1-10.
- Tests are offline by default; network tests remain opt-in.

## Review Focus

- Lowercase R2/R3 variable names (`q43a`, `q80`) must resolve case-insensitively.
- Unicode apostrophes (`Don’t know`) and high AB missing codes (`9994`, `94`) must become `NA`.
- Extra categories must follow `recode: null` and `missing`; neither may leak as values.
- Excluded rounds must raise under `strict=True` and produce an NA column under `strict=False`.
- Colliding or ambiguous names must be rejected at validation time or raise at load time.

---

### Task 1: Fix missing-code detection

**Files:**
- Modify: `src/pyafrobarometer/metadata.py`
- Test: `tests/test_metadata.py`

**Interfaces:**
- Consumes: none.
- Produces: `metadata.missing_codes(meta, column) -> list[int]` (unchanged signature).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_metadata.py`:

```python
def test_curly_apostrophe_dont_know_is_missing():
    meta = {
        "variable_value_labels": {
            "Q41A": {9: "Don’t know/Haven’t heard enough to say"}
        }
    }
    assert 9 in metadata.missing_codes(meta, "Q41A")


def test_not_asked_in_country_codes_are_missing():
    meta = {
        "variable_value_labels": {
            "Q37A": {94: "Not asked in country", 9994: "Not asked in country"}
        }
    }
    assert {94, 9994} <= set(metadata.missing_codes(meta, "Q37A"))


def test_valid_code_nine_is_not_missing():
    meta = {"variable_value_labels": {"Q1": {9: "Nine or more"}}}
    assert 9 not in metadata.missing_codes(meta, "Q1")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_metadata.py -v`
Expected: FAIL on the curly-apostrophe and `94`/`9994` cases.

- [ ] **Step 3: Implement the fix**

In `src/pyafrobarometer/metadata.py`:
- Normalize Unicode apostrophes before matching in `_looks_missing`.
- Add `93`, `94`, `95`, `96`, `997`, `999`, `9994`, `9995`, `9998`, `9999` to `FALLBACK_MISSING_CODES`.
- Keep label-based detection as the guard. Do not treat a code as missing solely because its number is in the fallback list.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_metadata.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_metadata.py src/pyafrobarometer/metadata.py
git commit -m "fix: detect unicode and AB missing codes"
```

---

### Task 2: Add the question schema module

**Files:**
- Create: `src/pyafrobarometer/harmonize/schema.py`
- Test: `tests/test_schema.py`

**Interfaces:**
- Consumes: none.
- Produces:
  - `QuestionRound(var: str | None, label: str | None, recode: dict[int, int | None], missing: tuple[int, ...], exclude: bool, reason: str | None)`
  - `QuestionDefinition(name: str, description: str, kind: str, values: dict[int, str], rounds: dict[int, QuestionRound])`
  - `parse_questions(payload: dict[str, Any]) -> dict[str, QuestionDefinition]`
  - `validate_questions(questions: dict[str, QuestionDefinition], index: pd.DataFrame | None = None) -> list[str]`
  - `resolve_column(name: str, columns: Iterable[str]) -> str | None`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_schema.py` with tests that pin:
- A minimal coded concept parses with `values`, `rounds`, `recode`, and `missing`.
- A `kind: text` concept parses without `values`.
- `validate_questions` rejects: coded without `values`, text with `recode`, bad recode target, uncovered native code, missing exclude reason, duplicate source variable in one round, `missing`/`recode` overlap.
- With an index fixture, validation rejects a concept name colliding with a raw name or canonical name, and a `var` absent from its round.
- `resolve_column` returns the real column for `q43a` vs `Q43A`, returns `None` when absent, and raises `HarmonizationError` for an ambiguous match.

Use this index fixture shape:

```python
INDEX = pd.DataFrame(
    [
        {"name": "Q37A", "round": 9, "kind": "question"},
        {"name": "q43a", "round": 2, "kind": "question"},
        {"name": "COUNTRY", "round": 9, "kind": "canonical"},
    ]
)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_schema.py -v`
Expected: FAIL with `ModuleNotFoundError` for `pyafrobarometer.harmonize.schema`.

- [ ] **Step 3: Implement the schema module**

Implement the dataclasses and functions exactly as named above. Keep parsing structural; `validate_questions` returns a list of human-readable problem strings and does not raise. `resolve_column` compares casefolded names and raises `HarmonizationError` on more than one match.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_schema.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_schema.py src/pyafrobarometer/harmonize/schema.py
git commit -m "feat: add question schema and validation"
```

---

### Task 3: Resolve variables case-insensitively

**Files:**
- Modify: `src/pyafrobarometer/harmonize/canonical.py`
- Modify: `src/pyafrobarometer/api.py`
- Test: `tests/test_canonical.py`
- Test: `tests/test_questions.py`

**Interfaces:**
- Consumes: `schema.resolve_column`.
- Produces: `apply_canonical` and `apply_families` accept lowercase source columns and return the actual source column in their mapping.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_canonical.py`:

```python
def test_apply_canonical_r2_lowercase_names():
    df = pd.DataFrame({"country": [3], "respno": ["A"], "q80": [30], "q96": [1]})
    out, mapping = canonical.apply_canonical(
        df, round_number=2, meta=meta_for(list(df.columns))
    )
    assert out["age"].tolist() == [30]
    assert mapping["age"] == "q80"
```

Add to `tests/test_questions.py`:

```python
def test_lowercase_source_variable_resolves():
    df = pd.DataFrame({"q43a": [0, 3]})
    out, mapping = canonical.apply_families(
        df, round_number=2, families=["trust_president"]
    )
    assert out["trust_president"].tolist() == [0, 3]
    assert mapping["trust_president"] == "q43a"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_canonical.py tests/test_questions.py -v`
Expected: FAIL because `Q80`/`Q43A` are not found.

- [ ] **Step 3: Implement case-insensitive resolution**

Use `schema.resolve_column` in:
- `apply_canonical` before reading `df[source]`.
- `apply_families` before reading `df[spec.var]`.
- `api._select_usecols` when adding needed columns.
- `api._country_values` for its fixed column names.
- `api._load_one` where family source variables are checked.

Use the returned actual column name for indexing and for `source_map`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_canonical.py tests/test_questions.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_canonical.py tests/test_questions.py src/pyafrobarometer/harmonize/canonical.py src/pyafrobarometer/api.py
git commit -m "fix: resolve round variables case-insensitively"
```

---

### Task 4: Extend the index with missing codes

**Files:**
- Modify: `src/pyafrobarometer/search.py`
- Modify: `scripts/update_catalog.py`
- Test: `tests/test_search.py`
- Test: `tests/test_update_catalog.py`
- Regenerate: `src/pyafrobarometer/metadata_index.json`

**Interfaces:**
- Consumes: `metadata.missing_codes`.
- Produces:
  - `search.INDEX_COLUMNS` includes `concept` and `missing_codes`.
  - `search.RESULT_COLUMNS` includes `concept`.
  - `search._read_index_payload() -> list[dict[str, Any]]` reads the shipped index.
  - Index rows include `concept: None` and `missing_codes: list[int]`.
  - `scripts/update_catalog.py --write --validate --metadata-rounds all` regenerates every round.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_search.py`:

```python
def test_result_columns_include_concept():
    out = search.search_variables("trust", index=INDEX, fuzzy=False)
    assert "concept" in out.columns


def test_load_index_fills_missing_optional_columns(monkeypatch):
    old = pd.DataFrame([{"name": "Q37A", "label": "Trust", "round": 9}])
    monkeypatch.setattr(search, "_read_index_payload", lambda: old.to_dict("records"))
    out = search.load_index()
    assert "concept" in out.columns and "missing_codes" in out.columns
```

Add to `tests/test_update_catalog.py`:

```python
def test_index_records_include_missing_codes():
    records = mod._index_records(
        {
            "column_names": ["Q37A"],
            "column_names_to_labels": {"Q37A": "Trust president"},
            "variable_value_labels": {"Q37A": {9: "Don’t know"}},
            "missing_ranges": {},
        },
        9,
    )
    assert records[0]["missing_codes"] == [9]
    assert "concept" in records[0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_search.py tests/test_update_catalog.py -v`
Expected: FAIL on missing columns and absent `missing_codes`.

- [ ] **Step 3: Implement the index changes**

In `search.py`:
- Add `concept` and `missing_codes` to `INDEX_COLUMNS`, and `concept` to `RESULT_COLUMNS`.
- Add `_read_index_payload()` to read the JSON `variables` list; `load_index` reindexes it to `INDEX_COLUMNS` so old payloads still work.
- Make `search_variables` reindex the supplied index to `INDEX_COLUMNS` before scoring.
- Include `concept` in `_score` when present.

In `scripts/update_catalog.py`:
- Add `missing_codes` and `concept: None` to each record.
- Make `_metadata_rounds` default to `all` for write/validate runs.
- Use case-insensitive name matching in `validate_crosswalk`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_search.py tests/test_update_catalog.py -v`
Expected: PASS.

- [ ] **Step 5: Regenerate the index**

Run: `uv run python scripts/update_catalog.py --write --validate --metadata-rounds all`
Expected: `problems: 0`; `metadata_index.json` contains rounds 1-10 and `missing_codes`.

- [ ] **Step 6: Run the full offline suite**

Run: `uv run pytest -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add tests/test_search.py tests/test_update_catalog.py src/pyafrobarometer/search.py scripts/update_catalog.py src/pyafrobarometer/metadata_index.json
git commit -m "feat: add missing codes to the metadata index"
```

---

### Task 5: Add the generator core

**Files:**
- Create: `scripts/build_questions.py`
- Test: `tests/test_build_questions.py`

**Interfaces:**
- Consumes: `metadata_index.json` as a DataFrame with `name`, `label`, `round`, `kind`, `value_labels`, `missing_codes`; optional legacy YAML.
- Produces:
  - `Candidate(name, description, kind, values, rounds, exact, confidence)`
  - `normalize_label(text: str) -> str`
  - `normalize_value_label(text: str) -> str`
  - `slugify(text: str) -> str`
  - `value_signature(labels: dict[str, str], missing: Iterable[int], recode: dict[int, int | None] | None = None) -> tuple[tuple[int, str], ...]`
  - `infer_values(rounds: dict[int, dict[str, str]], missing: dict[int, list[int]], recodes: dict[int, dict[int, int | None]] | None = None) -> dict[int, str] | None`
  - `build_candidates(index: pd.DataFrame, legacy: dict[str, dict[int, dict[str, Any]]] | None = None) -> list[Candidate]`
  - `legacy_from_yaml(payload: dict[str, Any]) -> dict[str, dict[int, dict[str, Any]]]`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_build_questions.py` with tests that pin:
- `normalize_label("Q43A. Trust the President?") == "trust the president"`.
- `slugify("Trust the President") == "trust_president"` and duplicates get `_2`.
- Exact groups across rounds become one candidate with per-round vars.
- Legacy input preserves the 32 names and recodes.
- Legacy `trust_president` infers `values[0] == "Not at all"` even though R1 uses codes 1-4 and different label wording; the inference applies each round's recode and takes target labels from the latest included round.
- `infer_values` returns a target mapping when all rounds share the same post-recode code set, and `None` when the code sets differ. `exact` is true only when all normalized labels also match.
- A candidate's `missing` uses the index `missing_codes` when present and falls back to label heuristics when absent.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_build_questions.py -v`
Expected: FAIL with `ModuleNotFoundError`/missing functions.

- [ ] **Step 3: Implement the generator core**

Use `rapidfuzz.fuzz.WRatio` for fuzzy proposals when available; fall back to exact grouping with a warning. Drop missing codes and codes recoded to `null` before comparing value signatures. Use the latest included round's labels for target `values` when code sets match. Keep output deterministic by sorting candidates by name. Do not write files in this task.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_build_questions.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_build_questions.py scripts/build_questions.py
git commit -m "feat: add question candidate generator"
```

---

### Task 6: Add the generator CLI and validation

**Files:**
- Modify: `scripts/build_questions.py`
- Test: `tests/test_build_questions.py`

**Interfaces:**
- Consumes: Task 5 functions, `schema.parse_questions`, `schema.validate_questions`.
- Produces: `main(argv=None) -> int` with:
  - `--index PATH` (default `src/pyafrobarometer/metadata_index.json`)
  - `--questions PATH` (default `src/pyafrobarometer/crosswalk/questions.yaml`)
  - `--proposed PATH` (default `build/questions.proposed.yaml`)
  - `--legacy PATH`
  - `--bootstrap`, `--propose`, `--accept-exact`, `--accept NAME` (repeatable)
  - `--validate`, `--strict-coverage`

- [ ] **Step 1: Write the failing tests**

Add tests that pin:
- `--bootstrap` writes exact candidates to the truth path and ambiguous candidates to the proposed path.
- `--accept-exact` is idempotent and preserves existing entries.
- `--accept NAME` merges one proposal.
- `--validate` reports a bad `var` and returns exit code 1.
- `--strict-coverage` fails when a repeated normalized label is unassigned.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_build_questions.py -v`
Expected: FAIL on missing CLI behavior.

- [ ] **Step 3: Implement the CLI and YAML serialization**

Serialize with `yaml.safe_dump(..., sort_keys=False)`. Never overwrite an existing truth entry. For `--bootstrap`, create the truth file only when it does not exist or when the user explicitly passes `--bootstrap`; legacy candidates always go to the truth file even when their labels differ, because their names and recodes are already reviewed. If a legacy candidate cannot infer `values`, stop with an error naming it instead of writing an invalid truth file.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_build_questions.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_build_questions.py scripts/build_questions.py
git commit -m "feat: add question generator CLI and validation"
```

---

### Task 7: Migrate questions.yaml and switch the loader

**Files:**
- Modify: `src/pyafrobarometer/harmonize/crosswalk.py`
- Replace: `src/pyafrobarometer/crosswalk/questions.yaml`
- Test: `tests/test_questions.py`
- Test: `tests/test_crosswalk_live.py`

**Interfaces:**
- Consumes: `schema.parse_questions`.
- Produces:
  - `question_map() -> dict[str, QuestionDefinition]`
  - `family_map() -> dict[str, dict[int, Mapping]]` compatibility wrapper
  - `family_rounds`, `family_descriptions`, `question_descriptions`
  - `LEGACY_QUESTIONS: tuple[str, ...]`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_questions.py`:

```python
def test_question_map_reads_questions_section():
    q = question_map()
    assert q["trust_president"].kind == "coded"
    assert q["trust_president"].values[0] == "Not at all"
    assert q["trust_president"].rounds[2].var.lower() == "q43a"


def test_legacy_names_are_preserved():
    q = question_map()
    assert "trust_president" in q
    assert len(LEGACY_QUESTIONS) == 32
```

Update `tests/test_crosswalk_live.py` to iterate `question_map()` and use case-insensitive resolution.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_questions.py -v`
Expected: FAIL because the YAML still has `families:`.

- [ ] **Step 3: Seed and generate the new YAML**

```bash
cp src/pyafrobarometer/crosswalk/questions.yaml /tmp/questions.legacy.yaml
uv run python scripts/build_questions.py \
  --bootstrap \
  --legacy /tmp/questions.legacy.yaml \
  --index src/pyafrobarometer/metadata_index.json \
  --questions src/pyafrobarometer/crosswalk/questions.yaml \
  --proposed build/questions.proposed.yaml
uv run python scripts/build_questions.py --validate --strict-coverage
```

Expected: the truth file uses `questions:` and contains the legacy 32; unresolved candidates are in `build/questions.proposed.yaml`.

- [ ] **Step 4: Implement the loader**

In `crosswalk.py`, parse the `questions:` section with `schema.parse_questions`, cache the result with `functools.lru_cache`, and make `family_map()` adapt it to the existing `Mapping` shape. Define `LEGACY_QUESTIONS` with the current 32 names. Update `family_rounds` and `family_descriptions` to use `question_map`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_questions.py tests/test_canonical.py -q`
Expected: PASS.

- [ ] **Step 6: Human review checkpoint**

Stop here. Ask the user to review `src/pyafrobarometer/crosswalk/questions.yaml` and `build/questions.proposed.yaml`. Accept or edit entries as needed, then rerun `--validate --strict-coverage` until it passes. Do not start Task 8 until the user approves the YAML.

- [ ] **Step 7: Commit**

```bash
git add src/pyafrobarometer/crosswalk/questions.yaml src/pyafrobarometer/harmonize/crosswalk.py tests/test_questions.py tests/test_crosswalk_live.py
git commit -m "feat: replace families with reviewed question concepts"
```

---

### Task 8: Apply question concepts with forced missing normalization

**Files:**
- Modify: `src/pyafrobarometer/harmonize/canonical.py`
- Test: `tests/test_questions.py`

**Interfaces:**
- Consumes: `question_map`, `schema.QuestionDefinition`, `schema.resolve_column`.
- Produces:
  - `apply_questions(df, *, round_number, questions, strict=True, catalog=None) -> tuple[pd.DataFrame, dict[str, str]]`
  - `apply_families(...)` remains as a wrapper over `apply_questions`.

- [ ] **Step 1: Write the failing tests**

Add tests with these names that pin:
- `test_apply_questions_maps_source` — a normal coded concept adds the target column and maps the source var.
- `test_apply_questions_forces_missing_na` — `missing` codes become `pd.NA` even without `normalize_missing`.
- `test_apply_questions_recode_null_na` — `recode: {code: null}` becomes `pd.NA`.
- `test_apply_questions_text_passthrough` — `kind: text` is copied without recoding.
- `test_apply_questions_excluded_round` — an excluded round raises under `strict=True` and adds an all-NA column under `strict=False`.
- `test_apply_questions_lowercase_source` — a lowercase source variable resolves.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_questions.py -k apply_questions -v`
Expected: FAIL because `apply_questions` does not exist.

- [ ] **Step 3: Implement `apply_questions`**

Order of operations per question:
1. Find the round entry; handle excluded/absent.
2. Resolve the actual column case-insensitively.
3. Replace codes in `missing` with `pd.NA`.
4. Apply `recode`, treating `None` targets as `pd.NA`.
5. Add the column under the concept name.
6. Record the actual source variable in the mapping.

Preserve the existing `apply_families` error messages: an absent round mentions "available in rounds", and a missing mapped variable mentions "absent", so the current tests and user-facing errors keep their meaning.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_questions.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_questions.py src/pyafrobarometer/harmonize/canonical.py
git commit -m "feat: apply question concepts with forced missing normalization"
```

---

### Task 9: Integrate concepts into load and Dataset

**Files:**
- Modify: `src/pyafrobarometer/api.py`
- Modify: `src/pyafrobarometer/dataset.py`
- Test: `tests/test_api.py`
- Test: `tests/test_dataset.py`
- Test: `tests/test_panel.py`

**Interfaces:**
- Consumes: `question_map`, `LEGACY_QUESTIONS`, `apply_questions`.
- Produces:
  - `_select_usecols` selects canonical plus requested concepts, case-insensitively.
  - `_load_one` calls `apply_questions`; `variables=None` + `harmonize=True` selects only `LEGACY_QUESTIONS`.
  - `_build_variables(meta, source_map, round_source_map)` adds `source_vars` and target value labels.
  - `Dataset.to_pandas(labels=True)` decodes concept columns with target `values`.

- [ ] **Step 1: Write the failing tests**

Add tests that pin:
- `ab.load(rounds=9, source=p, harmonize=True)` still adds the legacy `trust_president`.
- `trust_president` code `9` becomes NA even without `normalize_missing`.
- `ds.variables()` has a `source_vars` mapping for `trust_president`.
- `to_pandas(labels=True)` decodes `trust_president` with target labels.
- `ab.load(rounds=9, source=p, harmonize=True, variables=["trust_president"])` selects the source variable through `usecols`.
- An unknown concept with `strict=False` warns and is omitted; `strict=True` raises.
- A local SAV with lowercase `q43a` and `harmonize=True` produces `trust_president`.
- `panel([8, 9], ["trust_president"])` still works and carries round metadata.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_api.py tests/test_dataset.py tests/test_panel.py -v`
Expected: FAIL on forced NA, `source_vars`, and target-label decoding.

- [ ] **Step 3: Implement the integration**

In `api.py`:
- Replace `family_map` selection with `question_map`.
- Default to `LEGACY_QUESTIONS` when `variables is None`.
- Call `apply_questions` instead of `apply_families`.
- Pass `round_source_map` to `_build_variables`.

In `dataset.py`:
- Import `question_map`.
- In `to_pandas`, use concept `values` for harmonized columns; do not decode `kind: text`.
- Keep per-round metadata decoding for canonical columns.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_api.py tests/test_dataset.py tests/test_panel.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full offline suite**

Run: `uv run pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/test_api.py tests/test_dataset.py tests/test_panel.py src/pyafrobarometer/api.py src/pyafrobarometer/dataset.py
git commit -m "feat: integrate question concepts into load and datasets"
```

---

### Task 10: Add questions() and question(), deprecate families()

**Files:**
- Modify: `src/pyafrobarometer/api.py`
- Modify: `src/pyafrobarometer/__init__.py`
- Modify: `tests/test_package.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `question_map`, `LEGACY_QUESTIONS`.
- Produces:
  - `questions() -> pd.DataFrame` with `name`, `description`, `kind`, `rounds`, `variables`, `values`.
  - `question(name) -> pd.DataFrame` with `round`, `var`, `label`, `recode`, `missing`, `excluded`, `reason`; raises `HarmonizationError` for unknown names.
  - `families()` warns `DeprecationWarning` and returns only the legacy 32 with the old columns.

- [ ] **Step 1: Write the failing tests**

Add tests that pin:
- `ab.questions()` includes a non-legacy concept from the generated YAML.
- `ab.question("trust_president")` returns rows for rounds 1-10.
- `ab.question("nope")` raises `HarmonizationError`.
- `ab.families()` returns exactly 32 rows and warns `DeprecationWarning`.
- `pyafrobarometer.questions` and `pyafrobarometer.question` are exported.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_api.py tests/test_package.py -v`
Expected: FAIL because the new functions are absent.

- [ ] **Step 3: Implement the public APIs**

Build the DataFrames from `question_map`. Keep `families()` filtering `LEGACY_QUESTIONS` and preserving its old column names. Add the new names to `__all__`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_api.py tests/test_package.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_api.py tests/test_package.py src/pyafrobarometer/api.py src/pyafrobarometer/__init__.py
git commit -m "feat: add questions and question APIs"
```

---

### Task 11: Add concept tags to the index

**Files:**
- Modify: `scripts/update_catalog.py`
- Test: `tests/test_update_catalog.py`
- Regenerate: `src/pyafrobarometer/metadata_index.json`

**Interfaces:**
- Consumes: `question_map`, `schema.validate_questions`.
- Produces:
  - Index `concept` is the stable name for mapped question rows and the canonical name for canonical rows.
  - Index `family` remains populated only for the legacy 32.
  - `validate_crosswalk` validates every question mapping case-insensitively.

- [ ] **Step 1: Write the failing tests**

Add tests that pin:
- `_index_records` tags `Q37A` in round 9 with `concept: trust_president`.
- The legacy `family` field is set for `trust_president` and not for a non-legacy concept.
- A missing source variable for any question is reported by `validate_crosswalk`.
- `validate_crosswalk` accepts lowercase source names for R2/R3.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_update_catalog.py -v`
Expected: FAIL because concepts are not tagged.

- [ ] **Step 3: Implement concept tagging**

Build a round-to-variable-to-concept map from `question_map` using `resolve_column`. Set `concept` for every mapped row and `family` only when the concept is in `LEGACY_QUESTIONS`. Make `validate_crosswalk` check every question and use case-insensitive membership.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_update_catalog.py -v`
Expected: PASS.

- [ ] **Step 5: Regenerate the index**

Run: `uv run python scripts/update_catalog.py --write --validate --metadata-rounds all`
Expected: `problems: 0`; every mapped row has a `concept`; R2/R3 family/concept tags are present.

- [ ] **Step 6: Verify the index**

Run: `uv run python -c "from pyafrobarometer import search; i=search.load_index(); print(i['concept'].notna().sum(), sorted(i['round'].unique()))"`
Expected: a nonzero concept count and `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]`.

- [ ] **Step 7: Commit**

```bash
git add tests/test_update_catalog.py scripts/update_catalog.py src/pyafrobarometer/metadata_index.json
git commit -m "feat: tag metadata index with question concepts"
```

---

### Task 12: Update docs, version, and verify the release

**Files:**
- Modify: `docs/guide/families.md` (replace with question concepts)
- Modify: `docs/guide/family-harmonization.md` (replace with question harmonization)
- Create: `docs/guide/master-codebook.md`
- Modify: `docs/guide/index.md`
- Modify: `docs/reference/functions.md`
- Modify: `docs/reference/index.md`
- Modify: `docs/tutorial/*` where families are mentioned
- Modify: `README.md`
- Modify: `docs/development.md`
- Modify: `zensical.toml`
- Modify: `pyproject.toml`
- Modify: `src/pyafrobarometer/__init__.py`

**Interfaces:**
- Consumes: all prior tasks.
- Produces: 0.1.2 release.

- [ ] **Step 1: Write the failing docs/version tests**

Update the existing version test in `tests/test_package.py`:

```python
def test_version():
    assert ab.__version__ == "0.1.2"
```

Run: `uv run pytest tests/test_package.py -v`
Expected: FAIL while the version is still `0.1.0`.

- [ ] **Step 2: Update the docs**

Replace family-focused pages with question/concept pages. Document `questions()`, `question()`, the `families()` deprecation, forced NA, the R2/R3 fix, and the propose/review/validate workflow. Update the nav in `zensical.toml`, the README quickstart, and `docs/development.md`.

- [ ] **Step 3: Bump the version**

Set `version = "0.1.2"` in `pyproject.toml` and `__version__ = "0.1.2"` in `src/pyafrobarometer/__init__.py`.

- [ ] **Step 4: Run the docs build**

Run: `uvx zensical build --clean`
Expected: strict build passes with no broken links.

- [ ] **Step 5: Run the full verification**

Run:
```bash
uv run pytest -q
uv run ruff check .
uv run mypy src
uv build
uvx twine check dist/*
```
Expected: all pass, and `dist/` contains `pyafrobarometer-0.1.2` sdist and wheel.

- [ ] **Step 6: Commit**

```bash
git add docs README.md zensical.toml pyproject.toml src/pyafrobarometer/__init__.py tests/test_package.py
git commit -m "docs: document question harmonization for 0.1.2"
```

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-10-26-question-harmonization.md`. The plan is ready for review and execution. Task 7 contains a human review gate for the generated crosswalk; do not skip it.
