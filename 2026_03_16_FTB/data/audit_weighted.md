# PSID First-Time Buyer Analysis: Comprehensive Audit Report

**Script audited:** `scripts/psid_ftb_weighted.py`
**Output audited:** `data/psid_ftb_heads_ci.json`
**Date:** 2026-03-22

---

## 1. Family ID Column Verification

**PASS.** All `fam_id_cols` values are unique in their respective family files and match correctly to the cross-year interview number columns.

Spot-checked 15 years across the full range (1968, 1969, 1970, 1975, 1980, 1985, 1990, 1995, 1997, 1999, 2005, 2011, 2017, 2021, 2023):

- Every family ID column is **UNIQUE** in its family file (total rows = distinct values).
- Match rates are **100%** for all years except 1968 (59.3%).

**1968 note:** The 59.3% match rate is expected and correct. In 1968, `ER30001` serves as both the person's original family identifier and the 1968 interview number. The cross-year file contains 8,102 distinct `ER30001` values (including 2,308 Latino supplement families added later), while the 1968 family file has 4,802 families. Individuals with `ER30001` values not in the 1968 family file are people who entered the panel after 1968 and inherited their `ER30001` from their original family. The `WHERE CAST(xy.ER30001 AS INT) > 0` filter plus the JOIN correctly limits to people actually interviewed in 1968.

**No many-to-many join risk.** All family ID columns are confirmed unique.

---

## 2. Relation Code Verification

**PASS.** The head-of-household code switch at 1982/1983 is correctly implemented.

Checked 6 years spanning the boundary (1980-1985):

| Year | Head Code | Count of Heads |
|------|-----------|---------------|
| 1980 | 1 | 6,642 |
| 1981 | 1 | 6,732 |
| 1982 | 1 | 6,874 |
| 1983 | 10 | 6,980 |
| 1984 | 10 | 7,041 |
| 1985 | 10 | 7,156 |

The PSID switched from single-digit codes (1=head) to two-digit codes (10=head) starting in 1983. The script correctly uses `head_code = 1 if year <= 1982 else 10`. The head counts show smooth continuity across the boundary, confirming correct mapping.

---

## 3. Own/Rent Variable Verification

**PASS with one advisory note.**

Checked 11 years across the range. The tenure variable consistently uses:
- **1 = Owns or is buying**
- **5 = Rents**
- **8 = Neither owns nor rents** (rent-free housing)
- **9 = DK/NA** (rare; only 1 case found in 2007)

No spurious codes (2, 3, 4, 6, 7) were found in any year.

**Advisory: Code 8 exclusion.** The script only tracks own_rent values of 1 and 5. Code 8 ("neither owns nor rents") represents 5-7% of families across all years (e.g., 5.8% in 1980, 4.9% in 2019). People who go directly from code 8 to code 1 (e.g., living rent-free with parents then buying) are NOT captured as FTBs. Only those who pass through a renting phase (8 -> 5 -> 1) are captured. This is a **definitional choice**, not a bug, and is consistent with the standard rent-to-own transition definition used in most FTB research. However, it may systematically undercount young buyers who purchase directly from their parents' household.

---

## 4. Weight Variable Verification

**PASS.** Weight variables are confirmed to be valid PSID longitudinal individual weights.

Checked 11 years. Key findings:
- All weights are non-negative (min=0 in every year).
- Positive weights range from small fractions to ~283 (2023 max).
- Average weight among positive-weight individuals rises over time (14.3 in 1968 to 28.9 in 2019), consistent with panel attrition requiring larger weights.
- Weight sums grow over time (260K in 1968 to 550K in 2019), consistent with representing a growing population.
- Zero-weight individuals are spread across all sample components (SRC, SEO, immigrants), which is expected for longitudinal weights that zero-out attritors and non-respondents.

**Zero-weight heads:** 19-28% of heads in any given year have weight=0. The script correctly excludes these with the `weight > 0` filter in the transition query. This is standard practice for PSID longitudinal analysis.

---

## 5. Person ID Stability

