"""
Build the county FIPS list for the 12 MSAs in scope.

MSAs (CBSA codes from OMB 2023 delineation):
  10 largest by 2020 pop + Austin + Charlotte.

Reads list1_2023.xlsx which has one row per principal-county membership.
"""
from pathlib import Path
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"

# CBSA codes for the 12 MSAs we want
MSAS = {
    "35620": "New York-Newark-Jersey City, NY-NJ",
    "31080": "Los Angeles-Long Beach-Anaheim, CA",
    "16980": "Chicago-Naperville-Elgin, IL-IN",
    "19100": "Dallas-Fort Worth-Arlington, TX",
    "26420": "Houston-The Woodlands-Sugar Land, TX",
    "12060": "Atlanta-Sandy Springs-Roswell, GA",
    "47900": "Washington-Arlington-Alexandria, DC-VA-MD-WV",
    "37980": "Philadelphia-Camden-Wilmington, PA-NJ-DE-MD",
    "33100": "Miami-Fort Lauderdale-Pompano Beach, FL",
    "38060": "Phoenix-Mesa-Chandler, AZ",
    "12420": "Austin-Round Rock-San Marcos, TX",
    "16740": "Charlotte-Concord-Gastonia, NC-SC",
}


def main():
    # The OMB file has a few header rows above the table — try to be robust
    raw = pd.read_excel(DATA / "omb_msa_delineation.xlsx", sheet_name=0, header=None)
    # Find header row by locating "CBSA Code"
    header_idx = None
    for i, row in raw.iterrows():
        if any("CBSA Code" == str(c).strip() for c in row.values):
            header_idx = i
            break
    if header_idx is None:
        raise SystemExit("Could not find CBSA Code header row")
    df = pd.read_excel(DATA / "omb_msa_delineation.xlsx", sheet_name=0, header=header_idx)
    print(f"Loaded {len(df)} rows; columns: {list(df.columns)[:10]}...")

    # Keep only Metropolitan Statistical Area rows in our 12 CBSAs
    df["CBSA Code"] = df["CBSA Code"].astype(str).str.zfill(5)
    out = df[df["CBSA Code"].isin(MSAS.keys())].copy()
    print(f"Matched rows: {len(out)}")

    # Get FIPS state + county codes
    out["state_fips"] = out["FIPS State Code"].astype(int).astype(str).str.zfill(2)
    out["county_fips"] = out["FIPS County Code"].astype(int).astype(str).str.zfill(3)
    out["fips_5"] = out["state_fips"] + out["county_fips"]
    out["msa_name_short"] = out["CBSA Code"].map(MSAS)

    keep_cols = [
        "CBSA Code", "msa_name_short", "CBSA Title",
        "Metropolitan Division Title",
        "County/County Equivalent", "State Name",
        "state_fips", "county_fips", "fips_5",
    ]
    keep_cols = [c for c in keep_cols if c in out.columns]
    out = out[keep_cols].rename(columns={"CBSA Code": "cbsa_code"})

    out_path = DATA / "counties_in_scope.csv"
    out.to_csv(out_path, index=False)
    print(f"Wrote {len(out)} counties → {out_path}")

    # Summary by MSA
    by_msa = out.groupby("msa_name_short").size().sort_values(ascending=False)
    print("\nCounties per MSA:")
    print(by_msa.to_string())


if __name__ == "__main__":
    main()
