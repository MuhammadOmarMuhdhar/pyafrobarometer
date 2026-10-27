# Next steps

You built a reproducible, weighted, multi-round trend and exported it to CSV.
That covers the core workflow. Here is where to go next.

## Go deeper

- [Guide](../guide/index.md) — every major feature explained in depth.
- [Afrobarometer concepts](../guide/concepts.md) — the full domain primer.
- [Question concepts](../guide/families.md) — find other comparable variables.
- [Master codebook](../guide/master-codebook.md) — how concepts are reviewed.
- [Panels](../guide/panels.md) — more panel patterns.
- [Caching and offline use](../guide/caching-and-offline.md) — reproducible runs
  without a network.
- [API reference](../reference/index.md) — exact signatures and return types.

## Try other analyses

- Replace `trust_president` with `trust_police`, `support_democracy`, or
  `corruption_president`.
- Filter to a set of countries with `countries=["Ghana", "Kenya", "Nigeria"]`.
- Compare urban and rural respondents using the canonical `urban_rural` column.
- Use `search_variables()` to find variables by label.
- Download a codebook to confirm a question's wording.

## A note on interpretation

The harmonized 0–3 scale is comparable across rounds, but the underlying
questions and country samples change. Always check the codebook and report
weights, missing-data handling, and the rounds you used.

## Keep developing

If you want to contribute to the package, see [Development](../development.md)
for the test, lint, and documentation workflow.
