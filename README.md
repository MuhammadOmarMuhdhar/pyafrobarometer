# pyafrobarometer

Programmatic access to [Afrobarometer](https://www.afrobarometer.org/) survey data
in Python: discover what exists, download it into a local cache, load it with
metadata intact, and harmonize comparable variables across rounds and countries.

> **Unofficial.** This package is not affiliated with or endorsed by
> Afrobarometer. Afrobarometer data are free to use under their
> [access policy](https://www.afrobarometer.org/data/), but remain copyrighted.
> This package does not redistribute microdata or codebooks; it downloads them
> to a user-local cache. Please cite Afrobarometer in publications.

## Installation

```bash
pip install pyafrobarometer
```

Optional extras:

```bash
pip install "pyafrobarometer[search]"    # fuzzy variable search
pip install "pyafrobarometer[codebook]"  # PDF codebook text extraction
```

Requires Python 3.10 or newer.

## Usage

```python
import pyafrobarometer as ab

# What rounds are available?
print(ab.rounds())

# Load Round 9 with value labels and canonical columns.
ds = ab.load(rounds=9, labels=True, harmonize=True)

# A two-round trend for one harmonized variable.
panel = ab.panel(rounds=[8, 9], variables=["trust_president"])

# Discover variables without downloading a dataset.
ab.search_variables("democracy")
```

Run `pytest` for the offline test suite. Network tests are marked `network` and
are excluded by default; run them with `pytest -m network`.

## Data policy

- Data and codebooks are stored only in the local cache reported by
  `ab.cache_dir()`.
- No Afrobarometer microdata, codebooks, or archives are committed to this
  repository.
- Downloads use HTTPS from `www.afrobarometer.org`.

## License

Code is released under the MIT License. See [LICENSE](LICENSE).
