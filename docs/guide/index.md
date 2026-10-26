# Guide

This guide explains every major feature of pyafrobarometer, step by step. Each
chapter is standalone, so you can read it in order or jump directly to the topic
you need. It doubles as a reference you can return to.

If you are new to the package, start with the [Tutorial](../tutorial/index.md)
for a short end-to-end project. This guide goes deeper.

## How to use this guide

- Chapters build on the same vocabulary but do not require the previous chapter.
- Code blocks are runnable. Outputs are illustrative.
- Every chapter links to the [API reference](../reference/index.md) for exact
  signatures and to related chapters.
- The [Tutorial](../tutorial/index.md) shows one opinionated path; this guide
  explains the options.

## Installation

```bash
pip install pyafrobarometer
```

Optional extras:

```bash
pip install "pyafrobarometer[search]"    # fuzzy variable search
pip install "pyafrobarometer[codebook]"  # PDF text extraction
```

Requires Python 3.10 or newer. For a development install, see
[Development](../development.md).

## Chapters

### Concepts and discovery

- [Afrobarometer concepts](concepts.md)
- [Rounds and the catalog](rounds.md)
- [Countries and coverage](countries.md)
- [Question families](families.md)

### Loading and shaping

- [Loading a round](loading.md)
- [Selecting variables](selecting-variables.md)
- [The Dataset object](dataset.md)
- [Value labels](value-labels.md)
- [Missing codes](missing-codes.md)
- [Weights](weights.md)
- [Canonical variables](canonical-variables.md)
- [Question-family harmonization](family-harmonization.md)
- [Multi-round loads](multi-round.md)
- [Local and remote sources](sources.md)

### Analysis

- [Panels](panels.md)
- [Variable search](search.md)
- [Codebooks](codebooks.md)

### Operations

- [Caching, TTL, and offline mode](caching-and-offline.md)
- [Citation and provenance](citation-and-provenance.md)
- [Data policy](data-policy.md)
- [Errors](errors.md)

### Finishing

- [Next steps](next-steps.md)

## Conventions

- `rounds` accepts an integer or an iterable of integers.
- `countries` and `variables` accept a string or an iterable of strings.
- `strict=True` raises on unavailable requested items; `strict=False` warns.
- Data is downloaded on first use and cached locally.
