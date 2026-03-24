# First-Time Home Buyers Really Are Older

Analysis code for the Home Economics article: "First-Time Home Buyers Really Are Older"

Published on [Substack](https://homeeconomics.substack.com)

## Data Sources

- **PSID (Panel Study of Income Dynamics)** — Cross-year individual file and annual/biennial family files (1968-2023). Used to track rent-to-own transitions for household heads. Source: University of Michigan Institute for Social Research.
- **CPS ASEC (Current Population Survey Annual Social and Economic Supplement)** — Microdata from 1962-2025. Used for marriage age and FTB inference via the MS-2 method.
- **AHS (American Housing Survey)** — Biennial survey data. Used for direct FTB age measurement via the FRSTHO/FIRSTHOME variable.
- **NY Fed Consumer Credit Panel/Equifax** — Published summary statistics from Liberty Street Economics blog posts (Lee & Tracy 2019, 2025). Used for CCP observed FTB age (mean and median).
- **ACS (American Community Survey)** — 1-year estimates. Used for free-and-clear homeownership rates and marriage age.
- **Redfin** — Published FTB age estimates from CPS ASEC analysis by Asad Khan (redfin.com/news/median-homebuying-age-2025/).

## Scripts

| Script | Description |
|--------|-------------|
| `psid_ftb_weighted.py` | **Primary analysis.** Weighted PSID FTB age with bootstrap CIs. Excludes Latino supplement, uses longitudinal weights. |
| `psid_ftb_proper.py` | Earlier unweighted PSID FTB analysis (superseded by weighted version) |
| `psid_ftb_ci_svg.py` | Generates standalone SVG of the PSID FTB chart for Illustrator |
| `ahs_ftb_age.py` | Computes FTB age from American Housing Survey microdata |
| `ftb_age_comparison.py` | Combines FTB age estimates from multiple sources (PSID, AHS, NY Fed CCP) |
| `ftb_all_sources_chart.py` | Multi-source FTB age comparison chart |
| `cps_ftb_chart.py` | CPS-based FTB age chart |
| `cps_ftb_longrun.py` | Long-run CPS FTB analysis |
| `ftb_longrun_chart.py` | Long-run FTB trend chart (ownership, marriage, headship) |
| `ms2_method_proper.py` | Marriage-based FTB age inference (MS-2 method) |
| `psid_milestones.py` | Life milestone timing from PSID (marriage, headship, homeownership) |
| `sankey_3cohorts.py` | Sankey diagram comparing Boomer/GenX/Millennial life stages |

## Outputs

Key charts:
- `psid_ftb_ci.html` — PSID median FTB age 1974-2023 with 90% CI (smoothed trend + CI band)
- `ccp_correction.html` — CCP observed vs. corrected vs. PSID comparison
- `psid_vs_ahs.html` — PSID vs. American Housing Survey comparison
- `ftb_all_sources.html` — All FTB age sources on one chart
- `boomerang_rate.html` — Boomerang buyer rate over time
- `psid_ftb_ci.svg` — Standalone SVG for Illustrator
