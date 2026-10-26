# Panels

[`panel()`](../reference/functions.md#panel) builds a multi-round dataset for a
fixed set of harmonized variables.

```python
import pyafrobarometer as ab

panel = ab.panel(
    rounds=[8, 9, 10],
    variables=["trust_president", "support_democracy"],
)
frame = panel.to_pandas(normalize_missing=True)

print(frame.columns)
print(frame.groupby("round")[["trust_president", "support_democracy"]].mean())
```

## Result shape

The result contains the keys `round`, `country`, and `year`, followed by the
requested variables.

```python
print(panel.rounds)
print(panel.countries[:5])
print(panel.provenance.years)
```

## Requirements

- `rounds` and `variables` are required.
- With the default `strict=True`, every requested variable must be available in
  every requested round. If one is missing, `panel()` raises
  `HarmonizationError` naming the missing variables.
- Variable names are harmonized names: question families or canonical variables.

`strict` is passed through to each round's load. With `strict=False`, an
unavailable family becomes a `pd.NA` column, so the panel can still be assembled.
A completely unknown name is warned about and is not added, which makes the
panel fail because the column is missing from one or more rounds.

## Filtering countries

```python
panel = ab.panel(
    rounds=[7, 8, 9],
    variables=["trust_president"],
    countries=["Ghana", "Kenya", "Nigeria"],
)
```

Country matching is case-insensitive and alias-aware. See
[Countries and coverage](countries.md).

## Labels

```python
panel = ab.panel(rounds=[8, 9], variables=["trust_president"], labels=True)
frame = panel.to_pandas()
```

Labels are decoded per round using that round's metadata.

## Weighted means

`panel()` keeps only the keys and the variables you request. Include `weight` in
`variables` when you need weighted means:

```python
panel = ab.panel(
    rounds=[8, 9, 10],
    variables=["trust_president", "weight"],
)
frame = panel.to_pandas(normalize_missing=True).dropna(
    subset=["trust_president", "weight"]
)
frame["weighted_trust"] = frame["trust_president"] * frame["weight"]

trend = (
    frame.groupby(["round", "country"])
    .agg(
        weighted_sum=("weighted_trust", "sum"),
        weight_sum=("weight", "sum"),
    )
)
trend["mean_trust"] = trend["weighted_sum"] / trend["weight_sum"]
print(trend.head())
```

See [Weights](weights.md) for the reasoning.

## Provenance

```python
print(panel.provenance.source_urls)
print(panel.provenance.rounds)
print(panel.provenance.years)
```

See [Citation and provenance](citation-and-provenance.md).

## See also

- [Multi-round loads](multi-round.md)
- [Weights](weights.md)
- [`panel()`](../reference/functions.md#panel)
- [Tutorial: build the trend](../tutorial/trend.md)
