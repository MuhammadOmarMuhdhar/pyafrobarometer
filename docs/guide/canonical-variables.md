# Canonical variables

Canonical variables give stable names to common respondent attributes.
`harmonize=True` adds them from a curated per-round crosswalk.

```python
import pyafrobarometer as ab

ds = ab.load(rounds=9, harmonize=True)
print(ds.to_pandas()[["country", "age", "gender", "weight"]].head())
```

## The canonical set

| Column | Meaning |
| --- | --- |
| `country` | Country name, decoded from labels when needed |
| `respondent_id` | Respondent identifier |
| `weight` | Survey weight |
| `region` | Region |
| `urban_rural` | Urban/rural classification |
| `age` | Respondent age |
| `gender` | Respondent gender |
| `education` | Education level |
| `interview_date` | Interview date |

## Per-round mapping

Source columns differ by round. Examples:

| Canonical | Round 1 | Round 2 | Round 9 |
| --- | --- | --- | --- |
| `age` | `age` | `Q80` | `Q1` |
| `gender` | `gender` | `Q96` | `Q100` |
| `education` | `educ` | `Q84` | `Q94` |
| `weight` | `withinwt` | `withinwt` | `withinwt_ea` |

For `weight`, the package prefers `withinwt_hh` when the file contains it. See
[Weights](weights.md).

## Omitted mappings

If a round has no verified source for a canonical variable, the column is left
out and a `UserWarning` names the variable and the missing source. The package
never guesses a mapping.

## Country decoding

The `country` column is decoded from value labels when the source is numeric. If
the file already has a string country column, it is used directly.

## Selecting canonical columns

```python
ds = ab.load(
    rounds=9,
    harmonize=True,
    variables=["age", "gender", "education"],
)
```

Canonical names and question concepts can be mixed in `variables=`. See
[Selecting variables](selecting-variables.md).

## Inspecting the source mapping

```python
print(ds.variables()[["name", "source_var"]])
print(ds.round_source_map)
```

## See also

- [Weights](weights.md)
- [Question harmonization](family-harmonization.md)
- [Master codebook](master-codebook.md)
- [`load()`](../reference/functions.md#load)
- [Tutorial: load and inspect](../tutorial/load.md)
