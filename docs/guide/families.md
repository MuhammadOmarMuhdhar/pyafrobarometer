# Question concepts

Question concepts give every repeated survey item a stable name across rounds.
They replace the older, 32-item "question families" layer. The concept name is
the column you request with `harmonize=True`, and the shipped master codebook
records the source variable, wording, recodes, and missing codes for each round.

```python
import pyafrobarometer as ab

questions = ab.questions()
print(questions[["name", "description", "rounds"]].head())
```

## Columns

`ab.questions()` returns one row per concept:

| Column | Meaning |
| --- | --- |
| `name` | Stable concept name you can request |
| `description` | Human-readable description |
| `kind` | `coded` or `text` |
| `rounds` | Sorted rounds where the concept is available |
| `variables` | Mapping of round number to source variable |
| `values` | Target value labels, empty for `text` concepts |

```python
trust = questions[questions["name"] == "trust_president"].iloc[0]
print(trust["rounds"])
print(trust["variables"])
print(trust["values"])
```

## Inspecting one concept

`ab.question(name)` is the authoritative per-round view:

```python
print(ab.question("trust_president"))
```

It returns `round`, `var`, `label`, `recode`, `missing`, `excluded`, and
`reason`. Excluded rounds appear with `excluded=True` and a reason instead of a
source variable.

## Sparse availability

Concepts are sparse by design:

- `social_media_news` is available from Round 6.
- `trust_army` is missing in Round 4.
- `bribe_police` starts in Round 6.
- Some Round 1 institutional-trust items are recoded from a 1–4 scale to 0–3.

Always check `rounds` before requesting a concept for a specific round.

## Finding a concept

```python
questions[questions["name"].str.contains("trust")]
questions[questions["description"].str.contains("democracy", case=False)]
```

For free-text search over concepts, raw variables, and labels, use
[`search_variables()`](../reference/functions.md#search_variables). Search results
include a `concept` column, so a raw `Q37A` can be traced back to
`trust_president`.

## Source variables

The `variables` mapping tells you which raw column backs the concept in each
round. For `trust_president`:

| Round | Source |
| --- | --- |
| 1 | `trspre` (recoded) |
| 2 | `Q43A` |
| 3 | `Q55A` |
| 4 | `Q49A` |
| 5 | `Q59A` |
| 6 | `Q52A` |
| 7 | `Q43A` |
| 8 | `Q41A` |
| 9 | `Q37A` |
| 10 | `Q37A` |

This is why hard-coding a source variable is fragile. Variable lookup is
case-insensitive, so Rounds 2 and 3 (`q43a`, `q80`) resolve correctly.

## Adding concepts to a load

```python
ds = ab.load(rounds=9, harmonize=True, variables=["trust_president"])
```

With `harmonize=True` and no `variables=`, the package adds canonical variables
plus only the original 32 concepts. Request any other concept by name.

See [Question harmonization](family-harmonization.md) for forced missing
normalization, strict mode, and recoding behavior.

## Deprecated `families()`

`ab.families()` still works for the original 32 names, but emits
`DeprecationWarning`. Use `ab.questions()` for the full catalog and
`ab.question(name)` for per-round details.

## See also

- [Question harmonization](family-harmonization.md)
- [Master codebook](master-codebook.md)
- [Variable search](search.md)
- [`questions()` and `question()`](../reference/functions.md#questions)
- [Tutorial: discover the data](../tutorial/discover.md)
