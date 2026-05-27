# Kids Leaving City — NYC

Analysis code for the Home Economics article: **"An Exodus of Children from NYC"** (working title).

Published on [Home Economics](https://home-economics.us).

The article tracks the 5 NYC boroughs' under-18 population decline since 2020 (about 150,000 children, ~9%), decomposes it into births / aging-out / domestic migration / international migration, and uses ACS microdata to identify where the families and children actually went — by county.

## Data Sources

- **U.S. Census Bureau Population Estimates Program (PEP)** — annual county under-18 estimates, stitched across five vintages to produce a seamless 1980–2024 series:
  - 1980s intercensal `pe-02-19YY` (5-year age groups)
  - 1990s postcensal `cany9Y` / `canj9Y` (direct under-18)
  - 2000s intercensal `co-est00int` (5-year age groups)
  - 2010s intercensal `cc-est2020int` (exact under-18)
  - 2020s `V2024` and `V2025` single-year-of-age (`cc-est2024-syasex`, `co-est2024-alldata`, `co-est2025-alldata`)
  - Endpoints: `https://www2.census.gov/programs-surveys/popest/datasets/`
- **NHGIS (IPUMS National Historical GIS)** — Decennial Census 1970–2020 county under-18 counts, used as anchors for the PEP stitching. Extracts pulled via `https://api.ipums.org`.
- **NCHS WONDER Natality** — county-level births 2007–2024 for the 22 NYC MSA counties, used in the natural-change decomposition. `https://wonder.cdc.gov/natality-current.html`.
- **NYC DOH Summary of Vital Statistics** — 5-borough births 1940+ for historical natural-change estimates.
- **U.S. Census Bureau ACS 1-year PUMS** — person-level microdata for migration analysis (pooled 2021 + 2022 + 2023 + 2024). Pulled via the Census PUMS API at `https://api.census.gov/data/{year}/acs/acs1/pums` and verified against the IPUMS USA extract `acs_1y_degfield_migration.csv.gz` in the Home Economics data lake. Key variables: `AGEP`, `MIG`, `MIGPLAC1`, `MIGPUMA1`, `STATEFIP`, `PUMA`, `PERWT`, `SERIAL`.
- **IRS SOI county-to-county Migration Data** — used for the all-people destination analysis (pooled 2020-21 + 2021-22 + 2022-23). `https://www.irs.gov/statistics/soi-tax-stats-migration-data`.
- **IPUMS USA crosswalks** — `PUMA_County_MigPUMA_Crosswalk.xlsx` and `PUMA10_to_PUMA20_best.parquet` from the data lake, used to attribute PUMA-level destinations to counties.
- **Natural Earth shapefiles** — ocean and lakes layers (`ne_10m_ocean.shp`, `ne_10m_lakes.shp`) for the static map background.
- **OMB 2023 CBSA delineations** — definition of NYC MSA (CBSA 35620, 22 counties).
- **External corroboration cited in the article:**
  - Jewish Insider, "Inside New Jersey's Orthodox boomtown" (2022) — Lakewood population growth quote
  - OJPAC — Rockland County / Ramapo Orthodox growth statistics
  - NYC Department of Education April 2025 family-exit survey

## Scripts

### Core data pipeline
- `build_nyc_under18_pep_seamless.py` — stitches five PEP releases into a continuous 1980–2024 annual under-18 series for the 22 NYC MSA counties, anchored to NHGIS Decennial counts. Output: `data/nyc_county_under18_pep_seamless.csv`.
- `build_nyc_under18_decomposition.py` — per-county annual decomposition 2010–2024: `ΔU18 = births − aging-out − deaths − net migration (domestic + international)`. Output: `data/nyc_county_under18_decomposition.csv`.
- `pull_pums_nyc_kid_migration.py` — pulls ACS PUMS person-level migration records for NYC-borough origin, all ages 2021–2024, via the Census PUMS API. Output: `data/pums_nyc_kid_migration_raw.parquet`.

### Charts in the article
- `build_nyc_pct_change_2020_map.py` — static map of % change in under-18 by NYC MSA county 2020–2024 (Economist red+blue diverging palette).
- `build_nyc_outflow_treemap_family_compare.py` — side-by-side WSJ-style treemap: households with kids vs without kids, where NYC borough movers went.
- `build_nyc_kid_outflow_treemap_counties.py` — WSJ-style treemap of NYC kid out-migration destinations by county.
- `build_nyc_outflow_treemap.py` — earlier IRS-based version of the outflow treemap (all people, not kid-specific).
- `build_nyc_under18_pep_smallmultiples.py` and `_grouped.py` — 22-panel small multiples of borough/suburb under-18 trajectories 1980–2024.
- `build_nyc_under18_pep_levels_shared.py` — same data, shared 0–700K y-axis.
- `build_nyc_vs_suburbs_lines.py` — two-line chart: NYC (5 boroughs aggregate) vs suburbs (17 counties aggregate).
- `build_nyc_rebased_interactive.py` — interactive index-to-100 line chart with a draggable rebase-year slider.
- `build_nyc_map_decomposition_pct_interactive.py` — interactive map with hover-to-decompose chart and selectable baseline year.
- `build_palette_picker.py` — 12 candidate diverging palettes side by side for selecting the final map color scheme.

### Helper scripts and earlier exploration
The `scripts/` directory contains additional helpers: PEP downloaders, NHGIS submission/polling, WHYMOVE (CPS ASEC) exploration, tract-level under-18 analysis, central-cities decomposition, and miscellaneous palette/style explorations.

## Outputs

- `nyc_pct_change_2020_map.svg` / `.png` — the article's main static map.
- `nyc_kid_outflow_treemap_counties.svg` / `.html` — county-level destination treemap for NYC kid emigrants.
- `nyc_outflow_treemap_family_compare.svg` / `.html` — the side-by-side family vs no-kids treemap.
- `nyc_under18_nyc_vs_suburbs.html` — two-line aggregate trajectory chart.
- `nyc_under18_counties_pep.html`, `nyc_under18_counties_pep_grouped.html`, `nyc_under18_levels_shared.html` — small-multiples 45-year trajectories.
- `nyc_under18_rebased_interactive.html`, `nyc_decomposition_map_pct_interactive.html` — interactive exploration charts.
- `nyc_decomposition_map.html`, `nyc_decomposition_map_pct.html` — earlier non-interactive map+chart variants.

## Data files included

The `data/` folder contains CSVs, JSONs, and small text files used or produced by the analysis (under 50MB each). Large source files — raw PEP cache, IRS migration zips, IPUMS extracts, NHGIS extracts, shapefiles, PDFs — are excluded from the repo. Reproduce them by running the relevant `pull_*.py` or `build_*.py` script with the appropriate API key set.
