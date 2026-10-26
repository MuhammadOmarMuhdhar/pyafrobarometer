# Data policy

## What the package does

- Stores data and codebooks only in the local cache reported by
  [`cache_dir()`](../reference/functions.md#cache_dir).
- Downloads over HTTPS from `www.afrobarometer.org` only.
- Does not commit Afrobarometer microdata, codebooks, or archives to the
  repository.
- Does not redistribute data. Files are downloaded to your machine.

## What you must do

- Cite Afrobarometer in publications. See
  [Citation and provenance](citation-and-provenance.md).
- Follow Afrobarometer's [access policy](https://www.afrobarometer.org/data/).
- Respect the copyright on the data and codebooks.

## Unofficial status

This package is not affiliated with or endorsed by Afrobarometer. It is an
independent client for their public data downloads.

## License

The package code is released under the MIT License. See the
[LICENSE](https://github.com/MuhammadOmarMuhdhar/pyafrobarometer/blob/main/LICENSE)
in the repository.

## See also

- [Citation and provenance](citation-and-provenance.md)
- [Caching, TTL, and offline mode](caching-and-offline.md)
- [Development](../development.md)
