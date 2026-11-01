# Power BI handoff

This release produces a validated-shape CSV model and a recipe. A native `.pbix` report has **not** been authored or visually validated. The local web viewer runs on macOS; Power BI Desktop requires a compatible Windows environment. Power BI Service capabilities depend on the workspace and account, so this document does not promise a particular browser authoring workflow.

## Export

```bash
poetry run luxrisk export --mode live --output exports/official-pack-01
```

Use a new destination each time. The resulting pack contains four UTF-8 CSV tables, a source manifest and a Markdown analytical brief. Missing values are empty numeric cells. `period_end` is an ISO calendar date for either month end or quarter end; `period` preserves its original label.

| Table | Grain / key | Purpose |
| --- | --- | --- |
| `fact_observation` | One row per `series_key, period` in the selected exported vintage | Values, source flags, period/date, mode and run ID |
| `dim_indicator` | `indicator` | Title, unit, frequency and exact meaning |
| `dim_geography` | `country` | Configured country names plus EA shared FX context |
| `dim_source` | `series_key` | Selected run ID, retrieval time, query URL and raw-response hash |

The manifest pins all run IDs used. Country series can have different ingestion timestamps; they are not claimed to be one simultaneous economic release. Exporting again later does not change an existing pack.

## Relationships and types

Load CSVs with comma delimiter, UTF-8 and dot-decimal numeric locale. Set `value` to Decimal Number, `period_end` to Date and IDs to Text except run_id (Whole Number). Set source URL category to Web URL. Create one-to-many, single-direction relationships:

- `dim_indicator[indicator]` → `fact_observation[indicator]`
- `dim_geography[country]` → `fact_observation[country]`
- `dim_source[series_key]` → `fact_observation[series_key]`

Keep `dim_source` disconnected from the other dimensions to avoid ambiguous paths. Facts must not be joined to source metadata by `run_id` alone because a run can contain multiple series. Use `series_key`.

## Measures: never sum percentage rates across time/countries

These measures are supplied as an authoring recipe; validate them in your Power BI environment. They return blank when country/indicator is ambiguous.

```dax
Selected Observation =
IF (
    HASONEVALUE ( dim_geography[country] ) &&
    HASONEVALUE ( dim_indicator[indicator] ) &&
    HASONEVALUE ( fact_observation[period] ),
    SELECTEDVALUE ( fact_observation[value] )
)

Latest Usable Period =
IF (
    HASONEVALUE ( dim_geography[country] ) &&
    HASONEVALUE ( dim_indicator[indicator] ),
    CALCULATE (
        MAX ( fact_observation[period_end] ),
        FILTER ( fact_observation, NOT ISBLANK ( fact_observation[value] ) )
    )
)

Latest Observed Value =
VAR LastDate = [Latest Usable Period]
RETURN
IF (
    NOT ISBLANK ( LastDate ),
    CALCULATE (
        SELECTEDVALUE ( fact_observation[value] ),
        fact_observation[period_end] = LastDate
    )
)
```

The latest measure respects the current filter context. It does not enforce a common peer date; use a single explicit common-period slicer for peer charts, matching the period reported by `luxrisk compare`. Monthly and quarterly metrics must have separate visuals or an explicit frequency filter. Disable default sums on the value column.

## Suggested pages

1. **Indicator desk:** country and indicator slicers; single observed value, unit, period, line chart with original values.
2. **Peer comparison:** one indicator and one explicitly common period; country comparison with units and coverage exclusions.
3. **Evidence:** source URL, query window, ingestion date, fingerprint, flags and missing cells. Explain EA as shared context.

The Python-generated analytical brief and JSON report hold forecast/anomaly evidence. Those are not silently recomputed with unrelated DAX rules.
