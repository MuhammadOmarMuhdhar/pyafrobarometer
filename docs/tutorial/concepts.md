# Afrobarometer concepts

Before writing code, it helps to know what is inside an Afrobarometer dataset.
This page is a short orientation. The [Guide's concepts chapter](../guide/concepts.md)
goes deeper.

## Rounds

Afrobarometer runs repeated surveys called **rounds**. Each round covers a set
of countries and is released as one merged file plus individual country files.
Variable names change between rounds: trust in the president is `trspre` in
Round 1, `Q43A` in Round 2, and `Q37A` in Rounds 9 and 10.

Rounds are numbered 1–10 in this package's catalog.

## Respondents and rows

Each row is one interviewed respondent. Columns are survey variables. A merged
file stacks all countries in a round, so the same column names appear for every
country.

## Merged and country-level files

- **Merged** — one file for all countries in a round. `load(rounds=...)` uses
  this by default.
- **Country** — one file per country and round. Passing `countries=` makes the
  package prefer country files when they exist.

CSV-only country pages are not supported; SAV, zipped SAV, and DTA are.

## Variables, labels, and codes

A **variable** is a column such as `Q37A`. It has a label describing the
question, and often **value labels** that map numeric codes to text:

| Code | Label |
| --- | --- |
| 0 | Not at all |
| 1 | Just a little |
| 2 | Somewhat |
| 3 | A lot |
| 9 | Don't know |

By default, the package keeps the raw numeric codes. `labels=True` decodes them;
`normalize_missing=True` replaces missing codes such as `9` with `pd.NA`.

## Missing codes

Survey files declare missing values in different ways: a range, explicit
user-missing values, or conventional codes such as `8`, `9`, `97`, `98`, `99`,
and `-1`. If you do not normalize them, a "don't know" code can be mistaken for a
high trust score.

## Weights

Survey weights correct for sampling differences so results represent the
population. The package exposes a canonical `weight` column, preferring
`withinwt_hh` when present. Weighted means are usually more appropriate than
unweighted means for cross-country comparisons.

## Question families

Because variable names change across rounds, the package defines **question
families** with stable names such as `trust_president`. A family maps each round
to its source variable and any recoding needed. Families are sparse: a family may
exist in Rounds 2–10 but not Round 1.

`families()` reports availability and source variables. Passing
`harmonize=True` with `variables=["trust_president"]` adds the harmonized column.

## Canonical variables

Canonical variables are stable columns for common respondent attributes:
`country`, `respondent_id`, `weight`, `region`, `urban_rural`, `age`, `gender`,
`education`, and `interview_date`. They are added when you pass
`harmonize=True`.

## Codebooks

A **codebook** documents every variable, its question text, and its value labels
for a round. Use `codebook()` to download one when you need the authoritative
definition.

## Citation

Afrobarometer data are free to use but remain copyrighted. Publications must
include the required acknowledgment. `citation()` builds it for you.

## Next

Now that you know the vocabulary, [discover the data](discover.md).
