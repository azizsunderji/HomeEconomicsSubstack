# How Long Do Closed Mortgage Accounts Stay on Credit Reports?

## Research Summary (March 2026)

**Bottom line:** Closed mortgage accounts in good standing remain on Equifax credit reports for **up to 10 years** from the date of closure. Closed accounts with negative marks remain for **7 years**. The FCRA itself imposes **no time limit on positive accounts** -- the 10-year window is a voluntary bureau practice, not a statutory requirement. The 7-year limit applies only to adverse information.

---

## 1. Equifax's Specific Policy

Equifax states explicitly:

- **Closed accounts paid as agreed:** "Can stay on your Equifax credit report for **up to 10 years** from the date it was reported by the lender to Equifax."
- **Accounts not paid as agreed:** "Can remain on your Equifax credit report for **up to 7 years**."
- **Late payments:** "Remain on your Equifax credit report for up to 7 years from the original delinquency date."
- **Collection accounts:** "Remain on your Equifax credit report for up to 7 years from the date of the first missed payment."

Source: [Equifax - How Long Does Information Stay on Credit Report](https://www.equifax.com/personal/education/credit/report/articles/-/learn/how-long-does-information-stay-on-credit-report/)

## 2. What the FCRA Actually Says (15 U.S.C. Section 1681c)

The FCRA (Section 605) sets **maximum reporting periods only for adverse information**:

- **7-year rule:** Applies to civil suits/judgments, paid tax liens, accounts placed for collection or charged to profit and loss, and "any other adverse item of information."
- **10-year rule:** Applies only to bankruptcy cases (Chapter 7 and 11).
- **Positive accounts:** The statute is **silent** on time limits for positive/good-standing accounts. There is no statutory requirement to remove them.

The 7-year clock for delinquent accounts starts "upon the expiration of the 180-day period beginning on the date of the commencement of the delinquency which immediately preceded the collection activity."

**Critical distinction:** The FCRA only restricts how long **negative** information can be reported. It does not require bureaus to retain positive information for any specific duration, nor does it require them to remove it. The 10-year retention of positive closed accounts is a **voluntary industry practice** by the bureaus, not a legal mandate.

Source: [15 U.S.C. Section 1681c](https://www.law.cornell.edu/uscode/text/15/1681c)

## 3. Confirmation from Other Bureaus and the CFPB

All three bureaus and the CFPB are consistent:

- **TransUnion:** Closed accounts in good standing stay for up to 10 years.
- **Experian:** "Once your mortgage is paid off, the loan will continue to appear on your credit reports for up to 10 years from the date it was closed as paid in full."
- **CFPB:** Positive payment history "may show up on your credit report so long as you are paying your accounts on time, and may be reported after a loan is paid off, and even after the account is closed." The CFPB specifies **no time limit** for positive information, and notes that "a credit reporting company generally can report most negative information for seven years."

Sources:
- [Experian - How Long Does Paid Mortgage Stay](https://www.experian.com/blogs/ask-experian/how-long-does-paid-mortgage-stay-on-credit-report/)
- [CFPB - How Long Does Information Stay](https://www.consumerfinance.gov/ask-cfpb/how-long-does-information-stay-on-my-credit-report-en-323/)

## 4. Has This Policy Changed Over Time?

The Consumer Credit Reporting Reform Act of 1996 (effective September 30, 1997) revised nearly every section of the FCRA. However, the core time limits in Section 605 -- 7 years for adverse items, 10 years for bankruptcy -- have been in the FCRA since its original passage in 1970. The 1996 amendments primarily:

- Clarified when the 7-year clock starts for delinquent accounts (the 180-day rule)
- Expanded duties for credit reporting agencies and information furnishers
- Added consumer dispute rights

The fundamental retention framework (7 years negative, no limit on positive) was in place throughout the 1990s and 2000s. The 10-year bureau practice for positive closed accounts appears to have been standard industry practice during this entire period.

## 5. Implications for the NY Fed Consumer Credit Panel (starting 1999)

### What This Means for Left-Censoring

If the NY Fed CCP begins in Q1 1999 and Equifax retains closed accounts in good standing for up to 10 years:

| Mortgage closed in... | Visible in 1999 CCP? | Visible in 2003 CCP? |
|---|---|---|
| 1998 | Yes | Yes (until ~2008) |
| 1995 | Yes | Yes (until ~2005) |
| 1992 | Yes | No (dropped ~2002) |
| 1990 | Yes (barely) | No (dropped ~2000) |
| 1989 | Possibly | No |
| 1985 | No | No |

**A mortgage closed (paid off or sold) in 1990 would still be visible on the credit report in 1999, at the very edge of the 10-year window.**

**A mortgage closed in 1995 would be clearly visible through 2005.**

### Important Caveat: "Up to" 10 Years

The language is "up to 10 years" -- not exactly 10 years. Some accounts may drop off sooner. The retention depends on:
1. Whether the lender continues reporting the account to Equifax
2. Equifax's own data management practices
3. The exact date of last reporting vs. date of closure

### NY Fed CCP Technical Notes on Closed Accounts

The NY Fed's own documentation states that inclusion in the CCP sample requires at least one of:
- A public record within the past 7 years
- A bankruptcy filing within the past 10 years
- An open credit account
- **A closed account that is still being reported to Equifax by the lender**

This means the CCP *can* see closed accounts, but only those that lenders are still actively reporting. A mortgage paid off in 1993 would likely still appear in 1999 if the lender had reported the closure and Equifax retained it per its 10-year policy. However, a mortgage paid off in 1988 would almost certainly have dropped off by 1999.

### Revised Assessment of Left-Censoring Bias

**This significantly reduces the left-censoring concern.** The blind spot is not "all mortgages closed before 1999" but rather "mortgages closed before approximately 1989-1990." This means:

- Someone who bought in 1985 and sold in 1993 would still show as having had a mortgage in the 1999 data.
- Someone who bought in 1975 and sold in 1987 would NOT show as having had a mortgage.
- The true blind spot is mortgages that were fully closed more than ~10 years before the panel start.

For the cohort analysis (people born 1960-1980 who might have bought homes in the 1980s-1990s):
- **Born 1960, bought at 28 (1988), sold at 35 (1995):** Visible in 1999 data. No censoring.
- **Born 1960, bought at 25 (1985), sold at 30 (1990):** Barely visible in 1999 (edge of 10-year window). Likely censored by 2000.
- **Born 1955, bought at 28 (1983), sold at 32 (1987):** NOT visible in 1999. Censored.

### Remaining Left-Censoring Issue

The left-censoring bias is smaller than if closed accounts dropped off immediately, but it still exists for:
1. Early buyers who sold/paid off before ~1989
2. People who had short ownership spells in the 1980s
3. The earliest cohorts in any analysis spanning back to the 1980s

The bias would be most acute in the first few years of the panel (1999-2002) and would diminish over time as the panel accumulates its own history of observed account openings.

### One More Consideration: Accounts with Late Payments

Mortgages closed with any delinquency history would drop off after only 7 years (by ~1992 for a mortgage that went delinquent in 1985). This creates a differential censoring pattern: the CCP would disproportionately *miss* troubled mortgages from the pre-panel era relative to clean ones, which could introduce a subtle bias in any analysis of historical mortgage holding patterns.
