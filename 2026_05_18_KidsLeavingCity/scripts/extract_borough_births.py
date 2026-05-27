"""
Extract NYC borough-level live births from NYC DOH Summary of Vital Statistics annual reports.

Each annual report contains a table titled:
  - "Live Births by Mother's Ancestry and Borough of Residence" (modern: PO2)
  - "Live Births by Ancestry of Mother and Borough of Residence" (older naming, e.g., 2010, 2009)
  - "Live Births, Spontaneous and Induced Terminations of Pregnancy by Borough of Residence" (1997-2005, Table 18)

The first data row of these tables is "Total" with values: Total, Manhattan, Bronx, Brooklyn, Queens, Staten Island (or Richmond), Non-Residents, Unknown.

We extract: NYC total (residents only) = Manhattan + Bronx + Brooklyn + Queens + Richmond/SI.
We also extract reported figures.
"""

import re
import os
from pathlib import Path

PDF_DIR = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity/data/nyc_doh_pdfs")

# Pattern for borough headers used in PDFs
BOROUGHS = ["Manhattan", "Bronx", "Brooklyn", "Queens", "Staten Island", "Richmond"]


def numbers_from_line(line):
    """Pull all integers (with optional commas) out of a line."""
    # remove dot leaders
    line = re.sub(r"\.{2,}", " ", line)
    return [int(x.replace(",", "")) for x in re.findall(r"\b\d{1,3}(?:,\d{3})+|\b\d{3,7}\b", line)]


def extract_modern_PO2(txt, year):
    """Modern annual reports (2006+): Table PO2 'Live Births by ... Ancestry ... and Borough of Residence'.
       First row after header is 'Total' with [Total, Manhattan, Bronx, Brooklyn, Queens, Staten Island, Non-Residents, Unknown]."""
    lines = txt.splitlines()
    # Some text-extracted PDFs scramble the table title (e.g. "TableTable PO2.PO2. LiveLive Births Births by by Ancestry of...")
    # Use a fuzzy contiguous-window match: any spot where lines mention Ancestry + Borough + Residence close together.
    # Skip table of contents (early in file): require Hispanic/Latino or Ancestry of Mother header follows.
    for i, line in enumerate(lines):
        if i < 1000:  # skip TOC
            continue
        window = " ".join(lines[i:i + 15])
        if re.search(r"PO2", window) and re.search(r"Ancestry", window, re.I) and re.search(r"Borough of Residence", window, re.I):
            # find Mother's Ancestry column header then look for 'Total' row
            for j in range(i, min(i + 40, len(lines))):
                stripped = lines[j].strip()
                if stripped.startswith("Total ") or stripped == "Total":
                    nums = numbers_from_line(lines[j])
                    if len(nums) < 6:
                        nums += numbers_from_line(lines[j + 1] if j + 1 < len(lines) else "")
                    if len(nums) >= 6 and nums[0] > 50000:
                        return parse_total_row(nums)
    # fallback: original strict pattern
    for i, line in enumerate(lines):
        if re.search(r"Live Births by .*Ancestry.*Borough of Residence", line, re.I) and "Table" in line:
            for j in range(i + 1, min(i + 40, len(lines))):
                stripped = lines[j].strip()
                if stripped.startswith("Total ") or stripped == "Total":
                    nums = numbers_from_line(lines[j])
                    if len(nums) < 6:
                        nums += numbers_from_line(lines[j + 1])
                    if len(nums) >= 6:
                        return parse_total_row(nums)
    return None


def parse_total_row(nums):
    """Given a sequence of numbers from a Total row, return dict.
       Expected: [Total, Manhattan, Bronx, Brooklyn, Queens, Staten Island, Non-Residents, Unknown]"""
    if len(nums) < 6:
        return None
    out = {
        "Total_reported": nums[0],
        "Manhattan": nums[1],
        "Bronx": nums[2],
        "Brooklyn": nums[3],
        "Queens": nums[4],
        "Staten_Island": nums[5],
    }
    if len(nums) >= 7:
        out["Non_Residents"] = nums[6]
    if len(nums) >= 8:
        out["Unknown"] = nums[7]
    out["NYC_residents"] = out["Manhattan"] + out["Bronx"] + out["Brooklyn"] + out["Queens"] + out["Staten_Island"]
    return out


