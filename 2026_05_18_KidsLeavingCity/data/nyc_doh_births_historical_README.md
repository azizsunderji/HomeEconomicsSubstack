# NYC DOH Historical Births by Borough, 1940-2024

## Source

All numbers come from a single source: the **NYC Department of Health and Mental
Hygiene, _Summary of Vital Statistics, New York City_** (annual). PDFs were
downloaded from `https://www.nyc.gov/assets/doh/downloads/pdf/vs/{YEAR}sum.pdf`
and from the publications page at
<https://www.nyc.gov/site/doh/data/data-publications/vital-statistics-reports.page>.

No CDC, NCHS, or NYS DOH data are used. The series is fully internal to NYC DOH.

## Coverage

- **Years 1940-2023**: covered.
- **Year 2024**: row included but blank — the 2024 Summary had not been
  published as of project date (2026-05-19). Provisional 2024 birth counts are
  available from NYC DOH's "Provisional Birth and Death Data" page but were
  NOT incorporated, to keep the source consistent.

### Borough-level coverage

| Years         | Boroughs available     | Source PDF(s)                     |
|---------------|------------------------|-----------------------------------|
| 1940-1994     | NYC total only         | `2023sum.pdf` Table PC1           |
| 1995-2002     | All 5 boroughs         | Annual `{year}sum.pdf` Table 18   |
| 2003-2023     | All 5 boroughs         | Annual `{year}sum.pdf` Table PO2  |

For 1940-1994 the borough breakdowns exist in the original annual reports, but
those PDFs (1988-1994) on the NYC DOH website are scanned images with no
extractable text layer and would require OCR. They are present in
`data/nyc_doh_pdfs/` if you want to OCR them later.

## Columns

- `year`
- `Bronx`, `Brooklyn`, `Manhattan`, `Queens`, `Staten_Island` — live births by
  borough of mother's residence (counts).
- `NYC_residents_sum_of_boroughs` — sum of the five borough columns. This is
  births to NYC residents only and excludes non-residents who gave birth in NYC
  hospitals and the small "residence unknown" category.
- `NYC_total_reported` — the city-total live-births figure as reported in the
  source table. **For 1995-2023 this includes non-resident births in NYC
  facilities** (Total = NYC residents + non-residents + residence unknown).
  For 1940-1994 this is the PC1 historical-table value (also reported total,
  see note on averages below).
- `is_5yr_average` — "Y" when the PC1 historical row provides only a 5-year
  average (1940-1980). The same averaged value is written into each year of
  the range. The years 1981-2023 are reported as single-year values.
- `source_year_pdf` — which annual report supplied the row.
- `extraction_method` — `PC1` (Table PC1 of 2023 report), `Table 18` (1995-2002
  style), or `PO2` (modern format).

## Methodology notes

1. **Borough of mother's residence vs occurrence.** The borough numbers in this
   CSV are by **mother's borough of residence**, taken from Table 18 (older
   reports) or Table PO2 (modern reports) — the same "Live Births by Borough of
   Residence" table series throughout. NYC DOH also publishes a "borough of
   birth" series (Table PO1 modern), which differs slightly because births to
   non-NYC residents in NYC hospitals are assigned to the hospital's borough,
   and NYC residents giving birth outside NYC are excluded.

2. **PC1 historical averages.** Table PC1 in the 2023 report presents pre-1981
   data as **5-year averages** of annual births (1898-1900 is a 3-year average,
   then 1901-1905, 1906-1910, ..., 1976-1980 in 5-year blocks). The CSV expands
   each block by repeating the averaged value across all years in the block and
   sets `is_5yr_average=Y`. Single-year pre-1966 figures appear in the 1965 and
   earlier annual summaries but are not available as extracted text. NYC DOH
   itself notes in PC1: _"Figures prior to 1966 are averages across the years
   presented; single-year figures prior to 1966 appear in the annual summaries
   for 1965 and earlier. Figures for 1898-1913 births are estimated."_

3. **Reported vs. true totals.** `NYC_total_reported` for 1995-2023 matches the
   "Total" row of the borough table, which includes non-resident and unknown
   rows; `NYC_residents_sum_of_boroughs` is the resident-only total. For
   1940-1994, only `NYC_total_reported` is available (from PC1). PC1 includes
   non-resident births for the modern years it covers as well, so the two
   series are conceptually comparable.

4. **Borough naming.** Older reports (1995-2002) label Staten Island as
   "Richmond"; the CSV uses "Staten_Island" throughout for consistency.

5. **2001 reissue.** PC1 carries two 2001 rows in the 2023 report — one
   including World Trade Center disaster deaths and one excluding them. Only
   the all-inclusive row affects deaths; the 2001 live-birth total used here
   (124,023) is unchanged.

6. **Footnotes from PC1**:
   - "‡" marks years where population data may vary by publication year.
   - PC1 is updated annually as the latest year's data is finalized; we used
     the most recent published edition (the 2023 Summary, dated 2025).

## Gaps and limitations

- **1940-1994 by borough is missing** (NYC-total only). If borough-level back
  to 1940 is required, the historical annual reports (1940-1994) would need to
  be OCRed. Each annual report contains the borough Table 18 (or its
  predecessor) for its own year.
- **2024 is blank.** The 2024 Summary had not been published as of 2026-05-19.
- **Pre-1981 NYC totals are 5-year averages**, not single-year values, as
  presented in PC1.

## Files in this directory

- `nyc_doh_births_historical.csv` — the dataset.
- `nyc_doh_births_historical_README.md` — this file.
- `nyc_doh_pdfs/` — all source PDFs used (and a few scanned ones that could not
  be parsed).

## Scripts

- `scripts/extract_borough_births.py` — parses borough live-births "Total" row
  from each annual PDF (handles both Table 18 and Table PO2 layouts).
- `scripts/build_births_csv.py` — combines per-year borough data with the PC1
  historical NYC-total series and writes the CSV.
