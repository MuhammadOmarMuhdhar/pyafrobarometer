# Countries and coverage

`countries()` lists the countries known to the package.

```python
import pyafrobarometer as ab

print(ab.countries()[:10])
print(ab.countries(round=9))
```

## Where names come from

Names are read from the value labels in the shipped metadata index for merged
rounds 1–10. If the index cannot provide them, the catalog's country entries are
used as a fallback. If neither source yields a name, `countries()` raises
`NotFoundError`.

## Filtering by country

Pass `countries=` to [`load()`](../reference/functions.md#load) or
[`panel()`](../reference/functions.md#panel):

```python
ghana = ab.load(rounds=9, countries="Ghana")
west_africa = ab.load(rounds=9, countries=["Ghana", "Benin", "Togo"])
```

Matching is case-insensitive and alias-aware. Names are normalized by removing
accents and punctuation and by mapping common aliases:

| Input | Resolves to |
| --- | --- |
| Ivory Coast | Côte d'Ivoire |
| Swaziland | Eswatini |
| Cape Verde | Cabo Verde |
| DRC, Congo Kinshasa | Democratic Republic of the Congo |
| Congo Brazzaville | Republic of the Congo |
| Burma | Myanmar |
| Macedonia | North Macedonia |

This means `countries="Cote d'Ivoire"` and `countries="Ivory Coast"` select the
same rows.

## Merged and country-level behavior

When you pass `countries=`, the package checks whether every requested country
has a country-level file. If so, it downloads those files. Otherwise it downloads
the merged file and filters it.

Filtering needs a country column. If a local source has none, `load()` raises
`HarmonizationError`; load with `harmonize=True` to add the canonical `country`
column first.

## CSV-only pages

Some country pages only offer CSV. CSV is not supported in this version, so the
package raises `NotFoundError` with a clear message. SAV, zipped SAV, and DTA are
supported.

## Coverage changes

Not every country appears in every round. `countries(round=...)` reflects the
requested round. When building a panel, countries missing from a round simply
have no rows for that round.

## See also

- [Loading a round](loading.md)
- [Local and remote sources](sources.md)
- [`countries()`](../reference/functions.md#countries)
- [Tutorial: discover the data](../tutorial/discover.md)