def extract_table18_old(txt, year):
    """1997-2005-style: Table 18 'Live Births, Spontaneous and Induced Terminations of Pregnancy
       by Borough of Residence and Age of Woman'.

       Walks down the table; each borough heading line (NEW YORK CITY, MANHATTAN, BRONX, BROOKLYN,
       QUEENS, RICHMOND, NON-RESIDENTS, RESIDENCE UNKNOWN) is followed by a 'Live Births' subrow.
       The first number on the 'Live Births' subrow is the live births count for that borough.
    """
    lines = txt.splitlines()
    result = {}

    # Find Table 18 location
    start = None
    for i, line in enumerate(lines):
        if re.search(r"^\s*Table\s+18[\.\s]+Live Births", line) or \
           re.search(r"^\s*Table\s+18[\.\s]", line) and "Live Births" in (lines[i + 1] if i + 1 < len(lines) else ""):
            start = i
            break
    if start is None:
        # alternative: look for the header "Borough of Residence" together with the first 'Pregnancy Outcome'
        for i, line in enumerate(lines):
            if "Live Births, Spontaneous and Induced Terminations" in line and "Borough" in (lines[i+1] if i+1<len(lines) else ""):
                start = i
                break
    if start is None:
        return None

    # Walk forward up to ~150 lines and pick out borough sections
    borough_map = {
        "NEW YORK CITY": "Total_reported",
        "MANHATTAN": "Manhattan",
        "BRONX": "Bronx",
        "BROOKLYN": "Brooklyn",
        "QUEENS": "Queens",
        "RICHMOND": "Staten_Island",
        "STATEN ISLAND": "Staten_Island",
        "NON-RESIDENTS": "Non_Residents",
        "NON RESIDENTS": "Non_Residents",
        "RESIDENCE UNKNOWN": "Unknown",
    }

    end = min(start + 200, len(lines))
    i = start
    while i < end:
        line = lines[i].strip()
        key = None
        for header, k in borough_map.items():
            if line.startswith(header):
                key = k
                break
        if key:
            # The line itself has the TOTAL pregnancy outcome (live + spont + induced) and age breakdown.
            # We need to find the 'Live Births' subrow that follows.
            # In the parsed text, it's typically within the next 5 lines.
            for j in range(i, min(i + 8, end)):
                if "Live Births" in lines[j] or "Live births" in lines[j]:
                    # The numbers may be split across this and next 2 lines.
                    chunk = lines[j] + " " + (lines[j + 1] if j + 1 < end else "") + " " + (lines[j + 2] if j + 2 < end else "")
                    nums = numbers_from_line(chunk)
                    if nums:
                        # First number after the label is the borough total live births
                        result[key] = nums[0]
                    break
            i += 4
            continue
        i += 1

    if not result:
        return None
    # Compute resident total
    boroughs = ["Manhattan", "Bronx", "Brooklyn", "Queens", "Staten_Island"]
    if all(b in result for b in boroughs):
        result["NYC_residents"] = sum(result[b] for b in boroughs)
    return result


def extract_for_year(year):
    txt_path = PDF_DIR / f"{year}sum.txt"
    if not txt_path.exists() or txt_path.stat().st_size == 0:
        return None
    txt = txt_path.read_text(errors="replace")

    # Try modern PO2 first
    result = extract_modern_PO2(txt, year)
    if result and result.get("NYC_residents", 0) > 50000:
        result["_method"] = "PO2"
        return result

    # Try old Table 18
    result = extract_table18_old(txt, year)
    if result and result.get("NYC_residents", 0) > 50000:
        result["_method"] = "Table18"
        return result

    return None


if __name__ == "__main__":
    years = sorted([int(p.stem.replace("sum", "")) for p in PDF_DIR.glob("*sum.pdf")])
    print(f"Found PDFs for years: {years}")
    print()
    rows = []
    for y in years:
        r = extract_for_year(y)
        if r:
            print(f"{y} ({r.get('_method', '?')}): Total_rep={r.get('Total_reported'):>7} | M={r.get('Manhattan'):>6} Bx={r.get('Bronx'):>6} Bk={r.get('Brooklyn'):>6} Q={r.get('Queens'):>6} SI={r.get('Staten_Island'):>5} | Residents={r.get('NYC_residents'):>6}")
            rows.append((y, r))
        else:
            print(f"{y}: FAILED")
