# Local quickstart

## Supported baseline

- CPython **3.12**, 64-bit. The package deliberately requires `>=3.12,<3.13`.
- Poetry **2.5.1**. Use an isolated Poetry installation such as `pipx install poetry==2.5.1`; do not install Poetry into the project's `.venv`.
- Modern browser for the local viewer. No JavaScript build tool or Node installation is required.
- Git if cloning; otherwise unzip the source archive and open its folder in Terminal.

If Python/Poetry are missing, use the [Python downloads](https://www.python.org/downloads/), [Poetry installation documentation](https://python-poetry.org/docs/#installation) or [pipx installation guide](https://pipx.pypa.io/stable/installation/). No cloud subscription, paid API or source credential is required for this release.

On macOS, check `uname -m`: `arm64` means Apple Silicon, `x86_64` means Intel. On Windows use 64-bit Python and `py -3.12 --version` to check its version. Windows users can give `poetry env use` the full Python 3.12 executable path if `3.12` is not resolved automatically.

## Phase 1: install and diagnose

From the folder containing `pyproject.toml`:

```bash
poetry --version
python3.12 --version
poetry env use 3.12
poetry sync
poetry check --lock
poetry run luxrisk doctor
poetry run pytest -q
```

Windows: the Python version check can be `py -3.12 --version`. The remaining Poetry commands are identical. The diagnosis should report `ok: true`, `resources_ok: true`, zero network requests and no user data written. Tests use tiny fixtures in temporary directories and exit with an assertion summary.

Do not run `poetry update` during initial reproduction. `poetry sync` installs the committed lock; it does not choose new versions. Runtime-only installation is `poetry sync --only main` if you do not need tests or developer tools.

## Phase 2: explicitly explore the authored demo on your machine

```bash
poetry run luxrisk demo
poetry run luxrisk serve --mode demo
```

Open http://127.0.0.1:8010. Choose Germany, France, Spain or Netherlands for the authored demo series. Other configured countries are a visible empty state until collected. Stop with **Ctrl+C**. Re-running `demo` appends another demo vintage; it never modifies live observations.

The scenario starts with editable assumptions: a USD 100,000 invoice, 1.1 USD/EUR, a -10% currency shock, EUR 500,000 floating debt and +100 bps. These are examples, not observations silently imported from a selected country.

## Phase 3: small official-source slices

```bash
poetry run luxrisk collect --country DE --indicators inflation,unemployment --start 2025-01 --end 2025-03
poetry run luxrisk collect --country DE --indicators gdp --start 2025-Q1 --end 2025-Q2
poetry run luxrisk collect --country DE --indicators eurusd --start 2025-01 --end 2025-03
poetry run luxrisk coverage --mode live
poetry run luxrisk serve --mode live
```

`country` is configurable independently of formulas. Country availability depends on the actual indicator response. EURUSD always uses entity **EA**. Monthly and quarterly windows belong in separate commands; mixing them fails before a request.

For a forecast-capable monthly series, choose a longer explicit window after these small checks succeed, for example `--start 2023-01 --end 2025-12`. This command is for your own local execution; it is not run by tests. Forecast availability still depends on contiguous values and source break flags.

**Each publication represents exactly its requested slice.** A later shorter window becomes the latest slice; it is not silently merged into a longer older history. Use the same window to investigate revisions, or select the older run ID. This makes the observation set behind each result explicit.

## Phase 4: compare and export

Collect a second country before comparing:

```bash
poetry run luxrisk collect --country FR --indicators inflation --start 2025-01 --end 2025-03
poetry run luxrisk compare --countries DE,FR --indicator inflation --mode live
poetry run luxrisk export --mode live --output exports/first-official-pack
```

Each export directory is new. Reusing an existing directory is refused. See [Power BI](power-bi.md) for table relationships, measures and the browser/desktop boundary.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Poetry cannot find Python 3.12 | Install it, then `poetry env use /absolute/path/to/python3.12` |
| A different Python is active | Run `poetry env info`; remove/recreate only this project's environment if necessary |
| Lock mismatch | Use the unchanged `pyproject.toml` and `poetry.lock` together; do not manually edit the lock |
| `No ledger yet` | Run the explicit demo or a small collect command first |
| No values for selected country | Inspect `coverage --mode live`; configured country is not collected coverage |
| Provider selector changed / no usable values | Inspect source metadata; update catalogue and fixtures deliberately. Previous successful slices remain available |
| `Retry later` / timeout | Stop and retry later; do not launch a bulk loop |
| Forecast unavailable | Need enough consecutive nonmissing observations without a source break |
| Viewer port occupied | Use `serve --port 8011`; open the same port in the browser |
| `--db` rejected | Put the global option before the command: `luxrisk --db workspace/test.sqlite coverage --mode live` |

Use the [reading map](start-here.md) after installation, not a tour of every class at once.
