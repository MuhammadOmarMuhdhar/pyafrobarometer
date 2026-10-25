# Variable search

[`search_variables()`](../reference/functions.md#search_variables) searches the
shipped metadata index for variable names, labels, and question families.

```python
import pyafrobarometer as ab

matches = ab.search_variables("trust president", rounds=[8, 9], limit=10)
print(matches[["name", "label", "round", "family", "score"]])
```

Search never downloads a dataset. It reads `metadata_index.json`, which ships
with the package for merged rounds 1–10 and is refreshed by the weekly catalog
job.

## Results

The returned DataFrame has these columns:

| Column | Meaning |
| --- | --- |
| `name` | Source variable name |
| `label` | Variable label |
| `round` | Round where the variable appears |
| `kind` | Entry kind recorded in the index |
| `family` | Harmonized family, when the variable belongs to one |
| `source_var` | Source variable for the family |
| `score` | Match score; `100` for an exact substring match |

Results are sorted by score and then by round, highest first.

## Fuzzy and substring matching

With `rapidfuzz` installed (the `[search]` extra), matching uses fuzzy scoring
and keeps scores of 60 or higher. Without it, matching falls back to
case-insensitive substring matching:

```python
# Fuzzy by default when rapidfuzz is installed.
ab.search_variables("trust pres")

# Force substring matching.
ab.search_variables("trust president", fuzzy=False)
```

## Filtering and limits

```python
ab.search_variables("corruption", rounds=9, limit=25)
ab.search_variables("internet", rounds=[5, 6, 7, 8, 9, 10])
```

`limit` caps the number of rows. A non-positive limit returns an empty DataFrame
with the result columns.

## See also

- [Discovery](discovery.md)
- [`families()`](../reference/functions.md#families)
- [`search_variables()`](../reference/functions.md#search_variables)
