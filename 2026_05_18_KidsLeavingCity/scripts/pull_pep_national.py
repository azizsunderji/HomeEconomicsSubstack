"""
Pull PEP V2019 (2011 baseline) and V2024 (2024 endpoint) for ALL US counties.
Uses cached state files where available; downloads missing ones.

Output:
  data/pep_2011_national.csv — fips_5, pop_under18, age_0_4, age_5_17 (state×county)
  data/pep_2024_national.csv — fips_5, pop_under18
"""
from __future__ import annotations
import urllib.request
from pathlib import Path

import duckdb
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
CACHE = DATA / "pep_cache"
CACHE.mkdir(exist_ok=True)

V2019_URL = "https://www2.census.gov/programs-surveys/popest/datasets/2010-2019/counties/asrh/cc-est2019-agesex-{state}.csv"
V2024_URL = "https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/asrh/cc-est2024-syasex-{state}.csv"

ALL_STATES = [
    "01", "02", "04", "05", "06", "08", "09", "10", "11", "12",
    "13", "15", "16", "17", "18", "19", "20", "21", "22", "23",
    "24", "25", "26", "27", "28", "29", "30", "31", "32", "33",
    "34", "35", "36", "37", "38", "39", "40", "41", "42", "44",
    "45", "46", "47", "48", "49", "50", "51", "53", "54", "55", "56",
]


def download(url: str, dest: Path, retries: int = 3) -> Path | None:
    if dest.exists() and dest.stat().st_size > 1000:
        return dest
    import time as _t
    for attempt in range(retries):
        try:
            print(f"  downloading {dest.name} (attempt {attempt+1})")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=180) as r:
                dest.write_bytes(r.read())
            return dest
        except Exception as e:
            print(f"    ↳ {e}; backoff")
            _t.sleep(5 * (attempt + 1))
    print(f"  ⚠ giving up on {dest.name}")
    return None


def main():
    print("=== V2019 (2011 baseline) — agesex by state ===")
    v2019_files = []
    for s in ALL_STATES:
        f = CACHE / f"v2019-agesex-{s}.csv"
        ok = download(V2019_URL.format(state=s), f)
        if ok and ok.stat().st_size > 5000:
            v2019_files.append(str(ok))
    print(f"  files: {len(v2019_files)}")
    # YEAR=4 = July 1, 2011
    df11 = duckdb.query(f"""
        SELECT
            LPAD(CAST(STATE AS VARCHAR),2,'0') || LPAD(CAST(COUNTY AS VARCHAR),3,'0') AS fips_5,
            UNDER5_TOT AS age_0_4,
            (AGE513_TOT + AGE1417_TOT) AS age_5_17,
            (UNDER5_TOT + AGE513_TOT + AGE1417_TOT) AS pop_under18
        FROM read_csv_auto({v2019_files!r}, encoding='latin-1')
        WHERE YEAR = 4 AND SUMLEV = 50
    """).df()
    df11.to_csv(DATA / "pep_2011_national.csv", index=False)
    print(f"  wrote pep_2011_national.csv — {len(df11)} counties")

    print("\n=== V2024 (2024 endpoint) — syasex by state ===")
    v2024_files = []
    for s in ALL_STATES:
        f = CACHE / f"v2024-syasex-{s}.csv"
        ok = download(V2024_URL.format(state=s), f)
        if ok and ok.stat().st_size > 5000:
            v2024_files.append(str(ok))
    print(f"  files: {len(v2024_files)}")
    # YEAR=6 = July 1, 2024 (V2024 vintage). Per-file reads to dodge a DuckDB
    # column-inference bug when SUMLEV varies across files via BOM/encoding.
    frames = []
    for fp in v2024_files:
        sub = duckdb.query(f"""
            SELECT
                LPAD(CAST(STATE AS VARCHAR),2,'0') || LPAD(CAST(COUNTY AS VARCHAR),3,'0') AS fips_5,
                SUM(CASE WHEN AGE BETWEEN 0 AND 17 THEN TOT_POP ELSE 0 END) AS pop_under18_2024
            FROM read_csv_auto('{fp}', encoding='latin-1', header=True)
            WHERE YEAR = 6
            GROUP BY 1
        """).df()
        frames.append(sub)
    df24 = pd.concat(frames, ignore_index=True)
    df24.to_csv(DATA / "pep_2024_national.csv", index=False)
    print(f"  wrote pep_2024_national.csv — {len(df24)} counties")


if __name__ == "__main__":
    main()
