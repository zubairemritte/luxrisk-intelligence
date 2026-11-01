# Function index

Generated from the actual Python definitions. Read [the start page](start-here.md) first.

| File | Definition | Responsibility |
| --- | --- | --- |
| [analysis.py](../luxrisk/analysis.py#L11) | `contiguous_tail` | Select the latest usable contiguous segment without filling calendar gaps. |
| [analysis.py](../luxrisk/analysis.py#L51) | `summarize` | Describe observed levels, percentage-point movements and freshness honestly. |
| [analysis.py](../luxrisk/analysis.py#L103) | `anomaly_signal` | Compare the latest value with a strictly earlier, contiguous reference window. |
| [analysis.py](../luxrisk/analysis.py#L155) | `evaluate_forecast` | Evaluate naive and drift one-step baselines on identical expanding-window origins. |
| [analysis.py](../luxrisk/analysis.py#L220) | `revision_diff` | Explain added, removed, revised and flag-only cells between two collected vintages. |
| [analysis.py](../luxrisk/analysis.py#L279) | `exposure_scenario` | Translate explicit currency/rate assumptions into mechanical EUR exposure changes. |
| [api.py](../luxrisk/api.py#L18) | `make_handler` | Bind a ledger to one HTTP handler type without starting a listener. |
| [api.py](../luxrisk/api.py#L135) | `serve` | Start the explicit local viewer until Ctrl+C. |
| [api.py](../luxrisk/api.py#L36) | `Handler.do_GET` | Route a single safe local read, returning visible empty/error states. |
| [api.py](../luxrisk/api.py#L105) | `Handler.respond` | Send a length-delimited response with conservative local-viewer headers. |
| [catalog.py](../luxrisk/catalog.py#L77) | `indicator_spec` | Resolve a public indicator ID to its canonical contract. |
| [catalog.py](../luxrisk/catalog.py#L98) | `country_code` | Normalize and validate a country filter without claiming provider coverage. |
| [cli.py](../luxrisk/cli.py#L21) | `doctor` | Diagnose runtime, SQLite and bundled resources without touching user data. |
| [cli.py](../luxrisk/cli.py#L49) | `parser` | Declare commands in one place so the code follows the public help screen. |
| [cli.py](../luxrisk/cli.py#L95) | `main` | Dispatch exactly one requested workflow with actionable errors. |
| [connectors.py](../luxrisk/connectors.py#L26) | `get_bytes` | Retrieve a bounded HTTPS response from an approved statistical provider. |
| [connectors.py](../luxrisk/connectors.py#L80) | `_numeric` | Parse a source number while preserving missingness and rejecting boolean values. |
| [connectors.py](../luxrisk/connectors.py#L311) | `validate_window` | Check frequency, order and bounded size before source access. |
| [connectors.py](../luxrisk/connectors.py#L106) | `EurostatConnector.__init__` | Configure transport without making a source request. |
| [connectors.py](../luxrisk/connectors.py#L121) | `EurostatConnector.collect` | Fetch one country/indicator slice within an explicit period window. |
| [connectors.py](../luxrisk/connectors.py#L158) | `EurostatConnector.normalize` | Decode one singleton-series JSON-stat cube independently of dimension order. |
| [connectors.py](../luxrisk/connectors.py#L220) | `ECBConnector.__init__` | Configure an injectable URL-to-bytes transport. |
| [connectors.py](../luxrisk/connectors.py#L235) | `ECBConnector.collect` | Fetch the monthly average USD-per-EUR exchange-rate slice. |
| [connectors.py](../luxrisk/connectors.py#L264) | `ECBConnector.normalize` | Validate ECB selectors and decode its observation CSV. |
| [demo.py](../luxrisk/demo.py#L12) | `create_demo` | Publish a labelled illustrative ledger on the user's own machine. |
| [models.py](../luxrisk/models.py#L13) | `period_end` | Translate an observation period to its final calendar day. |
| [models.py](../luxrisk/models.py#L39) | `period_number` | Map a monthly or quarterly label to an integer within its frequency. |
| [models.py](../luxrisk/models.py#L60) | `utc_now` | Return the current UTC ingestion timestamp as an ISO 8601 string. |
| [models.py](../luxrisk/models.py#L98) | `Observation.__post_init__` | Validate a normalized row immediately after construction. |
| [pipeline.py](../luxrisk/pipeline.py#L9) | `validate_batch` | Check normalized identity, frequency, uniqueness and sensible mathematical ranges. |
| [pipeline.py](../luxrisk/pipeline.py#L131) | `rows_to_observations` | Convert stored dictionary rows into typed analysis inputs. |
| [pipeline.py](../luxrisk/pipeline.py#L54) | `CollectionService.__init__` | Assemble dependencies without contacting providers. |
| [pipeline.py](../luxrisk/pipeline.py#L78) | `CollectionService.collect` | Collect an explicit small set, committing all requested slices atomically. |
| [reporting.py](../luxrisk/reporting.py#L17) | `series_report` | Assemble one traceable indicator panel without duplicating its calculations. |
| [reporting.py](../luxrisk/reporting.py#L68) | `compare_countries` | Compare peers at the most recent common nonmissing period, without forward fill. |
| [reporting.py](../luxrisk/reporting.py#L131) | `write_csv` | Write a UTF-8 BI table with stable headers and safe spreadsheet text cells. |
| [reporting.py](../luxrisk/reporting.py#L163) | `export_pack` | Build a reproducible star-schema CSV pack and analytical brief for Power BI. |
| [warehouse.py](../luxrisk/warehouse.py#L17) | `Warehouse.__init__` | Remember where this project's SQLite ledger lives. |
| [warehouse.py](../luxrisk/warehouse.py#L32) | `Warehouse.initialize` | Create the ledger directory and tables if they do not exist. |
| [warehouse.py](../luxrisk/warehouse.py#L51) | `Warehouse.publish` | Append one successful multi-series vintage in a single SQL transaction. |
| [warehouse.py](../luxrisk/warehouse.py#L110) | `Warehouse.record_failure` | Append an unsuccessful attempt without altering published series. |
| [warehouse.py](../luxrisk/warehouse.py#L134) | `Warehouse.read_series` | Load one explicitly selected successful vintage and its provenance. |
| [warehouse.py](../luxrisk/warehouse.py#L191) | `Warehouse.vintages` | List successful run IDs for one series, newest first. |
| [warehouse.py](../luxrisk/warehouse.py#L221) | `Warehouse.coverage` | Report actual latest series availability rather than configured-country promises. |
