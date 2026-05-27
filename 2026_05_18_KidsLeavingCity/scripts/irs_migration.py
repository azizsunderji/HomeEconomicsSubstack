"""
Download IRS SOI county-to-county migration files (tax years 2011-12 through
2021-22) and compute annual inner→outer flows per MSA.

Variables in IRS files:
  y1_statefips, y1_countyfips — county of residence in year 1 (origin)
  y2_statefips, y2_countyfips — county in year 2 (destination)
  n1 — number of returns (households)
  n2 — number of exemptions (people: filers + dependents)
  AGI — aggregate adjusted gross income

We compute total flows by summing n2 (exemptions ≈ people).
"""
from __future__ import annotations
import io
import urllib.request
import zipfile
from pathlib import Path
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
# Use pre-downloaded IRS files from the MiamiRise project
SOURCE_DIR = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_04_21_MiamiRise/data/irs_soi_migration/county")

INNER = {
    "New York-Newark-Jersey City, NY-NJ": [(36, 5), (36, 47), (36, 61), (36, 81), (36, 85)],
    "Los Angeles-Long Beach-Anaheim, CA": [(6, 37)],
    "Chicago-Naperville-Elgin, IL-IN": [(17, 31)],
    "Dallas-Fort Worth-Arlington, TX": [(48, 113), (48, 439)],
    "Houston-The Woodlands-Sugar Land, TX": [(48, 201)],
    "Atlanta-Sandy Springs-Roswell, GA": [(13, 121), (13, 89)],
    "Washington-Arlington-Alexandria, DC-VA-MD-WV": [(11, 1), (51, 13), (51, 510)],
    "Philadelphia-Camden-Wilmington, PA-NJ-DE-MD": [(42, 101)],
    "Miami-Fort Lauderdale-Pompano Beach, FL": [(12, 86)],
    "Phoenix-Mesa-Chandler, AZ": [(4, 13)],
    "Austin-Round Rock-San Marcos, TX": [(48, 453)],
    "Charlotte-Concord-Gastonia, NC-SC": [(37, 119)],
}


YEAR_PAIRS = ["1112", "1213", "1314", "1415", "1516", "1617",
              "1718", "1819", "1920", "2021", "2122", "2223"]


def load_year(yp: str) -> pd.DataFrame:
    p = SOURCE_DIR / f"countyoutflow{yp}.csv"
    if not p.exists():
        raise FileNotFoundError(p)
    df = pd.read_csv(p, dtype=str, on_bad_lines="skip", encoding="latin-1")
    df.columns = [c.strip().lower() for c in df.columns]
    for c in ("n1", "n2", "agi"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    return df


def main():
    rows = []
    counties = pd.read_csv(DATA / "counties_in_scope.csv", dtype=str)
    counties["s"] = counties["state_fips"].astype(int)
    counties["cf"] = counties["county_fips"].astype(int)

    for yp in YEAR_PAIRS:
        try:
            df = load_year(yp)
            df = df[df["y2_statefips"].notna() & df["y1_statefips"].notna()]
            # Convert FIPS to int for matching
            for c in ("y1_statefips", "y1_countyfips", "y2_statefips", "y2_countyfips"):
                df[c] = pd.to_numeric(df[c], errors="coerce")
            df = df.dropna(subset=["y1_statefips", "y1_countyfips", "y2_statefips", "y2_countyfips"])
            for c in ("y1_statefips", "y1_countyfips", "y2_statefips", "y2_countyfips"):
                df[c] = df[c].astype(int)

            # For each MSA, count inner→outer + outer→inner flows
            for msa, inner_pairs in INNER.items():
                inner_set = set(inner_pairs)
                msa_pairs = set(zip(
                    counties[counties["msa_name_short"] == msa]["s"],
                    counties[counties["msa_name_short"] == msa]["cf"]
                ))
                outer_set = msa_pairs - inner_set
                if not outer_set:
                    continue

                io_mask = (
                    df[["y1_statefips", "y1_countyfips"]].apply(tuple, axis=1).isin(inner_set)
                    & df[["y2_statefips", "y2_countyfips"]].apply(tuple, axis=1).isin(outer_set)
                )
                oi_mask = (
                    df[["y1_statefips", "y1_countyfips"]].apply(tuple, axis=1).isin(outer_set)
                    & df[["y2_statefips", "y2_countyfips"]].apply(tuple, axis=1).isin(inner_set)
                )

                io_flow = df.loc[io_mask, ["n1", "n2"]].sum()
                oi_flow = df.loc[oi_mask, ["n1", "n2"]].sum()

                # Dependents proxy: exemptions − 1.5 × returns (avg ~1.5 filers/return)
                io_returns = int(io_flow.get("n1", 0))
                io_exemp = int(io_flow.get("n2", 0))
                oi_returns = int(oi_flow.get("n1", 0))
                oi_exemp = int(oi_flow.get("n2", 0))
                rows.append({
                    "year_pair": yp,
                    "msa": msa,
                    "inner_to_outer_returns": io_returns,
                    "inner_to_outer_exemptions": io_exemp,
                    "inner_to_outer_dependents": max(0, int(io_exemp - 1.5 * io_returns)),
                    "outer_to_inner_returns": oi_returns,
                    "outer_to_inner_exemptions": oi_exemp,
                    "outer_to_inner_dependents": max(0, int(oi_exemp - 1.5 * oi_returns)),
                })
            print(f"  {yp}: processed.")
        except Exception as e:
            print(f"  {yp}: ERROR {e}")

    out = pd.DataFrame(rows)
    out["net_outflow_exemptions"] = out["inner_to_outer_exemptions"] - out["outer_to_inner_exemptions"]
    out["net_outflow_dependents"] = out["inner_to_outer_dependents"] - out["outer_to_inner_dependents"]
    out.to_csv(DATA / "irs_inner_outer_flows.csv", index=False)
    print(f"\nWrote {len(out)} rows → data/irs_inner_outer_flows.csv")

    piv = out.pivot_table(index="year_pair", columns="msa",
                          values="net_outflow_exemptions").fillna(0).astype(int)
    piv.columns = [c.split(",")[0].split("-")[0].strip() for c in piv.columns]
    print("\nNet inner→outer EXEMPTIONS by year (positive = more leaving than arriving):")
    print(piv.to_string())


if __name__ == "__main__":
    main()
