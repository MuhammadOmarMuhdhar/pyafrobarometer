# pyafrobarometer

pyafrobarometer enables intuitive, programmatic access to
[Afrobarometer](https://www.afrobarometer.org/) survey data in Python. Explore
codebooks, browse available datasets, inspect the reviewed question codebook, and
load data for analysis in one workflow.

!!! warning "Unofficial package"

    This package is not affiliated with or endorsed by Afrobarometer.
    Afrobarometer data are free to use under their
    [access policy](https://www.afrobarometer.org/data/), but remain
    copyrighted. Please cite Afrobarometer in publications.

## Install

```bash
pip install pyafrobarometer
```

Requires Python 3.10 or newer. See
[Installation](guide/index.md#installation) for optional extras.

## Quick example

```python
import pyafrobarometer as ab

# Every reviewed cross-round concept.
print(ab.questions()[["name", "rounds"]].head())

# Per-round source variables and recodes for one concept.
print(ab.question("trust_president"))

# Load Round 9 with canonical columns and harmonized question concepts.
ds = ab.load(rounds=9, harmonize=True)
print(ds.to_pandas()[["country", "age", "trust_president"]].head())

# A two-round trend takes three lines.
panel = ab.panel(rounds=[8, 9], variables=["trust_president"])
trend = panel.to_pandas(normalize_missing=True)
print(trend.groupby("round")["trust_president"].mean())
```
