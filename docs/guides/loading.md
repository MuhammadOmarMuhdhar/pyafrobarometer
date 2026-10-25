# Loading data

[`load()`](../reference/functions.md#load) returns a `Dataset`: a pandas
DataFrame plus variable metadata and provenance.

## Basic loading

```python
import pyafrobarometer as ab

ds = ab.load(rounds=9)
print(ds)
```

`rounds` accepts a single round number or an iterable of rounds. When it is
omitted, every merged round in the catalog is loaded. The result always has a
`round` column and a `year` column.

Loading more than one round concatenates the frames and merges their metadata.

## Selecting countries

```python
ghana = ab.load(rounds=9, countries="Ghana")
west_africa = ab.load(rounds=9, countries=["Ghana", "Benin", "Togo"])
```

Country matching is case-insensitive and alias-aware. When every requested
country has a country-level file, those files are used; otherwise the merged
file is downloaded and filtered.

Filtering needs a country column. If a local source has none, `load()` raises
`HarmonizationError`; load with `harmonize=True` to add the canonical `country`
column first.

## Selecting variables

```python
# Raw source variables, without harmonization.
raw = ab.load(rounds=9, variables=["Q37A", "Q1"])

# Harmonized families and canonical columns.
clean = ab.load(rounds=9, harmonize=True, variables=["trust_president", "age"])
```

With `harmonize=False`, names are raw source columns. With `harmonize=True`,
names may be question families from [`families()`](../reference/functions.md#families)
or canonical variables such as `country` and `age`.

`strict` controls what happens when a requested name is unavailable:

- `strict=True` (default) raises `HarmonizationError`.
- `strict=False` warns and keeps the columns that do exist. For an unavailable
  family, a column of `pd.NA` is added.

## Language

Merged datasets exist in English (`language="en"`, the default) and sometimes
French (`language="fr"`):

```python
ds_fr = ab.load(rounds=9, language="fr")
```

## Labels and missing codes

```python
ds = ab.load(rounds=9, labels=True, normalize_missing=True)
```

- `labels=True` decodes value labels from the SPSS metadata.
- `normalize_missing=True` replaces declared missing codes with `pd.NA`.

Both are applied when the dataset is built, so `ds.to_pandas()` is already
converted. See [Value labels and missing codes](labels-and-missing.md).

## Local and remote sources

Use `source=` to load a file you already have:

```python
ds = ab.load(source="AB_R9_merged.sav", rounds=9, harmonize=True)
```

`source` accepts a path, a list of paths, or a URL on `www.afrobarometer.org`.
Remote URLs are restricted to that host and HTTPS. `rounds=` is required when
harmonizing a local source, because the crosswalk is round-specific.

If `source` is a list and `rounds` is a list, the entries are paired by position.
A single round applies to every source in the list.

## Working with a Dataset

`Dataset` delegates attribute access to the underlying DataFrame:

```python
ds = ab.load(rounds=9)

print(ds.shape)
print(ds.head())
print(ds["Q37A"].value_counts().head())
print(len(ds))
print(list(ds))          # column names
```

`ds.to_pandas()` returns a copy. Mutating the copy never mutates the dataset:

```python
frame = ds.to_pandas()
frame["new"] = 1
assert "new" not in ds
```

Create a narrower dataset with `subset()`:

```python
small = ds.subset(countries=["Ghana"], columns=["round", "country", "Q37A"])
print(small)
```

`subset()` keeps the variable metadata and provenance and updates the recorded
countries.

## Provenance

Every dataset carries a `Provenance` record:

```python
print(ds.provenance.source_urls)
print(ds.provenance.retrieved_at)
print(ds.rounds, ds.countries)
```

See [`Dataset`](../reference/dataset.md) for the full interface.
