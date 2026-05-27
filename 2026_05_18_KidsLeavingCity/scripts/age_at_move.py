"""
For each of our 12 MSAs, tabulate the age distribution of children who moved
from the MSA's "inner" county/counties to its "outer" counties in the past year.

Uses IPUMS ACS 5-year PUMS (latest window = YEAR=2023, covering 2019-2023).
Inter-county moves (MIGRATE1 IN (3,4)). Weighted by PERWT.

Output: data/age_at_move.csv with rows of (msa, age, inner_to_outer, outer_to_inner, total_in_msa).
       outputs/age_at_move_*.html — one chart per MSA showing age distribution.
"""
from __future__ import annotations
from pathlib import Path
import json
import duckdb
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OUTPUTS = PROJECT / "outputs"
DL = Path("/Users/azizsunderji/Dropbox/Home Economics/Data")
PUMS = DL / "Reference" / "Microdata" / "ACS" / "acs_5year_all_windows.parquet"

# Inner-county definition per MSA: which counties are the "core" / "central city"
# Everything else in the MSA's county list is "outer".
INNER = {
    "New York-Newark-Jersey City, NY-NJ": [
        (36, 5), (36, 47), (36, 61), (36, 81), (36, 85),   # 5 boroughs
    ],
    "Los Angeles-Long Beach-Anaheim, CA": [
        (6, 37),   # LA County
    ],
    "Chicago-Naperville-Elgin, IL-IN": [
        (17, 31),  # Cook County
    ],
    "Dallas-Fort Worth-Arlington, TX": [
        (48, 113), (48, 439),  # Dallas County + Tarrant County (Fort Worth)
    ],
    "Houston-The Woodlands-Sugar Land, TX": [
        (48, 201),  # Harris County
    ],
    "Atlanta-Sandy Springs-Roswell, GA": [
        (13, 121), (13, 89),   # Fulton + DeKalb
    ],
    "Washington-Arlington-Alexandria, DC-VA-MD-WV": [
        (11, 1), (51, 13), (51, 510),  # DC + Arlington VA + Alexandria city
    ],
    "Philadelphia-Camden-Wilmington, PA-NJ-DE-MD": [
        (42, 101),  # Philadelphia County
    ],
    "Miami-Fort Lauderdale-Pompano Beach, FL": [
        (12, 86),   # Miami-Dade
    ],
    "Phoenix-Mesa-Chandler, AZ": [
        (4, 13),    # Maricopa
    ],
    "Austin-Round Rock-San Marcos, TX": [
        (48, 453),  # Travis
    ],
    "Charlotte-Concord-Gastonia, NC-SC": [
        (37, 119),  # Mecklenburg
    ],
}


def main():
    counties = pd.read_csv(DATA / "counties_in_scope.csv", dtype=str)
    counties["state_fips"] = counties["state_fips"].astype(int)
    counties["county_fips"] = counties["county_fips"].astype(int)

    rows = []

    for msa, inner_pairs in INNER.items():
        msa_counties = counties[counties["msa_name_short"] == msa]
        if msa_counties.empty:
            print(f"SKIP {msa} — no counties found")
            continue

        inner_set = set(inner_pairs)
        all_set = set(zip(msa_counties["state_fips"], msa_counties["county_fips"]))
        outer_set = all_set - inner_set

        if not outer_set:
            print(f"SKIP {msa} — no outer counties")
            continue

        def state_county_tuples_sql(pairs):
            return ",".join([f"({s},{c})" for s, c in pairs])

        inner_tup = state_county_tuples_sql(inner_set)
        outer_tup = state_county_tuples_sql(outer_set)

        sql = f"""
        WITH kids AS (
            SELECT AGE, PERWT,
                   STATEFIP, COUNTYFIP,
                   MIGPLAC1, MIGCOUNTY1,
                   MIGRATE1
            FROM '{PUMS}'
            WHERE YEAR = 2023
              AND AGE < 18
              AND PERWT > 0
              AND MIGRATE1 IN (2, 3, 4)
        )
        SELECT
            AGE,
            SUM(CASE WHEN
                (MIGPLAC1, MIGCOUNTY1) IN ({inner_tup})
              AND (STATEFIP, COUNTYFIP) IN ({outer_tup})
            THEN PERWT ELSE 0 END) AS inner_to_outer,
            SUM(CASE WHEN
                (MIGPLAC1, MIGCOUNTY1) IN ({outer_tup})
              AND (STATEFIP, COUNTYFIP) IN ({inner_tup})
            THEN PERWT ELSE 0 END) AS outer_to_inner,
            SUM(CASE WHEN
                (MIGPLAC1, MIGCOUNTY1) IN ({inner_tup})
              AND (STATEFIP, COUNTYFIP) IN ({inner_tup})
              AND MIGRATE1 = 3
            THEN PERWT ELSE 0 END) AS inner_to_inner_diff_county,
            SUM(CASE WHEN
                (STATEFIP, COUNTYFIP) IN ({inner_tup})
              AND MIGRATE1 = 1
            THEN PERWT ELSE 0 END) AS inner_nonmovers,
            SUM(CASE WHEN
                (STATEFIP, COUNTYFIP) IN ({outer_tup})
              AND MIGRATE1 = 1
            THEN PERWT ELSE 0 END) AS outer_nonmovers
        FROM kids
        GROUP BY AGE
        ORDER BY AGE
        """
        df = duckdb.query(sql).df()
        df["msa"] = msa
        rows.append(df)

        i2o_total = df["inner_to_outer"].sum()
        o2i_total = df["outer_to_inner"].sum()
        print(f"  {msa[:40]:42s}  inner→outer kids/yr={int(i2o_total):>6}  outer→inner={int(o2i_total):>6}")

    out = pd.concat(rows, ignore_index=True)
    out.to_csv(DATA / "age_at_move.csv", index=False)
    print(f"\nWrote {len(out)} rows → data/age_at_move.csv")


if __name__ == "__main__":
    main()
