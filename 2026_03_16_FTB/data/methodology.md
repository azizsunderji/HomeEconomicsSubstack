# FTB Age Analysis: Detailed Methodology

*Last updated: 2026-03-21*

---

## Section 1: The PSID Measurement

### What Is the PSID?

The Panel Study of Income Dynamics (PSID) is a longitudinal household survey conducted by the University of Michigan's Institute for Social Research. Launched in 1968, it is the longest-running household panel survey in the world. The original sample comprised roughly 5,000 families, and the study has followed these families and their descendants ever since. When children in PSID families grow up and form their own households, they become new PSID "splitoff" families and continue to be tracked.

The PSID is nationally representative, but with one important structural feature: it includes a Survey of Economic Opportunity (SEO) oversample of low-income families, originally designed to study poverty dynamics. This means low-income households are overrepresented in the raw data. Population-level analyses typically apply survey weights to correct for this; our analysis does not apply weights (see discussion below).

### How We Construct Person Identifiers

Every individual in the PSID is uniquely and permanently identified by two variables from the 1968 cross-year individual file:

- **ER30001**: The 1968 Interview Number (identifies the original family the person belongs to)
- **ER30002**: The Person Number within that family

We concatenate these as `ER30001 + "_" + ER30002` to create a stable person key (e.g., "3042_2"). This identifier never changes, regardless of which family unit the person lives in during subsequent waves. This is the foundation of all person-level longitudinal tracking in the PSID.

### The Cross-Year Individual File

The PSID provides a "cross-year individual file" that contains one row per person who has ever appeared in the study. For each survey wave, this file contains variables indicating:

- **Interview Number**: Which family unit the person belonged to in that wave (allows joining to the family-level data file for that year)
- **Age**: The person's age in that wave
- **Relation to Head**: Whether the person was the household head (code 1 or 10), spouse/partner (code 2, 20, or 22), child, or other relation

The variable names change across waves. For example, the interview number column is `ER30001` in 1968, `ER30020` in 1969, `ER33101` in 1994, and `ER35101` in 2023. Our script (`scripts/psid_ftb_proper.py`) contains a complete mapping of 43 waves from 1968 to 2023, specifying the interview number, age, and relation-to-head variable names for each year.

### How We Identify Rent-to-Own Transitions

The process involves joining two PSID data sources for each wave:

1. **Cross-year individual file**: Provides person tracking (person key), age, and relation to head
2. **Family files** (one per wave): Provide household-level variables including tenure status (own vs. rent)

For each wave, we:
1. Extract each person's interview number, age, and relation to head from the cross-year file
2. Join to the corresponding family file on interview number to obtain the household's tenure status
3. Filter to household heads only (relation to head = 1)
4. Record whether the household owns (code 1) or rents (code 5)

This produces a person-year panel: for each person, we observe their tenure status in every wave they appear.

### Definition of "First-Time Buyer"

A person is classified as a first-time buyer in year Y if:

