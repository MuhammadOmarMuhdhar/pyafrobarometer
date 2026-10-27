# Cross-round question harmonization and master codebook

Date: 2026-10-26
Status: Draft for review
Target release: 0.1.2

## Summary

Replace the curated 32-family crosswalk with a reviewed YAML catalog that gives
every repeated survey variable a stable concept name. The catalog becomes the
package's master codebook. A developer-only generator proposes candidates from
the shipped metadata index; the reviewed YAML is the only runtime truth.

The change also fixes two existing defects found during design:

- Rounds 2 and 3 store variable names in lowercase (`q43a`) while the crosswalk
  uses uppercase (`Q43A`), so current R2/R3 harmonization is broken.
- Missing-code detection misses labels with Unicode apostrophes (`Don’t know`)
  and several AB missing codes (`93`, `94`, `997`, `998`, `9994`), so
  `normalize_missing=True` leaks values such as `9` into results.

## Goals

- Give every repeated variable a stable, concept-level name, even when it
  appears in only two rounds.
- Keep the existing 32 family names as canonical names for their concepts.
- Make value harmonization explicit and reviewable in YAML.
- Force missing codes and explicitly excluded categories to `NA` for harmonized
  question columns.
- Keep `questions.yaml` as the single source of truth; derive search/index data
  from it.
- Provide a generator and validator that make ~540 reviewed entries practical.

## Non-goals

- Deriving matches at runtime. The runtime reads only the reviewed YAML.
- Automatic statistical normalization (0-1 or z-scores). Normalization means
  aligning category schemes, not rescaling.
- Replacing the official per-round codebook PDFs.
- Parsing codebook PDFs in the first release. The generator is designed so PDF
  enrichment can be added later without changing the runtime or YAML schema.

## Current state

- `src/pyafrobarometer/crosswalk/questions.yaml` contains 32 families and 270
  family-round mappings.
- `src/pyafrobarometer/metadata_index.json` contains 3,419 variable-round rows
  (3,336 questions, 83 canonical), with labels and value labels.
- 540 normalized labels appear in at least two rounds with one variable per
  round; 201 of those appear in exactly two rounds.
- R2/R3 family tags in the metadata index are empty because the index merge
  retained stale rows.
- `harmonize=True` applies recodes, but missing-code normalization and label
  decoding are opt-in.
- The metadata index has no missing-code field.

## Data model

### File

`src/pyafrobarometer/crosswalk/questions.yaml`

```yaml
version: 1
questions:
  trust_president:
    description: Trust in the President
    kind: coded
    values:
      0: Not at all
      1: Just a little
      2: Somewhat
      3: A lot
    rounds:
      1:
        var: trspre
        label: "Trust the president to do what is right?"
        missing: [8, 9]
        recode: {1: 0, 2: 1, 3: 2, 4: 3}
      2:
        var: q43a
      10:
        var: Q37A
        missing: [-1, 8, 9, 9994]

  pay_bribe_document:
    description: Frequency of paying a bribe for a document or permit
    kind: coded
    values: {0: Never, 1: Once or twice, 2: A few times, 3: Often}
    rounds:
      2:
        var: q59a
        recode: {4: 3}
        missing: [9, 98]
      3:
        var: q57a
        recode: {7: null}
        missing: [9, 998]
      10:
        exclude: true
        reason: "Question not fielded in this round"
```

### Concept fields

| Field | Required | Meaning |
|---|---|---|
| `description` | yes | Human-readable summary |
| `kind` | no | `coded` or `text`; defaults to `coded` when omitted |
| `values` | coded only | Target codebook: code to label |
| `rounds` | yes | Mapping of round number to round entry |

For `kind: coded`, `values` is required. For `kind: text` (dates, names, free
text), `values` is omitted and no recoding is performed; `missing` still applies.

### Round fields

| Field | Required | Meaning |
|---|---|---|
| `var` | unless excluded | Source variable; matched case-insensitively |
| `label` | yes unless excluded | Source question wording for the master codebook |
| `recode` | no | Native code to target code; `null` maps to `NA` |
| `missing` | no | True missing/refused/DK/not-asked codes mapped to `NA` |
| `exclude` | no | `true` removes the round from the concept |
| `reason` | when excluded | Why the round cannot be part of the concept |

There is no `status` field. The committed YAML is approved by definition.

### Validation rules

- `version` is `1`; `questions` is a mapping of unique stable names.
- A stable name must not collide, case-insensitively, with a canonical variable
  name or with a raw variable name in any round.
- A stable name must be a lowercase slug: letters, digits, and underscores.
- `kind` is `coded` or `text`; `coded` requires a non-empty `values` mapping and
  `text` must not define `values` or `recode`.
- `values` codes are unique, labels are non-empty, and no target code is also
  listed in a round's `missing`.
- `rounds` keys are integers in 1-10.
- Each round is either excluded with a `reason`, or has `var` and `label`.
- `var` must exist in that round's metadata when matched case-insensitively,
  and must resolve to exactly one column.