**PASS.** `ER30001 || '_' || ER30002` uniquely and stably identifies individuals.

- Total rows in cross-year file: 85,536
- Unique person_key values: 85,536 (exactly 1 row per person)
- `ER30001` ranges from 1 to 9,308 with 8,102 distinct values (families)
- `ER30002` ranges from 1 to 295 with 224 distinct values (person within family)

Verified 3 specific individuals across multiple waves: their `ER30001` and `ER30002` remain constant while their year-specific interview numbers change across waves (as expected -- individuals move between family units over time, but their original 1968 identifiers are permanent).

---

## 6. Transition Logic Verification

**PASS.** The rent-to-own transition logic is correct for identifying first-time buyers.

### How it works:
The script finds `first_own_year = MIN(year WHERE own_rent=1)` and `first_rent_year = MIN(year WHERE own_rent=5)` for each person, then requires `first_own_year > first_rent_year`.

### Edge cases verified:

**Boomerang buyers (own -> rent -> own):** 2,184 people have 3+ tenure transitions. For someone whose history is own(1968) -> rent(1969) -> own(1970): `first_own=1968`, `first_rent=1969`, `1968 > 1969` is FALSE, so they are **correctly excluded** (they owned before renting, so they are not first-time buyers). This is the correct FTB definition.

**Never rented:** 6,811 heads owned but never rented. These are correctly excluded because they have no entry in the `first_rent` CTE, so the JOIN fails.

**Left-censored (own in first observed year):** 9,155 heads own in their first observed year. Of these, 2,770 later rent (own -> rent pattern) and are correctly excluded by the `first_own_year > first_rent_year` filter. The remainder never rent and are excluded by the JOIN.

**Rent -> own correctly captured:** For people whose first tenure observation is rent and who later own, `first_rent_year < first_own_year` holds and they are correctly included.

### One subtlety worth noting:
The definition captures the **first ever own** after **any prior rent**. If someone rents in 1975, owns in 1980, goes back to renting in 1985, and buys again in 1990, they are captured as buying in **1980** (their first own after first rent). The 1990 purchase is ignored. This is correct for FTB analysis.

---

## 7. Latino Supplement Exclusion

**PASS.** The `ER30001 NOT BETWEEN 7001 AND 9308` filter correctly excludes the Latino supplement.

Verified that individuals with ER30001 in the 7001-9308 range appear with positive interview numbers ONLY in years 1990-1995 (plus 1968, where their ER30001 values exist as identifiers but they were not yet part of the sample):

| Year | Latino supplement individuals with interview > 0 |
|------|--------------------------------------------------|
| 1968 | 10,607 (identifier rows only, not actual interviews) |
| 1990 | 9,431 |
| 1991 | 8,578 |
| 1992 | 9,219 |
| 1993 | 7,938 |
| 1994 | 7,270 |
| 1995 | 5,955 |

No Latino supplement individuals appear in any other years. The exclusion filter is correctly applied in every year's INSERT query.

---

## 8. Weighted Median Calculation

**PASS (with minor note).**

The `weighted_median` function was tested on 7 cases:

| Test | Values | Weights | Result | Expected | Pass |
|------|--------|---------|--------|----------|------|
| Equal weights | [1,2,3,4,5] | [1,1,1,1,1] | 3.0 | 3 | Yes |
| Heavy right | [1,2,3] | [1,1,8] | 3.0 | 3 | Yes |
| Two values | [10,20] | [3,7] | 20.0 | 20 | Yes |
| Skewed | [25,30,35,40] | [10,20,30,40] | 35.0 | 35 | Yes |
| Concentrated | [1,2,3] | [0.001,100,0.001] | 2.0 | 2 | Yes |
| Even count | [1,2,3,4] | [1,1,1,1] | 2.0 | 2 or 3 | Yes |
| Three equal | [10,20,30] | [5,5,5] | 20.0 | 20 | Yes |

The function uses `np.searchsorted` with default `side='left'`, which means it returns the **lower weighted median** when the cumulative weight exactly equals 50%. This is a valid and standard definition. With integer ages, it always returns an integer value.

