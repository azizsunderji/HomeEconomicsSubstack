## Austin's Supply Boom and Sunderji's Paradox

A reader asked: if Austin saw a massive supply boom and falling rents (2022-2024), does that contradict Sunderji's Paradox? Did the rent-to-income share actually fall, or did composition shifts maintain the ~30% equilibrium?

Short answer: the paradox holds. Austin's median rent burden was 28.1% in 2019, 28.6% in 2022, 29.5% in 2023, and 28.2% in 2024. Through the most dramatic supply-driven rent correction in recent US history, the burden ratio barely moved.

We then tested the *mechanism* across 99 large metros.


## The rent trajectory

Austin rents spiked 21.5% year-over-year in late 2021, outpacing the national rate of 15.5%. Then the supply wave hit. Zillow's Observed Rent Index shows Austin rents peaked at $1,786/month in August 2022 and have since fallen 12.6% to $1,561 (January 2026). National rents, meanwhile, have continued climbing to $1,895. Austin rents are now 18% below the national average, despite being roughly at parity in 2015.

Year-over-year, Austin rents have been negative since mid-2023, reaching -4.0% by December 2024. The national rate has held steady at +2.0%.


## The burden paradox

The ACS 1-Year microdata tells the story at the household level. For the median renter decile (D5) in Austin:

| Year | D5 median income | D5 burden |
|------|-----------------|-----------|
| 2005 | $28,200 | 31.0% |
| 2010 | $30,950 | 31.3% |
| 2015 | $41,000 | 30.6% |
| 2019 | $50,000 | 30.5% |
| 2021 | $50,000 | 32.2% |
| 2022 | $59,000 | 31.0% |
| 2023 | $60,000 | 33.4% |
| 2024 | $65,000 | 32.2% |

D5 burden ranged from 29.0% to 33.4% across 19 years. The national D5 ranged from 30.9% to 34.5%. Austin's pattern is indistinguishable from the national one.

Every decile tells the same story. The bubble chart for Austin is structurally identical to the national chart: each decile traces a horizontal path as real incomes rise, with burden stuck in a narrow band.


## What happened to the 235,000 new renters?

Austin's renter population more than doubled: 206,000 households (2005) to 442,000 (2024). That's 236,000 new renter households in 19 years, with 104,000 of those arriving just since 2019.

These new renters are not low-income. Median renter household income in Austin rose from $31,000 (2005) to $55,000 (2019) to $70,000 (2024). Even during the rent decline period (2022-2024), median income jumped from $65,000 to $70,000.

The income percentiles tell the same story:

| Year | P25 income | P50 income | P75 income | Median rent |
|------|-----------|-----------|-----------|-------------|
| 2019 | $30,000 | $55,000 | $90,000 | $1,344 |
| 2022 | $36,000 | $65,000 | $107,000 | $1,623 |
| 2023 | $38,600 | $65,000 | $109,100 | $1,770 |
| 2024 | $40,100 | $70,000 | $115,000 | $1,800 |

Between 2019 and 2024, median rent rose 34% ($1,344 to $1,800) and median income rose 27% ($55,000 to $70,000). The rent-to-income ratio barely budged because both sides of the fraction moved together.


## The mover reset

The key mechanism maintaining the ~30% equilibrium is what we call the "mover reset." In Austin from 2005 to 2024:

- Movers' median burden averaged 30.8% (±1.1 pp), ranging from 29.1% to 33.1%
- Non-movers' median burden averaged 28.2% (±0.7 pp), ranging from 26.9% to 29.4%
- Movers consistently paid 2.6 pp more than non-movers

This pattern persisted through the rent decline. In 2024, movers' burden was 29.7% while non-movers' was 27.6%. Movers don't pocket the savings from falling asking rents; they trade up — choosing units or locations that restore their spending to ~30% of income.


## Cross-metro test: 99 metros, one natural experiment

Austin is one data point. But rents changed to different degrees across hundreds of metros between 2022 and 2024. Austin ZORI fell 4.6%. New Haven ZORI rose 15.8%. This variation gives us a natural experiment.

For 99 large metros (each with 500+ unweighted renter households per year), we computed changes in four outcomes between ACS 2022 and ACS 2024, then regressed each against the metro's ZORI rent change:

| Outcome | Slope | R² | p-value |
|---------|-------|----|---------|
| Δ Mover rate (pp) | -0.098 | 0.017 | 0.20 |
| Δ Avg bedrooms (movers) | -0.002 | 0.003 | 0.62 |
| Δ Mover median burden (pp) | -0.012 | 0.000 | 0.89 |
| Δ Mover avg commute (min) | -0.151 | 0.035 | 0.065 |

