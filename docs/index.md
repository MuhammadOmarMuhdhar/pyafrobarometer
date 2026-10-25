# pyafrobarometer

Programmatic access to [Afrobarometer](https://www.afrobarometer.org/) survey data
in Python: discover what exists, download it into a local cache, load it with
metadata intact, and harmonize comparable variables across rounds and countries.

!!! warning "Unofficial package"

    This package is not affiliated with or endorsed by Afrobarometer.
    Afrobarometer data are free to use under their
    [access policy](https://www.afrobarometer.org/data/), but remain
    copyrighted. This package does not redistribute microdata or codebooks; it
    downloads them to a user-local cache. Please cite Afrobarometer in
    publications.

## Install

```bash
pip install pyafrobarometer
```

Requires Python 3.10 or newer. See [Installation](getting-started/installation.md)
for optional extras.

## Quick example

```python
import pyafrobarometer as ab

# Load Round 9 with canonical columns and harmonized question families.
ds = ab.load(rounds=9, harmonize=True)
print(ds.to_pandas()[["country", "age", "trust_president"]].head())

# A two-round trend takes three lines.
panel = ab.panel(rounds=[8, 9], variables=["trust_president"])
trend = panel.to_pandas(normalize_missing=True)
print(trend.groupby("round")["trust_president"].mean())
```

## What it does

- **Discover.** `ab.rounds()`, `ab.countries()`, and `ab.families()` report what
  is available without downloading a dataset.
- **Download and cache.** Data and codebooks are fetched from
  `www.afrobarometer.org` into a local cache and reused across runs.
- **Load with metadata.** `Dataset` keeps SPSS metadata, value labels, missing
  codes, and provenance alongside the data.
- **Harmonize.** A curated crosswalk maps canonical variables and comparable
  question families across rounds 1–10, never guessing an unverified mapping.
- **Search.** `ab.search_variables()` searches the shipped metadata index for
  merged rounds 1–10 without touching the network.

## Where to go next

- [Installation](getting-started/installation.md)
- [Quickstart](getting-started/quickstart.md)
- [Discovery](guides/discovery.md)
- [Loading data](guides/loading.md)
- [Harmonization](guides/harmonization.md)
- [API reference](reference/index.md)
