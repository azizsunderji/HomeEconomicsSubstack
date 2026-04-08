#!/usr/bin/env python3
"""Build combined OECD net migration dataset from best available sources.

NET MIGRATION ONLY — no mixing with gross inflows.

Sources:
1. National stats offices for Anglosphere + key countries (back to 2000-2001)
   - US: CBO total net (incl. undocumented) 2001-2025, Census 2011-2017 fallback
   - Canada: StatCan (incl. NPRs) fiscal year, 2000-2025
   - UK: Eurostat CNMIGRAT 2000-2019 + ONS LTIM 2020-2025
   - Australia: ABS NOM (calendar year) 2000-2024
   - New Zealand: Stats NZ 2000-2025
   - Germany: Destatis 2018-2024 (Eurostat fills 2000-2017)
   - Spain: INE 2018-2024 (Eurostat fills 2000-2017)
   - Portugal, Netherlands, Switzerland, Sweden, Ireland: national 2018+ (Eurostat fills earlier)
2. Eurostat CNMIGRAT for all other European OECD (2000-2024)

Countries without net migration data (JPN/KOR/ISR/TUR/MEX/CHL/COL/CRI) are EXCLUDED.

Output: data/oecd_immigration_net.csv
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
HOUSING_DATA = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_03_31_HousingHappiness/data")
MIG_PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_03_29_GlobalMigrationCrackdown")

ISO3_TO_NAME = {
    "AUS": "Australia", "AUT": "Austria", "BEL": "Belgium", "BGR": "Bulgaria",
    "CAN": "Canada", "CHE": "Switzerland", "CYP": "Cyprus", "CZE": "Czechia",
    "DEU": "Germany", "DNK": "Denmark", "ESP": "Spain", "EST": "Estonia",
    "FIN": "Finland", "FRA": "France", "GBR": "United Kingdom", "GRC": "Greece",
    "HRV": "Croatia", "HUN": "Hungary", "ISL": "Iceland", "IRL": "Ireland",
    "ITA": "Italy", "LTU": "Lithuania", "LUX": "Luxembourg", "LVA": "Latvia",
    "MLT": "Malta", "NLD": "Netherlands", "NOR": "Norway", "NZL": "New Zealand",
    "POL": "Poland", "PRT": "Portugal", "ROU": "Romania", "SVK": "Slovakia",
    "SVN": "Slovenia", "SWE": "Sweden", "USA": "United States",
}

ANGLOPHONE = ["USA", "CAN", "GBR", "AUS", "NZL", "IRL"]


def load_wb_population():
    pop = pd.read_csv(HOUSING_DATA / "wb_population_all.csv")
    pop = pop[pop["iso3"].str.len() == 3]
    d = {}
    for _, r in pop.iterrows():
        d[(r["iso3"], int(r["year"]))] = r["population"]
    return d


def get_pop(iso3, year, pop_dict):
    p = pop_dict.get((iso3, year))
    if not p:
        for off in [1, -1, 2, -2]:
            p = pop_dict.get((iso3, year + off))
            if p:
                break
    return p


def load_eurostat_all():
    """Load Eurostat CNMIGRAT for all countries including UK."""
    es = pd.read_csv(HOUSING_DATA / "eurostat_cnmigrat.csv")

    ES_TO_ISO3 = {
        'AT': 'AUT', 'BE': 'BEL', 'BG': 'BGR', 'CZ': 'CZE', 'CY': 'CYP',
        'DK': 'DNK', 'EE': 'EST', 'FI': 'FIN', 'FR': 'FRA', 'DE': 'DEU',
        'EL': 'GRC', 'HR': 'HRV', 'HU': 'HUN', 'IS': 'ISL', 'IE': 'IRL',
        'IT': 'ITA', 'LV': 'LVA', 'LT': 'LTU', 'LU': 'LUX', 'MT': 'MLT',
        'NL': 'NLD', 'NO': 'NOR', 'PL': 'POL', 'PT': 'PRT', 'RO': 'ROU',
        'SK': 'SVK', 'SI': 'SVN', 'ES': 'ESP', 'SE': 'SWE', 'CH': 'CHE',
    }

    rows = []
    for _, r in es.iterrows():
        geo = r["geo"]
        iso3 = ES_TO_ISO3.get(geo)
        if iso3 and pd.notna(r["OBS_VALUE"]):
            rows.append((iso3, int(r["TIME_PERIOD"]), int(r["OBS_VALUE"]),
                         "Eurostat CNMIGRAT", "net"))

    # UK from separate fetch (2000-2019)
    uk_eurostat = {
        2000: 143871, 2001: 172928, 2002: 199267, 2003: 208001,
        2004: 255377, 2005: 298425, 2006: 276579, 2007: 300810,
        2008: 256010, 2009: 237267, 2010: 266730, 2011: 217012,
        2012: 166308, 2013: 242448, 2014: 295122, 2015: 350177,
        2016: 286367, 2017: 280428, 2018: 256931, 2019: 270352,
    }
    for yr, val in uk_eurostat.items():
        rows.append(("GBR", yr, val, "Eurostat CNMIGRAT", "net"))

    return pd.DataFrame(rows, columns=["iso3", "year", "value", "source", "metric"])


def load_national_stats():
    """Load national stats office data — used to OVERRIDE Eurostat for recent years."""
    rows = []

    # --- US: CBO total net immigration (incl. undocumented), 2001-2025 ---
    # Full annual series from CBO Jan 2024 Demographic Outlook + Jan 2025/Sep 2025 revisions
    # Includes LPR+, INA Nonimmigrants, and Other Foreign Nationals (undocumented)
    cbo = pd.read_csv(DATA / "cbo_net_immigration_by_category.csv")
    for _, r in cbo.iterrows():
        rows.append(("USA", int(r["year"]), int(r["total_net_immigration"]) * 1000,
                      "CBO", "net_total"))

    # --- Canada: StatCan fiscal year (mapped to calendar year label) ---
    statcan = {
        2000: 236760, 2001: 237935, 2002: 183749, 2003: 194146,
        2004: 200175, 2005: 216100, 2006: 219751, 2007: 250003,
        2008: 269208, 2009: 262804, 2010: 231005, 2011: 260557,
        2012: 260834, 2013: 247302, 2014: 176890, 2015: 303739,
        2016: 319990, 2017: 426077, 2018: 447470, 2019: 327749,
        2020: 148869, 2021: 670698, 2022: 1078729, 2023: 1181967,
        2024: 355095,
    }
    for yr, val in statcan.items():
        rows.append(("CAN", yr, val, "Statistics Canada", "net_incl_npr"))

    # --- UK: ONS LTIM 2020-2025 (Eurostat covers 2000-2019) ---
    ons = {
        2020: 111000, 2021: 251000, 2022: 681000, 2023: 924000,
        2024: 649000, 2025: 204000,
    }
    for yr, val in ons.items():
        rows.append(("GBR", yr, val, "ONS LTIM", "net"))

    # --- Australia: ABS NOM (calendar year) ---
    abs_nom = {
        2000: 111441, 2001: 136076, 2002: 110475, 2003: 110104,
        2004: 106425, 2005: 137009, 2006: 182196, 2007: 244020,
        2008: 315690, 2009: 246890, 2010: 172040, 2011: 206230,
        2012: 240260, 2013: 208370, 2014: 182340, 2015: 186750,
        2016: 243840, 2017: 241660, 2018: 252210, 2019: 247620,
        2020: -4970, 2021: 9310, 2022: 437860, 2023: 530620,
        2024: 329935,
    }
    for yr, val in abs_nom.items():
        rows.append(("AUS", yr, val, "ABS NOM", "net"))

    # --- New Zealand: Stats NZ (year ended June) ---
    statsnz = {
        2000: -9800, 2001: -9300, 2002: 32800, 2003: 42500,
        2004: 22000, 2005: 8600, 2006: 10700, 2007: 10100,
        2008: 4700, 2009: 12500, 2010: 16500, 2011: 3900,
        2012: -3200, 2013: 7900, 2014: 33500, 2015: 53400,
        2016: 64600, 2017: 59500, 2018: 49000, 2019: 52100,
        2020: 84800, 2021: -6600, 2022: -17700, 2023: 108400,
        2024: 70400, 2025: 13700,
    }
    for yr, val in statsnz.items():
        rows.append(("NZL", yr, val, "Stats NZ", "net"))

    # --- Recent national overrides for European countries (2018+) ---
    national_recent = {
        "DEU": ({2018: 399680, 2019: 327060, 2020: 220251, 2021: 329163,
                 2022: 1462089, 2023: 662964, 2024: 430183}, "Destatis"),
        "ESP": ({2018: 334158, 2019: 454232, 2020: 219357, 2021: 191094,
                 2022: 727005, 2023: 642296, 2024: 626268}, "INE"),
        "PRT": ({2018: 23757, 2019: 67113, 2020: 57768, 2021: 72079,
                 2022: 136194, 2023: 155701, 2024: 143641}, "Eurostat/INE"),
        "NLD": ({2018: 86371, 2019: 108035, 2020: 68359, 2021: 107198,
                 2022: 223798, 2023: 137366, 2024: 107768, 2025: 94686}, "CBS"),
        "CHE": ({2018: 39634, 2019: 43114, 2020: 54548, 2021: 50039,
                 2022: 68648, 2023: 138671, 2024: 80333}, "BFS/Eurostat"),
        "SWE": ({2018: 85621, 2019: 68087, 2020: 33581, 2021: 51947,
                 2022: 58955, 2023: 21080, 2024: 29748}, "SCB"),
        "IRL": ({2018: 44400, 2019: 44000, 2020: 44700, 2021: 21800,
                 2022: 51700, 2023: 77600, 2024: 79300, 2025: 59700}, "CSO"),
    }
    for iso3, (vals, src) in national_recent.items():
        for yr, val in vals.items():
            rows.append((iso3, yr, val, src, "net"))

    return pd.DataFrame(rows, columns=["iso3", "year", "value", "source", "metric"])


def main():
    pop_dict = load_wb_population()

    eurostat = load_eurostat_all()
    national = load_national_stats()

    # For countries with national data: use national, fill earlier years from Eurostat
    # For countries with Eurostat only: use Eurostat throughout

    national_countries = national["iso3"].unique()
    eurostat_only = eurostat[~eurostat["iso3"].isin(national_countries)]

    # Build combined: start with Eurostat for all countries
    # Then override with national where available
    combined_rows = []

    for iso3 in sorted(set(list(eurostat["iso3"].unique()) + list(national["iso3"].unique()))):
        nat = national[national["iso3"] == iso3].set_index("year")
        eur = eurostat[eurostat["iso3"] == iso3].set_index("year")

        # Get all years from both
        all_years = sorted(set(list(nat.index) + list(eur.index)))

        for yr in all_years:
            if yr in nat.index:
                # National overrides Eurostat
                r = nat.loc[yr]
                if isinstance(r, pd.DataFrame):
                    r = r.iloc[0]
                combined_rows.append((iso3, yr, r["value"], r["source"], r["metric"]))
            elif yr in eur.index:
                r = eur.loc[yr]
                if isinstance(r, pd.DataFrame):
                    r = r.iloc[0]
                combined_rows.append((iso3, yr, r["value"], r["source"], r["metric"]))

    combined = pd.DataFrame(combined_rows, columns=["iso3", "year", "value", "source", "metric"])

    # Add per-capita rate
    combined["rate_per1000"] = combined.apply(
        lambda r: r["value"] / get_pop(r["iso3"], int(r["year"]), pop_dict) * 1000
        if get_pop(r["iso3"], int(r["year"]), pop_dict) else np.nan, axis=1
    )
    combined["country"] = combined["iso3"].map(ISO3_TO_NAME)
    combined = combined.sort_values(["iso3", "year"]).reset_index(drop=True)

    # Save
    out_path = DATA / "oecd_immigration_net.csv"
    combined.to_csv(out_path, index=False)

    print(f"Saved {out_path}")
    print(f"  {len(combined)} rows, {combined['iso3'].nunique()} countries")
    print(f"  Year range: {combined['year'].min()}–{combined['year'].max()}")

    # Summary
    print(f"\n{'Country':<20} {'Source(s)':<30} {'Years':>12} {'Latest':>10}")
    print("-" * 75)
    for iso3 in sorted(combined["iso3"].unique()):
        sub = combined[combined["iso3"] == iso3]
        sources = sub["source"].unique()
        src_str = " + ".join(sources[:2])
        if len(sources) > 2:
            src_str += f" +{len(sources)-2}"
        yr_range = f"{sub['year'].min()}–{sub['year'].max()}"
        latest = sub.sort_values("year").iloc[-1]
        rate = f"{latest['rate_per1000']:.1f}"
        name = ISO3_TO_NAME.get(iso3, iso3)
        anglo = " *" if iso3 in ANGLOPHONE else ""
        print(f"{name:<20} {src_str:<30} {yr_range:>12} {rate:>10}{anglo}")

    print(f"\n* = Anglophone")
    print(f"\nTotal OECD countries with net migration: {combined['iso3'].nunique()}")


if __name__ == "__main__":
    main()
