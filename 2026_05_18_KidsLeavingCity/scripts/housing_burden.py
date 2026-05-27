"""
Compute county-level housing burden (% of households paying ≥30% of income on
housing, owners + renters combined) for 2011 and 2023 from ACS 5-year PUMS.

Merge with our existing ΔPop_under18 (2011 → 2024) and county populations to
produce a scatter-ready dataset.

Output: data/housing_burden.csv
"""
from __future__ import annotations
from pathlib import Path
import duckdb
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
PUMS = "/Users/azizsunderji/Dropbox/Home Economics/Data/Reference/Microdata/ACS/acs_5year_all_windows.parquet"


def burden_by_county(year: int) -> pd.DataFrame:
    """Returns county × (pct_burdened, median_burden, n_households_weighted)."""
    sql = f"""
    WITH households AS (
        SELECT
            STATEFIP, COUNTYFIP, HHWT, HHINCOME, OWNERSHP, OWNCOST, RENTGRS, RENT
        FROM '{PUMS}'
        WHERE YEAR = {year}
          AND PERNUM = 1                    -- one record per household
          AND HHWT > 0
          AND HHINCOME > 0                  -- exclude undefined burden
          AND HHINCOME < 9999998             -- top-code sentinel
          AND OWNERSHP IN (1, 2)             -- owned or rented
          AND COUNTYFIP > 0                  -- skip suppressed counties
    ),
    with_burden AS (
        SELECT *,
            CASE
                WHEN OWNERSHP = 1 AND OWNCOST > 0 AND OWNCOST < 99999
                    THEN (OWNCOST * 12.0) / HHINCOME
                WHEN OWNERSHP = 2 AND RENTGRS > 0 AND RENTGRS < 99999
                    THEN (RENTGRS * 12.0) / HHINCOME
                ELSE NULL
            END AS burden
        FROM households
    )
    SELECT
        STATEFIP, COUNTYFIP,
        SUM(CASE WHEN burden IS NOT NULL THEN HHWT ELSE 0 END) AS hh_weighted,
        SUM(CASE WHEN burden >= 0.30 THEN HHWT ELSE 0 END) AS hh_burdened,
        SUM(CASE WHEN burden >= 0.50 THEN HHWT ELSE 0 END) AS hh_severely
    FROM with_burden
    GROUP BY 1, 2
    """
    df = duckdb.query(sql).df()
    df = df[df["hh_weighted"] > 0].copy()
    df["pct_burdened"] = df["hh_burdened"] / df["hh_weighted"] * 100
    df["pct_severely"] = df["hh_severely"] / df["hh_weighted"] * 100
    df["fips_5"] = df["STATEFIP"].astype(int).astype(str).str.zfill(2) \
                 + df["COUNTYFIP"].astype(int).astype(str).str.zfill(3)
    df["year"] = year
    return df[["fips_5", "year", "hh_weighted", "pct_burdened", "pct_severely"]]


def main():
    print("Computing housing burden 2011 (ACS 5-year 2007-2011)...")
    b2011 = burden_by_county(2011)
    print(f"  {len(b2011)} counties")
    print("Computing housing burden 2023 (ACS 5-year 2019-2023)...")
    b2023 = burden_by_county(2023)
    print(f"  {len(b2023)} counties")

    # Merge to one row per county with both years
    m = b2011.merge(b2023, on="fips_5", suffixes=("_2011", "_2023"), how="outer")
    m["pct_burdened_delta"] = m["pct_burdened_2023"] - m["pct_burdened_2011"]

    # Merge ΔPop_under18 from our existing decomposition
    dec = pd.read_csv(DATA / "decomposition.csv", dtype={"fips_5": str})
    dec["fips_5"] = dec["fips_5"].str.zfill(5)
    out = m.merge(
        dec[["fips_5", "msa_name_short", "County/County Equivalent",
             "pop_under18", "pop_under18_2024", "delta_under18"]],
        on="fips_5", how="left",
    )
    out["delta_under18_pct"] = out["delta_under18"] / out["pop_under18"] * 100
    out.to_csv(DATA / "housing_burden.csv", index=False)
    print(f"\nWrote {len(out)} rows → data/housing_burden.csv")

    # Quick sanity check — for our 142 counties only
    in_scope = out[out["msa_name_short"].notna()].copy()
    print(f"\nCounties in scope with burden + ΔPop: {in_scope.dropna(subset=['pct_burdened_2023','delta_under18_pct']).shape[0]}")
    print("\nTop 5 most burdened (2023):")
    cols = ["fips_5", "County/County Equivalent", "msa_name_short",
            "pct_burdened_2023", "pct_burdened_delta", "delta_under18_pct", "pop_under18"]
    print(in_scope.nlargest(5, "pct_burdened_2023")[cols].to_string(index=False))
    print("\nTop 5 biggest INCREASE in burden:")
    print(in_scope.nlargest(5, "pct_burdened_delta")[cols].to_string(index=False))


if __name__ == "__main__":
    main()
