# Quickstart

This page walks through the main workflow: discover what exists, load a round,
harmonize it, and compare rounds.

!!! note "The first load downloads data"

    Discovery uses the shipped catalog or a cached index. `load()` and
    `panel()` download the requested data files from `www.afrobarometer.org` into
    the local cache the first time. Later calls reuse the cache. Set
    `PYAFROBAROMETER_OFFLINE=1` to forbid network access; see
    [Caching and offline use](../guides/caching-and-offline.md).

## 1. Discover what is available

```python
import pyafrobarometer as ab

print(ab.rounds()[["round", "year", "language", "data_url"]])
print(ab.families()[["family", "rounds"]])
print(ab.countries(round=9)[:10])
```

`rounds()` lists merged datasets, `families()` lists comparable question
families and the rounds that carry them, and `countries()` lists country names.

## 2. Load a round

```python
ds = ab.load(rounds=9)
print(ds)
print(ds.variables().head())
print(ds.to_pandas(normalize_missing=True).head())
```

`Dataset` wraps a pandas DataFrame. Attribute access is delegated, so
`ds.head()`, `ds.shape`, `ds["Q37A"]`, and `len(ds)` work as expected.
`ds.to_pandas()` always returns a copy; mutating it never mutates the dataset.

## 3. Add canonical columns and harmonized families

```python
ds = ab.load(rounds=9, harmonize=True)
frame = ds.to_pandas()
print(frame[["country", "age", "trust_president"]].head())
```

With `harmonize=True`, canonical variables such as `country`, `age`, `gender`,
and `weight` are added, and requested question families such as
`trust_president` are mapped from the round's source variable. See
[Harmonization](../guides/harmonization.md) for the full list and the rules for
missing mappings.

## 4. Compare rounds

```python
panel = ab.panel(rounds=[8, 9], variables=["trust_president"])
trend = panel.to_pandas(normalize_missing=True)
print(trend.groupby("round")["trust_president"].mean())
```

`panel()` loads each round with harmonization enabled, keeps the keys `round`,
`country`, and `year`, and concatenates the requested variables. See
[Panels](../guides/panels.md).

## Next steps

- [Discovery](../guides/discovery.md)
- [Loading data](../guides/loading.md)
- [Harmonization](../guides/harmonization.md)
- [Value labels and missing codes](../guides/labels-and-missing.md)
- [API reference](../reference/index.md)
