# Multi-round loads

Pass a list of rounds to load several rounds at once.

```python
import pyafrobarometer as ab

ds = ab.load(rounds=[8, 9, 10], harmonize=True, variables=["trust_president"])
frame = ds.to_pandas()
print(frame.groupby("round")["trust_president"].mean())
```

## What happens

- Each round is downloaded and loaded separately.
- Frames are concatenated with `pd.concat`.
- Metadata is merged, keeping per-round definitions.
- `round` and `year` identify the source round.
- The recorded countries are the union of countries across rounds.

## Per-round metadata

A merged load keeps per-round SPSS metadata:

```python
print(ds.rounds)
print(ds.round_meta.keys())
print(ds.round_source_map[9])
```

`to_pandas(labels=True)` and `to_pandas(normalize_missing=True)` use each round's
metadata, so codes decode correctly across rounds.

## Countries across rounds

```python
print(len(ds.countries))
print(frame.groupby("round")["country"].nunique())
```

Not every country appears in every round. Group by round before comparing
country counts.

## When to use `panel()` instead

`load(rounds=[...])` is a general concatenation. For a tidy analysis frame with
the keys `round`, `country`, and `year` and a fixed variable set, use
[`panel()`](../reference/functions.md#panel). See [Panels](panels.md).

## Memory

Loading many rounds or many concepts can produce a large frame. Select `variables`
and `countries` to keep memory under control.

## See also

- [Panels](panels.md)
- [Loading a round](loading.md)
- [The Dataset object](dataset.md)
- [`load()`](../reference/functions.md#load)
