"""Single user entry point: diagnose, collect, inspect, compare, export and serve."""

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import cast

from luxrisk import __version__
from luxrisk.analysis import exposure_scenario
from luxrisk.catalog import COUNTRIES, INDICATORS
from luxrisk.connectors import SourceError
from luxrisk.demo import create_demo
from luxrisk.models import JsonObject, Mode
from luxrisk.pipeline import CollectionService
from luxrisk.reporting import compare_countries, export_pack, series_report
from luxrisk.warehouse import Warehouse


def doctor() -> JsonObject:
    """Diagnose runtime, SQLite and bundled resources without touching user data.

    Returns:
        Version, runtime, SQLite version, SQL/static presence and an overall boolean.

    Side effects:
        Reads package resources and runs an in-memory SQLite query; no network or filesystem writes.

    """
    root: Path = Path(__file__).parent
    resources: bool = all(
        (root / part).is_file()
        for part in ("sql/schema.sql", "static/index.html", "static/app.js", "static/style.css")
    )
    with sqlite3.connect(":memory:") as conn:
        sqlite_ok: bool = conn.execute("SELECT 1").fetchone()[0] == 1
    return {
        "version": __version__,
        "python": sys.version.split()[0],
        "sqlite": sqlite3.sqlite_version,
        "resources_ok": resources,
        "ok": resources and sqlite_ok and sys.version_info[:2] == (3, 12),
        "network_requests": 0,
        "user_data_written": False,
    }


def parser() -> argparse.ArgumentParser:
    """Declare commands in one place so the code follows the public help screen.

    Returns:
        Configured parser; does not read process arguments or execute operations.

    Side effects:
        None.

    """
    result: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="luxrisk", description="Traceable economic signals and exposure assumptions"
    )
    result.add_argument("--db", type=Path, default=Path("workspace/luxrisk.sqlite"))
    sub = result.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Check installation without collection")
    sub.add_parser("catalog", help="List definitions and configured countries")
    sub.add_parser("demo", help="Generate clearly labelled authored examples locally")
    collect = sub.add_parser("collect", help="Collect an explicit bounded official-source slice")
    collect.add_argument("--country", required=True)
    collect.add_argument("--indicators", default="inflation,unemployment")
    collect.add_argument("--start", required=True)
    collect.add_argument("--end", required=True)
    for name in ("inspect", "compare", "coverage", "export", "serve"):
        command = sub.add_parser(name)
        command.add_argument("--mode", choices=("demo", "live"), default="demo")
        if name in {"inspect", "compare"}:
            command.add_argument("--indicator", choices=tuple(INDICATORS), default="inflation")
        if name == "inspect":
            command.add_argument("--country", default="DE")
            command.add_argument("--run-id", type=int)
        if name == "compare":
            command.add_argument("--countries", default="DE,FR")
        if name == "export":
            command.add_argument("--output", type=Path, required=True)
        if name == "serve":
            command.add_argument("--port", type=int, default=8010)
    scenario = sub.add_parser("scenario")
    scenario.add_argument("--imports-usd", type=float, default=100_000)
    scenario.add_argument("--eurusd", type=float, required=True)
    scenario.add_argument("--fx-shock-pct", type=float, default=-10)
    scenario.add_argument("--debt-eur", type=float, default=500_000)
    scenario.add_argument("--rate-shock-bps", type=float, default=100)
    return result


def main() -> int:
    """Dispatch exactly one requested workflow with actionable errors.

    Returns:
        Process exit code 0 on success, 1 on handled operational errors or failed diagnosis.
        Argument syntax errors use argparse's exit code 2.

    Side effects:
        Prints JSON. Only demo/collect write SQLite; export creates a new CSV pack;
        serve starts a local read-only viewer. No collection runs implicitly.

    """
    args: argparse.Namespace = parser().parse_args()
    store: Warehouse = Warehouse(args.db)
    try:
        mode: Mode = cast(Mode, getattr(args, "mode", "demo"))
        output: JsonObject | list[JsonObject]
        if args.command == "doctor":
            output = doctor()
        elif args.command == "catalog":
            from dataclasses import asdict

            output = {
                "countries": COUNTRIES,
                "indicators": {name: asdict(spec) for name, spec in INDICATORS.items()},
            }
        elif args.command == "demo":
            output = {
                "run_id": create_demo(store),
                "mode": "demo",
                "label": "Authored illustration",
            }
        elif args.command == "collect":
            output = CollectionService(store).collect(
                args.country, args.indicators.split(","), args.start, args.end
            )
        elif args.command == "inspect":
            output = series_report(store, args.country, args.indicator, mode, args.run_id)
        elif args.command == "compare":
            output = compare_countries(store, args.countries.split(","), args.indicator, mode)
        elif args.command == "coverage":
            output = store.coverage(mode)
        elif args.command == "export":
            output = export_pack(store, mode, args.output)
        elif args.command == "scenario":
            output = exposure_scenario(
                args.imports_usd, args.eurusd, args.fx_shock_pct, args.debt_eur, args.rate_shock_bps
            )
        else:
            from luxrisk.api import serve

            serve(store, args.port, mode)
            return 0
        print(json.dumps(output, indent=2, ensure_ascii=False, allow_nan=False))
        return (
            1 if args.command == "doctor" and isinstance(output, dict) and not output["ok"] else 0
        )
    except (ValueError, SourceError, OSError, sqlite3.Error) as exc:
        print(f"LuxRisk: {exc}", file=sys.stderr)
        return 1