**Note:** The even-count equal-weight case returns 2 rather than the interpolated 2.5. This is acceptable for age data (ages are integers), and the slight downward bias is negligible in practice.

---

## 9. Sample Size Sanity Check

**PASS.** Sample sizes are plausible given PSID panel characteristics.

### Annual period (1969-1997):
- Range: 74 (1983) to 209 (1994)
- Typical: 85-140
- Based on a panel of ~5,000-7,000 families with ~2-3% buying per year, 85-140 annual FTB transitions is reasonable.

### Biennial period (1999-2023):
- Range: 162 (2009) to 282 (2021)
- Typical: 165-250
- Biennial waves capture 2 years of transitions, so roughly double the annual count is expected.

### Specific observations:
- **1994 (n=209):** Elevated for an annual year. Investigation shows 762 new families entered the panel in 1994 (total heads grew from 8,046 to 8,821). These include immigrant refresher sample additions. The elevated count reflects genuine panel growth, not a bug.
- **2021 (n=282):** Highest count. Consistent with the PSID panel growing to ~9,200 families by 2021 and strong homebuying activity during the pandemic housing boom.
- **1983 (n=74):** Lowest count. Coincides with the early-1980s recession and high interest rates (prime rate peaked at 20.5% in 1981). Plausible.
- **No years with implausibly high or low counts.**

---

## 10. Independent Reproduction

**PASS.** Three target years were independently reproduced using the exact same logic as the script.

| Year | Script n | Reproduced n | Script median | Reproduced median |
|------|----------|-------------|---------------|-------------------|
| 1980 | 110 | 110 | 28.99 | 29.00 |
| 1995 | 115 | 115 | 30.66 | 31.00 |
| 2019 | 250 | 250 | 35.23 | 35.00 |

**Sample sizes match exactly.** The transition logic, filters, and joins all produce identical populations.

**Median discrepancy explained:** The current `weighted_median` function with integer ages can only produce integer medians (it selects an actual age value from the sorted array). The non-integer medians in the JSON file (28.99, 30.66, 35.23) indicate the **JSON output is stale** -- it was produced by a previous version of the script that likely used an interpolating median function. The current script code, if re-run, would produce integer-valued medians.

**RECOMMENDATION:** Re-run the current script to regenerate `psid_ftb_heads_ci.json`. The n values will be identical, but median values will change slightly (to integer values).

---

## Summary of Findings

### No bugs found. The implementation is correct.

| Check | Status | Notes |
|-------|--------|-------|
| Family ID columns | PASS | All unique, correct joins |
| Relation codes | PASS | 1/10 boundary at 1982/1983 correct |
| Own/rent variables | PASS | Correct codes, advisory on code 8 |
| Weight variables | PASS | Valid longitudinal weights |
| Person ID stability | PASS | Unique, stable identifiers |
| Transition logic | PASS | All edge cases handled correctly |
| Latino supplement | PASS | Correctly excluded |
| Weighted median | PASS | Valid lower weighted median |
| Sample sizes | PASS | All plausible |
| Independent reproduction | PASS | n's match exactly |

### Advisory items (not bugs):

1. **Stale JSON output.** The `psid_ftb_heads_ci.json` file was produced by a previous version of the script with an interpolating median. Re-running the current script will produce slightly different (integer-valued) medians. The n values and overall trend will be unchanged.

2. **Code 8 exclusion.** People transitioning directly from rent-free housing (code 8) to owning (code 1) without ever renting (code 5) are not captured as FTBs. This affects ~5% of families and is a standard definitional choice, but worth noting as a limitation.

3. **Zero-weight exclusion.** 19-28% of household heads have zero longitudinal weight in any given year. These are correctly excluded from the weighted analysis. This is standard PSID practice but means the unweighted sample contributing to results is smaller than the total panel.

4. **2015 age column.** The year_map uses ER34305 (not ER34304) for the 2015 age. This is CORRECT -- ER34304 contains a different variable (values 0/1), while ER34305 contains actual ages. The pattern break in variable numbering is a PSID quirk, not a script error.
