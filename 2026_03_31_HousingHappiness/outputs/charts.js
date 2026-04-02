// Chart registry — append new entries here, project_page.html loads this via <script>
var CHARTS_DATA = [
  {
    "id": "scatter_14yr_matched_37",
    "title": "Housing costs and happiness (37 countries)",
    "subtitle": "Change in PTI (2009–11 → 2023–25) vs change in happiness over same period. R² = 0.23, p = 0.003, N = 37. Matched time periods, full OECD sample.",
    "file": "scatter_14yr_matched_37countries.html",
    "width": 960,
    "height": 1060,
    "tags": ["scatter", "37-country", "matched", "significant"],
    "date": "2026-03-31T22:00",
    "source": "OECD Analytical House Prices, World Happiness Report 2026"
  },
  {
    "id": "scatter_10yr_residual_37",
    "title": "What GDP, social support, and health can't explain",
    "subtitle": "WHR residual happiness vs 10-year PTI change (2013–15 → 2023–25). R² = 0.24, p = 0.002, N = 37. Housing explains ~24% of unexplained happiness variance.",
    "file": "scatter_10yr_residual_37countries.html",
    "width": 960,
    "height": 1060,
    "tags": ["scatter", "37-country", "residual", "significant"],
    "date": "2026-03-31T22:00",
    "source": "OECD Analytical House Prices, World Happiness Report 2026"
  },
  {
    "id": "r2_by_horizon",
    "title": "Housing costs predict happiness at longer horizons",
    "subtitle": "R² between PTI change and happiness measures by lookback period (3–24 years). Relationship peaks at 10–14 years. Filled dots = p < 0.05.",
    "file": "r2_by_horizon.html",
    "width": 960,
    "height": 1060,
    "tags": ["line", "sweep", "r-squared", "methodology"],
    "date": "2026-03-31T22:00",
    "source": "OECD Analytical House Prices, World Happiness Report 2026"
  },
  {
    "id": "anglophone_vs_rest_trends",
    "title": "The Anglophone divergence",
    "subtitle": "Mean happiness (Cantril ladder) and price-to-income index for 6 Anglophone vs 15 other OECD countries, 2011–2023 annual panel.",
    "file": "anglophone_vs_rest_trends.html",
    "width": 960,
    "height": 1060,
    "tags": ["line", "trends", "anglophone", "dual-panel"],
    "date": "2026-03-30T23:00",
    "source": "OECD Analytical House Prices, World Happiness Report via Our World in Data"
  },
  {
    "id": "scatter_pti_change_vs_happiness_20",
    "title": "Housing costs and happiness (20 countries, earlier version)",
    "subtitle": "OECD price-to-income change (2011–13 → 2023–25) vs happiness change (2006–10 → 2023–25). R² = 0.12, p = 0.15. 20 countries only. MISMATCHED time periods — superseded by 37-country version.",
    "file": "scatter_pti_change_vs_happiness_change.html",
    "width": 960,
    "height": 1060,
    "tags": ["scatter", "20-country", "superseded"],
    "date": "2026-03-31T16:00",
    "source": "OECD Analytical House Prices, World Happiness Report 2026"
  },
  {
    "id": "scatter_recent_pti_vs_happiness",
    "title": "The recent picture",
    "subtitle": "Change in PTI (2018 → 2023–25) vs change in happiness over same period. R² = 0.01, not significant. 20 countries. Too short a horizon for signal.",
    "file": "scatter_recent_pti_vs_happiness_change.html",
    "width": 960,
    "height": 1060,
    "tags": ["scatter", "recent", "not-significant"],
    "date": "2026-03-31T16:00",
    "source": "OECD Analytical House Prices, World Happiness Report 2026"
  },
  {
    "id": "scatter_pti_change_vs_pure_residual",
    "title": "Housing costs and unexplained happiness",
    "subtitle": "37 OECD countries, 2023-25",
    "file": "scatter_pti_change_vs_pure_residual.html",
    "width": 960,
    "height": 987,
    "tags": ["scatter", "pti", "residual", "happiness"],
    "date": "2026-04-01T12:00",
    "source": "Source: OECD Analytical House Prices, World Happiness Report 2026"
  },
  {
    "id": "paired_bars_pti_vs_happiness",
    "title": "Housing costs rose most where happiness fell — and where it didn't",
    "subtitle": "Countries sorted by PTI change, 2013-15 to 2023-25",
    "file": "paired_bars_pti_vs_happiness.html",
    "width": 960,
    "height": 987,
    "tags": ["bar", "paired", "pti", "happiness", "change"],
    "date": "2026-04-01T13:00",
    "source": "Source: OECD Analytical House Prices, World Happiness Report 2026"
  },
  {
    "id": "slope_pti_vs_happiness",
    "title": "Housing got more expensive \u2014 but happiness went every direction",
    "subtitle": "PTI change vs happiness change, 37 OECD countries",
    "file": "slope_pti_vs_happiness.html",
    "width": 960,
    "height": 987,
    "tags": ["slope", "pti", "happiness", "change"],
    "date": "2026-04-01T13:00",
    "source": "Source: OECD Analytical House Prices, World Happiness Report 2026"
  }
,
{
    "id": "bump_happiness_rankings",
    "title": "The Anglosphere's slide in happiness",
    "subtitle": "Happiness ranking among 37 OECD countries, 2011-2025",
    "file": "bump_happiness_rankings.html",
    "width": 960,
    "height": 987,
    "tags": ["bump", "ranking", "happiness", "anglosphere"],
    "date": "2026-04-01T15:00",
    "source": "Source: World Happiness Report 2026"
}
,
{
    "id": "binned_bubble_pti_happiness",
    "title": "Housing costs don't predict happiness",
    "subtitle": "Countries grouped by PTI change, bubble = population",
    "file": "binned_bubble_pti_happiness.html",
    "width": 960,
    "height": 987,
    "tags": ["bubble", "binned", "pti", "happiness"],
    "date": "2026-04-01T16:00",
    "source": "Source: OECD Analytical House Prices, World Happiness Report 2026"
}
,
{
    "id": "small_multiples_pti_happiness",
    "title": "Housing costs and happiness, country by country",
    "subtitle": "PTI (blue) and happiness (red/black), 2011-2025",
    "file": "small_multiples_pti_happiness.html",
    "width": 960,
    "height": 1800,
    "tags": ["small-multiples", "pti", "happiness", "time-series"],
    "date": "2026-04-01T16:30",
    "source": "Source: OECD Analytical House Prices, World Happiness Report 2026"
}
,
{
    "id": "scatter_pti_vs_happiness_bubble",
    "title": "Housing costs and happiness",
    "subtitle": "Bubble scatter, PTI change vs happiness change",
    "file": "scatter_pti_vs_happiness_bubble.html",
    "width": 960,
    "height": 987,
    "tags": ["scatter", "bubble", "pti", "happiness"],
    "date": "2026-04-01T17:00",
    "source": "Source: OECD Analytical House Prices, World Happiness Report 2026"
}
];