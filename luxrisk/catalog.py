"""One catalogue for indicator definitions, source filters and configured countries."""

from luxrisk.models import Indicator

COUNTRIES: dict[str, str] = {
    "AT": "Austria",
    "BE": "Belgium",
    "CH": "Switzerland",
    "CZ": "Czechia",
    "DE": "Germany",
    "DK": "Denmark",
    "ES": "Spain",
    "FI": "Finland",
    "FR": "France",
    "IE": "Ireland",
    "IT": "Italy",
    "LU": "Luxembourg",
    "NL": "Netherlands",
    "NO": "Norway",
    "PL": "Poland",
    "SE": "Sweden",
}
INDICATORS: dict[str, Indicator] = {
    "inflation": Indicator(
        "inflation",
        "Consumer price inflation",
        "Eurostat",
        "prc_hicp_manr",
        "M",
        "% year-on-year",
        "All-items harmonised consumer price annual rate; not a price index.",
        (("freq", "M"), ("coicop", "CP00"), ("unit", "RCH_A")),
        65,
    ),
    "unemployment": Indicator(
        "unemployment",
        "Unemployment rate",
        "Eurostat",
        "une_rt_m",
        "M",
        "% of labour force",
        "Total sex, age 15-74, seasonally adjusted unemployment rate.",
        (("freq", "M"), ("s_adj", "SA"), ("age", "TOTAL"), ("sex", "T"), ("unit", "PC_ACT")),
        95,
    ),
    "gdp": Indicator(
        "gdp",
        "Real GDP growth",
        "Eurostat",
        "namq_10_gdp",
        "Q",
        "% quarter-on-quarter",
        "Chain-linked volume GDP change on previous quarter, seasonally and calendar adjusted.",
        (("freq", "Q"), ("s_adj", "SCA"), ("unit", "CLV_PCH_PRE"), ("na_item", "B1GQ")),
        160,
    ),
    "eurusd": Indicator(
        "eurusd",
        "Euro / US dollar",
        "ECB",
        "EXR/M.USD.EUR.SP00.A",
        "M",
        "USD per EUR",
        "Monthly average euro reference rate; shared currency context, not a national indicator.",
        (
            ("FREQ", "M"),
            ("CURRENCY", "USD"),
            ("CURRENCY_DENOM", "EUR"),
            ("EXR_TYPE", "SP00"),
            ("EXR_SUFFIX", "A"),
        ),
        65,
    ),
}


def indicator_spec(indicator: str) -> Indicator:
    """Resolve a public indicator ID to its canonical contract.

    Args:
        indicator: One of inflation, unemployment, gdp or eurusd.

    Returns:
        An immutable metadata record shared by collection, validation and presentation.

    Raises:
        ValueError: The identifier is unknown.

    Side effects:
        None.

    """
    if indicator not in INDICATORS:
        raise ValueError(f"Unknown indicator: {indicator}; choose {', '.join(INDICATORS)}")
    return INDICATORS[indicator]


def country_code(country: str) -> str:
    """Normalize and validate a country filter without claiming provider coverage.

    Args:
        country: A configured two-letter code; surrounding whitespace is ignored.

    Returns:
        An uppercase code.

    Raises:
        ValueError: Country is not in the configured European catalogue.

    Side effects:
        None; provider availability is checked by the actual response.

    """
    code: str = country.strip().upper()
    if code not in COUNTRIES:
        raise ValueError(f"Choose a configured country: {', '.join(COUNTRIES)}")
    return code
