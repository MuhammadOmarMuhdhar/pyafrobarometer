# Tutorial

This tutorial walks you through a complete analysis with pyafrobarometer. You
will build a small script that measures trust in the president across Rounds 8,
9, and 10, then writes a country-by-round trend to CSV.

It is the shortest path from zero to a working analysis. For a complete tour of
every feature, use the [Guide](../guide/index.md).

## What you will build

```text
round,country,mean_trust,respondents
8,Benin,1.42,1200
8,Ghana,1.87,1200
...
10,Kenya,1.31,1600
```

- `round` — Afrobarometer round
- `country` — country name
- `mean_trust` — weighted mean of `trust_president` on the 0–3 scale
- `respondents` — number of non-missing respondents contributing to the mean

## What you will learn

- What Afrobarometer rounds, countries, variables, and question families are.
- How to discover available data without downloading it.
- How to load a round with metadata intact.
- How to decode labels, normalize missing codes, and apply weights.
- How to harmonize comparable variables across rounds.
- How to build a multi-round panel and export it.
- How to cite Afrobarometer correctly.

## Assumptions

- You have Python 3.10 or newer.
- You are comfortable with basic Python and pandas.
- You have a network connection for the first download. Later runs use the
  local cache.

## Install

```bash
pip install pyafrobarometer
```

Optional extras are not needed for this tutorial. See
[Installation](../guide/index.md#installation) for the search and codebook
extras.

## Create the script

Create a file named `trust_trend.py` in an empty directory:

```python
import pyafrobarometer as ab

print(ab.__version__)
```

Run it:

```bash
python trust_trend.py
```

You should see the installed version. Nothing is downloaded yet.

## How the chapters work

Each chapter adds a section to `trust_trend.py`. You can run the script after
every chapter to see the intermediate result. The final script is the complete
analysis.

If you get stuck, the [Guide](../guide/index.md) explains each feature in depth,
and the [API reference](../reference/index.md) lists exact signatures.

## Next

Start with [Afrobarometer concepts](concepts.md).
