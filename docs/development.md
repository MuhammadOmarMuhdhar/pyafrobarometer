# Development

## Setup

```bash
git clone https://github.com/MuhammadOmarMuhdhar/pyafrobarometer.git
cd pyafrobarometer
pip install -e ".[dev]"
```

The `dev` extra includes `pytest`, `pytest-cov`, `respx`, `ruff`, `mypy`,
`rapidfuzz`, `pypdf`, and the pandas type stubs.

## Tests

The default suite is offline:

```bash
pytest
```

Network tests hit `www.afrobarometer.org` and download large files. They are
excluded by default and must be selected explicitly:

```bash
pytest -m network
```

## Lint and type checks

```bash
ruff check .
mypy src
```

The project uses a 100-character line length and strict mypy settings, as
configured in `pyproject.toml`.

## Documentation

Install the docs extra:

```bash
pip install -e ".[docs]"
```

Preview the site with live reload at `http://localhost:8000`:

```bash
zensical serve
```

Build the static site into `site/`:

```bash
zensical build --clean
```

The build runs in strict mode, so broken links or anchors fail the build.

The site sources live in `docs/`. The internal design and plan documents under
`docs/superpowers/` are excluded from the build through `exclude_docs` in
`zensical.toml`.

## Question crosswalk

`src/pyafrobarometer/crosswalk/questions.yaml` is the reviewed master codebook
and the only runtime source of truth for cross-round question concepts. The
generator is a build-time authoring aid; it never runs at query time and never
silently overwrites reviewed entries.

```bash
# Propose candidates for new or changed labels.
python scripts/build_questions.py --propose

# Accept all exact matches or a specific concept.
python scripts/build_questions.py --accept-exact
python scripts/build_questions.py --accept trust_president

# Validate schema, source variables, and coverage.
python scripts/build_questions.py --validate
python scripts/build_questions.py --validate --strict-coverage
```

Review `build/questions.proposed.yaml`, merge accepted entries into
`questions.yaml`, and rerun validation. The `--strict-coverage` check reports
repeated labels that are not assigned to a concept; resolve or intentionally
defer them before a release.

The metadata index is regenerated from the crosswalk and per-round metadata:

```bash
python scripts/update_catalog.py --write --metadata-rounds all
```

Do not edit `metadata_index.json` by hand. Each mapped variable carries a
`concept` tag; `family` remains only for the original 32 names.

## Catalog refresh

The catalog is refreshed by a script that parses the Afrobarometer site and
validates links and crosswalk coverage:

```bash
python scripts/update_catalog.py --write --validate --metadata-rounds all
```

The script updates `src/pyafrobarometer/manifest.json` and
`src/pyafrobarometer/metadata_index.json`. A weekly GitHub Actions workflow runs
it and opens a pull request when the files change.

## Continuous integration

| Workflow | Purpose |
| --- | --- |
| `update-catalog.yml` | Weekly catalog refresh, validation, tests, and a pull request |
| `docs.yml` | Build and deploy this site to GitHub Pages on pushes to `main` |
| `publish.yml` | Build, check, and publish to PyPI when a GitHub release is published |

CI is never in the runtime path. A failed catalog refresh only means the package
keeps using its cached or baked catalog.

## Publishing the docs

The docs workflow deploys the `site/` directory with GitHub Pages. The repository
must be configured to publish from GitHub Actions:

1. Open the repository settings.
2. Go to **Pages**.
3. Set **Source** to **GitHub Actions**.

After that, pushes to `main` that touch `docs/`, `zensical.toml`, or
`pyproject.toml` deploy automatically. The workflow can also be run manually.

## Releasing to PyPI

Publishing uses PyPI trusted publishing, so no API token is stored in the
repository. The `publish.yml` workflow builds the sdist and wheel, runs
`twine check`, and uploads them when a GitHub release is published.

One-time setup on PyPI:

1. Sign in to PyPI and open **Account settings → Publishing**.
2. Add a pending publisher with owner `MuhammadOmarMuhdhar`, repository
   `pyafrobarometer`, workflow `publish.yml`, and environment `pypi`.
3. In the GitHub repository, create an environment named `pypi` (Settings →
   Environments).

Each release:

1. Bump `version` in `pyproject.toml` and `__version__` in
   `src/pyafrobarometer/__init__.py`.
2. Commit and push.
3. Create a GitHub release with a tag such as `v0.1.2`.

The workflow publishes automatically. To verify the artifacts before releasing:

```bash
uv build
uvx twine check dist/*
```

## Data files

Never commit Afrobarometer microdata, archives, or codebooks. The `.gitignore`
excludes `*.sav`, `*.zip`, and `*.pdf`. The package downloads data into the local
cache at runtime. See
[Data policy](guide/data-policy.md).
