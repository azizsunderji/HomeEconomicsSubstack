"""
Build a county x decade MSA membership panel for the U.S., 1950-2020.

For each decade, marks True/False whether each U.S. county was part of a:
  - Standard Metropolitan Area (1950)
  - Standard Metropolitan Statistical Area (1960, 1970)
  - Metropolitan Statistical Area (1980, 1990, 2000) -- includes MSAs, PMSAs (within CMSAs).
    All counties in MSA/PMSA/CMSA designations count as metro.
  - CBSA Metropolitan Statistical Area (2010, 2020) -- Micropolitan EXCLUDED.

Sources (saved to data/omb_delineations/):
  1950: 50mfips.txt           -- Bureau of the Budget, Oct 1950
  1960: 60mfips.txt           -- OMB, Nov 1960
  1970: 73mfips.txt           -- OMB, 4/27/1973 (incorporates 1970 census)
  1980: 83mfips.txt           -- OMB, 6/27/1983 (first MSA-framework delineation, post-1980 census)
  1990: 93mfips.txt           -- OMB, 6/30/1993 (post-1990 census MSA update)
  2000: 99mfips.txt           -- OMB, 6/30/1999 (last MSA-framework delineation, pre-CBSA)
  2010: 2013/list1.xls        -- OMB, Feb 2013 (first CBSA delineation post-2010 census)
  2020: 2023/list1_2023.xlsx  -- OMB, Jul 2023 (first CBSA delineation post-2020 census)

Master county list: under18_by_county_decade.csv (covers every U.S. county for every decade).

Output: data/msa_membership_by_decade.csv with columns
  county_fips, county_name, state_name,
  in_msa_1950, in_msa_1960, in_msa_1970, in_msa_1980,
  in_msa_1990, in_msa_2000, in_msa_2010, in_msa_2020,
  first_msa_decade

Run: python scripts/build_msa_membership_panel.py
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OMB = DATA / "omb_delineations"
OUT = DATA / "msa_membership_by_decade.csv"


# -----------------------------------------------------------------------------
# Parsers for fixed-width OMB text files (50mfips through 99mfips)
# -----------------------------------------------------------------------------

# 1950/1960/1970-style file: lines with a county look like
#   "0080        39153                 Summit County"
# Columns: 1-4 = MSA code; 13-17 = state+county FIPS (5 digits).
# We extract any line where the first 4 chars are a 4-digit MSA code AND
# a 5-digit county FIPS appears in the line.
_RE_5DIG = re.compile(r"\b(\d{5})\b")
_RE_AREA_HEADER = re.compile(r"^(\d{4})\s{4,}(.+)$")


def _parse_mfips_simple(path: Path, kind: str) -> pd.DataFrame:
    """Parse 50/60/73-era mfips.txt files.

    These have a simple layout:
      - lines that start with a 4-digit code followed by lots of whitespace and a
        title containing "SMA" or "SMSA" = area-header line (no county data)
      - lines that start with a 4-digit code, then state+county FIPS = county line

    All county lines in these files are part of a Standard Metropolitan
    (Statistical) Area -- there is no MSA/non-MSA distinction within the file,
    and there are no Micropolitan areas (CBSA framework didn't exist yet).
    """
    counties = set()
    current_area_title = None
    with open(path, "r", encoding="latin-1") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            # Find lines starting with 4-digit code
            m_area = _RE_AREA_HEADER.match(line)
            if m_area:
                title = m_area.group(2).strip()
                # Skip header titles that don't look like SMA/SMSA areas
                if "SMA" in title or "SMSA" in title or "MSA" in title:
                    current_area_title = title
                else:
                    current_area_title = None
            # Try to extract county FIPS from line.
            # In these files, the county FIPS is the 5-digit number after the
            # area code in the "STATE/COUNTY FIPS" column.
            # We strip the leading 4-digit area code and look for a 5-digit code
            # in the columns 13-17 region.
            if len(line) >= 18:
                # The state+county FIPS lives roughly in chars 13-17 (0-indexed 12-17)
                # but to be safe, scan the line for a 5-digit number that's preceded
                # by whitespace after the area code.
                # In simple files: 4-digit code, whitespace, 5-digit county FIPS
                rest = line[4:]
                # Find first 5-digit run; skip city FIPS (which is 5 digits but in
                # later columns and represents place codes).
                # We require it to appear within the first 20 chars after the
                # area code (covers col 17).
                m = re.search(r"^\s{4,}(\d{5})\b", rest[:25])
                if m:
                    fips = m.group(1)
                    # Skip records that are pure city/town FIPS by ensuring this
                    # is in the COUNTY column. The state+county FIPS starts in
                    # col 13 (chars 12 to 17). Verify by checking position.
                    pos = line.find(fips, 4)
                    if pos >= 8 and pos <= 16:
                        counties.add(fips)
    return pd.DataFrame({"county_fips": sorted(counties)})


def parse_50mfips(path: Path) -> set[str]:
    """1950 SMA file. Use the already-clean sma_1950_counties.csv when available."""
    sma_csv = DATA / "sma_1950_counties.csv"
    if sma_csv.exists():
        df = pd.read_csv(sma_csv, dtype={"county_fips": str})
        df["county_fips"] = df["county_fips"].str.zfill(5)
        return set(df["county_fips"].unique())
    return set(_parse_mfips_simple(path, "1950")["county_fips"])


def parse_60mfips(path: Path) -> set[str]:
    return set(_parse_mfips_simple(path, "1960")["county_fips"])


def parse_73mfips(path: Path) -> set[str]:
    return set(_parse_mfips_simple(path, "1973")["county_fips"])


# -----------------------------------------------------------------------------
# 83/93/99mfips have a more complex layout with MSA/PMSA/CMSA columns and
# central/outlying flag. The county FIPS column starts at char 25.
# We want ALL counties listed in any MSA, PMSA, or CMSA -- they are all
# metropolitan. There are NO non-metro entries in these files.
# -----------------------------------------------------------------------------

def _parse_mfips_msa_pmsa(path: Path) -> set[str]:
    """Parse 83/93/99-style mfips files.

    Layout (per file's own documentation):
      chars 1-4   : MSA/CMSA FIPS code
      chars 9-12  : PMSA FIPS code
      chars 17-18 : Alternative CMSA code
      chars 25-29 : State+county FIPS (5 digits)
      char  33    : Central/outlying flag
      chars 49+   : Title

    For our purpose every line with a 5-digit county FIPS in chars 25-29
    contributes a metro county. The file has no Micropolitan areas
    (Micropolitan was introduced with CBSAs in 2003).

    Skip lines like "NECMA" (New England County Metropolitan Area) -- those are
    alternative aggregations and contain the same counties already listed in
    MSAs. We retain only lines whose nearest area-header line is an MSA, PMSA,
    or CMSA (not NECMA).
    """
    counties = set()
    current_is_metro = False
    with open(path, "r", encoding="latin-1") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            # An area-header line has the title in the right part of the line and
            # NO county FIPS. We detect by checking whether chars 25-29 are blank.
            header_cell = line[24:29] if len(line) >= 29 else ""
            title_cell = line[48:].strip() if len(line) >= 49 else ""
            if header_cell.strip() == "" and title_cell:
                # Determine area type
                # Examples: "Abilene, TX MSA", "...PMSA", "...CMSA", "...NECMA"
                if title_cell.endswith(" NECMA") or "NECMA" in title_cell.split()[-1]:
                    current_is_metro = False
                elif (
                    title_cell.endswith(" MSA")
                    or title_cell.endswith(" PMSA")
                    or title_cell.endswith(" CMSA")
                ):
                    current_is_metro = True
                else:
                    # ignore -- some files have stray non-area headers
                    pass
                continue
            # County line
            if len(line) >= 29:
                fips = line[24:29]
                if fips.isdigit() and current_is_metro:
                    counties.add(fips)
    return counties


def parse_83mfips(path: Path) -> set[str]:
    return _parse_mfips_msa_pmsa(path)


def parse_93mfips(path: Path) -> set[str]:
    return _parse_mfips_msa_pmsa(path)


def parse_99mfips(path: Path) -> set[str]:
    return _parse_mfips_msa_pmsa(path)


# -----------------------------------------------------------------------------
# 2013 and 2023 CBSA files (Excel)
# -----------------------------------------------------------------------------

def _parse_cbsa_xls(path: Path) -> set[str]:
    """Parse a CBSA list1 file. Filter to Metropolitan Statistical Area only."""
    df = pd.read_excel(path, sheet_name=0, header=2)
    df = df[df["Metropolitan/Micropolitan Statistical Area"] == "Metropolitan Statistical Area"].copy()
    # Build 5-digit county FIPS
    df["FIPS State Code"] = df["FIPS State Code"].astype("Int64").astype(str).str.zfill(2)
    df["FIPS County Code"] = df["FIPS County Code"].astype("Int64").astype(str).str.zfill(3)
    df["county_fips"] = df["FIPS State Code"] + df["FIPS County Code"]
    return set(df["county_fips"].unique())


def parse_2013_list1(path: Path) -> set[str]:
    return _parse_cbsa_xls(path)


def parse_2023_list1(path: Path) -> set[str]:
    return _parse_cbsa_xls(path)


# -----------------------------------------------------------------------------
# Main build
# -----------------------------------------------------------------------------

DECADE_FILES = {
    1950: ("50mfips.txt", parse_50mfips),
    1960: ("60mfips.txt", parse_60mfips),
    1970: ("73mfips.txt", parse_73mfips),
    1980: ("83mfips.txt", parse_83mfips),
    1990: ("93mfips.txt", parse_93mfips),
    2000: ("99mfips.txt", parse_99mfips),
    2010: ("2013_list1.xls", parse_2013_list1),
    2020: ("2023_list1.xlsx", parse_2023_list1),
}

# -----------------------------------------------------------------------------
# Known FIPS fixups
# -----------------------------------------------------------------------------
# The 1960 OMB file has a typo: Bergen County, NJ is listed as 34000 (should be
# 34003). The 1950 and 1960 files include South Norfolk city, VA (51785) which
# was merged into Chesapeake (51550) in 1963; in the modern master county list
# this territory appears as Chesapeake. We remap to the modern equivalent.
FIPS_REMAP = {
    "34000": "34003",   # Bergen County, NJ -- typo in 1960 file
    "51785": "51550",   # South Norfolk city VA -> merged into Chesapeake city in 1963
}

# Connecticut switched from counties to 9 planning regions in 2022, and the
# 2023 OMB CBSA delineation uses planning regions instead of counties. The
# master county list still uses the 8 historical counties (FIPS 09001..09015).
# We map each MSA-classified planning region to ALL the historical counties
# it overlaps (per the official 2022 CT planning region geographies). A
# historical county counts as in-MSA if ANY of its territory overlaps an
# MSA-classified planning region.
CT_PR_TO_COUNTIES = {
    "09110": ["09003", "09013"],            # Capitol PR: Hartford, Tolland
    "09120": ["09001"],                     # Greater Bridgeport PR: Fairfield
    "09130": ["09007", "09009", "09011"],   # Lower CT River Valley PR: Middlesex, New Haven, New London
    "09140": ["09001", "09005", "09009"],   # Naugatuck Valley PR: Fairfield, Litchfield, New Haven
    "09150": ["09011", "09013", "09015"],   # Northeastern PR: New London, Tolland, Windham  (Micropolitan in 2023)
    "09160": ["09003", "09005"],            # Northwest Hills PR: Hartford, Litchfield  (Micropolitan in 2023)
    "09170": ["09007", "09009"],            # South Central PR: Middlesex, New Haven
    "09180": ["09011", "09015"],            # Southeastern PR: New London, Windham
    "09190": ["09001", "09005"],            # Western PR: Fairfield, Litchfield
}


def load_master_county_list() -> pd.DataFrame:
    """Master U.S. county list, from under18_by_county_decade.csv."""
    df = pd.read_csv(
        DATA / "under18_by_county_decade.csv",
        dtype={"county_fips": str},
    )
    df["county_fips"] = df["county_fips"].str.zfill(5)
    counties = (
        df.groupby("county_fips", as_index=False)
        .agg(county_name=("county_name", "first"), state_name=("state_name", "first"))
        .sort_values("county_fips")
        .reset_index(drop=True)
    )
    return counties


def main() -> None:
    print("=" * 70)
    print("Building MSA membership panel, 1950-2020")
    print("=" * 70)

    master = load_master_county_list()
    print(f"Master county list: {len(master):,} counties")

    decade_sets: dict[int, set[str]] = {}
    for decade, (fname, parser) in DECADE_FILES.items():
        path = OMB / fname
        if not path.exists():
            raise FileNotFoundError(f"Missing source file: {path}")
        fips_set = parser(path)

        # Apply general FIPS remaps (e.g. 1960 typo 34000 -> 34003;
        # South Norfolk VA 51785 -> Chesapeake 51550)
        for bad, good in FIPS_REMAP.items():
            if bad in fips_set:
                fips_set.discard(bad)
                fips_set.add(good)

        # CT 2020: planning regions -> historical counties (any overlap with MSA PR)
        if decade == 2020:
            ct_msa_counties: set[str] = set()
            for pr, counties in CT_PR_TO_COUNTIES.items():
                if pr in fips_set:
                    ct_msa_counties.update(counties)
            # Remove all CT PR codes from the set, add the historical counties
            fips_set = {c for c in fips_set if not c.startswith("091") or len(c) != 5 or c[2:] in {"001","003","005","007","009","011","013","015"}}
            # Cleaner: drop any 5-digit code starting with "091" that isn't a known county
            ct_valid = {"09001","09003","09005","09007","09009","09011","09013","09015"}
            fips_set = {c for c in fips_set if not c.startswith("091") or c in ct_valid}
            fips_set.update(ct_msa_counties)

        decade_sets[decade] = fips_set
        # Sanity check: report a known target count
        print(f"  {decade}: {fname:<22}  -> {len(fips_set):>5} counties in MSA")

    # Build the panel
    panel = master.copy()
    for decade, fips_set in decade_sets.items():
        col = f"in_msa_{decade}"
        panel[col] = panel["county_fips"].isin(fips_set)

    # first_msa_decade
    decade_cols = [f"in_msa_{d}" for d in sorted(decade_sets.keys())]

    def _first_year(row: pd.Series) -> int:
        for d in sorted(decade_sets.keys()):
            if row[f"in_msa_{d}"]:
                return d
        return 0

    panel["first_msa_decade"] = panel.apply(_first_year, axis=1).astype(int)

    # Report counties that are in a delineation file but NOT in master county list
    print("\nUnmatched FIPS (in delineation file but not in master county list):")
    master_fips = set(master["county_fips"])
    for decade, fips_set in decade_sets.items():
        unmatched = fips_set - master_fips
        if unmatched:
            sample = sorted(unmatched)[:10]
            print(f"  {decade}: {len(unmatched)} unmatched -- sample: {sample}")
        else:
            print(f"  {decade}: 0 unmatched (clean)")

    # Save
    panel.to_csv(OUT, index=False)
    print(f"\nWrote {OUT}")
    print(f"Rows: {len(panel):,}")

    # Final summary
    print("\nSummary of counties in MSA per decade:")
    for d in sorted(decade_sets.keys()):
        n = panel[f"in_msa_{d}"].sum()
        print(f"  {d}: {n:>5} counties")
    print("\nFirst-MSA-decade distribution:")
    print(panel["first_msa_decade"].value_counts().sort_index())


if __name__ == "__main__":
    main()