- For `kind: coded`, every native code that is not in `missing` must have a
  `recode` entry or already equal a target code. A `recode` target must exist
  in `values`, or be `null`. A code may not appear in both `missing` and
  `recode`.
- Excluded entries contain only `exclude` and `reason`, plus an optional
  reference `label`; they may not define `recode` or `missing`.
- Two concepts may not claim the same source variable in the same round.

## Runtime behavior

### Resolution

- `question_map()` reads `questions:` and returns a richer mapping that includes
  `kind`, `values`, per-round `label`, `missing`, `recode`, and exclusion data.
  The mapping is cached in-process.
- `family_map()` remains as a compatibility wrapper that adapts the new mapping
  to the old `Mapping(var, decode_country, recode)` shape used by callers that
  have not moved to the richer fields.
- Variable lookup is case-insensitive. If both cases exist in one round, loading
  raises `HarmonizationError` rather than choosing silently.
- Stable concept names take precedence over raw variable names; canonical names
  keep their existing precedence. Collisions are rejected at validation time,
  so precedence is never ambiguous in a valid catalog.

### Public catalog

- `ab.questions()` returns one row per concept with `name`, `description`,
  `kind`, `rounds`, `variables`, and `values`.
- `ab.question(name)` returns the master-codebook detail as a DataFrame with
  `round`, `var`, `label`, `recode`, `missing`, `excluded`, and `reason`.
- An unknown name passed to `question()` raises `HarmonizationError`.
- `ab.families()` is deprecated and returns only the original 32 names, so
  existing code keeps its previous meaning. It warns with `DeprecationWarning`.
- The original 32 names are held in a `LEGACY_QUESTIONS` constant used by
  `families()` and by the default-harmonize behavior.

### Loading

- `load(harmonize=True, variables=[...])` accepts canonical names, stable concept
  names, and raw variables, in that precedence.
- With `variables=None` and `harmonize=True`, only canonical variables plus the
  legacy 32 concepts are added. All other concepts are available by explicit
  name. This preserves current behavior and prevents hundreds of automatic
  columns.
- For harmonized question columns, `missing` codes and `recode: null` always map
  to `pd.NA`, regardless of `normalize_missing`. `normalize_missing=True` keeps
  its current meaning for raw, non-harmonized columns.
- `to_pandas(labels=True)` decodes harmonized question columns with the concept's
  target `values`, so codes decode consistently across rounds. Canonical
  variables keep per-round decoding. `kind: text` columns are not decoded.
- Sparse behavior is unchanged: `strict=True` raises when a requested concept
  has no entry (or is excluded) in a requested round; `strict=False` warns and
  adds a `pd.NA` column.
- `Dataset.variables()` keeps its columns. For a concept, `value_labels` is the
  target `values`, `missing_codes` is the union across included rounds, and
  `source_var` is the earliest included round's source variable. A new
  `source_vars` column holds the round-to-variable mapping. `question(name)` is
  the authoritative per-round view.

### Missing codes

The shared detector in `metadata.py` is fixed before the crosswalk work:

- Normalize Unicode apostrophes before matching so `Don’t know` matches
  `don't know`.
- Extend fallback codes to the AB conventions (`93`, `94`, `95`, `96`, `97`,
  `997`, `998`, `999`, `9994`, `9995`, `9998`, `9999`).
- Keep label-based detection as the guard so a numeric code is only treated as
  missing when its label also looks missing.

These fixed codes feed both the YAML generation and `normalize_missing` for raw
columns.

### Discovery

- `search_variables()` adds a `concept` column and searches concept names and
  descriptions in addition to raw names, labels, and the legacy `family` field.
- `family` remains in search results as a deprecated alias for legacy concepts
  for one release.
- `codebook(round)` continues to return the official per-round PDF.

## Master codebook and index

- `questions.yaml` is the master codebook and the only source of truth.
- `metadata_index.json` is a derived search index. Each row gains:
  - `concept`: canonical name for canonical rows, stable concept name for
    question rows.
  - `missing_codes`: declared/derived missing codes for that variable.
- The legacy `family` field is retained for compatibility and is populated only
  for the original 32 concepts; `concept` is populated for every mapped row.
- The index is regenerated from the YAML and the round metadata. The stale merge
  behavior in `scripts/update_catalog.py` is removed; index generation covers all
  rounds 1-10, not just the rounds present in a previous index.
- The generator must be run before index regeneration so concept tags are
  complete. Validation fails if an index row's `concept` is not present in the
  YAML, or if a YAML entry is missing from the index.
- `scripts/update_catalog.py` validates canonical and question mappings with
  `question_map()` so the R2/R3-style gaps are caught for every round.

## Generator and review workflow

### Tool

`scripts/build_questions.py`, developer-only. It is never imported at runtime.

### Inputs

- `src/pyafrobarometer/metadata_index.json` for labels, value labels, and vars.
- Optional `--codebooks` enrichment is deferred to a later release.

### Candidate generation

1. Skip variables already covered by canonical mappings.
2. Normalize labels (Unicode NFKC, casefold, strip `Q43A.` prefixes and
   punctuation) and group exact matches.
