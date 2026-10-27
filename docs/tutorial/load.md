# Load and inspect a round

Add the load step:

```python
ds = ab.load(rounds=9, harmonize=True, variables=["trust_president"])

print(ds)
print(ds.variables()[["name", "label", "source_var"]])
print(ds.to_pandas()[["country", "trust_president"]].head())
```

The first run downloads the Round 9 merged file into the local cache. Later runs
reuse it.

## What happened

- `rounds=9` selects the merged Round 9 file.
- `harmonize=True` adds canonical columns (`country`, `age`, `weight`, …) and
  the requested `trust_president` concept.
- `variables=["trust_president"]` limits the harmonized concepts to the one you
  need.

`ds` is a `Dataset`, not a raw DataFrame. Its representation summarizes the
rounds, countries, row count, and whether harmonization was applied.

`ds.variables()` shows the variable metadata. For `trust_president`, the
`source_var` column tells you which raw variable it came from (`Q37A` in Round
9).

`ds.to_pandas()` returns a copy of the frame:

```python
frame = ds.to_pandas()
print(frame[["country", "trust_president"]].head())
```

## Inspect before you analyze

Useful checks at this stage:

```python
print(frame["country"].nunique())
print(frame["trust_president"].value_counts(dropna=False).head())
print(frame["trust_president"].isna().sum())
```

The raw values are still numeric codes. A `9` means "don't know", not a high
level of trust. You will fix that next.

## Next

[Clean and weight the data](clean.md).