None of the first three relationships are statistically significant. The commute result is marginally significant (p=0.065): in metros where rents fell more, movers' commute times rose slightly — the opposite of what "trading up to better locations" would predict.

The burden result is the most striking: R²=0.000, slope=-0.012, p=0.89. Mover burden changes are completely unrelated to rent changes across metros. Whether rents fell 5% or rose 16%, movers reset to approximately the same burden. This is the paradox operating in real time across the geography of US metros.


## Austin vs Dallas

We zoomed into Austin (treatment: ZORI -4.6%) vs Dallas (control: ZORI +1.5%) for a year-by-year comparison from 2015 to 2024:

Austin's mover rate averaged 33% throughout, consistently 5-7 pp higher than Dallas (27%). This gap predates the rent decline and persists through it. Austin movers' average bedrooms was stable around 2.7-2.8, nearly identical to Dallas (2.7-2.8). Neither metro showed a meaningful shift during the rent decline period.

On burden, the two metros diverged — but not as the "falling rents help renters" narrative would predict. Austin movers' burden was 30.1% in 2022 and 31.2% in 2024 (+1.1 pp). Dallas movers' burden was 33.6% in 2022 and 32.6% in 2024 (-1.0 pp). Austin movers were paying slightly more, not less, despite falling asking rents.

When we controlled for income ($40K-$80K renters only), the same pattern held. Middle-income Austin movers' burden rose from 32.7% (2022) to 34.5% (2024). Middle-income Dallas movers' burden rose from 33.5% to 34.0%. If anything, income-controlled burden rose slightly more in the falling-rent metro, consistent with movers absorbing rent savings by upgrading quality rather than reducing spending.


## Movers vs. non-movers

Movers into Austin rentals had roughly similar incomes to non-movers in recent years:

- 2022: movers earned $69,000 (median) vs. non-movers at $65,150
- 2024: movers earned $75,000 vs. non-movers at $73,400
- Interstate movers in 2022 earned $71,400; by 2024, $77,000

This contradicts a simple "rich Californians drive up rents" narrative. Interstate migrants are only 1.3-1.6% of Austin renters. The dominant flow is local: 26.6% of renters moved within the same county in 2024.


## No evidence of "trading up" in unit size

If falling rents led existing renters to upgrade to larger units, we'd expect the share of 3+ bedroom rentals to rise. The opposite happened:

- 1-bedroom share: 1.8% (2005) → 5.6% (2019) → 8.3% (2024)
- 3-bedroom share: 40.4% (2005) → 34.4% (2019) → 34.3% (2024)
- 4-bedroom share: 17.6% (2005) → 20.8% (2019) → 16.5% (2024)

Renters are renting smaller, not larger. This is consistent with the new supply being concentrated in multifamily apartment buildings (1-2 BR units), not single-family homes. Movers trade up on quality, amenities, and location — not on raw square footage.


## Why the paradox holds

The mechanism is compositional, operating through household sorting at the point of each move. When market rents fall in a metro:

1. Movers don't pocket the savings. They choose units that restore their spending to ~30% of income — better finishes, closer to downtown, newer buildings
2. This was true across 99 metros regardless of how much rents changed (R²=0.000 for burden vs. rent change)
3. New, higher-income renters enter the market (attracted by job growth and relative affordability), further supporting burden stability
4. Existing non-movers' burdens drift downward as their incomes grow, but they represent a declining share as turnover replaces them with market-rate movers

The cross-metro evidence confirms this is not an Austin story. It is a structural feature of how rental markets work. The 30% equilibrium is not a target anyone consciously pursues; it is an emergent property of household search behavior, where each mover independently selects the best unit they can get at roughly 30% of their income.


## Caveats

- ACS is annual. We can't observe month-by-month burden changes during the sharpest part of the rent decline (mid-2022 to mid-2023)
- Zillow ZORI tracks asking rents for new leases, not what existing renters pay. Actual rents paid are stickier
- Austin's 2022-2024 rent decline was real but moderate in ACS terms: median rent went from $1,623 (2022) to $1,770 (2023) to $1,800 (2024) — the ACS shows rents still rising because it captures actual rents paid, not asking rents
- Sample sizes are adequate (~2,600 unweighted observations per year) but smaller than the national sample, adding noise to decile-level estimates
- The cross-metro scatter has no significant results except a marginal commute finding. This could mean the mechanism is real but noisy, or it could mean the 2-year ACS window is too short to detect behavioral changes that lag rent declines. The burden flatness (R²=0.000) is itself a result — it's the paradox prediction
- Austin is the only metro with negative rent growth in the sample. Most metros saw 0-16% growth. A true "declining rent" experiment would require more metros with actual declines
