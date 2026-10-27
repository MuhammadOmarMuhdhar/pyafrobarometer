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

With `harmonize=True`, names may be canonical variables, question concepts, or
raw variables:

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

With harmonization enabled, an unavailable concept in a round becomes a `pd.NA`
column when `strict=False`. A completely unknown name is warned about and is not
added.

## Default harmonized columns

Omit `variables=` with `harmonize=True` to add canonical variables plus the
original 32 concept names:

```python
ds = ab.load(rounds=9, harmonize=True)
print(ds.variables()[["name", "source_var", "source_vars"]])
```

The full catalog is much larger. Use `ab.questions()` to find the concept you need
and request it explicitly; this avoids hundreds of automatic columns.

```python
print(ab.questions()[["name", "rounds"]].head())
```

## See also

- [Loading a round](loading.md)
- [Question harmonization](family-harmonization.md)
- [Master codebook](master-codebook.md)
- [Canonical variables](canonical-variables.md)
- [`load()`](../reference/functions.md#load)
