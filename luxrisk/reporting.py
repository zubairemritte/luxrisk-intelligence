"""One reporting layer shared by CLI, local HTTP viewer and portable BI exports."""

import csv
import json
import shutil
import tempfile
from dataclasses import asdict
from pathlib import Path

from luxrisk.analysis import anomaly_signal, evaluate_forecast, revision_diff, summarize
from luxrisk.catalog import COUNTRIES, INDICATORS, country_code, indicator_spec
from luxrisk.models import JsonObject, Mode, Observation, period_end
from luxrisk.pipeline import rows_to_observations
from luxrisk.warehouse import Warehouse


def series_report(
    store: Warehouse, country: str, indicator: str, mode: Mode, run_id: int | None = None
) -> JsonObject:
    """Assemble one traceable indicator panel without duplicating its calculations.

    Args:
        store: Read-only ledger access owner.
        country: Configured country; EURUSD transparently resolves to shared entity EA.
        indicator: Catalogue ID.
        mode: demo or live.
        run_id: Optional exact vintage. Revisions compare with its immediate predecessor.

    Returns:
        Source evidence, stored rows, summary, anomaly rule, baseline evaluation and revisions.
        Empty series stay visibly unavailable.

    Raises:
        ValueError: Country, indicator or mode is invalid.
        FileNotFoundError: No ledger exists.

    Side effects:
        Read-only SQLite access; never triggers collection or overwrites files.

    """
    code: str = country_code(country)
    spec = indicator_spec(indicator)
    if mode not in {"demo", "live"}:
        raise ValueError("Choose demo or live")
    entity: str = "EA" if indicator == "eurusd" else code
    data: JsonObject = store.read_series(entity, indicator, mode, run_id)
    rows: tuple[Observation, ...] = rows_to_observations(data["rows"], entity, indicator)
    versions: list[int] = store.vintages(entity, indicator, mode)
    selected: int | None = data.get("run_id")
    changes: list[JsonObject] = []
    if selected in versions and versions.index(selected) + 1 < len(versions):
        prior: JsonObject = store.read_series(
            entity, indicator, mode, versions[versions.index(selected) + 1]
        )
        changes = revision_diff(rows_to_observations(prior["rows"], entity, indicator), rows)
    return data | {
        "requested_country": code,
        "shared_context": entity == "EA",
        "catalogue": asdict(spec),
        "summary": summarize(rows),
        "anomaly": anomaly_signal(rows, 8 if spec.frequency == "Q" else 12),
        "forecast": evaluate_forecast(rows, min_train=8 if spec.frequency == "Q" else 12),
        "vintages": versions,
        "revisions": changes,
    }


def compare_countries(
    store: Warehouse, countries: list[str], indicator: str, mode: Mode
) -> JsonObject:
    """Compare peers at the most recent common nonmissing period, without forward fill.

    Args:
        store: Ledger holding successful vintages.
        countries: Between two and six distinct configured countries.
        indicator: A national indicator; shared EURUSD is not a peer ranking.
        mode: Isolated demo or live cohort.

    Returns:
        Common period, unit, values and exact vintage IDs; unavailable when no overlap exists.

    Raises:
        ValueError: Peer selection or catalogue ID is invalid, or vintage definitions differ.
        FileNotFoundError: Ledger does not exist.

    Side effects:
        Read-only queries. Does not force all countries to share an ingestion timestamp.

    """
    codes: list[str] = [country_code(code) for code in countries]
    spec = indicator_spec(indicator)
    if indicator == "eurusd" or not 2 <= len(codes) <= 6 or len(set(codes)) != len(codes):
        raise ValueError("Choose 2-6 distinct peers and a national indicator")
    datasets: list[JsonObject] = [store.read_series(code, indicator, mode) for code in codes]
    if any(not data["rows"] for data in datasets):
        return {
            "available": False,
            "reason": "At least one peer has no collected series in this mode",
        }
    definitions: set[str] = {json.dumps(data["definition"], sort_keys=True) for data in datasets}
    if len(definitions) != 1:
        raise ValueError(
            "Vintage indicator definitions differ; collect comparable definitions first"
        )
    maps: list[dict[str, float]] = [
        {row["period"]: row["value"] for row in data["rows"] if row["value"] is not None}
        for data in datasets
    ]
    common: set[str] = set(maps[0]).intersection(*(set(mapping) for mapping in maps[1:]))
    if not common:
        return {"available": False, "reason": "No common nonmissing period across selected peers"}
    period: str = max(common)
    return {
        "available": True,
        "period": period,
        "indicator": indicator,
        "unit": spec.unit,
        "peers": [
            {
                "country": code,
                "name": COUNTRIES[code],
                "value": mapping[period],
                "run_id": data["run_id"],
                "retrieved_at": data["retrieved_at"],
            }
            for code, mapping, data in zip(codes, maps, datasets, strict=True)
        ],
    }


