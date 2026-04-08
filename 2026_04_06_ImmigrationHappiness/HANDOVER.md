# Immigration & Happiness — Handover

## Project Goal
Investigate whether immigration levels or surges correlate with happiness declines across OECD countries, particularly for the Anglosphere. Spun off from the HousingHappiness project after housing costs showed no correlation.

## What's Been Done

### Data Assembly (complete)
- **Immigration dataset**: `data/oecd_immigration_net.csv` — 30 OECD countries, 2000-2025, NET migration only
  - US: CBO total net (incl. undocumented), full annual 2001-2025
  - Canada: StatCan (incl. NPRs), 2000-2024
  - UK: Eurostat 2000-2019 + ONS LTIM 2020-2025
  - Australia: ABS NOM 2000-2024
  - New Zealand: Stats NZ 2000-2025
  - 25 European OECD: Eurostat CNMIGRAT 2000-2024
  - 8 non-European countries EXCLUDED (JPN/KOR/ISR/TUR/MEX/CHL/COL/CRI) — only had gross inflows, not net
- **CBO detailed data**: `data/cbo_net_immigration_by_category.csv` — US net immigration by category (LPR+, nonimmigrant, undocumented) 2001-2025
- **Happiness data**: In parent project at `../2026_03_31_HousingHappiness/data/whr2026_happiness_changes.csv` — WHR 2026, change 2006→2025

### Data Quality Investigation (complete)
- World Bank SM.POP.NETM is unreliable — diverges from national stats by 2-5x for recent years
- OECD B11 (gross inflows) only captures permanent legal admissions — misses NPRs (Canada), undocumented (US), temp visas
- Comparison charts in parent project: `../2026_03_31_HousingHappiness/outputs/small_multiples_immigration_3sources.html`

### Article Research (complete)
- `data/media_coverage.md` — No outlet tests immigration as explanatory variable for Anglosphere happiness decline
- `data/commentary_and_academic.md` — O'Connor (2020): no effect; WHR 2018: r=0.96 immigrant/native happiness; Brockmann (2026): gendered effects
- `data/policy_details.md` — All 5 Anglosphere countries cracked down 2024-25
- `data/public_opinion.md` — Opinion shifted fast but no poll links immigration attitudes to personal happiness

### Charts (in progress)
- `outputs/bar_immigration_change.html` — Horizontal bar: change in immigration rate, 30 countries
- `outputs/line_immigration_surges.html` — Line chart: top movers + Anglosphere, 2000-2025

### Key Idiosyncrasies
- **USA**: CBO includes undocumented. 2009-2019 annual data recovered (not just decade avg). 2014 was 1.64M, 2019 was only 415K.
- **Canada**: StatCan includes NPRs. 2023 peak 1.18M, 2024 collapsed to 355K.
- **UK**: Methodology break at 2021 (IPS → RAPID). Pre-/post-2021 not strictly comparable.
- **Estonia/Lithuania/Latvia**: 2022 spikes are Ukrainian refugees. Happiness gains predate immigration.
- **Germany**: 2022 spike (1.46M) also Ukrainian refugees.
- **Switzerland**: 2023 spike includes Ukrainian S-status reclassification.

## Not Yet Done
1. **Happiness correlation analysis** — The whole point. Run regressions with clean data across multiple time windows.
2. **Synthesis research file** — Phase 7 of article research not yet written.
3. **Notion page updates** — Key findings not yet posted to Notion.

## Notion Page
- Page ID: `337008aa-e629-8093-9e09-e96f09279b1e`
- Questions DB: `33a008aa-e629-8170-84c9-dd568e925205`
- URL: https://www.notion.so/337008aae62980939e09e96f09279b1e

## Parent Project
`/Users/azizsunderji/Dropbox/Home Economics/2026_03_31_HousingHappiness/` — contains the housing-happiness analysis (PTI vs happiness, R²≈0) and earlier immigration attempts with bad WB data.

## Environment
- Python 3 (Anaconda): `/Applications/anaconda3/bin/python3`
- Key packages: pandas, numpy, scipy, matplotlib, statsmodels, httpx
- D3.js in outputs/ for charts
- Brand font: Oracle (`FONT_DIR` in scripts)
- Brand palette: Blue #0BB4FF, Green #67A275, Red #F4743B, Black #3D3733, BG #F6F7F3
