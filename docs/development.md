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

## Data files

Never commit Afrobarometer microdata, archives, or codebooks. The `.gitignore`
excludes `*.sav`, `*.zip`, and `*.pdf`. The package downloads data into the local
cache at runtime. See
[Data policy](guide/data-policy.md).
