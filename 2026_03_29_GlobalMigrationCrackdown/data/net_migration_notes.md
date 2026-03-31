# Net Migration Data: 10 Countries, 2018-2025
## Compilation Notes & Decisions Made

### Sweden: Definition discrepancy
- Eurostat flow data (immigration - emigration) used as primary source for 2018-2023.
- Multiple sources (Macrotrends, search results) cite higher net migration for 2021 (51,947) and 2022 (58,955) than Eurostat flow data shows (42,347 and 51,844). The difference likely comes from "other corrections" or "statistical adjustments" in the population register. 
- 2023 is especially tricky: SCB conducted a mass deregistration of people with expired residence permits, which inflated the emigration count. Some sources report 55,209 net, others 21,080. The truth depends on whether you count deregistrations as emigration.
- **DECISION**: Used Eurostat flow data for consistency across European countries. This may undercount 2021-2022 by ~10K due to missing statistical adjustments.
- 2024: Used press reports (immigration 116,197 - emigration 86,449 = 29,748).

### Switzerland: 2023 spike is a reclassification artifact
- The 2023 net migration of ~139K is partly artificial: ~50K Ukrainians who arrived in 2022 with temporary S-status were reclassified into the permanent resident population after 12 months. This counts as "immigration" in the statistics even though they were already physically present.
- Eurostat CNMIGRAT (residual method) used rather than Eurostat flow data, because flow data shows implausibly low net migration (~15K for 2018-2019) that doesn't match BFS press releases or population growth.

### UK: Methodology break at 2021
- Pre-2021: International Passenger Survey (IPS) based estimates
- 2021+: Admin-based RAPID estimates using DWP Registration and Population Interaction Database
- ONS explicitly warns these are not directly comparable
- Year ending June (not calendar year). YE June figures mapped to the later calendar year (e.g., YE Jun 2023 → "2023")
- The peak was actually YE March 2023 at 944K, but YE June 2023 was 924K
- YE December 2024 revised down to 345K (from provisional 431K)

### Canada: Massive NPR component
- Canada's net migration is dominated by Net Non-Permanent Residents (NPR), which was 789K in 2023 alone
- 2025 shows negative total net migration (-134K) driven by NPR exodus (-462K) as temporary resident caps took effect
- This is the most dramatic reversal in any country in the dataset

### Germany: 2022 Ukraine spike
- The 1.46M net migration in 2022 is register-based (Destatis). Eurostat's residual method shows only 209K for the same year — a >1.2M discrepancy. The register-based Destatis figure is authoritative for Germany.

### Australia: Financial year mapping
- ABS reports by financial year (July-June). FY2017-18 mapped to 2018, FY2018-19 to 2019, etc.
- FY2020-21 was negative (-85K) due to border closures

### Ireland: Year ending April
- CSO reports year ending April. The year label used by CSO is used here.
- Pre-2023 figures from Wikipedia vital statistics table (sourced from CSO but may have been revised)

### Spain: INE vs Eurostat — perfect match
- INE's "saldo migratorio con el exterior" matches Eurostat flow data exactly for 2018-2023, confirming data quality.
- 2024 from INE press release (Dec 2025).

### Netherlands: CBS API data
- Pulled directly from CBS OpenData API (dataset 83474ENG), fully automated and verifiable
- "Emigration including administrative corrections" used (standard CBS definition)
- 2025 is provisional (all months available but subject to revision)
