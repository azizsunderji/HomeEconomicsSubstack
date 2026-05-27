"""
Build an ACS 1-year time series of NET migration of children (under 18) from
inner counties to outer counties of each MSA, year-by-year (2005-2024, except
2020 which ACS didn't release).

For each (MSA, survey_year):
  inner_to_outer_kids = SUM(PERWT) for kids who currently live in an OUTER
                        county and lived in an INNER county 1 year ago
  outer_to_inner_kids = mirror
  net = inner_to_outer - outer_to_inner

Output: data/acs_kid_migration_ts.csv
"""
from __future__ import annotations
from pathlib import Path
import duckdb
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
F = "/Users/azizsunderji/Dropbox/Home Economics/Data/Reference/Microdata/ACS/acs_5year_all_windows.parquet"
# Note: each YEAR is the END YEAR of a 5-year window (e.g., YEAR=2023 = 2019-2023).
# PERWT in 5-year files = annual-equivalent (avg over the 5-year window).

INNER = {
    "New York-Newark-Jersey City, NY-NJ": [(36, 5), (36, 47), (36, 61), (36, 81), (36, 85)],
    "Los Angeles-Long Beach-Anaheim, CA": [(6, 37)],
    "Chicago-Naperville-Elgin, IL-IN": [(17, 31)],
    "Dallas-Fort Worth-Arlington, TX": [(48, 113), (48, 439)],
    "Houston-The Woodlands-Sugar Land, TX": [(48, 201)],
    "Atlanta-Sandy Springs-Roswell, GA": [(13, 121), (13, 89)],
    "Washington-Arlington-Alexandria, DC-VA-MD-WV": [(11, 1), (51, 13), (51, 510)],
    "Philadelphia-Camden-Wilmington, PA-NJ-DE-MD": [(42, 101)],
    "Phoenix-Mesa-Chandler, AZ": [(4, 13)],
    "Austin-Round Rock-San Marcos, TX": [(48, 453)],
    "Charlotte-Concord-Gastonia, NC-SC": [(37, 119)],
    # Miami excluded — Miami-Dade COUNTYFIP suppressed in PUMS
}


def main():
    counties = pd.read_csv(DATA / "counties_in_scope.csv", dtype=str)
    counties["s"] = counties["state_fips"].astype(int)
    counties["cf"] = counties["county_fips"].astype(int)

    rows = []
    for msa, inner_pairs in INNER.items():
        inner_set = set(inner_pairs)
        msa_pairs = set(zip(
            counties[counties["msa_name_short"] == msa]["s"],
            counties[counties["msa_name_short"] == msa]["cf"],
        ))
        outer_set = msa_pairs - inner_set
        if not outer_set:
            continue
        inner_tup = ",".join([f"({s},{c})" for s, c in inner_set])
        outer_tup = ",".join([f"({s},{c})" for s, c in outer_set])

        # Outflow only — kids who lived in an inner county 1 year ago and moved
        # somewhere else (anywhere, not just within MSA). Destination doesn't
        # matter for the "pace of families leaving city centers" question.
        sql = f"""
        WITH kids AS (
            SELECT YEAR, AGE, PERWT, STATEFIP, COUNTYFIP, MIGPLAC1, MIGCOUNTY1, MIGRATE1
            FROM '{F}'
            WHERE AGE < 18 AND PERWT > 0 AND MIGRATE1 IN (3, 4)
        )
        SELECT
            YEAR,
            SUM(CASE WHEN (MIGPLAC1, MIGCOUNTY1) IN ({inner_tup})
                THEN PERWT ELSE 0 END) AS kids_leaving_inner,
            SUM(CASE WHEN (STATEFIP, COUNTYFIP) IN ({inner_tup})
                THEN PERWT ELSE 0 END) AS kids_arriving_inner
        FROM kids
        GROUP BY YEAR
        ORDER BY YEAR
        """
        df = duckdb.query(sql).df()
        df["msa"] = msa
        rows.append(df)
        df["net_kid_outflow"] = df["kids_leaving_inner"] - df["kids_arriving_inner"]
        print(f"  {msa[:40]:42s}  years: {df.shape[0]:>3}, mean leaving: "
              f"{int(df['kids_leaving_inner'].mean()):>6}, mean net out: {int(df['net_kid_outflow'].mean()):>6}")

    out = pd.concat(rows, ignore_index=True)
    out["net_kid_outflow"] = out["kids_leaving_inner"] - out["kids_arriving_inner"]
    out = out[["YEAR", "msa", "kids_leaving_inner", "kids_arriving_inner", "net_kid_outflow"]]
    out.to_csv(DATA / "acs_kid_migration_ts.csv", index=False)
    print(f"\nWrote {len(out)} rows → data/acs_kid_migration_ts.csv")


if __name__ == "__main__":
    main()
