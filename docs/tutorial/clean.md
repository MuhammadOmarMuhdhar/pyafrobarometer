# Clean and weight the data

Survey codes need two fixes before averaging: missing values and weights.

## Normalize missing codes

```python
frame = ds.to_pandas(normalize_missing=True)
clean = frame.dropna(subset=["trust_president", "weight"])

print(clean["trust_president"].value_counts(dropna=False).head())
```

`normalize_missing=True` replaces declared missing codes with `pd.NA`. Without
it, a code like `9` ("don't know") would be averaged as if it were a valid
answer.

The `dropna` call removes rows that cannot contribute to a weighted mean.

## Decode labels (optional)

Labels are useful for inspection, not for arithmetic:

```python
labeled = ds.to_pandas(labels=True, normalize_missing=True)
print(labeled["trust_president"].value_counts(dropna=False).head())
```

Now the values read "Not at all", "Just a little", and so on. Keep the numeric
version for calculations.

## Apply weights

Afrobarometer samples are not self-weighting. The package provides a canonical
`weight` column, preferring `withinwt_hh` when the round includes it.

```python
unweighted = clean["trust_president"].mean()
weighted = (
    (clean["trust_president"] * clean["weight"]).sum()
    / clean["weight"].sum()
)

print(f"unweighted={unweighted:.2f} weighted={weighted:.2f}")
```

The weighted mean is usually the right choice for population-level statements.
Report which one you used.

## Check the scale

`trust_president` is coded 0–3 in the harmonized data:

| Code | Meaning |
| --- | --- |
| 0 | Not at all |
| 1 | Just a little |
| 2 | Somewhat |
| 3 | A lot |

Round 1 is recoded from its original 1–4 scale to match.

## Next

[Build the trend](trend.md).
