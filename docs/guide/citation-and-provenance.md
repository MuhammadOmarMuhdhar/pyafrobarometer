# Citation and provenance

Afrobarometer data are free to use but remain copyrighted. Cite them in
publications and keep a record of what you loaded.

## Citation helper

```python
import pyafrobarometer as ab

print(ab.citation(rounds=[8, 9, 10], countries=["Ghana", "Kenya"]))
```

A loaded dataset can cite itself:

```python
ds = ab.load(rounds=9)
print(ds.citation())
```

The helper fills in years from the catalog when they are known. If the catalog
cannot be read, it still returns a citation without years.

## Required acknowledgment

> Afrobarometer Data, [Country(ies)], [Round(s)], [Year(s)], available at
> http://www.afrobarometer.org.

Include this in publications that use the data.

## Provenance

Every `Dataset` carries a `Provenance` record:

```python
print(ds.provenance.source_urls)
print(ds.provenance.retrieved_at)
print(ds.provenance.rounds)
print(ds.provenance.countries)
print(ds.provenance.language)
print(ds.provenance.years)
print(ds.provenance.codebook_url)
```

| Field | Meaning |
| --- | --- |
| `source_urls` | Data URLs or local paths used |
| `retrieved_at` | ISO 8601 UTC timestamp |
| `rounds` | Rounds in the dataset |
| `countries` | Countries found in the data |
| `language` | Dataset language |
| `years` | Survey years known from the catalog |
| `codebook_url` | Codebook URL, when known |
| `codebook_path` | Local codebook path, when known |

Save provenance alongside exported results for reproducibility.

## See also

- [Data policy](data-policy.md)
- [`citation()`](../reference/functions.md#citation)
- [`Dataset.citation()`](../reference/dataset.md#citation)
- [`Provenance`](../reference/dataset.md#provenance)
- [Tutorial: cite the data](../tutorial/cite.md)
