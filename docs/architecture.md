# Architecture and design decisions

The project has one executable workflow and five responsibilities. This is a local analytical product; there is no cloud deployment hidden behind installation.

| Responsibility | Owner | Contract |
| --- | --- | --- |
| Command selection | `cli.py` | No action runs implicitly |
| Official retrieval | `connectors.py`, `catalog.py` | Exact selectors, bounded transport, preserved bytes |
| Safe publication | `pipeline.py`, `warehouse.py`, `sql/` | Validate first, append atomically, preserve success on failure |
| Statistical reasoning | `analysis.py` | Pure, frequency-aware, inspectable formulas |
| Shared presentation | `reporting.py`, `api.py`, `static/` | CLI/UI/export reuse one analysis path |

## Publication and schema

`collection` records successful or failed attempts. `raw_response` records the exact bytes, hash, provider URL, retrieval time and definition used for a country/indicator slice. `observation` stores normalized values and source flags. A SQL view selects the latest successful run **per mode, entity and indicator**.

The raw and observation primary keys prevent duplicate series or periods within one vintage. Foreign keys tie every observation to a raw-response receipt. A multi-series publication is one transaction. Failed attempts receive a separate audit row and never become an available series.

A vintage is a complete requested slice, not an automatically merged history. Old slices remain addressable by run ID. Comparisons can select the latest series from different successful runs; the export manifest makes those choices explicit. This avoids pretending that different countries were necessarily released or ingested simultaneously.

The packaged SQL schema is included in wheels as well as source archives. SQLite reads use read-only URIs, including safe paths with spaces. No ORM or SQL service needs to be installed.

## Why this release has no external runtime package

Python's standard library is sufficient for bounded HTTPS access, immutable typed data records, SQLite, simple statistical baselines, CSV exports and a local report viewer. Avoiding a dataframe/native modelling stack reduces installation friction without hiding the calculations.

Poetry still owns the environment and lock. Development tools and the build backend have exact versions. A strict type checker and authored tests provide contracts; the catalogue remains the single definition source.

## Why not dbt, Airflow and a cloud warehouse now?

The first release has a small local data volume, explicit user-triggered collection and a compact SQLite model. Adding orchestration or a second transformation engine now would duplicate responsibilities. A scheduled production service would justify a migration to a managed warehouse, orchestration, schema migrations and a public-serving framework; these are follow-up design decisions, not implemented claims.

## Why two simple forecasting baselines?

Naive and drift provide transparent reference performance on the same origins. A more complex model earns a place only after a separately held-out, vintage-aware evaluation shows value. Small histories, break flags and missing dates suppress evaluation rather than produce misleading scores.

## Local viewer boundary

The viewer binds to `127.0.0.1`, rejects unrelated Host headers and only serves whitelisted assets and read-only calculation routes. It has no collection, export, file upload or arbitrary-file endpoint. It uses no external font, script, CDN or tracking service. It is a local development/review interface, not an internet production server.

## Extension sequence

1. Review historical investigation flags with a labelled evidence notebook before reporting detection performance.
2. Add an explicit provider contract, recorded probe and authored negative tests before enabling another indicator.
3. Compare further models on a separate final period; preserve the currently available-vintage caveat.
4. Build and visually validate a native Power BI report from the exported model before claiming one exists.
