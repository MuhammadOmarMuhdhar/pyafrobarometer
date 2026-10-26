# Question-family harmonization

Question families add stable, comparable columns across rounds.

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

For each requested family, the package looks up the round's source variable in
the crosswalk, applies any recoding, and writes the result under the family name.
The `source_var` column in `ds.variables()` records the mapping.

## All families by default

Omit `variables=` with `harmonize=True` to add every family available in the
round:

```python
ds = ab.load(rounds=9, harmonize=True)
```

This can produce many columns. Prefer explicit selection when you know what you
need.

## Sparse families and strict mode

Families are sparse. If a family is unavailable in a round:

```python
# Raise (default).
ab.load(rounds=4, harmonize=True, variables=["trust_army"])

# Warn and add a pd.NA column.
ds = ab.load(rounds=4, harmonize=True, variables=["trust_army"], strict=False)
```

- `strict=True` raises `HarmonizationError`.
- `strict=False` warns and adds a column filled with `pd.NA`.

A family that does not exist in the crosswalk at all is warned about and is not
added, even with `strict=False`.

## Recoding

Some families recode the source scale. For example, Round 1 institutional-trust
items are recoded from 1–4 to 0–3 so they match later rounds. The recode is part
of the crosswalk; you do not need to do it manually.

## Combining with canonical variables

```python
ds = ab.load(
    rounds=9,
    harmonize=True,
    variables=["trust_president", "age", "gender"],
)
```

Canonical names and family names can be mixed. See
[Canonical variables](canonical-variables.md).

## Inspecting families

```python
families = ab.families()
print(families[["family", "description", "rounds"]])
```

See [Question families](families.md) for the catalog and source mappings.

## See also

- [Question families](families.md)
- [Selecting variables](selecting-variables.md)
- [`families()`](../reference/functions.md#families)
- [Tutorial: discover the data](../tutorial/discover.md)
