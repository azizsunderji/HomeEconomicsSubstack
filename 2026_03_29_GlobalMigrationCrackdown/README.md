# Global Migration Crackdown

Analysis code and data for the Home Economics article on the synchronized global immigration boom and bust across nine Western countries (2018–2025).

Published on [Substack](https://homeeconomics.substack.com)

## Data Sources

- **Census Bureau** — US net international migration (Vintage 2025 population estimates, revised Dec 2024 methodology)
- **CBO** — US net international migration 2021–2025 (The Demographic Outlook: 2026 to 2056, cbo.gov/publication/61994)
- **Statistics Canada** — Canadian net international migration and population estimates (Table 17-10-0040-01)
- **ONS** — UK long-term international migration by nationality (year ending June, ltimnov25.xlsx)
- **ABS** — Australia net overseas migration by country of birth (TableBuilder)
- **Destatis** — Germany net migration (register-based migration statistics)
- **Eurostat** — Portugal, Netherlands, Ireland net migration (DEMO_GIND)
- **Stats NZ** — New Zealand net migration (outcomes-based)
- **CSO** — Ireland net migration (year ending April)
- **CBS** — Netherlands net migration
- **IRCC** — Canada immigration by nationality (study permits, work permits, permanent residents)
- **DHS** — US lawful permanent residents by country of birth (Yearbook Table 3)
- **ACS** — US foreign-born population by country of birth (Table B05006, 2018–2024)
- **OECD** — International Migration Outlook 2025, SDMX API inflows by nationality
- **Environics Institute** — Canadian public opinion on immigration (fall 2024 survey)

## Scripts

- `scripts/analysis.py` — Boilerplate analysis script (data lake queries, D3 chart generation)

## Outputs

- `outputs/global_migration_small_multiples.html` — **Main chart**: 3x3 small multiples showing net migration per 1,000 population for 9 countries (2018–2025), sorted by peak rate
- `outputs/global_migration_stacked.html` — Stacked bar chart showing total net migration to all 9 countries combined, by destination
- `outputs/global_migration_decline.html` — Indexed line chart (population indexed to 2020=100) with hover interaction
- `outputs/global_migration_small_multiples.svg` — SVG export of main chart for Illustrator editing

## Key Finding

Net migration to these nine countries collectively tripled from 2.6 million (2019) to 7.2 million (2023), then collapsed to 1.3 million (2025) — half the pre-pandemic level. The crackdown overshot in the other direction.
