# Rents and Work From Home

Analysis code for the Home Economics article: "Why did rents soar in Miami but plunge in Austin?"

Published on [Substack](https://homeeconomics.substack.com)

## Data Sources

- **Zillow ZORI** — Metro-level monthly observed rent index (all homes, smoothed)
- **Census Building Permits Survey** — County and CBSA-level annual permits (2015–2025)
- **BLS Current Employment Statistics** — Metro total nonfarm and federal government employment
- **FRED** — Metro payroll series (e.g., `WASH911NA` for DC, `PAYEMS` for national)
- **American Community Survey 1-Year** — WFH share and federal worker share by metro (IPUMS extract)
- **Quarterly Census of Employment & Wages** — CBSA-level federal employment (quarterly)
- **Bloom/SWAA WFH Research** — Monthly city-level WFH rates from the Survey of Working Arrangements and Attitudes

## Scripts

- `01_pull_data.py` — Downloads and aggregates raw data: Zillow ZORI, Census permits, BLS employment, DC/Montgomery County open data
- `02_build_panel.py` — Builds annual and monthly metro panels by merging ZORI, BLS, permits, ACS WFH/federal shares, QCEW, and population estimates
- `03_regression_analysis.py` — Runs panel regressions (rent growth ~ permits + employment + WFH share) and DC decomposition; generates cross-sectional scatter data
- `04_charts.py` — Generates D3.js interactive HTML charts (rent trajectory, scatter plots, waterfall decomposition)
- `08_dc_vs_national_yoy.py` — Creates 2x2 small-multiples chart comparing DC vs. national on permits, rents, employment, and WFH
- `export_scatter_svg.py` — Exports side-by-side static SVG scatter (permits vs. rent and WFH vs. rent) with population-scaled bubbles

## Outputs

- `06_wfh_scatter.html` — Scatter plot: WFH share vs. cumulative rent change by metro (2019–2025)
- `14_side_by_side_scatter.html` — Side-by-side: permits vs. rent change and WFH vs. rent change
- `15_emp_rent_gap_line.html` — Employment vs. rent growth gap over time
- `03_decomposition_waterfall.html` — DC rent change decomposition (supply, employment, WFH, residual)
- `wfh_r2_evolution.html` — Year-by-year R² evolution: WFH vs. permits vs. employment as rent predictors
