# Data contracts and local HTTP interface

## The three supporting records

| Record / field | Type | Meaning |
| --- | --- | --- |
| `Indicator.id` | str | Stable application identifier, e.g. inflation |
| `Indicator.provider / dataset` | str | Official provider and precise source dataset/key |
| `Indicator.frequency / unit` | str | M or Q and the measured unit |
| `Indicator.filters` | tuple of string pairs | Exact dimensional selectors checked by the adapter |
| `Indicator.lag_days` | int | Project-defined freshness threshold from period end |
| `Observation.country` | str | Configured two-letter country, or EA for shared currency context |
| `Observation.indicator` | str | Catalogue ID |
| `Observation.period` | str | Valid `YYYY-MM` or `YYYY-Qn` label |
| `Observation.value` | float or None | Finite measured value, or explicit missing cell |
| `Observation.status` | str | Original provider quality flags, or demo label |
| `SourceBatch.payload` | bytes | Exact original response, not reserialized JSON |
| `SourceBatch.url / retrieved_at` | str | Original query and project ingestion timestamp |
| `SourceBatch.observations` | tuple of Observation | Normalized rows checked before publication |

Data records are immutable. A constructor performs no network/database action. `Observation` validates its calendar, entity and finite-value shape; `validate_batch` checks catalogue identity, frequency, domains and duplicate keys. `Warehouse.publish` expects a validated batch; use `CollectionService` for normal collection.

## Provider JSON and output JSON

`JsonObject` is an explicit `dict[str, Any]` boundary for external JSON and heterogeneous report payloads. It does not claim a fully statically typed external provider schema. Strict dimensional checks, validated observation records and negative fixtures check those runtime boundaries. Typed model records are used for statistical inputs.

The Eurostat normalizer accepts the documented singleton-series JSON-stat response used by this application, with sparse/dense value cells and original flags. It rejects extra dimensions, empty country/age selections and wrong unit/scope. It is not a general-purpose parser for every possible JSON-stat cube.

## Read-only local routes

Start with `poetry run luxrisk serve --mode demo`; base URL is `http://127.0.0.1:8010`. The UI calls these same endpoints. There is no write, arbitrary-file, export or provider-fetch endpoint.

| GET route | Query parameters | Result |
| --- | --- | --- |
| `/api/catalog` | none | Country catalogue, definitions and initial mode |
| `/api/coverage` | mode | Actually stored latest successful series |
| `/api/report` | country, indicator, mode, optional run_id | Rows, exact source receipt, summary, signal, evaluation and revision explanation |
| `/api/compare` | countries as comma-separated 2-6 distinct codes, indicator, mode | Latest common nonmissing period, units and source versions |
| `/api/scenario` | imports (USD), fx (USD/EUR), shock (%), debt (EUR), bps | Mechanical invoice and annual interest effects |

Mode must be demo or live. A configured but uncollected series returns an explicit empty report; an absent database or invalid parameter returns an actionable 400 response. Unknown paths return 404. Nonlocal Host headers return 403. JSON numbers never serialize NaN/Infinity.

## Filesystem contract

Only explicit demo/collect operations create `workspace/luxrisk.sqlite` by default. Export builds in a temporary sibling directory and renames it into a new destination; it refuses overwrite. Diagnosis uses an in-memory SQLite connection. The HTTP viewer and report reads never create a ledger or refresh a provider.

The default database option is global: `luxrisk --db workspace/another.sqlite inspect ...`. A Windows/macOS path containing spaces is supported as a quoted path argument.
