# Zensical documentation site — design

**Date:** 2026-10-25
**Status:** Approved design, pending implementation plan
**Scope:** Add a Zensical-powered documentation site to pyafrobarometer.

## Goal

Give pyafrobarometer a browsable documentation site that is accurate to the
current public API, previewable locally with `zensical serve`, and deployed
automatically to GitHub Pages from `main`.

## Constraints

- Content must reflect the current code in `src/pyafrobarometer/`; no invented
  features or options.
- The internal working documents under `docs/superpowers/` must not be published.
- The existing `README.md` stays intact because it is the PyPI long description.
- No changes to library code or runtime dependencies.
- Site sources live in `docs/`, the Zensical default, so the project keeps a
  conventional layout.
- `site_url` is `https://muhammadomarmuhdhar.github.io/pyafrobarometer/`, based
  on the current `origin` remote.

## Configuration

Create `zensical.toml` at the repository root:

```toml
[project]
site_name = "pyafrobarometer"
site_url = "https://muhammadomarmuhdhar.github.io/pyafrobarometer/"
site_description = "Programmatic access to Afrobarometer survey data in Python."
site_author = "pyafrobarometer contributors"
copyright = "&copy; 2026 pyafrobarometer contributors"
docs_dir = "docs"
site_dir = "site"
repo_url = "https://github.com/MuhammadOmarMuhdhar/pyafrobarometer"
repo_name = "MuhammadOmarMuhdhar/pyafrobarometer"
edit_uri = "edit/main/docs/"
exclude_docs = "superpowers/"
strict = true
nav = [
  { "Home" = "index.md" },
  { "Getting started" = [
    "getting-started/installation.md",
    "getting-started/quickstart.md",
  ] },
  { "Guides" = [
    "guides/discovery.md",
    "guides/loading.md",
    "guides/harmonization.md",
    "guides/panels.md",
    "guides/labels-and-missing.md",
    "guides/search.md",
    "guides/codebooks.md",
    "guides/caching-and-offline.md",
    "guides/citation-and-data-policy.md",
  ] },
  { "API reference" = [
    "reference/index.md",
    "reference/functions.md",
    "reference/dataset.md",
    "reference/errors.md",
  ] },
  { "Development" = "development.md" },
]

[project.theme]
features = [
  "navigation.tabs",
  "navigation.sections",
  "navigation.indexes",
  "navigation.top",
  "navigation.tracking",
  "content.action.edit",
  "content.action.view",
  "toc.follow",
]
```

The explicit `nav` keeps page order stable and prevents excluded directories from
leaking into navigation. `exclude_docs = "superpowers/"` keeps the design and plan
documents out of both the build and the search index. They remain in the
repository.

## Content map

All pages are new Markdown files under `docs/`. Prose is written for a reader who
has Python and pandas experience but has not used this package.

| Path | Purpose |
| --- | --- |
| `index.md` | Project overview, unofficial/copyright notice, install one-liner, short example, entry points to the guides. |
| `getting-started/installation.md` | `pip install`, optional `[search]` and `[codebook]` extras, Python >= 3.10, editable dev install. |
| `getting-started/quickstart.md` | Discover rounds and families, load a round, harmonize, build a two-round panel. |
| `guides/discovery.md` | `rounds()`, `countries()`, `families()`, merged vs country-level data, CSV limitation. |
| `guides/loading.md` | `load()` options, local `source`, `Dataset` behaviour, `to_pandas()`, `subset()`. |
| `guides/harmonization.md` | Canonical variables, question families, sparse availability, `strict`. |
| `guides/panels.md` | `panel()` across rounds, required variables, returned shape and provenance. |
| `guides/labels-and-missing.md` | `labels=True`, `normalize_missing=True`, declared missing codes, raw defaults. |
| `guides/search.md` | `search_variables()`, fuzzy vs substring, metadata index, no downloads. |
| `guides/codebooks.md` | `codebook()`, `extract_text`, `Dataset.codebook()`, `[codebook]` extra. |
| `guides/caching-and-offline.md` | Cache location, `PYAFROBAROMETER_CACHE_DIR`, index TTL, `PYAFROBAROMETER_OFFLINE`, `clear_cache()`. |
| `guides/citation-and-data-policy.md` | `citation()`, required acknowledgment, local-only storage, no redistribution. |
| `reference/index.md` | How the reference is organised and a table of public names. |
| `reference/functions.md` | Signatures, parameters, returns, and raises for every public function exported from `pyafrobarometer`. |
| `reference/dataset.md` | `Dataset` properties, methods, delegation, and the `Provenance` dataclass. |
| `reference/errors.md` | Exception hierarchy and when each error is raised. |

### Reference accuracy sources

- Functions and signatures: `src/pyafrobarometer/api.py` and
  `src/pyafrobarometer/__init__.py`.
- `Dataset` and `Provenance`: `src/pyafrobarometer/dataset.py`.
- Exceptions: `src/pyafrobarometer/errors.py`.
- Usage examples and environment variables: `README.md`.

No API reference content is auto-generated. Pages are hand-written so sparse
docstrings do not leak into the site.

## Build and deployment

- Add a `docs` optional dependency group to `pyproject.toml`:
  `docs = ["zensical"]`. This lets contributors run
  `pip install -e ".[docs]"`.
- Add `.github/workflows/docs.yml`:
  - Triggers: push to `main` touching `docs/**`, `zensical.toml`, or
    `pyproject.toml`; `workflow_dispatch`.
  - Permissions: `contents: read`, `pages: write`, `id-token: write`.
  - Concurrency group for Pages deployments.
  - Steps: checkout, set up Python, `pip install zensical`,
    `zensical build --clean`, upload the `site` directory with
    `actions/upload-pages-artifact`, deploy with `actions/deploy-pages`.
- Add `site/` to `.gitignore`.
- Add a short "Documentation" link near the top of `README.md`, pointing at the
  published site. The rest of the README is unchanged.

GitHub Pages must be configured to publish from GitHub Actions. That is a
repository setting outside the code change and is called out in the development
guide.

## Error handling and edge cases

- `docs/superpowers/` is excluded, so internal specs never appear on the site.
- Link validation is enabled by default; `strict = true` makes the build fail on
  any invalid link or anchor. The build is the acceptance check.
- If GitHub Pages is not enabled, the workflow fails at deploy time; the build
  step still validates the docs.
- The site is static and does not download Afrobarometer data at build time.

## Verification

1. `pip install -e ".[docs]"` (or install `zensical` into the existing `.venv`).
2. `zensical build --clean` completes without errors or link warnings.
3. Inspect `site/` to confirm the expected pages exist and `superpowers/` is
   absent.
4. `zensical serve` renders the navigation and search as configured (manual
   smoke check).
5. Existing offline test suite still passes (`pytest`), confirming no library
   changes.

## Non-goals

- No mkdocstrings or auto-generated API pages.
- No custom theme, CSS overrides, logo, or versioned documentation.
- No changes to `src/` or runtime dependencies.
- No replacement of the README.
