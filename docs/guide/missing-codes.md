# Missing codes

Survey files encode "don't know", "refused", and "not applicable" as numeric
codes. If you leave them in, a missing answer can look like a valid value.

## Normalize missing codes

```python
import pyafrobarometer as ab

ds = ab.load(rounds=9, normalize_missing=True)
frame = ds.to_pandas()
print(frame["Q37A"].isna().sum())
```

`normalize_missing=True` replaces declared missing codes with `pd.NA`.

You can also normalize after loading:

```python
ds = ab.load(rounds=9)
clean = ds.to_pandas(normalize_missing=True)
```

## Where missing codes come from

The package collects them from three sources:

1. **Declared range** — the SPSS `missing_ranges` metadata.
2. **User-missing values** — explicit values in `missing_user_values`.
3. **Fallback codes** — conventional codes whose labels look missing.

The fallback set is `8`, `9`, `97`, `98`, `99`, `997`, `998`, `999`, and `-1`. A
code is only treated as missing when its label looks like "don't know",
"refused", "missing", "no answer", "unknown", "not applicable", "not asked", or
similar.

## Why it matters

Consider a trust question coded 0–3 with `9` for "don't know":

```python
raw = ab.load(rounds=9).to_pandas()["Q37A"]
print(raw.mean())          # 9s inflate the mean

clean = ab.load(rounds=9).to_pandas(normalize_missing=True)["Q37A"]
print(clean.mean())        # 9s removed
```

Always decide how to handle missing data and report it.

## Per-round behavior

When a dataset spans multiple rounds, each round's missing definitions are used:

```python
ds = ab.load(rounds=[8, 9], harmonize=True, normalize_missing=True)
print(ds.to_pandas()["trust_president"].isna().sum())
```

## Missing versus labels

`labels=True` and `normalize_missing=True` can be combined. Normalization runs
first conceptually; decoded output shows `NaN` for missing values.

```python
ds = ab.load(rounds=9, labels=True, normalize_missing=True)
print(ds.to_pandas()["Q37A"].value_counts(dropna=False).head())
```

## See also

- [Value labels](value-labels.md)
- [The Dataset object](dataset.md)
- [`load()`](../reference/functions.md#load)
- [Tutorial: clean and weight](../tutorial/clean.md)
