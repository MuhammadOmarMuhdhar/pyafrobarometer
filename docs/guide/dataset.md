# The Dataset object

[`load()`](../reference/functions.md#load) and
[`panel()`](../reference/functions.md#panel) return a `Dataset`, which wraps a
pandas DataFrame with metadata and provenance.

```python
import pyafrobarometer as ab

ds = ab.load(rounds=9)
print(ds)
```

## Attribute delegation

Attribute access is delegated to the DataFrame:

```python
ds.head()
ds.shape
ds["Q37A"]
ds.groupby("country")["Q37A"].mean()
len(ds)
list(ds)      # column names
```

A missing attribute raises `AttributeError`.

## Properties

| Property | Type | Meaning |
| --- | --- | --- |
| `rounds` | `list[int]` | Rounds in the dataset |
| `countries` | `list[str]` | Countries recorded in provenance |
| `round_meta` | `dict[int, dict]` | Per-round SPSS metadata |
| `round_source_map` | `dict[int, dict[str, str]]` | Per-round harmonized-to-source mapping |
| `harmonized` | `bool` | Whether harmonization was requested |
| `provenance` | `Provenance` | Source and retrieval details |

## variables()

```python
ds.variables()
```

Returns a copy of the variable metadata with `name`, `label`, `value_labels`,
`missing_codes`, and `source_var`. Harmonized columns show the source variable
they came from.

## to_pandas()

```python
ds.to_pandas(labels=False, normalize_missing=False)
```

Returns a copy of the frame. Mutating the copy never mutates the dataset.

- `labels=True` decodes value labels.
- `normalize_missing=True` replaces missing codes with `pd.NA`.

When the dataset spans multiple rounds, metadata is applied per round.

```python
frame = ds.to_pandas(labels=True, normalize_missing=True)
```

## subset()

```python
ds.subset(countries=None, columns=None)
```

Returns a new `Dataset` filtered by country and/or columns. Country matching is
case-insensitive and alias-aware. Metadata and provenance are preserved, and the
recorded countries are updated.

```python
small = ds.subset(countries=["Ghana"], columns=["round", "country", "Q37A"])
```

Raises `HarmonizationError` if country filtering is requested and no country
column exists.

## citation() and codebook()

```python
print(ds.citation())
path = ds.codebook()
```

`citation()` returns the required acknowledgment. `codebook()` downloads the
associated codebook and raises `CodebookError` if none is available. See
[Citation and provenance](citation-and-provenance.md) and
[Codebooks](codebooks.md).

## Copying and iteration

```python
frame = ds.to_pandas()
columns = list(ds)
rows = len(ds)
```

`to_pandas()` is the only way to get a mutable frame. The `Dataset` itself is a
read-through wrapper.

## See also

- [`Dataset`](../reference/dataset.md#dataset)
- [`Provenance`](../reference/dataset.md#provenance)
- [Loading a round](loading.md)
- [Multi-round loads](multi-round.md)
