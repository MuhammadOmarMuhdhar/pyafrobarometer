# Afrobarometer concepts

If you're unfamiliar with how Afrobarometer works, this page explains the data
model behind pyafrobarometer. Understanding these concepts makes the package much
more intuitive.

## What Afrobarometer is

Afrobarometer is a pan-African survey program that measures public opinion on
democracy, governance, the economy, and daily life. It publishes microdata for
researchers; the data are free to use but require citation.

The package is a third-party client, not officially affiliated with
Afrobarometer.

## Rounds

Afrobarometer surveys are released in **rounds** every 2–3 years, and each round
covers a set of countries.

Variable names change between rounds. For example, the trust-in-the-president
question is `trspre` in Round 1, `Q43A` in Round 2, and `Q37A` in Rounds 9 and
10. The package's crosswalk maps these names for you.

## Respondents and rows

Each row is one interviewed respondent. Columns are survey variables. A merged
file stacks all countries, so a single column can contain responses from every
country in the round.

## Merged and country-level files

| Kind | Scope | When used |
| --- | --- | --- |
| Merged | All countries in a round | Default for `load(rounds=...)` |
| Country | One country and round | Preferred when `countries=` covers every requested country |

Country pages may offer SAV, zipped SAV, or DTA. Pages that only offer CSV raise
`NotFoundError` because CSV is not supported.

## Variables and labels

A variable is a column such as `Q37A`. Its metadata includes:

- A **label** describing the question.
- **Value labels** mapping codes to text.
- **Missing codes** declared by the file or inferred from labels.

Raw loads keep numeric codes. `labels=True` decodes them, and
`normalize_missing=True` replaces missing codes with `pd.NA`.

## Missing codes

Afrobarometer files use different missing conventions. The package collects
missing codes from:

1. The SPSS declared missing range.
2. Explicit user-missing values.
3. Conventional codes with missing-looking labels: `8`, `9`, `97`, `98`, `99`,
   `997`, `998`, `999`, `-1`.

See [Missing codes](missing-codes.md) for details.

## Weights

Survey weights correct for sampling differences. The canonical `weight` column
prefers `withinwt_hh` when the round includes it. Weighted means are usually more
appropriate than unweighted means for population-level statements. See
[Weights](weights.md).

## Canonical variables

Canonical variables give stable names to common respondent attributes:

| Column | Meaning |
| --- | --- |
| `country` | Country name |
| `respondent_id` | Respondent identifier |
| `weight` | Survey weight |
| `region` | Region |
| `urban_rural` | Urban/rural classification |
| `age` | Age |
| `gender` | Gender |
| `education` | Education |
| `interview_date` | Interview date |

They are added when `harmonize=True`. See
[Canonical variables](canonical-variables.md).

## Question concepts

Question concepts group comparable survey items under stable names such as
`trust_president`, `support_democracy`, and `social_media_news`. A concept maps
each round to its source variable, wording, recodes, and missing codes. Concepts
are sparse: one may start in Round 6 or be absent in Round 4.

`questions()` reports the full catalog and `question(name)` shows every round,
including excluded rounds. The older `families()` call still works for the
original 32 names but is deprecated. See [Question concepts](families.md),
[Question harmonization](family-harmonization.md), and the
[Master codebook](master-codebook.md).

## Crosswalk guarantees

Mappings come from curated YAML files shipped with the package. A mapping that
cannot be verified is omitted with a warning; it is never guessed. Unknown
concepts raise `HarmonizationError`.

## Codebooks

A codebook documents every variable, question wording, and value label for a
round. Use [Codebooks](codebooks.md) when you need the authoritative definition.

## Catalog and metadata index

Two shipped artifacts make discovery fast:

- `manifest.json` — the baked catalog of rounds and data URLs.
- `metadata_index.json` — variable names, labels, concepts, value labels, and
  missing codes for merged rounds 1–10.

The catalog is refreshed weekly in CI. At runtime, a cached live index takes
precedence when fresh; otherwise the baked manifest is used. See
[Rounds and the catalog](rounds.md) and
[Caching, TTL, and offline mode](caching-and-offline.md).

## Citation and data policy

Afrobarometer data are free to use but remain copyrighted. Cite them in
publications and follow the access policy. See
[Citation and provenance](citation-and-provenance.md) and
[Data policy](data-policy.md).

## Glossary

| Term | Meaning |
| --- | --- |
| Round | A survey wave |
| Merged file | One file covering all countries in a round |
| Country file | One file for a single country and round |
| Variable | A survey column such as `Q37A` |
| Value label | Text for a numeric code |
| Missing code | A code representing no usable answer |
| Weight | A sampling correction factor |
| Canonical variable | A stable column such as `country` or `age` |
| Question concept | A stable name for a comparable question across rounds |
| Crosswalk | The mapping from concepts/canonical names to source variables |
| Codebook | Documentation of variables and codes |
| Provenance | Source URLs, rounds, countries, and retrieval time |

## See also

- [Rounds and the catalog](rounds.md)
- [Question concepts](families.md)
- [Master codebook](master-codebook.md)
- [Canonical variables](canonical-variables.md)
- [Tutorial: Afrobarometer concepts](../tutorial/concepts.md)
