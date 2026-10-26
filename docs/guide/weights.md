# Weights

Afrobarometer samples are designed to represent national populations, but the
raw sample is not self-weighting. Use weights for population-level estimates.

## The canonical weight column

With `harmonize=True`, the package adds a `weight` column:

```python
import pyafrobarometer as ab

ds = ab.load(rounds=9, harmonize=True)
frame = ds.to_pandas()
print(frame[["country", "weight"]].head())
```

The source differs by round. When a round includes `withinwt_hh`, the package
prefers it; otherwise it uses the round's `withinwt` or equivalent.

## Weighted mean

```python
frame = ab.load(rounds=9, harmonize=True).to_pandas(normalize_missing=True)
clean = frame.dropna(subset=["trust_president", "weight"])

weighted = (
    (clean["trust_president"] * clean["weight"]).sum()
    / clean["weight"].sum()
)
print(weighted)
```

Compare with the unweighted mean:

```python
print(clean["trust_president"].mean())
```

The two can differ when some groups are over- or under-sampled.

## Weighted means by group

```python
frame["weighted_trust"] = frame["trust_president"] * frame["weight"]

by_country = (
    frame.dropna(subset=["trust_president", "weight"])
    .groupby("country")
    .agg(
        weighted_sum=("weighted_trust", "sum"),
        weight_sum=("weight", "sum"),
    )
)
by_country["mean_trust"] = by_country["weighted_sum"] / by_country["weight_sum"]
print(by_country.head())
```

## Panels

[`panel()`](../reference/functions.md#panel) keeps only the keys and the
variables you request. Include `weight` explicitly:

```python
panel = ab.panel(
    rounds=[8, 9, 10],
    variables=["trust_president", "weight"],
)
frame = panel.to_pandas(normalize_missing=True)
print(frame[["round", "country", "weight"]].head())
```

The [tutorial](../tutorial/trend.md) uses this pattern to build a weighted trend.

## When not to weight

Weights are intended for descriptive population estimates. For some modeling
tasks you may choose unweighted data, but state your choice and justify it.

## See also

- [Canonical variables](canonical-variables.md)
- [Panels](panels.md)
- [Tutorial: clean and weight](../tutorial/clean.md)
- [`load()`](../reference/functions.md#load)
