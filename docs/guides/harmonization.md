# Harmonization

Afrobarometer variable names change between rounds. Harmonization adds stable
column names so the same analysis works across rounds.

```python
ds = ab.load(rounds=9, harmonize=True)
print(ds.to_pandas()[["country", "age", "gender", "trust_president"]].head())
```

Two things happen when `harmonize=True`:

1. **Canonical variables** are added from a curated per-round crosswalk.
2. **Question families** are added for the requested families, or for every
   family available in the round when no `variables=` are given.

Mappings come from `canonical.yaml` and `questions.yaml` inside the package.
A mapping that cannot be verified is omitted with a warning; it is never guessed.

## Canonical variables

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

The source column differs by round. For example, `age` comes from `age` in Round
1, `Q80` in Round 2, and `Q1` in later rounds. For `weight`, the package prefers
`withinwt_hh` when that column is present.

If a round has no verified source for a canonical variable, the column is left
out and a `UserWarning` names the variable and the missing source.

## Question families

Question families group comparable survey items across rounds. Inspect them with
[`families()`](../reference/functions.md#families):

```python
print(ab.families()[["family", "description", "rounds"]])
```

Examples include `trust_president`, `trust_parliament`, `trust_police`,
`support_democracy`, `satisfaction_democracy`, `corruption_president`,
`econ_country_present`, and `social_media_news`.

Request specific families:

```python
ds = ab.load(
    rounds=9,
    harmonize=True,
    variables=["trust_president", "trust_police", "support_democracy"],
)
```

Or request every family available in the round by omitting `variables=`:

```python
ds = ab.load(rounds=9, harmonize=True)
```

### Sparse availability

Families are sparse by design. `families()` reports the rounds where each family
exists. For example:

- `social_media_news` is available from Round 6.
- `trust_army` is missing in Round 4.
- Round 1 institutional-trust items are recoded from the 1–4 scale to 0–3.
- `bribe_police` starts in Round 6.

### Strict mode

`strict` controls unavailable families:

```python
# Raise if trust_army is requested for Round 4.
ab.load(rounds=4, harmonize=True, variables=["trust_army"])

# Warn and add a pd.NA column instead.
ds = ab.load(rounds=4, harmonize=True, variables=["trust_army"], strict=False)
```

With `strict=False`, a family that exists in the crosswalk but not in the
requested round produces a warning and a column filled with `pd.NA`. A family
that does not exist at all is also warned about and is not added.

## Combined with labels and missing codes

Harmonization runs before conversion, so labels and missing-code normalization
apply to the harmonized columns too:

```python
ds = ab.load(rounds=9, harmonize=True, labels=True, normalize_missing=True)
frame = ds.to_pandas()
print(frame["trust_president"].value_counts(dropna=False))
```

The `Dataset` tracks which source variable produced each harmonized column:

```python
print(ds.variables()[["name", "source_var"]])
```

## See also

- [Panels](panels.md) — harmonization across multiple rounds
- [`families()`](../reference/functions.md#families)
- [`load()`](../reference/functions.md#load)
