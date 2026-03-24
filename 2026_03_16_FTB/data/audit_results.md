# Audit: FTB Long-Run Chart Data and Methodology

**Date**: 2026-03-20
**Files audited**:
- `scripts/ftb_longrun_chart.py` (chart with hardcoded data)
- `scripts/ms2_method_proper.py` (CPS MS-2 computation)
- `scripts/psid_ftb_proper.py` (PSID rent-to-own transitions)
- `data/ms2_method_proper.json` (MS-2 output)
- `data/acs_direct_marriage_age.json` (ACS marriage output)
- `data/psid_ftb_transitions.json` (PSID output)

---

## 1. DATA TRACEABILITY: Hardcoded Values vs. Source JSON Files

### Marriage (CPS MS-2, 1976-2007): PASS
All 32 hardcoded values (1976-2007) match `data/ms2_method_proper.json` exactly.

### Marriage (ACS direct, 2008-2023): PASS
All 16 hardcoded values (2008-2023) match `data/acs_direct_marriage_age.json` exactly.

### Headship (CPS MS-2, 1976-2025): PASS
All 50 hardcoded values match `data/ms2_method_proper.json` exactly, including 2024-2025.

### Ownership (PSID, 1974-2023): PASS
All 36 hardcoded values match `data/psid_ftb_transitions.json` median column exactly.

---

## 2. MS-2 Methodology Audit (`scripts/ms2_method_proper.py`)

### 2a. "Permanently never" share from ages 45-54: CORRECT
The script averages the proportion who have "never experienced X" across ages 45-54 (line 55-58). This is the standard Shryock & Siegel approach. The age range 45-54 is appropriate for marriage (fertility window closing, most first marriages have occurred). For headship it is also reasonable though headship can change at any age.

### 2b. Target threshold P/2: CORRECT
`prop_eventual = 1 - perm_never` (line 59), then `target = prop_eventual / 2` (line 65). This correctly halves the eventual-experiencer share, not the total population.

### 2c. Interpolation: CORRECT
The threshold is converted to `threshold = 1 - target` (line 71), then the script walks ages looking for where S_a drops below that threshold. Linear interpolation: `fraction = (prev_s - threshold) / (prev_s - s_a)` applied to `prev_age + fraction` (lines 82-83). This is standard and correct.

### 2d. Population scope: ALL ADULTS -- CORRECT for marriage, DEBATABLE for headship
The query (line 33-41) filters `AGE BETWEEN 15 AND 54` with no restriction on relationship to household head. This is correct for marriage (MS-2 should use all adults). For headship, using all adults is also the right approach for the MS-2 method since you need the full age distribution of "not yet head" vs "head/spouse".

### 2e. Weight usage: CORRECT
Uses `ASECWT` (person-level ASEC supplement weight) throughout. This is the correct weight for CPS ASEC person-level tabulations.

### 2f. MARST=6 for "never married": CORRECT
IPUMS CPS codes MARST=6 as "Never married/single." This is the correct code.

### 2g. RELATE codes 101, 201, 202, 203 for head/spouse: CORRECT
- 101 = Head/Householder
- 201 = Spouse
- 202 = Opposite sex spouse (post-2019)
- 203 = Same sex spouse (post-2019)

Including 202/203 is appropriate to capture all spouses after IPUMS recoded them.

---

## 3. ACS Direct Marriage Measure

### 3a. Missing computation script: FLAG
There is no script in `scripts/` that generates `data/acs_direct_marriage_age.json`. The chart source line references "ACS direct (YRMARR)" but the computation script is not preserved in this project folder. This is a reproducibility gap -- the ACS direct marriage values cannot be regenerated from the scripts in this project.

### 3b. Variable usage (from chart source note: YRMARR)
The chart references YRMARR (year of first marriage) from the ACS. The standard approach would be: filter to persons where `YRMARR == survey_year` (married for the first time in the survey year), then take the median age. This is conceptually cleaner than MS-2 for recent years because it directly observes first marriages rather than inferring them from cross-sectional proportions.

Note: IPUMS ACS variable YRMARR is available 2008+ (derived from MARRINYR and related questions). An alternative approach uses MARRNO=1 (first marriage) combined with MARRINYR=2 (married in last year). Both should yield the same result. Without the script, this cannot be verified.

---

## 4. PSID Methodology Audit (`scripts/psid_ftb_proper.py`)

### 4a. Transition logic: CORRECT but with caveats
The script correctly:
- Links persons across waves via ER30001+ER30002 (stable person identifiers)
- Requires a rent observation (own_rent=5) BEFORE the first own observation (own_rent=1)
- Filters to household heads only (relation=1)

### 4b. Head-only restriction: METHODOLOGICAL CONCERN
The script filters `relation = 1` (heads only) when building the panel (line 161). This means:
- A person who becomes an owner while being a spouse or child in someone else's household is EXCLUDED
- The "first time buyer" is really "first time head-of-owner-household"
- This conflates headship with ownership and could bias upward (people may own before becoming head, e.g., as a spouse)

