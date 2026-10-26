# Codebooks

Codebooks document every variable, question wording, and value label for a
round. They are downloaded on demand and cached alongside the data.

```python
import pyafrobarometer as ab

path = ab.codebook(round=10)
print(path)
```

## Country-specific codebooks

```python
path = ab.codebook(round=9, country="Ghana")
```

The merged English codebook is preferred when `country` is omitted.

## Text extraction

```python
text_path = ab.codebook(round=10, extract_text=True)
print(text_path.read_text()[:500])
```

With `extract_text=True`, the PDF text is written to a `.txt` file next to the
cached PDF, and the path to that text file is returned. Text extraction requires
the `[codebook]` extra:

```bash
pip install "pyafrobarometer[codebook]"
```

Without `pypdf`, the call raises `CodebookError` with an install hint.

## From a dataset

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
| No PDF link can be found | `CodebookError` |
| Download fails or returns a non-PDF response | `CodebookError` |
| `extract_text=True` without `pypdf` | `CodebookError` |

## See also

- [`codebook()`](../reference/functions.md#codebook)
- [`Dataset.codebook()`](../reference/dataset.md#codebook)
- [Data policy](data-policy.md)
- [Caching, TTL, and offline mode](caching-and-offline.md)
