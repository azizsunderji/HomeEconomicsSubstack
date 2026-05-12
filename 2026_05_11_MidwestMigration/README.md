# Midwest Migration

Analysis code for the Home Economics article on the Midwest's apparent migration recovery: the region's net domestic migration finally turned positive in 2025 (+16K, the first positive year in over a decade), but the improvement came almost entirely from collapsing outflows rather than new arrivals — and the people still leaving in high proportions are increasingly well-educated and high-earning.

Published on [Substack](https://homeeconomics.substack.com).

## Data Sources

- **Census ACS state-to-state migration (2005–2024).** Annual interstate flow matrix.
  Source path: `Data/State_Migration/state_to_state_migration_2005_2024.parquet`. Used to compute Midwest inflow, outflow, and net domestic flows excluding intra-Midwest moves.
- **Census Population Estimates Program (PEP), latest vintages.** State and region-level births, deaths, natural change, domestic migration, international migration, and population, 2010–2025.
  Source path: `Data/PopulationEstimates/state_pop_estimates_long.parquet`. Used for natural-change panels, the 2025 net domestic migration reading, and regional comparisons.
- **IPUMS ACS 1-Year microdata.** Person-level records used to compute the composition of Midwest out-migrants and arrivers by age, household income, education, and presence of children.
  Source path: `Data/ACS_1Y/acs_1y.parquet`.

## Scripts

All scripts live in `scripts/`. They read from the data lake locations above and write PNG/SVG/CSV outputs into `outputs/`.

- `build_midwest_4series.py` — Four-line chart (inflow, outflow, net domestic, international) for the Midwest, 2005–2025.
- `build_midwest_in_out_intl.py` — Inflow and outflow lines plus international migration overlay.
- `build_midwest_dom_intl_net.py` — Net domestic vs. international migration comparison for the Midwest.
- `build_regional_natural_change.py` — Four-panel births vs. deaths chart for each Census region, 2011–2025.
- `build_regional_intl_migration.py` — International migration by region.
- `build_regional_population.py` — Regional population totals over time.
- `build_regional_pop_yoy.py` — Year-over-year population growth by region.
- `build_state_decomp_2021v2024.py` — Per-state contribution to Midwest improvement, decomposing 2021 vs. 2024 into inflow change vs. outflow change.
- `build_state_inflow_outflow_panels.py` — Twelve-state small-multiples showing inflow and outflow time series for each Midwestern state.
- `build_midwest_cohort_panels.py` — Multi-panel cohort decomposition of Midwest out-migration by age, income, education, and family status.
- `build_leavers_absolute.py` — Absolute counts of Midwest leavers by income and education bin.
- `build_leavers_panels.py` — Side-by-side panels of leaver composition over time.
- `build_leavers_2panel_education.py` — Two-panel education chart: no degree vs. bachelor's or more.

## Outputs

Key charts in `outputs/`:

- `midwest_4series_migration.svg/.png` — The four-line headline chart: inflow, outflow, net domestic, international.
- `midwest_state_decomposition_2021v2024.svg/.png` — Per-state contribution to the regional improvement (green = fewer leaving, blue = more arriving).
- `regional_births_deaths.svg/.png` — Births vs. deaths panels for each region.
- `midwest_leavers_2panel_education.svg/.png` — Out-migrants by degree status.
- `midwest_outmigrants_income_real.svg/.png` — Out-migrants by real household income bin.
- `midwest_outmigrants_kids.svg/.png` — Out-migrants by presence of children under 18.
- `midwest_in_out_international.svg/.png` — Inflow/outflow with international migration overlay.
- `regional_panels_v3.svg/.png` — Four-region inflow/outflow/net panels.
- `tweet1_inflow_outflow.svg/.png` … `tweet6_natural_change.svg/.png` — Standalone single-chart versions for social posts.

The full data tables underlying the charts are in `outputs/*.csv`.

## Notes

- `midwest_findings.md` (in the project root) contains the prose summary of all key findings and the methodology notes used to write the article.
- All charts use the Home Economics brand palette and the Oracle font (preserved in SVG via `svg.fonttype = 'none'` for Illustrator compatibility).
