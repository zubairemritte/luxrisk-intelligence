"""SQLite vintage ledger: immutable source bytes and atomic successful publication."""

import hashlib
import json
import sqlite3
from contextlib import closing
from dataclasses import asdict
from pathlib import Path

from luxrisk.catalog import indicator_spec
from luxrisk.models import JsonObject, Mode, SourceBatch, utc_now


class Warehouse:
    """Own one local ledger path; construction never opens or creates the database."""

    def __init__(self, path: Path) -> None:
        """Remember where this project's SQLite ledger lives.

        Args:
            path: Writable local path; reads require an existing ledger.

        Returns:
            None; stores the path without touching the filesystem.

        Side effects:
            None.

        """
        self.path: Path = path

    def initialize(self) -> None:
        """Create the ledger directory and tables if they do not exist.

        Returns:
            None; existing rows and raw bytes are preserved.

        Raises:
            OSError: Directory cannot be created.
            sqlite3.Error: SQLite cannot open or initialize the schema.

        Side effects:
            Creates a directory and database when absent; enables foreign-key constraints.

        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        schema: str = Path(__file__).with_name("sql").joinpath("schema.sql").read_text()
        with closing(sqlite3.connect(self.path)) as conn:
            conn.executescript(schema)

    def publish(self, batches: tuple[SourceBatch, ...], mode: Mode, note: str) -> int:
        """Append one successful multi-series vintage in a single SQL transaction.

        Args:
            batches: Already-validated source batches; at least one row per batch.
            mode: demo or live, kept separate in every read.
            note: Short run description, not a claim about economic performance.

        Returns:
            Monotonically increasing run ID used to reproduce this exact vintage.

        Raises:
            ValueError: Batch is empty or mode is invalid.
            sqlite3.IntegrityError: Duplicate series/period keys violate the ledger contract.
            sqlite3.Error: Commit fails; the entire transaction rolls back.

        Side effects:
            Initializes storage if necessary; inserts metadata, exact payload bytes and observations.
            Never updates or deletes an existing vintage.

        """
        if (
            not batches
            or mode not in {"demo", "live"}
            or any(not batch.observations for batch in batches)
        ):
            raise ValueError("Publish at least one nonempty batch in demo or live mode")
        self.initialize()
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute("PRAGMA foreign_keys=ON")
            cursor: sqlite3.Cursor = conn.execute(
                "INSERT INTO collection(mode,collected_at,status,note) VALUES (?,?,?,?)",
                (mode, utc_now(), "success", note),
            )
            assert cursor.lastrowid is not None
            run_id: int = cursor.lastrowid
            for batch in batches:
                conn.execute(
                    "INSERT INTO raw_response VALUES (?,?,?,?,?,?,?,?)",
                    (
                        run_id,
                        batch.country,
                        batch.indicator,
                        batch.url,
                        batch.retrieved_at,
                        hashlib.sha256(batch.payload).hexdigest(),
                        batch.payload,
                        json.dumps(asdict(indicator_spec(batch.indicator))),
                    ),
                )
                conn.executemany(
                    "INSERT INTO observation VALUES (?,?,?,?,?,?)",
                    [
                        (run_id, row.country, row.indicator, row.period, row.value, row.status)
                        for row in batch.observations
                    ],
                )
            return run_id

    def record_failure(self, mode: Mode, error: str) -> None:
        """Append an unsuccessful attempt without altering published series.

        Args:
            mode: Requested analytical mode.
            error: Diagnostic message, limited to 500 characters in the ledger.

        Returns:
            None; creates an audit entry with no raw or observation rows.

        Raises:
            sqlite3.Error: The failure record itself cannot be committed.

        Side effects:
            Initializes storage and appends a failed collection. Last successful vintages remain selected.

        """
        self.initialize()
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute(
                "INSERT INTO collection(mode,collected_at,status,note) VALUES (?,?,?,?)",
                (mode, utc_now(), "failed", error[:500]),
            )

    def read_series(
        self, country: str, indicator: str, mode: Mode, run_id: int | None = None
    ) -> JsonObject:
        """Load one explicitly selected successful vintage and its provenance.

        Args:
            country: Country/entity code, including EA for the shared exchange rate.
            indicator: Catalogue ID.
            mode: Isolated demo or live cohort.
            run_id: Exact successful vintage; None chooses the latest for this series.

        Returns:
            Dictionary with rows, source definition, hash, URL, timestamps and run_id;
            an empty rows list when the series is not collected.

        Raises:
            FileNotFoundError: The ledger does not exist.
            sqlite3.Error: The ledger cannot be read.

        Side effects:
            Opens SQLite read-only; never creates, changes or refreshes data.

        """
        if not self.path.is_file():
            raise FileNotFoundError(
                "No ledger yet. Run 'luxrisk demo' or collect a small live slice."
            )
        with closing(sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
            conn.row_factory = sqlite3.Row
            raw: sqlite3.Row | None = conn.execute(
                "SELECT r.*,c.mode,c.collected_at FROM raw_response r JOIN collection c USING(run_id) "
                "WHERE r.country=? AND r.indicator=? AND c.mode=? AND c.status='success' "
                "AND (? IS NULL OR r.run_id=?) ORDER BY r.run_id DESC LIMIT 1",
                (country, indicator, mode, run_id, run_id),
            ).fetchone()
            if raw is None:
                return {"rows": [], "mode": mode, "country": country, "indicator": indicator}
            rows: list[JsonObject] = [
                dict(row)
                for row in conn.execute(
                    "SELECT period,value,status FROM observation WHERE run_id=? AND country=? AND indicator=? ORDER BY period",
                    (raw["run_id"], country, indicator),
                )
            ]
            return {
                "rows": rows,
                "mode": mode,
                "country": country,
                "indicator": indicator,
                "run_id": raw["run_id"],
                "collected_at": raw["collected_at"],
                "retrieved_at": raw["retrieved_at"],
                "url": raw["url"],
                "sha256": raw["sha256"],
                "definition": json.loads(raw["definition_json"]),
            }

    def vintages(self, country: str, indicator: str, mode: Mode) -> list[int]:
        """List successful run IDs for one series, newest first.

        Args:
            country: Country or EA entity.
            indicator: Catalogue ID.
            mode: demo or live, never mixed.

        Returns:
            Run IDs usable with read_series; empty when storage is absent.

        Raises:
            sqlite3.Error: An existing ledger cannot be queried.

        Side effects:
            Read-only access with no database creation.

        """
        if not self.path.is_file():
            return []
        with closing(sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
            return [
                row[0]
                for row in conn.execute(
                    "SELECT r.run_id FROM raw_response r JOIN collection c USING(run_id) "
                    "WHERE r.country=? AND r.indicator=? AND c.mode=? AND c.status='success' ORDER BY r.run_id DESC",
                    (country, indicator, mode),
                )
            ]

    def coverage(self, mode: Mode) -> list[JsonObject]:
        """Report actual latest series availability rather than configured-country promises.

        Args:
            mode: Analytical cohort to inspect.

        Returns:
            One row per available series, including missing-cell counts and retrieval time.

        Raises:
            sqlite3.Error: An existing database cannot be queried.

        Side effects:
            Read-only query; returns an empty list before first publication.

        """
        if not self.path.is_file():
            return []
        with closing(sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
            conn.row_factory = sqlite3.Row
            return [
                dict(row)
                for row in conn.execute(
                    "SELECT l.country,l.indicator,l.run_id,r.retrieved_at,MIN(o.period) AS first_period,"
                    "MAX(o.period) AS last_period,COUNT(*) AS periods,COUNT(o.value) AS values_present "
                    "FROM latest_series l JOIN raw_response r USING(run_id,country,indicator) "
                    "JOIN observation o USING(run_id,country,indicator) WHERE l.mode=? "
                    "GROUP BY l.country,l.indicator,l.run_id ORDER BY l.country,l.indicator",
                    (mode,),
                )
            ]
