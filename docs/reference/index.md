# API reference

The public API is re-exported from the top-level `pyafrobarometer` package:

```python
import pyafrobarometer as ab

print(ab.__version__)
```

## Public names

| Name | Kind | Summary |
| --- | --- | --- |
| [`rounds()`](functions.md#rounds) | function | List merged rounds from the catalog |
| [`countries()`](functions.md#countries) | function | List country names |
| [`questions()`](functions.md#questions) | function | Describe every reviewed question concept |
| [`question()`](functions.md#question) | function | Show one concept's per-round details |
| [`families()`](functions.md#families) | function | Deprecated legacy 32-name view |
| [`load()`](functions.md#load) | function | Load one or more rounds into a `Dataset` |
| [`panel()`](functions.md#panel) | function | Build a multi-round dataset for selected variables |
| [`search_variables()`](functions.md#search_variables) | function | Search the shipped metadata index |
| [`codebook()`](functions.md#codebook) | function | Download a codebook, optionally extract text |
| [`citation()`](functions.md#citation) | function | Build the required acknowledgment |
| [`cache_dir()`](functions.md#cache_dir) | function | Return the cache directory |
| [`clear_cache()`](functions.md#clear_cache) | function | Remove cached files |
| [`Dataset`](dataset.md#dataset) | class | DataFrame wrapper with metadata and provenance |
| [`Provenance`](dataset.md#provenance) | dataclass | Source URLs, retrieval time, rounds, countries |
| [`AfrobarometerError`](errors.md#afrobarometererror) | exception | Base class for all package errors |
| [`CatalogError`](errors.md#catalogerror) | exception | Catalog fetch or parse failure |
| [`DownloadError`](errors.md#downloaderror) | exception | Download or validation failure |
| [`CacheError`](errors.md#cacheerror) | exception | Cache read, write, or lock failure |
| [`NotFoundError`](errors.md#notfounderror) | exception | Requested item is unavailable |
| [`HarmonizationError`](errors.md#harmonizationerror) | exception | Crosswalk or variable mapping failure |
| [`CodebookError`](errors.md#codebookerror) | exception | Codebook download or extraction failure |

## Package version

`pyafrobarometer.__version__` is the installed version string, for example
`"0.1.2"`.

## See also

- [Functions](functions.md)
- [`Dataset` and `Provenance`](dataset.md)
- [Errors](errors.md)
