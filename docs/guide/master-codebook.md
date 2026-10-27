# Master codebook

The master codebook is the reviewed, shipped source of truth for cross-round
question concepts. It lives at
[`src/pyafrobarometer/crosswalk/questions.yaml`](https://github.com/MuhammadOmarMuhdhar/pyafrobarometer/blob/main/src/pyafrobarometer/crosswalk/questions.yaml)
and is read at runtime by `load()`, `panel()`, `questions()`, and `question()`.

Nothing is derived from the live website at query time. The YAML is committed,
reviewed, and versioned with the package.

## Schema

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
        label: Trust the president to do what is right?
        missing: [8, 9]
        recode: {1: 0, 2: 1, 3: 2, 4: 3}
      2:
        var: q43a
      10:
        var: Q37A
        missing: [-1, 8, 9, 9994]
  interviewer_comment:
    description: Interviewer comment
    kind: text
    rounds:
      9:
        var: Q119v
```

### Fields

| Field | Meaning |
| --- | --- |
| `description` | Human-readable concept description |
| `kind` | `coded` (default) or `text` |
| `values` | Target codebook for `coded` concepts |
| `rounds` | Per-round mapping |
| `rounds.<n>.var` | Source variable; lookup is case-insensitive |
| `rounds.<n>.label` | Source wording, also the reviewable codebook text |
| `rounds.<n>.recode` | Native code → target code; `null` means `pd.NA` |
| `rounds.<n>.missing` | True missing codes, always mapped to `pd.NA` |
| `rounds.<n>.exclude` | Drop the round from the concept |
| `rounds.<n>.reason` | Required explanation for an excluded round |

There is no `status` field. The committed YAML is approved by definition.

## Runtime behavior

- Coded concept columns are normalized: `missing` and `recode: null` become
  `pd.NA`, whether or not `normalize_missing=True`.
- `labels=True` uses the concept's target `values`, not the per-round source
  labels.
- `text` concepts are copied without recoding or label decoding.
- Variable lookup is case-insensitive, so `q43a` in Rounds 2–3 resolves.
- `strict=True` raises when a requested concept is absent or excluded in a
  round; `strict=False` warns and adds a `pd.NA` column.

## Discovery APIs

```python
import pyafrobarometer as ab

ab.questions()             # one row per concept
ab.question("trust_president")  # per-round var, label, recode, missing, excluded
```

`search_variables()` also searches concept names and descriptions and returns a
`concept` column, so a raw variable can be traced to its stable name.

## Developer workflow

The generator is a build-time authoring aid. It never runs during `load()` and
never silently edits the reviewed truth file.

```bash
# Show the available modes.
uv run python scripts/build_questions.py --help

# Propose candidates into build/questions.proposed.yaml.
uv run python scripts/build_questions.py --propose

# Accept candidates explicitly.
uv run python scripts/build_questions.py --accept trust_president
uv run python scripts/build_questions.py --accept-exact

# Validate schema, source variables, and coverage.
uv run python scripts/build_questions.py --validate
uv run python scripts/build_questions.py --validate --strict-coverage
```

Review the proposed YAML, merge the entries you want, and rerun validation. The
weekly catalog job only refreshes metadata; it never changes the reviewed
crosswalk.

## Derived metadata index

`src/pyafrobarometer/metadata_index.json` is generated from the codebook and
per-round metadata. Each mapped variable carries a `concept` tag, and only the
original 32 concepts also carry a deprecated `family` tag. The index is what
`search_variables()` and `countries()` read, so discovery stays fast and offline.

## See also

- [Question concepts](families.md)
- [Question harmonization](family-harmonization.md)
- [Variable search](search.md)
- [Development](../development.md)
