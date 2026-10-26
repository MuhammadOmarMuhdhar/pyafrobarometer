# Loading a round

[`load()`](../reference/functions.md#load) returns a `Dataset`: a pandas
DataFrame plus metadata and provenance.

## Basic loading

```python
import pyafrobarometer as ab

ds = ab.load(rounds=9)
print(ds)
```

`rounds` accepts a single round number or an iterable of rounds. When omitted,
every merged round in the catalog is loaded.

The result always has:

- `round` — the round number.
- `year` — the survey year from the catalog, or `pd.NA` for a local source
  without catalog metadata.

## Selecting rounds

```python
one = ab.load(rounds=9)
many = ab.load(rounds=[8, 9, 10])
```

Loading more than one round concatenates the frames and merges their metadata.
See [Multi-round loads](multi-round.md).

## Language

Merged datasets exist in English and sometimes French:

```python
ds_fr = ab.load(rounds=9, language="fr")
```

`language="en"` is the default. The filter applies to both merged and
country-level catalog entries.

## What gets downloaded

The first load downloads the requested data file into the local cache. Later
loads reuse it. Set `PYAFROBAROMETER_OFFLINE=1` to forbid network access. See
[Caching, TTL, and offline mode](caching-and-offline.md).

Pass `refresh=True` to force a catalog refresh before the round is selected. This
is separate from the data cache: an already-downloaded file is still reused.

## Inspecting the result

```python
print(ds.shape)
print(ds.rounds)
print(ds.countries[:5])
print(ds.variables().head())
print(ds.to_pandas().head())
```

`Dataset` delegates attribute access to the DataFrame, so `ds.head()` and
`ds.shape` work. See [The Dataset object](dataset.md).

## Options

The full signature is:

```python
ab.load(
    rounds=None,
    countries=None,
    variables=None,
    labels=False,
    normalize_missing=False,
    harmonize=False,
    language="en",
    source=None,
    refresh=False,
    strict=True,
)
```

The following chapters cover each option:

- [Selecting variables](selecting-variables.md)
- [Value labels](value-labels.md)
- [Missing codes](missing-codes.md)
- [Canonical variables](canonical-variables.md)
- [Question-family harmonization](family-harmonization.md)
- [Local and remote sources](sources.md)

## See also

- [`load()`](../reference/functions.md#load)
- [Tutorial: load and inspect](../tutorial/load.md)
