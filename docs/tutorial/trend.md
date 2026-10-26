# Build the trend

Now build the multi-round panel and export the result.

```python
panel = ab.panel(rounds=ROUNDS, variables=["trust_president", "weight"])
frame = panel.to_pandas(normalize_missing=True)
frame = frame.dropna(subset=["trust_president", "weight"])

frame["weighted_trust"] = frame["trust_president"] * frame["weight"]

trend = (
    frame.groupby(["round", "country"])
    .agg(
        weighted_sum=("weighted_trust", "sum"),
        weight_sum=("weight", "sum"),
        respondents=("trust_president", "size"),
    )
    .reset_index()
)
trend["mean_trust"] = trend["weighted_sum"] / trend["weight_sum"]
trend = trend[["round", "country", "mean_trust", "respondents"]]
trend = trend.sort_values(["round", "country"]).reset_index(drop=True)

print(trend.head())
trend.to_csv("trust_trend.csv", index=False)
```

## What `panel()` did

`panel()` loads each round with harmonization enabled, keeps the keys `round`,
`country`, and `year`, and concatenates the requested variables. The result is a
`Dataset` with:

- `round` — the survey round.
- `country` — the country name.
- `year` — the survey year from the catalog.
- `trust_president` — the harmonized variable.
- `weight` — the survey weight, included because it was requested.

`panel()` keeps only the keys and the variables you request, so include `weight`
when you need weighted means.

Because the panel keeps per-round metadata, `to_pandas(normalize_missing=True)`
uses each round's own missing-code definitions.

## Inspect the result

```python
print(trend.shape)
print(trend["respondents"].sum())
print(trend.pivot(index="country", columns="round", values="mean_trust").head())
```

The pivot is a quick way to see change over time. Countries missing from a round
show `NaN`.

## The CSV

`trust_trend.csv` has one row per round and country:

```text
round,country,mean_trust,respondents
8,Benin,1.42,1200
8,Ghana,1.87,1200
...
```

You can open it in pandas, a spreadsheet, or a plotting tool.

## Next

[Cite the data and finish](cite.md).