3. Compare non-missing value labels. Exact label and identical value labels are
   eligible for bulk acceptance; everything else is proposed for review.
4. Fuzzy-match remaining groups with `rapidfuzz` (dev dependency) using token
   overlap blocking and a configurable threshold.
5. Infer target `values` when all rounds share the same non-missing labels.
   Otherwise leave `values` unset and flag the concept. Proposals may therefore
   be incomplete; the validator runs on `questions.yaml`, and incomplete
   proposals are expected in the proposed file.
6. Propose per-round `missing` from declared metadata plus improved detection.
7. Propose recodes by label matching: identical codes/labels need none,
   reordered categories are recoded, extra categories become `null` or a merge
   suggestion.
8. Generate a slug from the concept label; disambiguate duplicates with a
   numeric suffix. Never rename the existing 32 concepts.

### Outputs and merge

- `--propose` writes `build/questions.proposed.yaml`. It contains only new or
  changed candidates and is not shipped.
- `--accept-exact` merges only exact label/value matches.
- `--accept NAME` merges one named proposal. Repeatable.
- Existing entries are never overwritten. New rounds are added to an existing
  concept when labels match; otherwise a new concept is proposed.
- Re-running is idempotent.

### Validation

`scripts/build_questions.py --validate` implements the validation rules above
and additionally:

- Prints concepts by round count and the list of repeated variables not assigned
  to any concept.
- Fails with `--strict-coverage` when a repeated variable (a normalized label
  appearing in at least two rounds) is unassigned.
- Treats strict coverage as a floor, not a ceiling: wording variants that never
  share a normalized label are covered only by fuzzy proposals and manual
  review. The report lists those as unassigned when their labels are similar.
- Checks that the index and YAML agree on concept membership.

### Review loop

`--propose` -> review `build/questions.proposed.yaml` -> `--accept-exact` plus
manual accepts or edits -> `--validate --strict-coverage` -> commit.

## Compatibility and migration

- Existing 32 names stay canonical; no renaming. Their entries are converted to
  the new schema and enriched with target `values` and per-round `label` data.
- `questions.yaml` changes its top-level key from `families:` to `questions:`.
- `family_map()` keeps working as a wrapper.
- `families()` is deprecated and returns the legacy 32.
- `search_variables()` keeps the `family` column as a deprecated alias for one
  release; `concept` is the new column.
- Forced missing-to-NA for harmonized columns is a documented behavior change.
- Version 0.1.2 updates `pyproject.toml` and `src/pyafrobarometer/__init__.py`.

## Testing

- Schema and validator tests: unknown keys, duplicate names, canonical/raw
  collisions, invalid `kind`, missing `values`, bad recode targets, uncovered
  native codes, missing exclude reason, invalid round numbers.
- Generator tests: exact grouping, fuzzy proposals, idempotent rerun,
  `--accept-exact`, merge preservation, coverage report.
- Runtime tests: case-insensitive resolution fixes R2/R3; forced NA; recode
  `null`; target-label decoding; excluded rounds under strict and non-strict;
  `questions()`/`question()`/`families()`; search `concept` column.
- Regression tests: R8/R10 curly-apostrophe DK, `9994`, R2 extra `Always`
  category, reversed difficulty scale.
- Catalog consistency test: every shipped YAML entry resolves against
  `metadata_index.json` offline; no duplicate source variables per round.
- Existing suite must pass after updating tests that assert 32 families.
- Network tests remain opt-in and excluded by default.

## Documentation and release

- Replace family-focused guide pages with question/concept pages; add a
  master-codebook guide; update the API reference, tutorial, README,
  `zensical.toml` navigation, and `docs/development.md` with the
  propose/review/validate workflow.
- Document forced NA, the R2/R3 fix, `questions()`/`question()`, and the
  `families()` deprecation.
- Release 0.1.2: run tests, ruff, mypy, build, `twine check`, and the existing
  PyPI release workflow.

## Risks

- Reviewing ~540 concepts is real work. Exact-match bulk acceptance keeps the
  manual set to the ambiguous entries, but the initial review is still
  substantial.
- Fuzzy matching can propose false merges. Every non-exact match requires review.
- Some concepts will have no honest common codebook. They are handled by
  merging categories, mapping categories to `null`, or excluding a round with a
  recorded reason.
- The YAML grows large. Parsing is cached in-process; `question_map()` is not
  re-parsed per round within a load.
- Forcing NA changes existing behavior for harmonized columns and is called out
  in the release notes.

## Success criteria

- `ab.questions()` exposes every repeated variable assigned during review, with
  the original 32 names unchanged.
- `ab.load(rounds=[2, 9], harmonize=True, variables=[...])` works for stable
  concepts, including the previously broken R2/R3 case.
- Harmonized question columns contain no undeclared missing codes.
- `harmonize=True` without `variables=` still adds only canonical variables plus
  the legacy 32.
- The generator is idempotent, the validator passes with strict coverage, and
  the index contains concept tags and missing codes for all rounds.
- The full offline test suite passes, and the package builds and checks cleanly
  for 0.1.2.
