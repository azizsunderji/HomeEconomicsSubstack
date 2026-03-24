# What Researchers Have Said About Biases in the NY Fed CCP First-Time Homebuyer Measure

## Research compiled: March 22, 2026

---

## 1. NY Fed's Own Acknowledgments

### 1a. The 2019 Paper: "A Better Measure of First-Time Homebuyers" (Lee & Tracy)

**Source:** [Liberty Street Economics, April 2019](https://libertystreeteconomics.newyorkfed.org/2019/04/a-better-measure-of-first-time-homebuyers/)
**Authors:** Donghoon Lee (NY Fed) and Joseph Tracy (then Dallas Fed)

**FTB Definition:** "We define a first-time buyer as the first appearance of an active mortgage since 1999 with no indication of any prior closed mortgages on the borrower's credit report."

**Key acknowledgments:**

1. **Boomerang buyer misclassification (in the official 3-year measure):** The official measure "will also potentially skew the characteristics of first-time buyers by including former homeowners who had transitioned back to renting (or other arrangement) and are now again purchasing a home."

2. **Cash buyer exclusion:** "because it is based on households' credit files, it does not reflect cash purchases."

3. **Implicit left-censoring acknowledgment:** They note their approach uses "the entire history of a household's credit file back to 1999" -- presented as an advantage over the 3-year official lookback, but without acknowledging that 1999 itself is a hard cutoff that creates its own left-censoring problem.

**What they do NOT acknowledge in the 2019 paper:**
- That the 1999 start date itself creates left-censoring bias (people who owned and sold before 1999 would be misclassified as FTBs)
- That the 10-year credit report retention window means the effective blind spot extends to ~1989, not just 1999
- That boomerang buyer contamination also affects their "better" CCP measure, not just the official 3-year measure -- anyone whose prior mortgage fell off their credit report (closed >10 years ago) would be misclassified
- That cash buyer exclusion could bias age estimates if cash-buying FTBs are systematically older or younger than mortgage-using FTBs

### 1b. The 2025 Update: "Who Is Still on First?" (Lee & Tracy)

**Source:** [Liberty Street Economics, August 2025](https://libertystreeteconomics.newyorkfed.org/2025/08/who-is-still-on-first-an-update-of-characteristics-of-first-time-homebuyers/)
**Authors:** Donghoon Lee (NY Fed) and Joseph Tracy (now Purdue/AEI nonresident senior scholar)

**Key findings reported:**
- Average (median) FTB ages: 37.9 (35) in 2000, 35.4 (32) in 2016, 36.4 (33) in 2019, 36.3 (33) in 2024
- "Despite the financial challenges in transitioning from renting to owning, over the past decade households have managed the transition at essentially the same average age."

**Limitation acknowledgments:**
- **Cash buyer exclusion:** "If a home purchase was made without a mortgage (such as a cash purchase) then it is not included in calculating the statistics."
- **Left-censoring:** NOT acknowledged. They reference data "since 1999" without noting this as a limitation.
- **Boomerang buyers:** NOT discussed.
- **Income data limitation:** They note they lack borrower-level income and instead use zip code averages from 2022 IRS statistics applied to all years.

### 1c. February 2025: "Are First-Time Home Buyers Facing Desperate Times?" (Lee & Tracy)

**Source:** [Liberty Street Economics, February 2025](https://libertystreeteconomics.newyorkfed.org/2025/02/are-first-time-home-buyers-facing-desperate-times/)

**Key quote on methodology:** "We identify FTBs as households that have never had a mortgage lien."

**Cash buyer assumption:** "An assumption that we make is that no FTB makes an all-cash purchase."

**Left-censoring, boomerang buyers:** NOT discussed.

### 1d. Joelle Scally (NY Fed CCP Manager) -- Direct Acknowledgment of Left-Censoring

**Source:** Email correspondence, March 16, 2026 (previously documented in scally_quote.md)

Scally explicitly acknowledged the left-censoring bias:

> "One difference between CCP and AHS will be that there is some left-censoring in the CCP. More specifically, our data begin in 1999, so if an individual had a mortgage loan open and paid it off before 1999, we will wrongly identify them as a first-time buyer if they rented from 1999-2002 and then bought in 2002. This would push up the average age, especially in the earlier years. This problem lessens as the CCP data series gets longer."

**Key takeaways from Scally:**
- The Fed acknowledges the bias exists: "we will wrongly identify them as a first-time buyer"
- The Fed acknowledges it biases age upward: "This would push up the average age, especially in the earlier years"
- The Fed acknowledges it decays over time: "This problem lessens as the CCP data series gets longer"
- Scally was uncertain about the 10-year credit report retention window: "I'm not sure about the 'ten-year window' that you mention"

### 1e. The CCP Foundational Data Set Paper (2024)

**Source:** [Liberty Street Economics, April 2024](https://libertystreeteconomics.newyorkfed.org/2024/04/the-new-york-fed-consumer-credit-panel-a-foundational-cmd-data-set/)
**Authors:** Andrew Haughwout, Donghoon Lee, Daniel Mangrum, Joelle Scally, Wilbert van der Klaauw

This paper describes the CCP as covering "5 percent of the population with a credit report -- approximately 14.2 million individuals in 2023:Q4" plus household members (additional 11.5%/32.9 million). Data begins Q1 1999.

**No discussion of FTB-specific limitations.** The paper does not address left-censoring, boomerang buyers, or cash buyer exclusion in the context of first-time buyer identification.

---

## 2. AEI (American Enterprise Institute) Positions

### 2a. AEI's Own FTB Measure: First-Time Buyer Mortgage Share Index (FBMSI)

**Source:** [AEI Press Release](https://www.aei.org/press/press-release-aeis-international-center-housing-risk-announces-first-release-first-time-buyer-mortgage-share-index-fbmsi/)
**Authors:** Edward J. Pinto

AEI's FBMSI uses their National Mortgage Risk Index (NMRI) database, which covers "nearly all government-guaranteed home purchase loans." They use the **federal government's official 3-year lookback definition:** an FTB is an individual borrower who had no ownership interest in a residential property during the three-year period preceding the purchase.

**Important:** AEI uses the official 3-year lookback definition for their FBMSI, which is the very definition the NY Fed's Lee & Tracy criticize in their 2019 paper for overstating FTBs by ~10 percentage points.

### 2b. AEI's CCP-Based Age Analysis (Pinto, Tracy & Lee)

**Source:** [AEI, 2025](https://www.aei.org/research-products/report/median-first-time-homebuyer-age-at-34-years-in-2025-little-changed-from-2024/)
**Authors:** Edward J. Pinto, Joseph S. Tracy, and Donghoon Lee

For FTB *age* analysis, AEI uses the NY Fed CCP data directly (the same dataset). Key findings:
- 2025: median age 34, average age 36.2
- "Little changed" from 2024 (33 and 36.4), 2019 (33 and 36.4), and 2007 (33 and 37.4)

**Cash buyer exclusion acknowledged:** "Since credit report data do not reflect cash transactions, first-time cash buyers are not included in this data set."

**No discussion of left-censoring or boomerang buyer bias.** The report presents the CCP data as essentially unbiased.

### 2c. AEI's Critique of NAR Data (Pinto & Tracy)

**Source:** [AEI, December 2025](https://www.aei.org/articles/nar-says-the-typical-first-time-homebuyer-age-was-40-this-year-up-from-33-in-2021-but-is-this-accurate/)

AEI's primary critique targets NAR's survey methodology:
- NAR response rate: 3.5% (6,103 of 189,750 surveys mailed), only 1,281 FTB respondents
- "The CCP data appears to offer a better historical view of the current position of FTBs."
- Age distribution bias: "Under age 35 groups are underrepresented by 17 percentage points and the aged 45 to 74 buyers are overrepresented by 18 percentage points respectively, compared to the CCP."
- "The NAR bias to a higher age is perhaps not surprising given that it is a mail survey with 120 questions, which doesn't lend itself to a high response rate by Millennials and GenZ-ers."

**No discussion of CCP's own biases.** AEI presents the CCP as the gold standard without acknowledging its limitations.

---

## 3. Joseph Tracy's Dual Role

Joseph Tracy is a critical figure. He is:
- Co-author of the original NY Fed CCP FTB papers (2019 with Lee)
- Now a "nonresident senior scholar at the American Enterprise Institute"
- Co-author of AEI's CCP-based FTB age reports (with Pinto and Lee)
- A "Distinguished Fellow at Purdue's Daniels School of Business"

Tracy's dual affiliation means the same researcher is behind both the NY Fed's and AEI's CCP-based FTB analysis. This explains why both institutions use identical methodology and reach identical conclusions -- it is literally the same analysis by the same people. Neither institution has incentive to critique a measure they jointly promote.

---

## 4. Cato Institute

**Source:** [Cato at Liberty Blog, "First-time Homebuyer Crisis: Fact or Fiction?"](https://www.cato.org/blog/first-time-homebuyer-crisis-fact-or-fiction)
**Authors:** Norbert Michel and Jerome Famularo

Cato uses the CCP data to argue against the "crisis" narrative:
- "The median age of the first-time homebuyer is approximately 33 years old -- not 40 -- and has been steady between 2001 and today."
- "Unlike survey estimates, the CCP figures are not subject to survey response bias since they consist of anonymized loan-level data."

**No discussion of CCP limitations.** Cato treats the CCP data as definitive and does not acknowledge left-censoring, boomerang buyer contamination, or cash buyer exclusion.

---

## 5. Wolf Richter / Wolf Street

### 5a. August 2025 Analysis

**Source:** [Wolf Street, August 2025](https://wolfstreet.com/2025/08/11/average-age-of-first-time-home-buyers-and-how-it-changed-over-the-past-25-years/)

Richter presents the NY Fed/Equifax CCP data as superior to NAR:
- "based on actual purchase and credit data (Equifax)" vs NAR which "is based on what its Realtors out in the field reported to NAR over the years. In addition, NAR is a lobbying group for Realtors."
- Average FTB age: 36.3 in 2024, range of 35.5-36.4 since 2012, down from 37.9 in early 2000s
- "The average age at which they do that hasn't changed much either, and has actually declined a little since 2000."

**On cash buyers:** A commenter asked about cash buyer exclusion. Richter confirmed Equifax only captures mortgaged purchases but noted he incorporated Redfin data for cash transactions when calculating FTB purchase share percentages.

**On boomerang buyers:** A commenter raised the 3-year FTB classification issue but Richter did not directly address this.

### 5b. December 2025 Analysis

**Source:** [Wolf Street, December 2025](https://wolfstreet.com/2025/12/05/nar-says-typical-first-time-homebuyer-age-was-40-in-2025-up-from-33-in-2021-but-is-this-accurate/)

Reiterates the NAR vs CCP comparison with updated 2025 data. Same conclusions: CCP shows stable FTB age around 33 median, NAR shows inflated ages due to survey response bias.

**No discussion of CCP's own biases.**

---

## 6. The Daily Economy / Craig Richardson

**Source:** [The Daily Economy, "No, First-Time Homebuyers Aren't All 40 Now"](https://thedailyeconomy.org/article/no-first-time-homebuyers-arent-all-40-now/)

Uses AEI/CCP data to push back on NAR claims. Notes that "cash buyers (23% of sub-$100k homes)" are excluded from mortgage-based analyses, which is a rare acknowledgment of the cash buyer bias from a CCP-sympathetic source. But presents this as a limitation of mortgage analyses generally, not as a specific bias in the CCP FTB measure.

---

## 7. Richmond Fed on Boomerang Buyers

**Source:** [Richmond Fed, Econ Focus Q1 2017, "The Missing Boomerang Buyers"](https://www.richmondfed.org/publications/research/econ_focus/2017/q1/cover_story)

This article discusses why former homeowners (post-foreclosure) have not returned to the housing market as expected. Key points:
- By law, negative credit events including foreclosure are removed from credit records after 7 years
- A 2015 RealtyTrac report estimated 7.3 million people would have sufficiently repaired credit to buy homes over the next 8 years
- But "this wave of boomerang buyers never materialized as expected"
- Mortgage credit availability in early 2017 was "only about one-half as available as it was in 2004"

**Relevance to CCP bias:** The Richmond Fed article confirms the mechanism by which boomerang buyers could be misclassified as FTBs in the CCP -- if their foreclosure/mortgage history ages off their credit report after 7 years, and they later take out a new mortgage, they would appear as first-time buyers in the CCP data. The Richmond Fed does not discuss this as a CCP data quality issue, however.

---

## 8. Credit Report Retention Rules (Key Background)

Per Equifax, Experian, TransUnion, and CFPB:
- **Closed accounts in good standing:** Remain on credit reports for **up to 10 years** from closure date
- **Closed accounts with negative marks:** Remain for **7 years** from original delinquency date
- **Positive information:** The FCRA imposes **no statutory time limit** -- the 10-year window is voluntary bureau practice

**Implication for CCP FTB classification:**
- A mortgage paid off in 1993 would likely still appear on a 1999 credit report (within 10-year window)
- A mortgage paid off in 1987 would NOT appear on a 1999 credit report (beyond 10-year window)
- A foreclosed mortgage from 1990 would have dropped off by 1997 (7-year rule for negative items)
- The effective blind spot for the CCP is mortgages closed before ~1989-1990, not all mortgages before 1999

---

## 9. Summary: Who Has Discussed What

| Bias | NY Fed (published papers) | NY Fed (Scally, private) | AEI | Cato | Wolf Street | Richmond Fed |
|---|---|---|---|---|---|---|
| **Left-censoring (1999 cutoff)** | Implicit only -- notes data starts 1999 but presents as advantage | **YES -- explicitly acknowledges "wrongly identify" and "push up average age"** | No | No | No | No |
| **Boomerang buyer misclassification** | Discussed only as flaw of 3-year official definition, NOT of their own CCP measure | No | No | No | Reader raised; not addressed | Discusses mechanism (7-year credit aging) but not as CCP data issue |
| **Cash buyer exclusion** | YES -- acknowledged in all papers | N/A | YES -- acknowledged | No | Acknowledged in comments | No |
| **10-year credit retention window** | No | Uncertain ("I'm not sure") | No | No | No | No |

---

## 10. The Gap in the Literature

**No published research has comprehensively analyzed the interaction of these three biases in the CCP FTB measure:**

1. **Left-censoring bias** (pre-~1989 mortgages invisible) -- which makes some repeat buyers look like FTBs, biasing FTB age *upward* in early years of the panel
2. **Boomerang buyer contamination** (people whose prior mortgage aged off their credit report >10 years ago) -- an ongoing bias that makes some repeat buyers look like FTBs at older ages
3. **Cash buyer exclusion** -- which removes an unknown population of FTBs, with unclear age distribution effects

The NY Fed's published papers present the CCP measure as a clear improvement over the official 3-year definition and the NAR survey, which it is on both counts. But they do not rigorously analyze the CCP's own biases. Joelle Scally's private acknowledgment of left-censoring bias is the only direct Fed statement on the issue, and even she was uncertain about the credit report retention mechanism.

AEI, Cato, Wolf Street, and other CCP advocates have been even less critical, treating the data as essentially unbiased. The entire discourse has been framed as "CCP vs. NAR" rather than examining the CCP's own measurement limitations.

---

## Sources

- [NY Fed: "A Better Measure of First-Time Homebuyers" (2019)](https://libertystreeteconomics.newyorkfed.org/2019/04/a-better-measure-of-first-time-homebuyers/)
- [NY Fed: "Who Is Still on First?" (2025)](https://libertystreeteconomics.newyorkfed.org/2025/08/who-is-still-on-first-an-update-of-characteristics-of-first-time-homebuyers/)
- [NY Fed: "Are First-Time Home Buyers Facing Desperate Times?" (2025)](https://libertystreeteconomics.newyorkfed.org/2025/02/are-first-time-home-buyers-facing-desperate-times/)
- [NY Fed: "The New York Fed Consumer Credit Panel: A Foundational CMD Data Set" (2024)](https://libertystreeteconomics.newyorkfed.org/2024/04/the-new-york-fed-consumer-credit-panel-a-foundational-cmd-data-set/)
- [AEI: "Median First-Time Homebuyer Age at 34 Years in 2025"](https://www.aei.org/research-products/report/median-first-time-homebuyer-age-at-34-years-in-2025-little-changed-from-2024/)
- [AEI: "NAR Says the Typical First-Time Homebuyer Age Was 40..."](https://www.aei.org/articles/nar-says-the-typical-first-time-homebuyer-age-was-40-this-year-up-from-33-in-2021-but-is-this-accurate/)
- [AEI: First-Time Buyer Mortgage Share Index (FBMSI) Press Release](https://www.aei.org/press/press-release-aeis-international-center-housing-risk-announces-first-release-first-time-buyer-mortgage-share-index-fbmsi/)
- [Cato: "First-time Homebuyer Crisis: Fact or Fiction?"](https://www.cato.org/blog/first-time-homebuyer-crisis-fact-or-fiction)
- [Wolf Street: "Average Age of First-Time Home Buyers" (Aug 2025)](https://wolfstreet.com/2025/08/11/average-age-of-first-time-home-buyers-and-how-it-changed-over-the-past-25-years/)
- [Wolf Street: "NAR Says Typical First-Time Homebuyer Age Was 40" (Dec 2025)](https://wolfstreet.com/2025/12/05/nar-says-typical-first-time-homebuyer-age-was-40-in-2025-up-from-33-in-2021-but-is-this-accurate/)
- [The Daily Economy: "No, First-Time Homebuyers Aren't All 40 Now"](https://thedailyeconomy.org/article/no-first-time-homebuyers-arent-all-40-now/)
- [Richmond Fed: "The Missing Boomerang Buyers" (2017)](https://www.richmondfed.org/publications/research/econ_focus/2017/q1/cover_story)
- [ResiClub: "The Vanishing Young Homebuyer"](https://www.resiclubanalytics.com/p/the-vanishing-young-homebuyer-median-first-time-homebuyer-age-jumps-from-28-in-1991-to-38-in-2024)
- [CFPB: "How Long Does Information Stay on My Credit Report?"](https://www.consumerfinance.gov/ask-cfpb/how-long-does-information-stay-on-my-credit-report-en-323/)
- [Equifax: Credit Report Retention](https://www.equifax.com/personal/education/credit/report/articles/-/learn/how-long-does-information-stay-on-credit-report/)
