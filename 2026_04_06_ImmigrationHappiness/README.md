# Immigration and Happiness

Analysis code for the Home Economics article: "Is High Immigration Making Us Unhappy?"

Published on [Substack](https://homeeconomics.substack.com)

## Data Sources

- **Gallup World Poll** (via World Happiness Report 2019/2026) -- life satisfaction (Cantril ladder) scores by country and year (`data/happiness_combined.csv`)
- **CBO Demographic Outlook** (Jan 2024, Jan 2025, Sep 2025, Jan 2026 vintages) -- U.S. net immigration by category (LPR+, INA Nonimmigrant, Other Foreign Nationals), 2001-2025 (`data/cbo_net_immigration_by_category.csv`)
- **Statistics Canada** -- net migration including non-permanent residents, 2000-2024
- **ONS Long-Term International Migration (LTIM)** -- UK net migration, 2020-2025
- **ABS Net Overseas Migration (NOM)** -- Australia net migration, 2000-2024
- **Stats NZ** -- New Zealand net migration, 2000-2025
- **Eurostat CNMIGRAT** -- net migration for European OECD countries, 2000-2024 (`../2026_03_31_HousingHappiness/data/eurostat_cnmigrat.csv`)
- **National statistics offices** (Destatis, INE, CBS, BFS, SCB, CSO) -- recent-year overrides for Germany, Spain, Portugal, Netherlands, Switzerland, Sweden, Ireland
- **World Bank** -- population by country (`../2026_03_31_HousingHappiness/data/wb_population_all.csv`) and GDP per capita (`../2026_03_31_HousingHappiness/data/wb_gdp_percapita.csv`)

## Scripts

- **`analysis.py`** -- Boilerplate/template script (unused scaffold for D3 chart generation)
- **`build_immigration_dataset.py`** -- Builds the combined OECD net migration dataset from Eurostat and national statistics offices; outputs `data/oecd_immigration_net.csv`
- **`create_cbo_immigration_data.py`** -- Creates the CBO U.S. net immigration by category dataset (LPR+, INA Nonimmigrant, Other Foreign Nationals); outputs `data/cbo_net_immigration_by_category.csv`
- **`cumulative_migration_small_multiples.py`** -- D3 small multiples chart showing cumulative net migrants per 1,000 population since 2000 for all OECD countries
- **`heatmap_bivariate.py`** -- D3 bivariate heatmap crossing happiness level (above/below median) with 1-year change direction (improving/declining), with immigration surge borders
- **`heatmap_happiness.py`** -- D3 heatmaps of happiness by country ranked by GDP per capita, in four variants: level, 1-year change, 3-year change, 5-year change; immigration surge cells get black borders
- **`immigration_change_charts.py`** -- D3 horizontal bar chart of change in net migration rate (2013-15 vs 2022-24) and line chart of immigration rate time series for top movers and Anglosphere
- **`immigration_happiness_analysis.py`** -- Core regression analysis: cross-sectional scatter (change in immigration vs change in happiness), horizon sweep, panel regression with year fixed effects, and lag structure; generates scatter plot
- **`timing_chart.py`** -- D3 small multiples (2x3) showing happiness and immigration rate on dual axes for the six Anglosphere countries, with peak happiness markers

## Outputs

### Scatter plots
- **`scatter_immigration_vs_happiness`** -- Change in net migration rate vs change in life satisfaction (2006-10 to 2020-24), bubble size = population, with regression line and R-squared
- **`scatter_cumulative_immigration_vs_happiness`** / **`scatter_cumulative_vs_happiness_full`** -- Cumulative immigration vs happiness variants

### Heatmaps
- **`heatmap_happiness_level`** -- Life satisfaction level by country (ranked by GDP), 2006-2025
- **`heatmap_happiness_1y`** / **`heatmap_happiness_3y`** / **`heatmap_happiness_5y`** -- 1/3/5-year change in life satisfaction
- **`heatmap_bivariate`** -- 2x2 bivariate (happiness level x change direction) with immigration surge borders

### Line charts
- **`line_immigration_surges`** -- Immigration rate time series for top movers and Anglosphere countries
- **`line_malta_immigration`** / **`line_slovakia_immigration`** -- Individual country immigration profiles

### Bar charts
- **`bar_immigration_change`** -- Horizontal bars showing change in net migration rate by country (2013-15 avg to 2022-24 avg)
- **`barbell_immigration_before_after`** -- Before/after barbell chart of immigration rates

### Small multiples
- **`small_multiples_cumulative_migration`** -- Cumulative net migrants per 1,000 population since 2000, one panel per country
- **`timing_happiness_vs_immigration`** -- Dual-axis panels (happiness + immigration) for the six Anglosphere countries