1. They are the **head** of their household in year Y (we restrict to heads to avoid counting children living in their parents' owned home)
2. Their household **owns** in year Y (tenure code = 1)
3. They were observed **renting** in at least one prior wave (tenure code = 5)
4. Year Y is the **first year** they appear as an owner, after having been observed as a renter

The critical requirement is #3: we must observe the person renting before they own. This is the left-censoring filter. A person who appears as an owner in their very first observation is excluded -- we cannot know if they are a first-time buyer or a long-time owner.

### Why This Measure Is Superior

The PSID approach is arguably the gold standard for measuring first-time homebuyer age because:

- We literally watch the same person go from renting to owning for the first time
- It is not based on self-reported "first-time buyer" status (which can be inaccurate)
- It is not based on mortgage origination records (which miss cash buyers and misclassify people whose prior mortgages are no longer on file)
- It captures the actual transition, not a synthetic cohort estimate
- The longitudinal design means we know the person's full housing history within the panel

### Wave Structure

- **1968-1997**: Annual interviews (30 waves)
- **1997-2023**: Biennial interviews (13 waves: 1999, 2001, 2003, ..., 2023)

The shift to biennial interviewing after 1997 has two implications:
1. We only observe transitions every 2 years, so a person who rented in 2017 and bought in 2018 would be recorded as a 2019 transition (their age in 2019, not 2018)
2. Sample sizes per wave are larger in the biennial era because transitions accumulate over 2 years instead of 1

### Left-Censoring

In 1968 (the first wave), everyone enters the panel fresh. We have no information about their prior housing history. A 45-year-old who appears as a renter in 1968 and buys in 1970 would be classified as a first-time buyer at age 47, even though they may have owned a home in 1960.

Our left-censoring filter (requiring prior rental observation) mitigates this, but it means:
- The first few waves (1968-1973) are unreliable because people haven't been observed long enough
- Our first reliable FTB observations begin around 1974-1976, when people who entered as young renters in 1968 have had enough time to potentially buy
- Early-wave medians are biased upward (1969 shows median 46, which is artifactual)
- We trim results to 1974+ for reporting

### Sample Sizes

From the `psid_ftb_transitions.json` data, the number of rent-to-own transitions (all transitions, including boomerang buyers) per wave:

| Period | Typical N per wave | Notes |
|--------|-------------------|-------|
| 1974-1989 (annual) | 129-198 | Smaller because annual; transitions accumulate over only 1 year |
| 1991-1997 (annual) | 152-368 | Larger due to Latino supplement additions |
| 1999-2023 (biennial) | 248-407 | Larger because transitions accumulate over 2 years |

From the `boomerang_buyers.json` data, the true FTB counts (excluding boomerang buyers):

| Period | Typical true FTB N per wave |
|--------|----------------------------|
| 1984-1989 | 255-392 |
| 1991-1997 | 229-480 |
| 1999-2023 | 349-587 |

With 250-500 true FTBs per wave, the standard error on the median is approximately 1-2 years. This means individual year-to-year movements of 1 year are within noise, but sustained trends of 2+ years over multiple waves are meaningful.

### The SEO Oversample

The PSID's SEO component oversamples low-income families. We do not apply survey weights in our analysis. How might this affect results?

- Low-income families may buy later in life (affordability constraints delay purchase)
- But low-income families are also less likely to ever buy, meaning they may not appear in our FTB sample at all
- The net effect is ambiguous: the oversample may pull FTB ages slightly upward (those low-income families who do buy, buy later), but this effect is partially offset by the fact that many never buy and are thus excluded
- Since we track trends over time (not absolute levels), the bias is roughly constant across waves and does not meaningfully affect the direction or magnitude of trends
- Comparison with AHS (which uses survey weights) shows similar levels and trends, suggesting the weighting issue is not large

### Known Issues: 1991-1994

The PSID added a Latino supplement sample in 1990-1992. These new sample additions entered the panel as adults, many already homeowners or with housing histories we cannot observe. This contaminates the left-censoring filter:

- 1991-1994 show elevated N (up to 368 vs. typical 150 in annual waves)
- 1994 shows a median FTB age of 35, a clear outlier compared to 29-31 in surrounding years
- This spike is likely artifactual, driven by supplement sample members being misclassified as first-time buyers

We flag 1991-1994 in our charts and note the likely contamination. The trend before (28-30 in late 1970s/1980s) and after (32-33 in late 1990s/2000s) is consistent and unaffected by the supplement.

---

## Section 2: The CCP Error Correction Model

### What Is the CCP?

The NY Fed's Consumer Credit Panel (CCP) is a longitudinal dataset derived from Equifax credit records. It constitutes a 5% random sample of all U.S. individuals with a Social Security number and a credit file. The CCP identifies first-time homebuyers as individuals who have a new mortgage appear on their credit report with no prior mortgage on file.

The CCP data begins in 1999. Results from the CCP have been widely cited, particularly through the NY Fed's Liberty Street Economics blog, showing a median first-time homebuyer age of roughly 34-35 that has been approximately flat since 2000.

### Joelle Scally's Confirmation

On March 16, 2026, Joelle Scally (NY Fed, manager of the CCP) confirmed via email the known limitations of the CCP for FTB measurement:
1. Left-censoring: Pre-1999 mortgages are invisible
2. Cash buyers are excluded
3. The CCP cannot distinguish primary residence purchases from investment properties

### Bias 1: Left-Censoring (Pushes Early Numbers UP)

**The problem:** The CCP begins in 1999. Any mortgage that was originated and paid off before 1999 is invisible. This means a person who owned a home in the 1990s, paid off or sold the mortgage, and then buys again in 2001 would appear as a "first-time buyer" in the CCP even though they are actually a repeat buyer.

**Who is affected:** Homeowners who were "free and clear" (owned without an active mortgage) when the CCP snapshot began. These tend to be older, long-time owners.

**Magnitude estimation:**
- From ACS data, 32-42% of owner-occupied homes are free and clear (no mortgage)
- Not all of these owners are actively buying; only a small fraction re-enter the market in any given year
- We estimate the contamination rate as ~12% of observed FTB volume in 2000, decaying over time as the CCP accumulates more history

**Decay assumption:** We model this as an exponential decay with a 5-year half-life. The logic: as time passes, the pool of people with pre-1999 mortgages that have since disappeared shrinks (they age out, die, or their subsequent transactions become visible within CCP history). By 2010 (~2 half-lives), contamination drops to ~3%. By 2015, it is negligible (~1%).

**This is an ASSUMPTION, not a measured quantity.** The 5-year half-life is a modeling choice. The true decay rate could be faster or slower.

### Bias 2: Boomerang Buyers (Pushes Numbers UP, Decays Over Time)

**The problem:** Some people who appear as first-time buyers in the CCP are actually "boomerang buyers" -- people who previously owned a home, returned to renting (due to foreclosure, divorce, relocation, etc.), and then purchased again. If their prior mortgage was before 1999 or otherwise not on their credit file, the CCP classifies them as first-timers.

**What we MEASURED from the PSID:**
- Roughly 32% of all rent-to-own transitions in the PSID are from people who previously owned as head or spouse (boomerang buyers)
- This rate is remarkably stable over time: 25-42% across waves from 1985 to 2023
- Boomerang buyers are significantly older: median age 37-47 (rising over time), vs. true FTBs at 29-34
- The age gap between boomerang buyers and true FTBs is 8-14 years

**Which boomerangs contaminate the CCP?** Only the pre-1999 portion. A person who owned in 1995, rented 1997-2003, and bought again in 2003 would have no prior mortgage in the CCP and would be misclassified as a first-timer. But a person who owned in 2005, rented 2008-2012, and bought in 2012 would have their 2005 mortgage on file and be correctly classified as a repeat buyer.

**Decay assumption:** We assume the fraction of boomerang buyers with pre-1999 prior ownership decays linearly over 15 years (2000-2015). By 2015, essentially all boomerang buyers' prior ownership histories fall within the CCP window and they are correctly excluded.

**This is an ASSUMPTION.** The linear decay and 15-year window are modeling choices.

**What we ASSUMED vs. MEASURED here:**
- MEASURED: The overall boomerang rate (~32%) and boomerang ages (from PSID)
- ASSUMED: That PSID boomerang rates and ages are representative of the broader population
- ASSUMED: The temporal decay of pre-1999 contamination

### Bias 3: Cash Buyer Exclusion (Pushes Recent Numbers DOWN)

**The problem:** The CCP only observes mortgage originations. Buyers who purchase homes with cash (no mortgage) are completely invisible. Since the CCP defines FTBs by the appearance of a first mortgage, cash FTBs are excluded.

**Why this matters for age measurement:** Cash buyers tend to be older. They have had more time to accumulate savings, receive inheritances, or sell prior assets. If older FTBs disproportionately pay cash, the CCP's observed average age is biased downward (younger than reality).

**Trend:** The cash share of home purchases has risen substantially:
- ~10% of purchases were all-cash in the early 2000s
- ~30% of purchases were all-cash by the 2020s (NAR, Redfin data)

**Assumptions:**
- Cash FTB share grew from 5% to 15% over 2000-2025 (lower than overall cash share because FTBs are younger and less likely to have cash)
- Cash FTBs have a median age of ~42-47 years (substantially older than mortgage FTBs)

**Both of these are ASSUMED, not directly measured.** We do not have a direct data source on the age distribution of cash-only first-time homebuyers.

### The Correction Formula

We apply a three-step correction to the CCP's observed average FTB age:

**Step 1: Remove contamination from boomerang and left-censored buyers**

```
corrected_avg = (CCP_observed_avg - boom_rate * boom_avg_age - left_rate * left_avg_age) / true_ftb_share
```

Where:
- `CCP_observed_avg` = The average FTB age reported by the CCP
- `boom_rate` = Estimated fraction of CCP "FTBs" who are actually boomerang buyers with pre-1999 histories
- `boom_avg_age` = Average age of boomerang buyers (from PSID)
- `left_rate` = Estimated fraction of CCP "FTBs" who are misclassified due to left-censoring
- `left_avg_age` = Estimated average age of left-censored contamination
- `true_ftb_share` = 1 - boom_rate - left_rate

**Step 2: Add back cash buyers**

```
final_avg = (1 - cash_share) * corrected_avg + cash_share * cash_avg_age
```

Where:
- `cash_share` = Estimated share of true FTBs who pay cash
- `cash_avg_age` = Estimated average age of cash FTBs

**Step 3: Convert average to median**

```
final_median = final_avg - avg_median_gap
```

The average-to-median gap is estimated from published CCP data and AEI tabulations:
- ~2.9 years in 2000 (younger right tail)
- ~3.5 years in 2024 (expanding right tail as some FTBs buy very late)

### Results

| Year | CCP Observed Avg | CCP Corrected Avg (est.) | CCP Corrected Median (est.) | PSID True FTB Median |
|------|-----------------|-------------------------|----------------------------|---------------------|
| 2000 | 34.5 | ~35 | ~32 | 33 (1999 wave) |
| 2005 | 35.8 | ~35 | ~32 | 32 (2005 wave) |
| 2010 | 35.4 | ~35 | ~32 | 31 (2011 wave) |
| 2015 | 36.5 | ~36 | ~33 | 32 (2015 wave) |
| 2020 | 37.0 | ~37 | ~34 | 34 (2021 wave) |
| 2025 | 37.8 | ~38 | ~34 | 33-34 (2023 wave) |

Key findings:
- **Uncorrected CCP median**: ~35 (2000) to ~34 (2025) = approximately flat
- **Corrected CCP median**: ~32 (2000) to ~34 (2025) = rising approximately +2 years
- **PSID true FTB median**: 32-33 (1999) to 33-34 (2023) = rising approximately +2 years
- The corrected CCP aligns with the PSID longitudinal measure

### Measured vs. Assumed Inputs

| Input | Source | Type |
|-------|--------|------|
| Boomerang buyer rate (~32%) | PSID longitudinal tracking | MEASURED |
| Boomerang buyer median age (37-47) | PSID longitudinal tracking | MEASURED |
| CCP observed average age (34.5-37.8) | Liberty Street Economics / NY Fed | MEASURED |
| Free-and-clear owner rate (32-42%) | American Community Survey | MEASURED |
| CCP average-to-median gap (2.9-3.5 yrs) | NY Fed and AEI publications | MEASURED |
| Left-censoring decay rate (5-yr half-life) | Modeling assumption | ASSUMED |
| Left-censoring initial contamination (12%) | Modeling assumption | ASSUMED |
| Cash FTB share (5% to 15%) | Modeling assumption | ASSUMED |
| Cash FTB median age (42-47) | Modeling assumption | ASSUMED |
| Boomerang pre-1999 fraction decay (linear, 15 yrs) | Modeling assumption | ASSUMED |
| PSID boomerang rates representative of population | Structural assumption | ASSUMED |

---

## Section 3: Validation

### 1. AHS Cross-Validation

The American Housing Survey (AHS) directly asks homeowners whether their current home is their first home ever owned and their age at purchase. This provides an independent measure of FTB age.

Comparison of PSID and AHS:
- Both show median FTB age of approximately 30 in the late 1980s
- Both show a gradual rise to 32-34 by 2023
- The AHS shows the sharpest increase after 2013 (from 30 to 34), which aligns with the PSID's movement from 31-32 to 33-34 over the same period
- The two sources are independent: PSID is longitudinal panel tracking; AHS is cross-sectional self-report

### 2. Corrected CCP Alignment

As detailed in Section 2, after correcting for the three known biases in the CCP:
- The corrected CCP median tracks the PSID measure within 1-2 years across the entire 2000-2023 overlap period
- Both show a true FTB median of approximately 32 in 2000, rising to 33-34 by 2023
- This convergence of a corrected administrative dataset (CCP) with a longitudinal survey (PSID) increases confidence in both measures

### 3. ACS Direct Marriage Age Validates CPS MS-2

For marriage age, we use two methods:
- **CPS MS-2 method** (1976-2007): A synthetic cohort approach based on the proportion married at each age, adjusted for the "permanently never married" share
- **ACS direct measurement** (2008-2023): The ACS variable YRMARR directly asks the year of first marriage, allowing exact computation of median age at first marriage

In overlapping years (2008-2013), the CPS MS-2 method and ACS direct measurement produce results within 0.5-1.5 years of each other, with the MS-2 method slightly overstating. This confirms that:
- The MS-2 method is a reasonable approximation
- Cross-survey validation (using one survey to check another) produces meaningful results
- The general approach of combining multiple imperfect data sources is sound

### 4. Stanford Center on Longevity (NLSY)

A paper from the Stanford Center on Longevity ("Generational Shifts in Age and Predictors of Homeownership") uses the National Longitudinal Survey of Youth (NLSY) -- a different longitudinal dataset from the PSID -- and finds consistent patterns:
- The gap between marriage and homeownership was approximately 6 years for older cohorts
- The gap narrowed to approximately 4 years for more recent cohorts
- Ownership ages have risen across generations

This provides independent longitudinal confirmation from a completely separate panel study that homeownership ages have indeed increased.

### Summary of Validation

| Validation | What It Shows | Confidence |
|------------|--------------|------------|
| PSID vs. AHS | Both show FTB age ~30 in 1980s, rising to 33-34 by 2023 | HIGH: Independent sources, same result |
| Corrected CCP vs. PSID | After bias correction, CCP matches PSID within 1-2 years | MODERATE: Depends on correction assumptions |
| ACS direct vs. CPS MS-2 | Marriage age methods agree within 1.5 years | HIGH: Ground-truth validation of methodology |
| NLSY vs. PSID | Different longitudinal panels show consistent ownership age trends | HIGH: Fully independent replication |
