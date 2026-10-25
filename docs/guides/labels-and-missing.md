# Value labels and missing codes

By default, `load()` keeps the raw numeric codes from the SPSS file. Two options
change that:

```python
ds = ab.load(rounds=9, labels=True, normalize_missing=True)
frame = ds.to_pandas()
```

## Value labels

`labels=True` decodes value labels from the SPSS metadata:

```python
ds = ab.load(rounds=9, labels=True)
frame = ds.to_pandas()
print(frame["Q37A"].value_counts(dropna=False))
```

Decoded columns use `object` dtype and contain the label text. Codes without a
label stay as their numeric value. Use this when you want readable categories;
keep the default when you need numeric analysis.

## Missing codes

`normalize_missing=True` replaces declared missing codes with `pd.NA`:

```python
ds = ab.load(rounds=9, normalize_missing=True)
frame = ds.to_pandas()
print(frame["Q37A"].isna().sum())
```

Missing codes are collected from three sources:

1. The SPSS declared missing range (`missing_ranges`).
2. Explicit user-missing values (`missing_user_values`).
3. Fallback codes that have labels indicating missing data. The fallback set is
   `8`, `9`, `97`, `98`, `99`, `997`, `998`, `999`, and `-1`, and a code is only
   treated as missing when its label looks like "don't know", "refused",
   "missing", "no answer", "not applicable", or similar.

The default keeps raw codes, so a mean that includes `9` ("don't know") will be
biased. Normalize missing values before computing statistics.

## Both together

```python
ds = ab.load(rounds=9, labels=True, normalize_missing=True)
frame = ds.to_pandas()
print(frame["trust_president"].value_counts(dropna=False))
```

With harmonization enabled, the conversion follows the source variable for each
harmonized column:

```python
ds = ab.load(rounds=9, harmonize=True, labels=True, normalize_missing=True)
print(ds.to_pandas()[["country", "trust_president"]].head())
```

When a dataset spans multiple rounds, metadata is applied per round. The same
numeric code can therefore decode differently in different rounds without
cross-contamination.

## See also

- [`load()`](../reference/functions.md#load)
- [`Dataset.to_pandas()`](../reference/dataset.md#to_pandas)
- [Harmonization](harmonization.md)
