"""
Build the final CSV combining:
  - NYC-total live births 1898-2023 from Table PC1 of the 2023 Summary of Vital Statistics
    (5-year averages pre-1966, single years 1966+)
  - Borough-level live births 1995-2023 from Tables 18 (1995-2002) and PO2 (2003-2023)

Single source throughout: NYC Department of Health and Mental Hygiene, "Summary of Vital
Statistics, New York City." Available at
https://www.nyc.gov/site/doh/data/data-publications/vital-statistics-reports.page
"""

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract_borough_births import extract_for_year, PDF_DIR

OUT_CSV = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity/data/nyc_doh_births_historical.csv")

# Table PC1 from 2023 sum.pdf — NYC-total live births by year.
# 5-year averages prior to 1966 are presented in the source as a single number.
# We expand these to the individual years, recording the same averaged value for each year in the range.
# This is consistent with how the source itself presents the data; the actual single-year
# values for 1940-1965 are only available in older annual summaries (e.g., 1965 and earlier).
PC1_AVERAGES = [
    # (start_year, end_year, average_births)
    (1898, 1900, 119_000),
    (1901, 1905, 129_000),
    (1906, 1910, 144_000),
    (1911, 1915, 140_581),
    (1916, 1920, 136_101),
    (1921, 1925, 130_462),
    (1926, 1930, 125_590),
    (1931, 1935, 106_179),
    (1936, 1940, 102_418),
    (1941, 1945, 126_495),
    (1946, 1950, 158_926),
    (1951, 1955, 163_526),
    (1956, 1960, 166_949),
    (1961, 1965, 165_197),
    (1966, 1970, 147_294),  # also presented as 5-yr avg
    (1971, 1975, 115_941),
    (1976, 1980, 108_058),
]

# Annual single-year totals from Table PC1 (1981 onward in the modern presentation).
PC1_ANNUAL = {
    1981: 108_547,
    1982: 111_487,
    1983: 112_353,
    1984: 113_332,
    1985: 118_542,
    1986: 122_108,
    1987: 127_386,
    1988: 132_226,
    1989: 137_673,
    1990: 139_630,
    1991: 138_148,
    1992: 136_002,
    1993: 133_583,
    1994: 133_662,
    1995: 131_009,
    1996: 126_901,
    1997: 123_313,
    1998: 124_252,
    1999: 123_739,
    2000: 125_563,
    2001: 124_023,
    2002: 122_937,
    2003: 124_345,
    2004: 124_099,
    2005: 122_725,
    2006: 125_506,
    2007: 128_961,
    2008: 127_680,
    2009: 126_774,
    2010: 124_791,
    2011: 123_029,
    2012: 123_231,
    2013: 120_457,
    2014: 122_084,
    2015: 121_673,
    2016: 120_367,
    2017: 117_013,
    2018: 114_296,
    2019: 110_442,
    2020: 100_022,
    2021: 99_262,
    2022: 99_459,
    2023: 98_389,
}


def main():
    # Pull borough-level data from each annual report we successfully parsed.
    borough_data = {}
    for pdf in sorted(PDF_DIR.glob("*sum.pdf")):
        m = re.match(r"(\d{4})sum", pdf.stem)
        if not m:
            continue
        year = int(m.group(1))
        r = extract_for_year(year)
        if r:
            borough_data[year] = r

    print(f"Borough-level data extracted for: {sorted(borough_data.keys())}")
    print()

    # Build NYC-total lookup
    nyc_total = {}
    averaged_years = set()
    for start, end, val in PC1_AVERAGES:
        for y in range(start, end + 1):
            nyc_total[y] = val
            averaged_years.add(y)
    for y, v in PC1_ANNUAL.items():
        nyc_total[y] = v
        if y in averaged_years:
            averaged_years.discard(y)

    # Write CSV
    rows = []
    for year in range(1940, 2024):  # 1940-2023 inclusive
        rec = {
            "year": year,
            "Bronx": "",
            "Brooklyn": "",
            "Manhattan": "",
            "Queens": "",
            "Staten_Island": "",
            "NYC_residents_sum_of_boroughs": "",
            "NYC_total_reported": nyc_total.get(year, ""),
            "is_5yr_average": "Y" if year in averaged_years else "",
            "source_year_pdf": "",
            "extraction_method": "",
        }
        if year in borough_data:
            b = borough_data[year]
            rec["Bronx"] = b.get("Bronx", "")
            rec["Brooklyn"] = b.get("Brooklyn", "")
            rec["Manhattan"] = b.get("Manhattan", "")
            rec["Queens"] = b.get("Queens", "")
            rec["Staten_Island"] = b.get("Staten_Island", "")
            rec["NYC_residents_sum_of_boroughs"] = b.get("NYC_residents", "")
            # Prefer the borough-table reported total when present (matches PC1 for all years)
            if b.get("Total_reported"):
                rec["NYC_total_reported"] = b["Total_reported"]
            rec["source_year_pdf"] = f"{year}sum.pdf"
            rec["extraction_method"] = b.get("_method", "")
        else:
            # NYC_total comes from PC1 (the 2023 historical table)
            rec["source_year_pdf"] = "2023sum.pdf (Table PC1)"
            rec["extraction_method"] = "PC1"
        rows.append(rec)

    # 2024 row: data not yet published as of project date (2026-05-19); leave blank.
    rows.append({
        "year": 2024,
        "Bronx": "", "Brooklyn": "", "Manhattan": "", "Queens": "", "Staten_Island": "",
        "NYC_residents_sum_of_boroughs": "", "NYC_total_reported": "",
        "is_5yr_average": "",
        "source_year_pdf": "(not yet published)",
        "extraction_method": "",
    })

    fieldnames = [
        "year",
        "Bronx", "Brooklyn", "Manhattan", "Queens", "Staten_Island",
        "NYC_residents_sum_of_boroughs",
        "NYC_total_reported",
        "is_5yr_average",
        "source_year_pdf",
        "extraction_method",
    ]
    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"Wrote {len(rows)} rows to {OUT_CSV}")

    # Print summary
    have_boroughs = sum(1 for r in rows if r["Bronx"] != "")
    have_total_only = sum(1 for r in rows if r["Bronx"] == "" and r["NYC_total_reported"] != "")
    blank = sum(1 for r in rows if r["NYC_total_reported"] == "")
    print(f"  Borough-level coverage: {have_boroughs} years")
    print(f"  NYC-total only:         {have_total_only} years")
    print(f"  Blank:                  {blank} years")


if __name__ == "__main__":
    main()
