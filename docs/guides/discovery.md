# Discovery

Use these functions to inspect what is available before downloading anything.
`rounds()` and `families()` are cheap: they use the cached catalog or the baked
manifest, not the survey files.

## Rounds

[`rounds()`](../reference/functions.md#rounds) returns one row per merged round
and language:

```python
import pyafrobarometer as ab

print(ab.rounds()[["round", "year", "countries", "language", "data_url"]])
```

The columns are:

| Column | Meaning |
| --- | --- |
| `round` | Afrobarometer round number |
| `year` | Survey year recorded in the catalog |
| `countries` | Number of countries in the merged file, when known |
| `data_url` | Direct URL of the merged data file |
| `codebook_url` | Direct URL of the merged codebook, when known |
| `language` | `en` or `fr` |

Rows are sorted by round and language. Pass `refresh=True` to ignore the cached
catalog index and fetch a fresh one.

## Countries

[`countries()`](../reference/functions.md#countries) returns country names:

```python
print(ab.countries()[:10])       # all rounds
print(ab.countries(round=9))     # one round
```

Names come from the value labels in the shipped metadata index. If the index
cannot provide them, the catalog's country entries are used instead. If neither
source yields a name, the function raises `NotFoundError`.

Country names are matched case-insensitively and normalized, so aliases such as
"Ivory Coast", "Côte d'Ivoire", and "Cote d Ivoire" resolve to the same
country when you filter with `countries=`.

## Question families

[`families()`](../reference/functions.md#families) describes the harmonized
question families:

```python
families = ab.families()
print(families[["family", "description", "rounds"]])
print(families.loc[families["family"] == "trust_president", "variables"].iloc[0])
```

The columns are:

| Column | Meaning |
| --- | --- |
| `family` | Harmonized column name you can request from `load()` or `panel()` |
| `description` | Human-readable description from the crosswalk |
| `rounds` | Sorted list of rounds where the family is available |
| `variables` | Mapping of round number to the source variable in that round |

Families are sparse by design. For example, `social_media_news` starts in Round
6, `trust_army` is missing in Round 4, and Round 1 institutional-trust items are
recoded from a 1–4 scale to 0–3.

## Merged and country-level data

The catalog contains two kinds of entries:

- **Merged** — one file covering all countries in a round. This is what
  `load(rounds=...)` uses by default.
- **Country** — one file per country and round, discovered from every
  data-sets listing page.

When you pass `countries=` to `load()`, the package prefers country-level files
when every requested country has one. Otherwise it falls back to the merged
file and filters it. Country pages that only offer CSV raise `NotFoundError`
because CSV is not supported; SAV, zipped SAV, and DTA are supported.

## Catalog sources

[`rounds()`](../reference/functions.md#rounds),
[`countries()`](../reference/functions.md#countries), and the download path use
the catalog in this order:

1. A cached live index, if it is younger than the TTL (seven days by default).
2. A freshly fetched live index, unless offline.
3. The baked `manifest.json` shipped with the package.

A failed refresh warns and falls back to the cached index or baked manifest; it
never blocks a load. See
[Caching and offline use](caching-and-offline.md) for the TTL, cache location,
and offline switch.
