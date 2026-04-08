// Chart registry — append new entries here, project_page.html loads this via <script>
var CHARTS_DATA = [
  {
    "id": "bar_immigration_change",
    "title": "The immigration surge, by country",
    "subtitle": "Change in net migration rate per 1,000, 2013-15 avg → 2022-24 avg",
    "file": "bar_immigration_change.html",
    "width": 960,
    "height": 1260,
    "tags": ["bar", "immigration", "change"],
    "date": "2026-04-06T20:30",
    "source": "Sources: CBO, Statistics Canada, ONS, ABS, Stats NZ, Eurostat CNMIGRAT"
  },
  {
    "id": "line_immigration_surges",
    "title": "Immigration surges and reversals",
    "subtitle": "Net migration rate per 1,000, top movers and Anglosphere, 2000-2025",
    "file": "line_immigration_surges.html",
    "width": 960,
    "height": 700,
    "tags": ["line", "immigration", "timeseries", "anglosphere"],
    "date": "2026-04-06T20:30",
    "source": "Sources: CBO, Statistics Canada, ONS, ABS, Stats NZ, Eurostat CNMIGRAT"
  },
  {
    "id": "barbell_immigration_before_after",
    "title": "Before and after the surge",
    "subtitle": "Average net migration rate per 1,000, 2005-15 avg vs 2015-25 avg",
    "file": "barbell_immigration_before_after.html",
    "width": 960,
    "height": 1190,
    "tags": ["barbell", "immigration", "before-after"],
    "date": "2026-04-06T20:45",
    "source": "Sources: CBO, Statistics Canada, ONS, ABS, Stats NZ, Eurostat CNMIGRAT"
  },
  {
    "id": "small_multiples_cumulative_migration",
    "title": "Cumulative immigration since 2000",
    "subtitle": "Cumulative net migrants per 1,000 population, rebased to zero, 35 countries",
    "file": "small_multiples_cumulative_migration.html",
    "width": 960,
    "height": 1326,
    "tags": ["small-multiples", "immigration", "cumulative", "timeseries"],
    "date": "2026-04-06T21:00",
    "source": "Sources: CBO, Statistics Canada, ONS, ABS, Stats NZ, Eurostat CNMIGRAT"
  },
  {
    "id": "scatter_cumulative_immigration_vs_happiness",
    "title": "Cumulative immigration and happiness",
    "subtitle": "R² = 0.51: cumulative net immigration per 1,000 (2000-21) vs happiness change (2017-19 → 2022-24)",
    "file": "scatter_cumulative_immigration_vs_happiness.html",
    "width": 960,
    "height": 987,
    "tags": ["scatter", "immigration", "happiness", "correlation", "key-finding"],
    "date": "2026-04-06T22:00",
    "source": "Sources: CBO, Statistics Canada, ONS, ABS, Stats NZ, Eurostat, Gallup/WHR"
  },
  {
    "id": "scatter_cumulative_vs_happiness_full",
    "title": "Cumulative immigration and happiness (full period)",
    "subtitle": "R² = 0.23, p = 0.004: cumulative net immigration per 1,000 (2000-24) vs happiness change (~2005 → ~2025)",
    "file": "scatter_cumulative_vs_happiness_full.html",
    "width": 960,
    "height": 987,
    "tags": ["scatter", "immigration", "happiness", "correlation", "key-finding", "publishable"],
    "date": "2026-04-06T22:30",
    "source": "Sources: CBO, Statistics Canada, ONS, ABS, Stats NZ, Eurostat, Gallup/WHR"
  },
  {
    "id": "scatter_immigration_vs_happiness",
    "title": "Immigration surge and happiness",
    "subtitle": "Change in net migration rate vs change in life satisfaction, 2006-10 → 2020-24 (R² = 0.17, positive slope)",
    "file": "scatter_immigration_vs_happiness.html",
    "width": 960,
    "height": 987,
    "tags": ["scatter", "immigration", "happiness"],
    "date": "2026-04-06T22:15",
    "source": "Sources: CBO, Statistics Canada, ONS, ABS, Stats NZ, Eurostat, Gallup/WHR"
  },
  {
    "id": "timing_happiness_vs_immigration",
    "title": "When did happiness decline?",
    "subtitle": "Life satisfaction and net migration rate, Anglosphere — timing mismatch",
    "file": "timing_happiness_vs_immigration.html",
    "width": 960,
    "height": 850,
    "tags": ["small-multiples", "timing", "anglosphere", "key-finding"],
    "date": "2026-04-07T00:00",
    "source": "Sources: Gallup/WHR, CBO, Statistics Canada, ONS, ABS, Stats NZ, CSO"
  },
  {
    "id": "heatmap_happiness_level",
    "title": "Rich, unhappy (level)",
    "subtitle": "Life satisfaction by country ranked by GDP per capita, 2006-2025. Hashing = immigration surge.",
    "file": "heatmap_happiness_level.html",
    "width": 960,
    "height": 1040,
    "tags": ["heatmap", "happiness", "gdp", "immigration", "key-finding", "publishable"],
    "date": "2026-04-07T00:15",
    "source": "Sources: Gallup/WHR, CBO, Eurostat, World Bank GDP"
  },
  {
    "id": "heatmap_happiness_1y",
    "title": "Rich, unhappy (1-year change)",
    "subtitle": "1-year change in life satisfaction, ranked by GDP per capita",
    "file": "heatmap_happiness_1y.html",
    "width": 960,
    "height": 1040,
    "tags": ["heatmap", "happiness", "change"],
    "date": "2026-04-07T00:15",
    "source": "Sources: Gallup/WHR, CBO, Eurostat, World Bank GDP"
  },
  {
    "id": "heatmap_happiness_3y",
    "title": "Rich, unhappy (3-year change)",
    "subtitle": "3-year change in life satisfaction, ranked by GDP per capita",
    "file": "heatmap_happiness_3y.html",
    "width": 960,
    "height": 1040,
    "tags": ["heatmap", "happiness", "change"],
    "date": "2026-04-07T00:15",
    "source": "Sources: Gallup/WHR, CBO, Eurostat, World Bank GDP"
  },
  {
    "id": "heatmap_happiness_5y",
    "title": "Rich, unhappy (5-year change)",
    "subtitle": "5-year change in life satisfaction, ranked by GDP per capita",
    "file": "heatmap_happiness_5y.html",
    "width": 960,
    "height": 1040,
    "tags": ["heatmap", "happiness", "change"],
    "date": "2026-04-07T00:15",
    "source": "Sources: Gallup/WHR, CBO, Eurostat, World Bank GDP"
  },
  {
    "id": "line_slovakia_immigration",
    "title": "Slovakia: net migration rate",
    "subtitle": "Net migrants per 1,000 population, 2000-2024",
    "file": "line_slovakia_immigration.html",
    "width": 960,
    "height": 500,
    "tags": ["line", "immigration", "slovakia", "diagnostic"],
    "date": "2026-04-07T00:30",
    "source": "Source: Eurostat CNMIGRAT"
  },
  {
    "id": "line_malta_immigration",
    "title": "Malta: net migration rate",
    "subtitle": "Net migrants per 1,000 population, 2000-2024. Peak: 42/1,000 in 2019.",
    "file": "line_malta_immigration.html",
    "width": 960,
    "height": 500,
    "tags": ["line", "immigration", "malta", "diagnostic"],
    "date": "2026-04-07T01:00",
    "source": "Source: Eurostat CNMIGRAT"
  },
  {
    "id": "heatmap_bivariate",
    "title": "Rich, unhappy (bivariate)",
    "subtitle": "Happiness level × 3-year change, ranked by GDP per capita, 2006-2025",
    "file": "heatmap_bivariate.html",
    "width": 960,
    "height": 1080,
    "tags": ["heatmap", "bivariate", "happiness", "key-finding", "publishable"],
    "date": "2026-04-07T02:00",
    "source": "Sources: Gallup/WHR, CBO, Eurostat, World Bank GDP"
  }
];
