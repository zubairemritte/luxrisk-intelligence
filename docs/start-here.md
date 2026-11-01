# Start here: one workflow, four operational classes

Start from the CLI, not from a list of classes:

```bash
poetry run luxrisk --help
poetry run luxrisk doctor
```

## Read four entry points

| Order | File / definition | Question |
| --- | --- | --- |
| 1 | [`cli.py / main`](../luxrisk/cli.py) | Which explicit action did the user choose? |
| 2 | [`pipeline.py / CollectionService.collect`](../luxrisk/pipeline.py) | How are slices validated before a safe publication? |
| 3 | [`connectors.py / EurostatConnector.collect`, then `normalize`](../luxrisk/connectors.py) | Which exact source series did we request and receive? |
| 4 | [`analysis.py / anomaly_signal`, then `evaluate_forecast`](../luxrisk/analysis.py) | What does the displayed statistical result mean? |

Follow storage after the collection service. Follow presentation after understanding one formula. Every Python function/method describes inputs, outputs, expected errors where relevant, and side effects. Annotations define parameters, returned shapes, stored fields and important local values; the strict checker also infers loop variables from typed collections.

## The classes that actually operate

| Class | What one instance keeps | Its responsibility | Who creates it? |
| --- | --- | --- | --- |
| `EurostatConnector` | Injectable URL-to-bytes callable | Request and normalize a precisely defined official statistical slice | `CollectionService` |
| `ECBConnector` | Injectable URL-to-bytes callable | Request and normalize the shared monthly EURUSD series | `CollectionService` |
| `CollectionService` | Two adapters and a warehouse | Orchestrate the bounded request, validation and atomic publication | CLI |
| `Warehouse` | One local SQLite path | Preserve vintages and query an isolated mode | CLI |

There is no second ingestion engine elsewhere. Calling a constructor does not collect data or create a database. The service calls an adapter, the adapter normalizes source bytes, validation checks the batch, and the warehouse commits it.

Supporting declarations do different jobs:

- `Indicator` is immutable metadata for a series definition.
- `Observation` is one immutable validated data row.
- `SourceBatch` carries exact bytes, request evidence and normalized rows until publication.
- `SourceError` is an exception, not a service.
- `api.make_handler` creates an internal HTTP handler type required by Python's local server. It only reads reports; you do not instantiate it when collecting data.
- `Mode`, `JsonObject` and `Fetcher` are type aliases, not services.

## Where to make a change

| Change | Owner |
| --- | --- |
| Add or modify a country / indicator definition | `catalog.py`; verify the official series and update `docs/sources.md` |
| Change source field mapping | Adapter's `normalize` method and authored contract fixtures |
| Change collection safety or range checks | `pipeline.py` |
| Change persistence / a SQL view | `warehouse.py`, `sql/schema.sql` |
| Change anomaly, forecast or scenario maths | `analysis.py` and hand-calculated tests |
| Change report composition / BI exports | `reporting.py` |
| Change visible labels / layout | `static/`; calculations remain in Python |
| Change a command | `cli.py` |

## Follow one inflation value

`collect --country DE --indicators inflation ...` reaches `main`. The service asks `EurostatConnector` for a monthly slice. The adapter checks every returned dimension (country, frequency, unit and all-items scope), preserving a missing cell as `None`. The service rejects duplicate periods or mismatched identities. `Warehouse.publish` writes the entire successful slice, its source bytes and metadata together. `series_report` reads a chosen run ID and calls the pure functions in `analysis.py`. The CLI, interface and export reuse that same report.

The reader can now answer: where did this number come from, what does it measure, when did this project retrieve it, and which exact vintage did the calculation use?

See the [complete function index](function-index.md) only when you need a specific definition. [Architecture](architecture.md) explains why the modules are separate.
