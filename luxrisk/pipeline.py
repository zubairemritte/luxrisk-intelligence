"""One collection workflow: fetch, validate, publish; failed attempts preserve prior results."""

from luxrisk.catalog import country_code, indicator_spec
from luxrisk.connectors import ECBConnector, EurostatConnector
from luxrisk.models import JsonObject, Observation, SourceBatch
from luxrisk.warehouse import Warehouse


def validate_batch(batch: SourceBatch) -> None:
    """Check normalized identity, frequency, uniqueness and sensible mathematical ranges.

    Args:
        batch: One adapter result with exact source bytes and observation rows.

    Returns:
        None when all contracts pass, including at least one usable observation.

    Raises:
        ValueError: Identity, unit-domain, frequency or duplicate-key checks fail.

    Side effects:
        None; an unusual inflation or GDP value is not discarded by an arbitrary plausibility band.

    """
    spec = indicator_spec(batch.indicator)
    seen: set[str] = set()
    if (
        not batch.payload
        or not batch.observations
        or all(row.value is None for row in batch.observations)
    ):
        raise ValueError("Empty source payload or no usable observations")
    expected_country: str = "EA" if batch.indicator == "eurusd" else country_code(batch.country)
    for row in batch.observations:
        if (
            row.indicator != spec.id
            or row.country != expected_country
            or batch.country != expected_country
        ):
            raise ValueError("Batch and observation identities differ")
        if ("Q" in row.period) != (spec.frequency == "Q") or row.period in seen:
            raise ValueError("Wrong frequency or duplicate observation period")
        seen.add(row.period)
        if row.value is not None:
            if spec.id == "unemployment" and not 0 <= row.value <= 100:
                raise ValueError("Unemployment percentage lies outside 0..100")
            if spec.id == "eurusd" and row.value <= 0:
                raise ValueError("An exchange rate must be positive")


class CollectionService:
    """Coordinate the two source adapters and one ledger; keep analytics outside ingestion."""

    def __init__(
        self,
        warehouse: Warehouse,
        eurostat: EurostatConnector | None = None,
        ecb: ECBConnector | None = None,
    ) -> None:
        """Assemble dependencies without contacting providers.

        Args:
            warehouse: Storage owner used only after a complete validation pass.
            eurostat: Optional injectable statistical adapter.
            ecb: Optional injectable exchange-rate adapter.

        Returns:
            None; stores three collaborators.

        Side effects:
            None.

        """
        self.warehouse: Warehouse = warehouse
        self.eurostat: EurostatConnector = eurostat or EurostatConnector()
        self.ecb: ECBConnector = ecb or ECBConnector()

    def collect(self, country: str, indicators: list[str], start: str, end: str) -> JsonObject:
        """Collect an explicit small set, committing all requested slices atomically.

        Args:
            country: Configured country; eurusd is always stored once as entity EA.
            indicators: One to four unique IDs of the same frequency.
            start: First monthly or quarterly period, inclusive.
            end: Final matching period, inclusive.

        Returns:
            Run ID, source-batch count and total normalized observations.

        Raises:
            ValueError: Request or normalized data violates a contract.
            SourceError: A provider is unavailable or its response differs from the catalogue.
            sqlite3.Error: Storage cannot commit.

        Side effects:
            Bounded provider requests, then one atomic ledger write. On failure, records a
            diagnostic attempt and re-raises; no requested series is partially replaced.

        """
        country = country_code(country)
        if not 1 <= len(indicators) <= 4 or len(set(indicators)) != len(indicators):
            raise ValueError("Request 1-4 unique indicator IDs")
        specs = [indicator_spec(name) for name in indicators]
        if len({spec.frequency for spec in specs}) != 1:
            raise ValueError("Collect monthly and quarterly series in separate commands")
        try:
            batches: list[SourceBatch] = []
            for spec in specs:
                batch: SourceBatch = (
                    self.ecb.collect(start, end)
                    if spec.provider == "ECB"
                    else self.eurostat.collect(spec.id, country, start, end)
                )
                validate_batch(batch)
                if any(not start <= row.period <= end for row in batch.observations):
                    raise ValueError("Provider returned observations outside the requested window")
                batches.append(batch)
            run_id: int = self.warehouse.publish(
                tuple(batches), "live", f"Explicit {start} to {end} slice"
            )
            return {
                "run_id": run_id,
                "batches": len(batches),
                "observations": sum(len(batch.observations) for batch in batches),
            }
        except Exception as exc:
            self.warehouse.record_failure("live", str(exc))
            raise


def rows_to_observations(
    rows: list[JsonObject], country: str, indicator: str
) -> tuple[Observation, ...]:
    """Convert stored dictionary rows into typed analysis inputs.

    Args:
        rows: Ledger rows with period, value and source status.
        country: Entity to attach, resolved by the caller.
        indicator: Shared catalogue ID.

    Returns:
        Validated immutable observations, preserving nulls and flags.

    Raises:
        KeyError: Required ledger fields are absent.
        ValueError: Observation validation fails.

    Side effects:
        None; this is the only stored-row conversion helper.

    """
    return tuple(
        Observation(country, indicator, row["period"], row["value"], row["status"]) for row in rows
    )
