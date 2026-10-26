# Dataset and Provenance

## Dataset

`Dataset` wraps a pandas DataFrame together with variable metadata and
provenance. [`load()`](functions.md#load) and [`panel()`](functions.md#panel)
return `Dataset` instances; you do not normally construct one directly.

```python
import pyafrobarometer as ab

ds = ab.load(rounds=9)
print(ds)
```

```
<Dataset rounds=[9] countries=[...] rows=... columns=... harmonized=False>
```

### Attribute delegation

Attribute access is delegated to the underlying DataFrame:

```python
ds.head()
ds.shape
ds["Q37A"]
ds.groupby("country")["Q37A"].mean()
len(ds)
list(ds)      # column names
```

Accessing a missing attribute raises `AttributeError`.

### Properties

| Property | Type | Meaning |
| --- | --- | --- |
| `rounds` | `list[int]` | Rounds in the dataset |
| `countries` | `list[str]` | Countries recorded in provenance |
| `round_meta` | `dict[int, dict]` | Per-round SPSS metadata |
| `round_source_map` | `dict[int, dict[str, str]]` | Per-round harmonized-to-source mapping |
| `harmonized` | `bool` | Whether harmonization was requested |
| `provenance` | `Provenance` | Source and retrieval details |

### variables

```python
ds.variables() -> pandas.DataFrame
```

Return a copy of the variable metadata with the columns `name`, `label`,
`value_labels`, `missing_codes`, and `source_var`. Harmonized columns appear with
the source variable they came from.

```python
print(ds.variables().head())
```

### to_pandas

```python
ds.to_pandas(labels: bool = False, normalize_missing: bool = False) -> pandas.DataFrame
```

Return a copy of the frame, optionally decoding value labels and normalizing
missing codes.

- `labels=True` replaces numeric codes with label text.
- `normalize_missing=True` replaces declared missing codes with `pd.NA`.

When the dataset spans multiple rounds, metadata is applied per round.

```python
frame = ds.to_pandas(labels=True, normalize_missing=True)
```

### subset

```python
ds.subset(
    countries=None,
    columns=None,
) -> Dataset
```

Return a new `Dataset` filtered by country and/or columns. Country matching is
case-insensitive and alias-aware. The variable metadata and provenance are
preserved, and the recorded countries are updated.

```python
small = ds.subset(countries=["Ghana"], columns=["round", "country", "Q37A"])
```

**Raises** `HarmonizationError` if country filtering is requested and no country
column is available.

### citation

```python
ds.citation() -> str
```

Return the required acknowledgment for the dataset's rounds and countries.

```python
print(ds.citation())
```

### codebook

```python
ds.codebook() -> pathlib.Path
```

Download and return the codebook associated with the dataset.

**Raises** `CodebookError` if the dataset has no codebook URL or the download
fails.

```python
path = ds.codebook()
```

## Provenance

`Provenance` is a frozen dataclass describing where a dataset came from.

```python
@dataclass(frozen=True)
class Provenance:
    source_urls: tuple[str, ...]
    retrieved_at: str
    rounds: tuple[int, ...]
    countries: tuple[str, ...]
    language: str
    years: tuple[int, ...] = ()
    codebook_url: str | None = None
    codebook_path: pathlib.Path | None = None
```

| Field | Meaning |
| --- | --- |
| `source_urls` | Data URLs or local paths used |
| `retrieved_at` | ISO 8601 UTC timestamp of the load |
| `rounds` | Rounds in the dataset |
| `countries` | Countries found in the data |
| `language` | Dataset language |
| `years` | Survey years known from the catalog |
| `codebook_url` | Codebook URL, when known |
| `codebook_path` | Local codebook path, when known |

```python
print(ds.provenance.source_urls)
print(ds.provenance.retrieved_at)
print(ds.provenance.rounds, ds.provenance.years)
```

## See also

- [Functions](functions.md)
- [Errors](errors.md)
- [Loading data](../guide/loading.md)
