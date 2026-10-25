# Installation

## Requirements

- Python 3.10 or newer
- A platform supported by `pandas` and `pyreadstat` (Linux, macOS, or Windows)

## Install from PyPI

```bash
pip install pyafrobarometer
```

The base install includes the catalog, cache, I/O, harmonization, and panel
features. It does not include fuzzy search or PDF text extraction.

## Optional extras

### Fuzzy variable search

```bash
pip install "pyafrobarometer[search]"
```

Adds [`rapidfuzz`](https://github.com/rapidfuzz/RapidFuzz) for fuzzy matching in
[`search_variables()`](../reference/functions.md#search_variables). Without it,
search falls back to case-insensitive substring matching.

### Codebook text extraction

```bash
pip install "pyafrobarometer[codebook]"
```

Adds [`pypdf`](https://github.com/py-pdf/pypdf) so
[`codebook(..., extract_text=True)`](../reference/functions.md#codebook) can turn
a downloaded PDF into text.

### Both extras

```bash
pip install "pyafrobarometer[search,codebook]"
```

## Development install

To work on the package itself:

```bash
git clone https://github.com/MuhammadOmarMuhdhar/pyafrobarometer.git
cd pyafrobarometer
pip install -e ".[dev]"
```

The `dev` extra adds the test, lint, and type-checking tools. To build this
documentation site locally, also install the `docs` extra:

```bash
pip install -e ".[docs]"
```

## Verify the install

```bash
python -c "import pyafrobarometer as ab; print(ab.__version__)"
```

Nothing is downloaded at import time. Data is fetched only when you call a
function that needs it, such as [`load()`](../reference/functions.md#load) or
[`rounds(refresh=True)`](../reference/functions.md#rounds). See
[Caching and offline use](../guides/caching-and-offline.md) for where files are
stored.
