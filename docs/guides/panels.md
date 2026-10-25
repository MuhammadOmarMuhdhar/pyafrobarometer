# Panels

[`panel()`](../reference/functions.md#panel) builds a multi-round dataset for a
set of harmonized variables.

```python
import pyafrobarometer as ab

panel = ab.panel(
    rounds=[8, 9],
    variables=["trust_president", "support_democracy"],
)
frame = panel.to_pandas(normalize_missing=True)

print(frame.columns)
print(frame.groupby("round")[["trust_president", "support_democracy"]].mean())
```

Each round is loaded with `harmonize=True`. The result contains the keys
`round`, `country`, and `year`, followed by the requested variables.

## Requirements

- `rounds` and `variables` are required.
- Every requested variable must be available in every requested round. If one is
  missing, `panel()` raises `HarmonizationError` naming the missing variables.
- Variable names are harmonized names: question families from
  [`families()`](../reference/functions.md#families) or canonical variables such
  as `age` and `gender`.

`strict` is passed through to each round's load. With `strict=False`, an
unavailable family becomes a `pd.NA` column, but the variable must still exist in
every round for the panel to be assembled.

## Filtering countries

```python
panel = ab.panel(
    rounds=[7, 8, 9],
    variables=["trust_president"],
    countries=["Ghana", "Kenya", "Nigeria"],
)
```

Country filtering uses the same alias-aware matching as
[`load()`](../reference/functions.md#load).

## Labels

```python
panel = ab.panel(rounds=[8, 9], variables=["trust_president"], labels=True)
frame = panel.to_pandas()
```

Value labels are decoded per round using that round's metadata, so a code that
means different things in different rounds is decoded correctly.

## Provenance

The panel's provenance combines the source URLs, years, and rounds of its
component datasets:

```python
print(panel.provenance.source_urls)
print(panel.provenance.rounds)
print(panel.provenance.years)
```

## Typical trend workflow

```python
panel = ab.panel(rounds=[6, 7, 8, 9, 10], variables=["trust_president"])
frame = panel.to_pandas(normalize_missing=True)

trend = (
    frame.dropna(subset=["trust_president"])
    .groupby(["round", "country"])["trust_president"]
    .mean()
    .unstack("round")
)
print(trend.head())
```

## See also

- [Harmonization](harmonization.md)
- [Value labels and missing codes](labels-and-missing.md)
- [`panel()`](../reference/functions.md#panel)
