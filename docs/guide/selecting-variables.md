# Selecting variables

`variables=` limits which columns are loaded or harmonized.

## Raw variables

Without harmonization, names are raw source columns:

```python
import pyafrobarometer as ab

raw = ab.load(rounds=9, variables=["Q37A", "Q1"])
print(raw.to_pandas().head())
```

The package reads only the requested columns where possible. A variable that does
not exist in the round is handled according to `strict`.

## Harmonized variables

With `harmonize=True`, names may be question families or canonical variables:

```python
clean = ab.load(
    rounds=9,
    harmonize=True,
    variables=["trust_president", "age", "gender"],
)
```

Canonical names include `country`, `respondent_id`, `weight`, `region`,
`urban_rural`, `age`, `gender`, `education`, and `interview_date`.

## Strict mode

```python
# Raise on unavailable names.
ab.load(rounds=9, variables=["Q37A", "NOT_A_VARIABLE"])

# Warn and keep what exists.
ds = ab.load(rounds=9, variables=["Q37A", "NOT_A_VARIABLE"], strict=False)
```

- `strict=True` (default) raises `HarmonizationError`.
- `strict=False` warns and keeps the columns that exist.

With harmonization enabled, an unavailable family in a round becomes a `pd.NA`
column when `strict=False`. A completely unknown name is warned about and is not
added.

## Selecting all families

Omit `variables=` with `harmonize=True` to add every family available in the
round:

```python
ds = ab.load(rounds=9, harmonize=True)
print(ds.variables()[["name", "source_var"]])
```

This can produce many columns. Select explicitly when you know what you need.

## See also

- [Loading a round](loading.md)
- [Question-family harmonization](family-harmonization.md)
- [Canonical variables](canonical-variables.md)
- [`load()`](../reference/functions.md#load)
