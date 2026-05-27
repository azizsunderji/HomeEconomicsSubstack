"""
Build U.S. under-18 county × decade panel, 1950-2020.

Reads NHGIS decennial extracts (already on disk in data/nhgis0122 and data/nhgis0123).

For each decade, sums the age-specific columns covering ages 0-17 (no interpolation
needed — each decade has detailed enough breakdowns to give exact under-18).

Output: data/under18_by_county_decade.csv
  columns: state_fips, county_fips, county_name, state_name, year, under18, total_pop

NHGIS county GISJOIN format: G + STATE(3) + 0 + COUNTY(3) + 0 — e.g. G3600610 = NY (36), Manhattan (061)
"""
from pathlib import Path
import duckdb
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"

NHGIS_122 = DATA / "nhgis0122" / "nhgis0122_csv"
NHGIS_123 = DATA / "nhgis0123" / "nhgis0123_csv"

# Each year: (csv_path, age_columns_under18, sex_or_persons_total_col_name_or_None)
# For Sex-by-Age tables, total under-18 = sum(male under-18) + sum(female under-18).
SPECS = {
    1950: {
        "csv":   NHGIS_122 / "nhgis0122_ds83_1950_county.csv",
        "under18_cols": [f"B1Y{n:03d}" for n in range(1, 11)],   # ages 0-17 (no sex split in this table)
    },
    1960: {
        "csv":   NHGIS_122 / "nhgis0122_ds90_1960_county.csv",
        "under18_cols": [f"B5L{n:03d}" for n in range(1, 19)],   # single ages 0-17
    },
    1970: {
        "csv":   NHGIS_122 / "nhgis0122_ds94_1970_county.csv",
        "under18_cols": [f"CBT{n:03d}" for n in range(1, 10)] + [f"CBT{n:03d}" for n in range(23, 32)],  # M 001-009 + F 023-031
    },
    1980: {
        "csv":   NHGIS_122 / "nhgis0122_ds104_1980_county.csv",
        "under18_cols": [f"C68{n:03d}" for n in range(1, 12)] + [f"C68{n:03d}" for n in range(27, 38)],  # M 001-011 + F 027-037
    },
    1990: {
        "csv":   NHGIS_123 / "nhgis0123_ds120_1990_county.csv",
        "under18_cols": [f"ET3{n:03d}" for n in range(1, 13)],   # ages 0-17 (persons total)
    },
    2000: {
        "csv":   NHGIS_122 / "nhgis0122_ds146_2000_county.csv",
        "under18_cols": [f"FMZ{n:03d}" for n in range(1, 5)] + [f"FMZ{n:03d}" for n in range(24, 28)],
    },
    2010: {
        "csv":   NHGIS_122 / "nhgis0122_ds172_2010_county.csv",
        "under18_cols": [f"H76{n:03d}" for n in range(3, 7)] + [f"H76{n:03d}" for n in range(27, 31)],
    },
    2020: {
        "csv":   NHGIS_122 / "nhgis0122_ds258_2020_county.csv",
        "under18_cols": [f"U7S{n:03d}" for n in range(3, 7)] + [f"U7S{n:03d}" for n in range(27, 31)],
    },
}


def fips_from_gisjoin(gj: str) -> str:
    """NHGIS GISJOIN for a county is 'G' + state(2) + '0' + county(3) + '0'.
    e.g. G0100010 → state=01, county=001 → FIPS '01001'."""
    return gj[1:3] + gj[4:7]


def load_year(year: int, spec: dict) -> pd.DataFrame:
    cols = spec["under18_cols"]
    csv = spec["csv"]

    # First, inspect the actual columns so we can be tolerant of variations.
    head = duckdb.query(f"SELECT * FROM read_csv_auto('{csv}', sample_size = 5) LIMIT 1").df()
    available = set(head.columns)
    missing = [c for c in cols if c not in available]
    if missing:
        # Some 1950/older codebooks use code with "5" prefix instead — try uppercasing or check.
        print(f"  WARN {year}: missing columns {missing[:5]} ... (have {len(available)} cols)")

    cols_used = [c for c in cols if c in available]
    sum_expr = " + ".join([f'COALESCE("{c}", 0)' for c in cols_used])

    q = f"""
    SELECT GISJOIN, STATE, COUNTY, STATEA, COUNTYA, ({sum_expr}) AS under18
    FROM read_csv_auto('{csv}', sample_size = 100000)
    """
    df = duckdb.query(q).df()
    df["year"] = year
    df["county_fips"] = df["GISJOIN"].apply(fips_from_gisjoin)
    df = df.rename(columns={"STATE": "state_name", "COUNTY": "county_name"})
    df = df[["county_fips", "state_name", "county_name", "year", "under18"]]
    return df


def main():
    frames = []
    for year, spec in SPECS.items():
        if not spec["csv"].exists():
            print(f"  SKIP {year}: {spec['csv']} not found")
            continue
        print(f"  loading {year}: {spec['csv'].name}")
        df = load_year(year, spec)
        print(f"    {len(df):,} counties, total under-18 = {df['under18'].sum()/1e6:.1f}M")
        frames.append(df)

    panel = pd.concat(frames, ignore_index=True)
    panel.to_csv(DATA / "under18_by_county_decade.csv", index=False)

    # Pivot for inspection
    pivot = panel.pivot_table(index="year", values="under18", aggfunc="sum") / 1e6
    print("\nUnder-18 total by decade (millions):")
    print(pivot.round(2))
    print(f"\nWrote {DATA / 'under18_by_county_decade.csv'} — {len(panel):,} rows")


if __name__ == "__main__":
    main()
