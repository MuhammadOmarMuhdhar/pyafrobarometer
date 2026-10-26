# Variable search

[`search_variables()`](../reference/functions.md#search_variables) searches the
shipped metadata index for variable names, labels, and question families.

```python
import pyafrobarometer as ab

matches = ab.search_variables("trust president", rounds=[8, 9, 10], limit=10)
print(matches[["name", "label", "round", "family", "score"]])
```

Search never downloads a dataset. It reads `metadata_index.json`, which ships
with the package for merged rounds 1–10 and is refreshed by the weekly catalog
job.

## Result columns

| Column | Meaning |
| --- | --- |
| `name` | Source variable name |
| `label` | Variable label |
| `round` | Round where the variable appears |
| `kind` | Entry kind recorded in the index |
| `family` | Harmonized family, when the variable belongs to one |
| `source_var` | Source variable for the family |
| `score` | Match score; `100` for a substring match |

Results are sorted by score and then by round, highest first.

## Fuzzy and substring matching

With `rapidfuzz` installed (the `[search]` extra), matching uses fuzzy scoring
and keeps scores of 60 or higher. Without it, matching falls back to
case-insensitive substring matching.

```python
ab.search_variables("trust pres")                  # fuzzy when available
ab.search_variables("trust president", fuzzy=False)  # substring
```

## Filtering and limits

```python
ab.search_variables("corruption", rounds=9, limit=25)
ab.search_variables("internet", rounds=[5, 6, 7, 8, 9, 10])
```

`limit` caps the number of rows. A non-positive limit returns an empty DataFrame
with the result columns.

## From search to load

Use the result to choose a family or source variable:

```python
match = ab.search_variables("trust president", rounds=9, limit=1).iloc[0]
print(match["family"], match["name"])

ds = ab.load(rounds=9, harmonize=True, variables=[match["family"]])
```

## See also

- [Question families](families.md)
- [Selecting variables](selecting-variables.md)
- [`search_variables()`](../reference/functions.md#search_variables)
- [Installation](index.md#installation)
