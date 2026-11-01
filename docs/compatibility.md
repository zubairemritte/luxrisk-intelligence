# Compatibility and dependency policy

## One supported baseline

CPython **3.12**, 64-bit; Poetry **2.5.1**. The project intentionally restricts its Python range to `>=3.12,<3.13`, matching the tested baseline rather than implying every Python version is supported.

There are **zero third-party runtime dependencies**. The application uses Python's bundled SQLite, urllib, dataclasses, HTTP server, statistics and CSV libraries. You do not need a database server, C/C++ compiler, Node, Docker or cloud account to run it.

| Role | Exact version / owner |
| --- | --- |
| Python minor | 3.12; interpreter managed outside the package |
| Poetry CLI | 2.5.1, installed separately |
| Build backend | `poetry-core==2.5.0` |
| pytest | 9.2.0 |
| Ruff | 0.17.3 |
| mypy | 2.4.1 |
| Transitive developer dependencies | Exact versions and artifact hashes in `poetry.lock` |

`pyproject.toml` is the single dependency declaration. `poetry.lock` is the single resolved dependency lock. There is no parallel requirements file with a competing version list. `poetry sync` reproduces the lock; `poetry update` is a deliberate maintenance operation, followed by the compatibility checks.

Development tools can use platform-specific wheels even though the runtime is standard-library-only. Lock resolution and available wheel metadata do not prove installation succeeded on a platform. Treat actual CI results as evidence.

## Four validated compatibility profiles

The workflow configures Linux x64, Windows x64, macOS Apple Silicon and macOS Intel with Python 3.12. Each installs locked development dependencies, diagnoses bundled files, checks types/style and runs the same tiny authored tests. It also builds a wheel and inspects packaged SQL/static resources.

**All four profiles passed in [GitHub Actions run 41308917902](https://github.com/zubairemritte/luxrisk-intelligence/actions/runs/41308917902).** This includes the locked installation, 21 small authored tests, strict types/style and wheel build on implementation commit `9098d61c35da0cc68fcb95133c8278c4435ee70b`. See [release evidence](release-0.1.0.md). These results validate the listed profiles, not every possible machine or network configuration.

The same commands work in PowerShell, Terminal and Bash through Poetry; use the full Python executable path if version discovery differs. Unicode/space paths, SQLite availability, antivirus locks, proxies, corporate TLS certificates and unavailable providers remain environmental factors, not guarantees made by a lockfile.

## Maintenance procedure

1. Change versions together in `pyproject.toml` only when necessary.
2. Resolve `poetry.lock`, sync a fresh environment and run `poetry check --lock`.
3. Run the authored test suite, strict types, Ruff and wheel-resource check.
4. Wait for all four remote profiles; record actual results and any excluded platform.
5. Keep the prior source/lock pair available for reproduction.

No zero-crash guarantee is made for every possible computer, OS version or proxy. The supported baseline and evidence are explicit.
