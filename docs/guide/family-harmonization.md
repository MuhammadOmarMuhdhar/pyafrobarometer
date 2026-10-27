# Question harmonization

Question harmonization adds stable, comparable concept columns across rounds.

```python
import pyafrobarometer as ab

ds = ab.load(
    rounds=9,
    harmonize=True,
    variables=["trust_president", "support_democracy"],
)
print(ds.to_pandas()[["country", "trust_president", "support_democracy"]].head())
```

## How it works

For each requested concept, the package looks up the round's source variable in
`questions.yaml`, replaces declared missing codes with `pd.NA`, applies any
recoding, and writes the result under the concept name. Lookup is
case-insensitive, which fixes the lowercase variable names in Rounds 2 and 3.

For harmonized question columns, missing normalization is **always on**. You do
not need `normalize_missing=True`; that option remains meaningful for raw,
non-harmonized columns.

`ds.variables()` records the mapping in `source_vars` (round → variable) and
`source_var` (the earliest included round's variable). `ab.question(name)` shows
every round, including excluded rounds.

## Default `harmonize=True`

With no `variables=`, the package adds canonical variables plus only the original
32 concept names:

```python
ds = ab.load(rounds=9, harmonize=True)
```

All other concepts are opt-in. Request them explicitly:

```python
ds = ab.load(
    rounds=9,
    harmonize=True,
    variables=["access_information_local_government_development_plan_budget"],
)
```

## Sparse concepts and strict mode

If a concept is unavailable or explicitly excluded in a round:

```python
# Raise (default).
ab.load(rounds=4, harmonize=True, variables=["trust_army"])

# Warn and add a pd.NA column.
ds = ab.load(rounds=4, harmonize=True, variables=["trust_army"], strict=False)
```

- `strict=True` raises `HarmonizationError`.
- `strict=False` warns and adds a column filled with `pd.NA`.

An unknown name is warned about and omitted with `strict=False`, even if it is
not a concept.

## Recoding and target values

Recodes and per-category exclusions live in the master codebook. For example,
Round 1 institutional-trust items are recoded from 1–4 to 0–3, and categories
that do not belong on the target scale are mapped to `pd.NA`.

`ds.to_pandas(labels=True)` decodes harmonized concepts with the concept's
target `values`, so code `2` means the same thing in every round. Canonical
variables keep per-round labels, and `kind: text` concepts are never decoded.

## Combining with canonical variables

```python
ds = ab.load(
    rounds=9,
    harmonize=True,
    variables=["trust_president", "age", "gender"],
)
```

Canonical names and concept names can be mixed. See
[Canonical variables](canonical-variables.md).

## Inspecting concepts

```python
questions = ab.questions()
print(questions[["name", "description", "rounds"]])
print(ab.question("trust_president"))
```

See [Question concepts](families.md) for the catalog and source mappings, and
[Master codebook](master-codebook.md) for the YAML format and review workflow.

## See also

- [Question concepts](families.md)
- [Master codebook](master-codebook.md)
- [Selecting variables](selecting-variables.md)
- [`questions()` and `question()`](../reference/functions.md#questions)
- [Tutorial: discover the data](../tutorial/discover.md)