### 4c. Sample sizes: ADEQUATE but modest
Sample sizes range from 70 (1969, excluded from chart) to 407 (2021). Most years have 120-350 transitions. These are unweighted counts. The PSID medians are reported as integers (no decimal precision), reflecting the small-sample limitation. A confidence interval of +/-2-3 years is likely for many years.

### 4d. No survey weights used: FLAG
The PSID script computes unweighted medians. PSID longitudinal weights should be applied for nationally representative estimates. This could introduce bias if attrition or oversampling (e.g., the SEO oversample of low-income families) affects the age distribution of transitions.

### 4e. Own/rent coding: own_rent=1 for own, own_rent=5 for rent
This is the standard PSID tenure coding. Correct.

---

## 5. Methodological Issues and Potential Criticisms

### 5a. CRITICAL: Headship MS-2 measures a reversible state
The MS-2 method was designed for irreversible events (marriage, death). Headship is reversible -- someone can be a head at 25, move back with parents at 28, then become head again at 30. The "never been head" rate at ages 45-54 captures people who are *currently* not heads, not people who have *never* been heads. This makes the headship MS-2 a "current headship median" rather than a "first headship median." The script's own documentation (line 16-17) acknowledges this limitation.

**Impact**: The headship MS-2 likely understates the true median age of first headship slightly, because some 45-54 year olds who *have* been heads are currently coded as non-heads, inflating the "permanently never" share and thus lowering the P/2 target.

### 5b. Marriage MS-2 vs ACS direct: Systematic gap at splice point
The chart splices CPS MS-2 (1976-2007) with ACS direct (2008-2023) at 2008. In the overlap years where both are available:
- 2008: MS-2=26.5, ACS=25.8 (gap=0.7)
- 2012: MS-2=27.2, ACS=26.4 (gap=0.8)
- 2019: MS-2=28.5, ACS=27.5 (gap=1.0)
- 2021: MS-2=29.2, ACS=27.6 (gap=1.6)

The gap grows over time (0.5-0.7 in early years, 1.0-1.6 by 2020s). This means:
1. The two methods are not measuring exactly the same thing
2. The splice introduces a **level shift downward** at 2008 -- the series appears to flatten/slow when it actually continued rising per the MS-2 measure
3. A reviewer could argue the splice is misleading because it understates post-2008 marriage age growth

The chart does mark the splice with a dot at 2008, which is good practice. But the growing divergence between the two methods means they are not equivalent measures.

### 5c. MS-2 marriage rising faster than ACS direct in recent years
The MS-2 marriage median reaches 29.2 by 2021 while the ACS direct measure shows only 27.6. This 1.6-year gap likely reflects:
- Rising "permanently never married" share among 45-54 year olds (driven by delayed marriage cohorts aging in), which pushes down the P/2 target and thus the MS-2 median
- The ACS direct measure captures actual first marriages in a given year, unaffected by cohort composition
- The MS-2 method may be increasingly distorted as the assumption of a "stable" never-married ceiling breaks down

### 5d. PSID ownership median is integer-valued
All PSID values are whole numbers (27, 28, 29...) while marriage and headship are reported to one decimal. This is a visualization artifact -- the PSID line appears "steppy" while the other lines are smooth. The integer precision reflects small sample sizes where the median falls on an observed age.

### 5e. Chart title says "1974-2025" but marriage/headship don't extend to 2025
- PSID: 1974-2023
- Marriage: 1976-2023
- Headship: 1976-2025

Only headship extends to 2025. The title implies all three series run through 2025.

### 5f. Chart label says "Marriage (CPS)" but 2008+ is ACS
The inline label for the marriage series says "(CPS)" but from 2008 onward the data source is ACS. The source note at the bottom correctly distinguishes the two, but the inline label is misleading.

### 5g. No confidence intervals or smoothing
Given PSID sample sizes of 100-400 unweighted observations per year, year-to-year fluctuations of 2-3 years in the median are within sampling noise. The 1994 spike to 35 (from 32 in 1993) is likely noise, not a real phenomenon. A reviewer might request bootstrapped confidence bands or 3-year moving averages.

---

## 6. Summary of Findings

| Check | Status |
|-------|--------|
| Chart values match source JSONs | PASS (all 4 series) |
| MS-2 methodology correct | PASS |
| MARST=6, RELATE codes correct | PASS |
| ASECWT weights used (CPS) | PASS |
| ACS computation script exists | FAIL (missing from project) |
| PSID uses survey weights | FAIL (unweighted) |
| Marriage splice introduces level shift | FLAG (growing gap, 0.5-1.6 yrs) |
| Headship MS-2 applied to reversible state | FLAG (acknowledged limitation) |
| PSID filters to heads only | FLAG (conflates headship with ownership) |
| Chart label accuracy | FLAG ("CPS" label covers ACS data post-2008) |
| Title date range accuracy | FLAG (implies all series to 2025) |
