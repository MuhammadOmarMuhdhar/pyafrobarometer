# Citation and data policy

## Citation helper

[`citation()`](../reference/functions.md#citation) builds the required
acknowledgment from rounds and countries:

```python
import pyafrobarometer as ab

print(ab.citation(rounds=[8, 9], countries=["Ghana", "Benin"]))
```

```
Afrobarometer Data, Ghana, Benin, Rounds 8, 9, 2022, 2023, available at http://www.afrobarometer.org.
```

A loaded dataset can cite itself:

```python
ds = ab.load(rounds=9)
print(ds.citation())
```

The helper fills in years from the catalog when they are known. If the catalog
cannot be read, it still returns a citation without years.

## Required acknowledgment

> Afrobarometer Data, [Country(ies)], [Round(s)], [Year(s)], available at
> http://www.afrobarometer.org.

Please include this acknowledgment in publications that use the data.

## Data policy

- Data and codebooks are stored only in the local cache reported by
  [`cache_dir()`](../reference/functions.md#cache_dir).
- No Afrobarometer microdata, codebooks, or archives are committed to this
  repository.
- Downloads use HTTPS from `www.afrobarometer.org` only.
- The package does not redistribute data. It downloads files to your machine.
- Afrobarometer data remain copyrighted. Follow their
  [access policy](https://www.afrobarometer.org/data/).

## Unofficial status

This package is not affiliated with or endorsed by Afrobarometer. It is an
independent client for their public data downloads.

## License

The package code is released under the MIT License. See the
[LICENSE](https://github.com/MuhammadOmarMuhdhar/pyafrobarometer/blob/main/LICENSE)
in the repository.

## See also

- [`citation()`](../reference/functions.md#citation)
- [`Dataset.citation()`](../reference/dataset.md#citation)
- [Caching and offline use](caching-and-offline.md)
