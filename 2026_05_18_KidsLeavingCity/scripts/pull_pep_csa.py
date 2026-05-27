"""
Extract PEP under-18 stocks for our 199 CSA counties from cached state files.
"""
from __future__ import annotations
from pathlib import Path
import duckdb
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
CACHE = DATA / "pep_cache"


def main():
    counties = pd.read_csv(DATA / "csa_counties.csv", dtype={"fips_5": str, "state_fips": str})
    counties["fips_5"] = counties["fips_5"].str.zfill(5)
    states = sorted(counties["state_fips"].unique())
    print(f"States: {len(states)} — {', '.join(states)}")

    v19 = [str(CACHE / f"v2019-agesex-{s}.csv") for s in states if (CACHE / f"v2019-agesex-{s}.csv").exists()]
    v24 = [str(CACHE / f"v2024-syasex-{s}.csv") for s in states if (CACHE / f"v2024-syasex-{s}.csv").exists()]
    print(f"V2019 cached: {len(v19)}, V2024 cached: {len(v24)}")

    # V2019 YEAR=4 = July 1, 2011
    df11 = duckdb.query(f"""
        SELECT
            LPAD(CAST(STATE AS VARCHAR),2,'0') || LPAD(CAST(COUNTY AS VARCHAR),3,'0') AS fips_5,
            UNDER5_TOT AS age_0_4,
            AGE513_TOT AS age_5_13,
            AGE1417_TOT AS age_14_17,
            (UNDER5_TOT + AGE513_TOT + AGE1417_TOT) AS pop_under18
        FROM read_csv_auto({v19!r}, encoding='latin-1')
        WHERE YEAR = 4 AND SUMLEV = 50
    """).df()
    df11 = df11[df11["fips_5"].isin(counties["fips_5"])]
    print(f"2011 pop: {len(df11)} counties matched")

    # V2024 YEAR=6 = July 1, 2024. Some files have BOM that mangles column names —
    # read each file individually and concatenate.
    frames = []
    for fpath in v24:
        sub = duckdb.query(f"""
            SELECT
                LPAD(CAST(STATE AS VARCHAR),2,'0') || LPAD(CAST(COUNTY AS VARCHAR),3,'0') AS fips_5,
                SUM(CASE WHEN AGE BETWEEN 0 AND 17 THEN TOT_POP ELSE 0 END) AS pop_under18_2024
            FROM read_csv_auto('{fpath}', encoding='latin-1', header=True)
            WHERE YEAR = 6
            GROUP BY 1
        """).df()
        frames.append(sub)
    df24 = pd.concat(frames, ignore_index=True)
    df24 = df24[df24["fips_5"].isin(counties["fips_5"])]
    print(f"2024 pop: {len(df24)} counties matched")

    merged = (
        counties.merge(df11[["fips_5", "pop_under18"]], on="fips_5", how="left")
                .merge(df24[["fips_5", "pop_under18_2024"]], on="fips_5", how="left")
    )
    merged["delta_under18"] = merged["pop_under18_2024"] - merged["pop_under18"]
    merged["delta_pct"] = merged["delta_under18"] / merged["pop_under18"] * 100
    merged.to_csv(DATA / "csa_decomposition.csv", index=False)
    print(f"\nWrote csa_decomposition.csv — {len(merged)} counties")
    miss = merged["pop_under18"].isna().sum() + merged["pop_under18_2024"].isna().sum()
    print(f"Missing cells: {miss}")


if __name__ == "__main__":
    main()
