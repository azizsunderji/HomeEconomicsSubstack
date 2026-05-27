"""
Build modern (2023 OMB) Metropolitan Statistical Area county crosswalk.

Output: data/modern_msa_counties.csv with columns:
  county_fips (5-digit), county_name, state_name, cbsa_code, cbsa_title,
  central_or_outlying ('Central' or 'Outlying'), in_modern_msa (bool)

Excludes Micropolitan areas — only MSAs (Metropolitan Statistical Areas).
"""
from pathlib import Path
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"

df = pd.read_excel(DATA / "omb_msa_delineation.xlsx", sheet_name="List 1", header=2)
msa = df[df["Metropolitan/Micropolitan Statistical Area"] == "Metropolitan Statistical Area"].copy()
msa["county_fips"] = msa["FIPS State Code"].astype(int).astype(str).str.zfill(2) + \
                    msa["FIPS County Code"].astype(int).astype(str).str.zfill(3)

out = msa[["county_fips", "County/County Equivalent", "State Name",
           "CBSA Code", "CBSA Title", "Central/Outlying County"]].copy()
out.columns = ["county_fips", "county_name", "state_name", "cbsa_code", "cbsa_title", "central_or_outlying"]
out["in_modern_msa"] = True

out.to_csv(DATA / "modern_msa_counties.csv", index=False)
print(f"Wrote {DATA / 'modern_msa_counties.csv'}")
print(f"  {len(out):,} counties in {out['cbsa_code'].nunique()} MSAs")
print(f"  Central: {(out['central_or_outlying']=='Central').sum()}; Outlying: {(out['central_or_outlying']=='Outlying').sum()}")
