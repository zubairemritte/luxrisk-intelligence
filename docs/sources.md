# Source register

Reviewed **1 November 2026**. These are official statistical sources, with explicit series selections. No generic website scraping, broker feed or private financial account is used.

## Eurostat

Provider: European Commission, Eurostat. [API introduction](https://ec.europa.eu/eurostat/en/web/user-guides/data-browser/api-data-access/api-introduction), [statistics API guide](https://ec.europa.eu/eurostat/en/web/user-guides/data-browser/api-data-access/api-getting-started/api), [reuse terms](https://ec.europa.eu/eurostat/help/copyright-notice).

Endpoint: `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}`. Format: JSON-stat 2.0. The connector requests one country and explicit time bounds, and checks singleton dimensions before normalization. The public API needs no credential. Its current dataset can contain revisions; do not assume historical vintages are available from this endpoint.

| ID | Dataset | Exact series filters | Interpretation |
| --- | --- | --- | --- |
| inflation | [`prc_hicp_manr`](https://ec.europa.eu/eurostat/databrowser/view/prc_hicp_manr/default/table) | `freq=M, coicop=CP00, unit=RCH_A` | All-items HICP annual rate of change |
| unemployment | [`une_rt_m`](https://ec.europa.eu/eurostat/databrowser/view/une_rt_m/default/table) | `freq=M, s_adj=SA, age=TOTAL, sex=T, unit=PC_ACT` | Total-age, total-sex unemployment percentage of labour force |
| gdp | [`namq_10_gdp`](https://ec.europa.eu/eurostat/databrowser/view/namq_10_gdp/default/table) | `freq=Q, s_adj=SCA, unit=CLV_PCH_PRE, na_item=B1GQ` | Real GDP percentage change on preceding quarter |

The unemployment provider age code is **TOTAL**, verified against the live structure; a plausible-looking `Y15-74` selector currently returns an empty age dimension. This project checks the actual source labels rather than silently replacing an empty response. See [Eurostat's unemployment metadata](https://ec.europa.eu/eurostat/cache/metadata/en/une_esms.htm) for the population definition and comparability caveats.

Country is a `geo` query parameter. Sixteen country codes are configured, but this is not a claim that all three series exist for every country/window. Missing observations and flags remain visible; wholly unusable responses do not replace an older success.

Reuse: statistical reuse is permitted with source acknowledgement, subject to Eurostat's stated exceptions. Exports retain dataset query, retrieval date and a fingerprint. Derived calculations and display changes are the responsibility of the project author, not Eurostat. Logos are not used as endorsements.

## ECB

Provider: European Central Bank. [API overview](https://data.ecb.europa.eu/help/api/overview), [data query documentation](https://data.ecb.europa.eu/help/api/data), [query examples](https://data.ecb.europa.eu/help/api/data-examples), [statistics reuse policy](https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/html/usage_policy.en.html), [disclaimer and copyright](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html).

Endpoint: `https://data-api.ecb.europa.eu/service/data/EXR/M.USD.EUR.SP00.A?format=csvdata&startPeriod=...&endPeriod=...`.

The connector checks monthly frequency, USD numerator, EUR denominator, reference-rate type, average suffix, USD unit and unit multiplier 0. The result is **USD per EUR**, not EUR per USD. It belongs to entity **EA / shared euro currency context**. Selecting a country does not create a national rate. No API key is required.

Reuse: acknowledge the ECB and keep the applicable data terms and disclaimer with redistributed statistics. Derived scenarios are project calculations, with no ECB endorsement. A reference rate is not an executable transaction quote.

## Request and retention policy

- Only adapter-generated HTTPS URLs on the two official providers are accepted.
- 20-second request timeout, 8 MB response limit, at most two transport attempts.
- A Retry-After delay above two seconds stops the attempt; the caller retries later.
- User supplies a bounded period window, at most 20 years. No automatic country loop runs during installation, tests or page load.
- Exact original bytes are stored locally alongside SHA-256, URL, ingestion time and the immutable series definition used.
- Source contract failures create an unsuccessful audit attempt while earlier successful vintages remain available.

## Small source probes and authored fixtures

The development checks distinguish official three-month/two-quarter source probes from authored automated-test fixtures. The [probe manifest](../examples/official-probe-manifest.json) records actual request URLs, hashes and row counts. It does not claim a full data collection, historical review or pan-European coverage.

Automated tests under `tests/fixtures/` are deliberately authored examples and are never presented as provider statistics. Full demo generation and full official collection remain explicit user-run commands.
