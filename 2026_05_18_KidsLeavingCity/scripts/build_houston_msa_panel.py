"""
Build Houston-MSA county membership by decade (1950-2020).

Parses the OMB delineation files in data/omb_delineations/ and extracts the
counties that were part of the Houston SMA/MSA/CBSA in each decennial.

Output: data/houston_msa_counties_by_decade.csv
  county_fips, county_name, in_1950, in_1960, in_1970, in_1980, in_1990, in_2000, in_2010, in_2020, first_in_houston_msa
"""
from pathlib import Path
import pandas as pd
import re

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OMB = DATA / "omb_delineations"


def parse_fixed_width(path):
    """Parse 50/60/73/83/93/99 fixed-width files. Returns list of TX county FIPS in Houston MSA/SMSA/CMSA/PMSA."""
    text = path.read_text(errors="replace").splitlines()
    # Step 1: identify all area codes (any column) appearing on header lines that mention Houston + TX.
    # Header lines: start with a 4-digit code, have NO 5-digit county FIPS, contain "Houston" + "TX".
    houston_codes = set()
    for line in text:
        if not re.match(r"^\d{4}\s", line):
            continue
        if re.search(r"\b\d{5}\b", line):  # has a county FIPS → it's a county row, not a header
            continue
        if "Houston" in line and ("TX" in line or "Texas" in line):
            # Pull every 4-digit code from the line (could be CMSA + PMSA codes)
            for tok in re.findall(r"\b\d{4}\b", line):
                houston_codes.add(tok)
    # Step 2: any line starting with a 4-digit code that has ANY Houston code AND a TX county FIPS
    counties = []
    for line in text:
        if not re.match(r"^\d{4}\s", line):
            continue
        codes_on_line = set(re.findall(r"\b\d{4}\b", line))
        if not (codes_on_line & houston_codes):
            continue
        # Find the 5-digit TX county FIPS (state 48)
        for token in line.split():
            if re.fullmatch(r"48\d{3}", token):
                counties.append(token)
                break
    return sorted(set(counties))


def parse_xlsx_houston(path, year):
    df = pd.read_excel(path, header=2)
    # Title column
    title_col = "CBSA Title"
    state_col = "FIPS State Code"
    county_col = "FIPS County Code"
    msa_col = "Metropolitan/Micropolitan Statistical Area"
    mask = (
        df[title_col].astype(str).str.contains("Houston", case=False, na=False)
        & df[msa_col].astype(str).str.contains("Metropolitan Statistical Area", case=False, na=False)
    )
    sub = df[mask].copy()
    sub["county_fips"] = sub[state_col].astype(int).astype(str).str.zfill(2) + sub[county_col].astype(int).astype(str).str.zfill(3)
    return list(sub["county_fips"].unique())


DECADES = {
    1950: ("50mfips.txt", parse_fixed_width),
    1960: ("60mfips.txt", parse_fixed_width),
    1970: ("73mfips.txt", parse_fixed_width),
    1980: ("83mfips.txt", parse_fixed_width),
    1990: ("93mfips.txt", parse_fixed_width),
    2000: ("99mfips.txt", parse_fixed_width),
    2010: ("2013_list1.xls", parse_xlsx_houston),
    2020: ("2023_list1.xlsx", parse_xlsx_houston),
}

houston_by_decade = {}
for yr, (filename, fn) in DECADES.items():
    path = OMB / filename
    if fn == parse_xlsx_houston:
        counties = fn(path, yr)
    else:
        counties = fn(path)
    houston_by_decade[yr] = counties
    print(f"{yr}: {len(counties)} counties in Houston MSA — {sorted(counties)}")

# All counties that have ever been in Houston MSA
all_counties = sorted(set().union(*houston_by_decade.values()))

# Map FIPS -> county name (from existing modern delineation)
modern = pd.read_csv(DATA / "modern_msa_counties.csv", dtype={"county_fips": str})
modern["county_fips"] = modern["county_fips"].str.zfill(5)
name_map = dict(zip(modern["county_fips"], modern["county_name"]))

# Also pull names from TX counties (some may not be in modern Houston MSA)
import duckdb
tx = duckdb.query(f"SELECT county_fips, county_name FROM read_csv_auto('{DATA}/under18_by_county_decade.csv') WHERE year = 2020 AND county_fips LIKE '48%'").df()
tx["county_fips"] = tx["county_fips"].astype(str).str.zfill(5)
for _, row in tx.iterrows():
    if row["county_fips"] not in name_map:
        name_map[row["county_fips"]] = row["county_name"]

rows = []
for cf in all_counties:
    r = {"county_fips": cf, "county_name": name_map.get(cf, cf)}
    first = None
    for yr in DECADES:
        in_y = cf in houston_by_decade[yr]
        r[f"in_{yr}"] = in_y
        if in_y and first is None:
            first = yr
    r["first_in_houston_msa"] = first
    rows.append(r)

out = pd.DataFrame(rows)
out.to_csv(DATA / "houston_msa_counties_by_decade.csv", index=False)
print(f"\nWrote {DATA / 'houston_msa_counties_by_decade.csv'} — {len(out)} unique counties")
print(out.to_string(index=False))
