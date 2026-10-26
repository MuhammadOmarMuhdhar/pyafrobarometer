# Discover the data

Update `trust_trend.py` to the following. This answers three questions: which
rounds exist, which countries are covered, and whether the variable you want is
available.

```python
import pyafrobarometer as ab

ROUNDS = [8, 9, 10]

rounds = ab.rounds()
print(rounds[["round", "year", "countries", "language"]])

print(ab.countries(round=9)[:10])

families = ab.families()
trust = families[families["family"] == "trust_president"].iloc[0]
print(trust[["family", "description", "rounds"]])
print(trust["variables"])
```

## What you should see

`ab.rounds()` prints one row per merged round and language. The columns include
the round number, survey year, country count, and data URL.

`ab.countries(round=9)` prints country names such as `Benin`, `Botswana`, and
`Burkina Faso`. Names come from the shipped metadata index, so this is fast and
does not download data.

The `trust_president` row shows:

- `description` — "Trust in the President".
- `rounds` — the rounds where the family is available.
- `variables` — a mapping from round number to the source variable. For Rounds
  9 and 10 it is `Q37A`; Round 8 uses `Q41A`.

## Why this matters

Afrobarometer variables are not stable across rounds. If you hard-code `Q37A`
you will get the wrong column in older rounds. The family crosswalk handles that
mapping for you.

The family is sparse by design. Checking `rounds` before requesting it avoids a
`HarmonizationError` later.

!!! note "No data yet"

    Nothing in this chapter downloads a survey file. Discovery reads the cached
    catalog and the shipped metadata index.

## Next

[Load and inspect a round](load.md).
