# Cite the data and finish

Afrobarometer data are free to use but remain copyrighted. Every publication
must include the required acknowledgment.

## Build the citation

```python
print(ab.citation(rounds=ROUNDS))
```

The helper fills in the years from the catalog:

```text
Afrobarometer Data, All Countries, Rounds 8, 9, 10, 2022, 2023, 2025, available at http://www.afrobarometer.org.
```

The required acknowledgment is:

> Afrobarometer Data, [Country(ies)], [Round(s)], [Year(s)], available at
> http://www.afrobarometer.org.

## Record provenance

The panel keeps the source URLs and retrieval time:

```python
print(panel.provenance.source_urls)
print(panel.provenance.retrieved_at)
print(panel.provenance.rounds, panel.provenance.years)
```

Save this alongside your results when you need a reproducible record.

## Data policy

- Data and codebooks are stored only in the local cache reported by
  `ab.cache_dir()`.
- No Afrobarometer microdata or codebooks are committed to this repository.
- Downloads use HTTPS from `www.afrobarometer.org` only.
- Follow Afrobarometer's [access policy](https://www.afrobarometer.org/data/).

## The complete script

Your `trust_trend.py` now discovers the data, loads a round, cleans it, builds a
panel, writes `trust_trend.csv`, and prints a citation. Run it from top to
bottom:

```bash
python trust_trend.py
```

## Next

[Next steps](next.md).
