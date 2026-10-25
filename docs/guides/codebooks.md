# Codebooks

Codebooks are downloaded on demand and cached alongside the data.

```python
import pyafrobarometer as ab

path = ab.codebook(round=10)
print(path)
```

[`codebook()`](../reference/functions.md#codebook) prefers the merged English
codebook for the round. Pass `country=` to request a country-specific codebook:

```python
path = ab.codebook(round=9, country="Ghana")
```

## Text extraction

```python
text_path = ab.codebook(round=10, extract_text=True)
print(text_path.read_text()[:500])
```

With `extract_text=True`, the PDF text is written to a `.txt` file next to the
cached PDF and the path to that text file is returned. Text extraction requires
the `[codebook]` extra:

```bash
pip install "pyafrobarometer[codebook]"
```

Without `pypdf`, the call raises `CodebookError` with an install hint.

## From a loaded dataset

A `Dataset` carries the codebook URL from the catalog:

```python
ds = ab.load(rounds=10)
path = ds.codebook()
print(path)
```

If the dataset has no codebook URL, `Dataset.codebook()` raises `CodebookError`.

## Errors

| Situation | Error |
| --- | --- |
| No codebook exists for the round or country | `NotFoundError` |
| No PDF link can be found on the resource page | `CodebookError` |
| Download fails or returns a non-PDF response | `CodebookError` |
| `extract_text=True` without `pypdf` | `CodebookError` |

## Data policy

Codebooks are stored only in the local cache. The package does not commit or
redistribute PDFs. See
[Citation and data policy](citation-and-data-policy.md).

## See also

- [`codebook()`](../reference/functions.md#codebook)
- [`Dataset.codebook()`](../reference/dataset.md#codebook)
- [Caching and offline use](caching-and-offline.md)
