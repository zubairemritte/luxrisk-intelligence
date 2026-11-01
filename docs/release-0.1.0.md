# Release evidence: 0.1.0

Prepared **1 November 2026**. Evidence distinguishes local checks from the separately executed GitHub compatibility matrix.

## Executed locally

| Check | Result | Scope |
| --- | --- | --- |
| Poetry resolution and `check --lock` | Passed | Exact direct versions plus transitive artifact hashes |
| Locked installation and `pip check` | Passed | Local Linux x64, CPython 3.12.14 |
| `luxrisk doctor` | Passed | SQLite and packaged SQL/static resources, no collection |
| Ruff lint and format | Passed | Source and small authored tests |
| Strict mypy | Passed | 11 application modules |
| Authored tests | **21 passed** | Tiny fixtures and temporary ledgers; 0 live-provider requests |
| Small actual-source adapter probes | **11 observations validated** | Inflation 3, unemployment 3, quarterly GDP 2, EURUSD 3; [query/hash manifest](../examples/official-probe-manifest.json) |
| Local browser review | Passed | 32 authored UI rows, Chromium desktop and 390 px mobile; no JS errors or horizontal page overflow |
| Interactive checks | Passed | Two baseline rows, common-period peers, scenario result, empty-state clearing |
| Source/wheel packaging | Passed | Build plus bundled SQL, HTML, CSS and JavaScript verification |
| Isolated wheel smoke check | Passed | Fresh runtime-only environment and a filesystem path containing spaces |

Source functions/methods have documented contracts and explicit parameter/return annotations; the complete [function index](function-index.md) follows actual definitions. Four operational classes own the collection/storage workflow; supporting records and the internal HTTP handler are explained separately.

## Remote compatibility checks passed

| Profile | Runtime | Status |
| --- | --- | --- |
| Linux x64 / Ubuntu 24.04 | Python 3.12 | Passed: locked installation, diagnosis, type/style checks, 21 small tests and wheel build |
| Windows x64 / Windows 2022 | Python 3.12 | Passed: locked installation, diagnosis, type/style checks, 21 small tests and wheel build |
| macOS Apple Silicon / macOS 14 | Python 3.12 | Passed: locked installation, diagnosis, type/style checks, 21 small tests and wheel build |
| macOS Intel / macOS 15 | Python 3.12 | Passed: locked installation, diagnosis, type/style checks, 21 small tests and wheel build |

All four profiles completed successfully in [GitHub Actions run 41308917902](https://github.com/zubairemritte/luxrisk-intelligence/actions/runs/41308917902), on implementation commit `9098d61c35da0cc68fcb95133c8278c4435ee70b`. This validates these runner/runtime profiles, not every possible local OS or network configuration.

## Deliberately not executed or claimed

- No full authored demo generation, full-country ingestion or long provider history.
- No cloud deployment or scheduled public collection.
- No historical anomaly-review precision, crisis probabilities or model business impact.
- No reconstruction of historical publication vintages from revised data.
- No native Power BI `.pbix` report or tenant-specific authoring validation.

The personal French PDF is delivered separately and is not part of public project files. No synthetic value is presented as an observed official statistic.