def write_csv(path: Path, columns: list[str], rows: list[JsonObject]) -> None:
    """Write a UTF-8 BI table with stable headers and safe spreadsheet text cells.

    Args:
        path: Destination within the caller's temporary export directory.
        columns: Ordered field names.
        rows: Dictionaries; absent/None fields serialize as empty cells.

    Returns:
        None; finite numeric values remain numeric, with dot decimal separators.

    Raises:
        OSError: Destination cannot be written.
        ValueError: A row contains a field not listed in columns.

    Side effects:
        Writes one file. Formula-leading text is prefixed with an apostrophe for Excel safety.

    """
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer: csv.DictWriter[str] = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            safe: JsonObject = {
                key: "'" + value
                if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r"))
                else value
                for key, value in row.items()
            }
            writer.writerow(safe)


def export_pack(store: Warehouse, mode: Mode, destination: Path) -> JsonObject:
    """Build a reproducible star-schema CSV pack and analytical brief for Power BI.

    Args:
        store: Local ledger; only available latest successful series are exported.
        mode: demo or live, kept separate.
        destination: New directory path. An existing path is refused to prevent accidental loss.

    Returns:
        Destination, series count and fact-row count. Manifest pins every exported run ID.

    Raises:
        ValueError: No series exist or mode is invalid.
        FileExistsError: Destination already exists.
        OSError: A file cannot be created or the final rename fails.

    Side effects:
        Builds in a sibling temporary directory, then renames it into place. Cleans partial
        output after an error; does not mutate SQLite or create a Power BI account/report.

    """
    if mode not in {"demo", "live"}:
        raise ValueError("Choose demo or live")
    if destination.exists():
        raise FileExistsError("Choose a new export directory to preserve the previous pack")
    coverage: list[JsonObject] = store.coverage(mode)
    if not coverage:
        raise ValueError("No successful series available for this mode")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp: Path = Path(tempfile.mkdtemp(prefix="luxrisk-export-", dir=destination.parent))
    try:
        facts: list[JsonObject] = []
        sources: list[JsonObject] = []
        brief: list[str] = [
            "# LuxRisk analytical brief",
            f"\nMode: **{mode}**. No investment recommendation or official rating.\n",
        ]
        for item in coverage:
            report: JsonObject = series_report(
                store,
                "DE" if item["country"] == "EA" else item["country"],
                item["indicator"],
                mode,
                item["run_id"],
            )
            series_key: str = item["country"] + ":" + item["indicator"]
            sources.append(
                {
                    "series_key": series_key,
                    "country": item["country"],
                    "indicator": item["indicator"],
                    "run_id": report["run_id"],
                    "retrieved_at": report["retrieved_at"],
                    "sha256": report["sha256"],
                    "url": report["url"],
                    "mode": mode,
                }
            )
            for row in report["rows"]:
                facts.append(
                    {
                        "series_key": series_key,
                        "country": item["country"],
                        "indicator": item["indicator"],
                        "run_id": report["run_id"],
                        "period": row["period"],
                        "period_end": str(period_end(row["period"])),
                        "value": row["value"],
                        "status": row["status"],
                        "mode": mode,
                    }
                )
            summary: JsonObject = report["summary"]
            brief.append(
                f"- {series_key}: {summary.get('value')} {summary.get('unit')} in {summary.get('period')}; vintage {report['run_id']}; stale={summary.get('stale')}."
            )
        write_csv(
            temp / "fact_observation.csv",
            [
                "series_key",
                "country",
                "indicator",
                "run_id",
                "period",
                "period_end",
                "value",
                "status",
                "mode",
            ],
            facts,
        )
        write_csv(
            temp / "dim_source.csv",
            [
                "series_key",
                "country",
                "indicator",
                "run_id",
                "retrieved_at",
                "sha256",
                "url",
                "mode",
            ],
            sources,
        )
        write_csv(
            temp / "dim_indicator.csv",
            ["indicator", "title", "frequency", "unit", "definition"],
            [
                {
                    "indicator": spec.id,
                    "title": spec.title,
                    "frequency": spec.frequency,
                    "unit": spec.unit,
                    "definition": spec.definition,
                }
                for spec in INDICATORS.values()
            ],
        )
        write_csv(
            temp / "dim_geography.csv",
            ["country", "name"],
            [
                {"country": code, "name": name}
                for code, name in (COUNTRIES | {"EA": "Shared euro currency context"}).items()
            ],
        )
        (temp / "manifest.json").write_text(
            json.dumps({"mode": mode, "sources": sources, "rows": len(facts)}, indent=2),
            encoding="utf-8",
        )
        (temp / "analytical_brief.md").write_text("\n".join(brief), encoding="utf-8")
        temp.rename(destination)
        return {"destination": str(destination), "series": len(sources), "observations": len(facts)}
    except Exception:
        shutil.rmtree(temp, ignore_errors=True)
        raise
