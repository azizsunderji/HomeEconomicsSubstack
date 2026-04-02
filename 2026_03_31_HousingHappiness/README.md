# Housing and Happiness

Analysis code for the Home Economics article: "English speaking countries are miserable"

Published on [Substack](https://homeeconomics.substack.com)

## Data Sources

- **OECD Analytical House Prices** — Price-to-income index (HPI_YDH), 37 countries, annual, 2015=100 base
- **World Happiness Report 2026** — Figure 2.1 Excel file with happiness decomposition (Cantril Ladder scores, 6-factor breakdown, 168 countries, 2011–2025)
- **Our World in Data** — Cantril Ladder happiness scores (supplementary)

## Scripts

- `analysis.py` — Boilerplate starter script
- `analyze.py` — Initial data exploration and merging of WHR + OECD PTI data
- `scatter_recent.py` — Scatter chart of PTI change vs happiness change
- `rebuild_scatter_charts.py` — Rebuilds scatter charts with updated styling
- `rebuild_all_charts.py` — Batch rebuild of all project charts
- `anglophone_trends.py` — Anglophone vs rest-of-OECD happiness trends over time
- `build_paired_bars.py` — Paired/overlapping bar chart of PTI change vs happiness change

## Key Outputs

- `scatter_pti_vs_happiness_bubble.html` — **Main chart**: Bubble scatter of PTI change vs happiness change, 37 countries, 2015–2025
- `bump_happiness_rankings.html` — Bump chart showing Anglosphere sliding down happiness rankings, 2011–2025
- `paired_bars_pti_vs_happiness.html` — Overlapping bar chart comparing housing cost changes and happiness changes
- `slope_pti_vs_happiness.html` — Slope chart connecting PTI change to happiness change
- `binned_bubble_pti_happiness.html` — Countries grouped into PTI quintiles, happiness change on y-axis
- `small_multiples_pti_happiness.html` — Per-country mini charts showing PTI and happiness trajectories
- `scatter_pti_change_vs_pure_residual.html` — PTI change vs the WHR model's unexplained residual
