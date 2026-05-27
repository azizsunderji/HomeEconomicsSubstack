"""
Pull Census PEP files for the 2011 baseline and 2024 endpoint.

2011 baseline: PEP V2019 cc-est2019-agesex-XX.csv
  - 5-year age brackets: UNDER5, AGE513, AGE1417 sum to under-18
  - For our 13-year window (2011→2024), aged-out cohort = AGE513 + AGE1417

2024 endpoint: PEP V2024 cc-est2024-syasex-XX.csv
  - Single year of age — sum AGE 0..17 for under-18 total

YEAR code lookup:
  V2019: YEAR=3 = July 1, 2011 (YEAR=1 is 4/1/2010 base, 2=7/1/2010, 3=7/1/2011, ...)
  V2024: YEAR=6 = July 1, 2024 (YEAR=1 is 4/1/2020 base, 2=7/1/2020, ..., 6=7/1/2024)
"""
from __future__ import annotations

import io
import urllib.request
from pathlib import Path

import duckdb
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
PEP_CACHE = DATA / "pep_cache"
PEP_CACHE.mkdir(exist_ok=True)

V2019_URL = "https://www2.census.gov/programs-surveys/popest/datasets/2010-2019/counties/asrh/cc-est2019-agesex-{state}.csv"
V2024_URL = "https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/asrh/cc-est2024-syasex-{state}.csv"


def states_in_scope() -> list[str]:
    counties = pd.read_csv(DATA / "counties_in_scope.csv", dtype=str)
    counties["state_fips"] = counties["state_fips"].str.zfill(2)
    return sorted(counties["state_fips"].unique())


def download(url: str, dest: Path, retries: int = 4) -> Path:
    if dest.exists() and dest.stat().st_size > 1000:
        return dest
    last_err = None
    for attempt in range(retries):
        try:
            print(f"  downloading {url} (attempt {attempt+1})")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=180) as r:
                data = r.read()
            dest.write_bytes(data)
            return dest
        except Exception as e:
            last_err = e
            print(f"    ↳ failed: {e}; backing off")
            import time as _t
            _t.sleep(5 * (attempt + 1))
    raise RuntimeError(f"download failed after {retries} attempts: {last_err}")


def pull_v2019(states):
    """Returns DataFrame: fips_5, under5, age513, age1417, year=2011."""
    files = []
    for s in states:
        f = PEP_CACHE / f"v2019-agesex-{s}.csv"
        try:
            download(V2019_URL.format(state=s), f)
            files.append(f)
        except Exception as e:
            print(f"  WARN state {s} V2019: {e}")
    print(f"  V2019 files: {len(files)}")
    sql = f"""
        SELECT
            LPAD(CAST(STATE AS VARCHAR), 2, '0') || LPAD(CAST(COUNTY AS VARCHAR), 3, '0') AS fips_5,
            UNDER5_TOT AS under5,
            AGE513_TOT AS age_5_13,
            AGE1417_TOT AS age_14_17
        FROM read_csv_auto({[str(f) for f in files]!r})
        WHERE YEAR = 4
          AND SUMLEV = 50
    """
    df = duckdb.query(sql).df()
    df["pop_under18"] = df["under5"] + df["age_5_13"] + df["age_14_17"]
    df["aged_out_5_17"] = df["age_5_13"] + df["age_14_17"]
    df["year"] = 2011
    return df


def pull_v2024(states):
    """Returns DataFrame: fips_5, pop_under18_2024."""
    files = []
    for s in states:
        f = PEP_CACHE / f"v2024-syasex-{s}.csv"
        try:
            download(V2024_URL.format(state=s), f)
            files.append(f)
        except Exception as e:
            print(f"  WARN state {s} V2024: {e}")
    print(f"  V2024 files: {len(files)}")
    sql = f"""
        SELECT
            LPAD(CAST(STATE AS VARCHAR), 2, '0') || LPAD(CAST(COUNTY AS VARCHAR), 3, '0') AS fips_5,
            SUM(CASE WHEN AGE BETWEEN 0 AND 17 THEN TOT_POP ELSE 0 END) AS pop_under18_2024
        FROM read_csv_auto({[str(f) for f in files]!r})
        WHERE YEAR = 6
          AND SUMLEV = 50
        GROUP BY 1
    """
    return duckdb.query(sql).df()


def main():
    states = states_in_scope()
    print(f"States in scope: {len(states)} — {', '.join(states)}")

    counties = pd.read_csv(DATA / "counties_in_scope.csv", dtype=str)
    counties["fips_5"] = counties["fips_5"].str.zfill(5)
    scope_fips = set(counties["fips_5"])
    print(f"Counties in scope: {len(scope_fips)}")

    print("\n--- V2019 (2011 baseline) ---")
    df2011 = pull_v2019(states)
    df2011 = df2011[df2011["fips_5"].isin(scope_fips)].copy()
    df2011.to_csv(DATA / "pep_2011.csv", index=False)
    print(f"Wrote {len(df2011)} rows → pep_2011.csv")

    print("\n--- V2024 (2024 endpoint) ---")
    df2024 = pull_v2024(states)
    df2024 = df2024[df2024["fips_5"].isin(scope_fips)].copy()
    df2024.to_csv(DATA / "pep_2024.csv", index=False)
    print(f"Wrote {len(df2024)} rows → pep_2024.csv")

    # Sanity check coverage
    missing_2011 = scope_fips - set(df2011["fips_5"])
    missing_2024 = scope_fips - set(df2024["fips_5"])
    if missing_2011:
        print(f"\nMissing in 2011: {missing_2011}")
    if missing_2024:
        print(f"\nMissing in 2024: {missing_2024}")

    # Quick preview
    merged = df2011.merge(df2024, on="fips_5", how="inner").merge(
        counties[["fips_5", "County/County Equivalent", "msa_name_short"]],
        on="fips_5", how="left",
    )
    merged["delta_under18"] = merged["pop_under18_2024"] - merged["pop_under18"]
    merged["delta_pct"] = merged["delta_under18"] / merged["pop_under18"] * 100
    print("\nTop 5 counties by largest decline:")
    print(merged.nsmallest(5, "delta_under18")[
        ["fips_5", "County/County Equivalent", "msa_name_short",
         "pop_under18", "pop_under18_2024", "delta_under18", "delta_pct"]
    ].to_string(index=False))
    print("\nTop 5 counties by largest gain:")
    print(merged.nlargest(5, "delta_under18")[
        ["fips_5", "County/County Equivalent", "msa_name_short",
         "pop_under18", "pop_under18_2024", "delta_under18", "delta_pct"]
    ].to_string(index=False))


if __name__ == "__main__":
    main()
