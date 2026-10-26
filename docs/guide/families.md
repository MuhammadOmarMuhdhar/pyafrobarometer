# Question families

Question families give comparable survey items a stable name across rounds.

```python
import pyafrobarometer as ab

families = ab.families()
print(families[["family", "description", "rounds"]])
```

## Columns

| Column | Meaning |
| --- | --- |
| `family` | Harmonized column name you can request |
| `description` | Human-readable description |
| `rounds` | Sorted list of rounds where the family is available |
| `variables` | Mapping of round number to source variable |

```python
trust = families[families["family"] == "trust_president"].iloc[0]
print(trust["rounds"])
print(trust["variables"])
```

## Sparse availability

Families are sparse by design:

- `social_media_news` is available from Round 6.
- `trust_army` is missing in Round 4.
- `bribe_police` starts in Round 6.
- Round 1 institutional-trust items are recoded from a 1–4 scale to 0–3.

Always check `rounds` before requesting a family for a specific round.

## Finding a family

```python
families[families["family"].str.contains("trust")]
families[families["description"].str.contains("democracy", case=False)]
```

For free-text search over variables, families, and labels, use
[`search_variables()`](../reference/functions.md#search_variables).

## Source variables

The `variables` mapping tells you which raw column backs the family in each
round. For `trust_president`:

| Round | Source |
| --- | --- |
| 1 | `trspre` (recoded) |
| 2 | `Q43A` |
| 3 | `Q55A` |
| 4 | `Q49A` |
| 5 | `Q59A` |
| 6 | `Q52A` |
| 7 | `Q43A` |
| 8 | `Q41A` |
| 9 | `Q37A` |
| 10 | `Q37A` |

This is why hard-coding a source variable is fragile.

## Adding families to a load

```python
ds = ab.load(rounds=9, harmonize=True, variables=["trust_president"])
```

See [Question-family harmonization](family-harmonization.md) for strict mode and
recoding behavior.

## See also

- [Question-family harmonization](family-harmonization.md)
- [Variable search](search.md)
- [`families()`](../reference/functions.md#families)
- [Tutorial: discover the data](../tutorial/discover.md)
