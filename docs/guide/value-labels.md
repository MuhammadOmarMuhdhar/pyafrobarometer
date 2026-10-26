# Value labels

SPSS files store numeric codes and a mapping from codes to text. By default,
pyafrobarometer keeps the numeric codes.

## Raw codes

```python
import pyafrobarometer as ab

ds = ab.load(rounds=9)
print(ds.to_pandas()["Q37A"].value_counts(dropna=False).head())
```

The output is numeric. This is what you want for arithmetic.

## Decoded labels

```python
ds = ab.load(rounds=9, labels=True)
print(ds.to_pandas()["Q37A"].value_counts(dropna=False).head())
```

`labels=True` replaces codes with label text. Decoded columns use `object` dtype.
Codes without a label stay numeric.

You can also decode after loading:

```python
ds = ab.load(rounds=9)
labeled = ds.to_pandas(labels=True)
```

## Per-round decoding

When a dataset spans multiple rounds, labels are applied using each round's own
metadata. The same code can mean different things in different rounds without
cross-contamination.

```python
ds = ab.load(rounds=[8, 9], harmonize=True, labels=True)
frame = ds.to_pandas()
print(frame.groupby("round")["trust_president"].value_counts().head())
```

## Labels and harmonized columns

For a harmonized column such as `trust_president`, the package uses the metadata
of the source variable that produced it. This is why labels work even though the
harmonized name does not exist in the SPSS file.

## When to use labels

Use labels for inspection, tables, and plots. Keep raw codes for means,
regressions, and any numeric computation.

## See also

- [Missing codes](missing-codes.md)
- [The Dataset object](dataset.md)
- [`Dataset.to_pandas()`](../reference/dataset.md#to_pandas)
- [Tutorial: clean and weight](../tutorial/clean.md)
