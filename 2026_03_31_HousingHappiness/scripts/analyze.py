"""
Housing Costs vs. Happiness: Is the Anglophone happiness decline linked to housing?
Uses OECD price-to-income ratios + World Happiness Report (Cantril ladder) data.
"""

import pandas as pd
import numpy as np
from scipy import stats
import json

PROJECT = "/Users/azizsunderji/Dropbox/Home Economics/Explorations/2026_03_30_HousingHappiness"
DATA = f"{PROJECT}/data"
GHC = "/Users/azizsunderji/Dropbox/Home Economics/GlobalHousingCrisis"

# ── 1. Load OECD price-to-income data ──────────────────────────────────────
oecd_file = f"{GHC}/OECD.ECO.MPD,DSD_AN_HOUSE_PRICES@DF_HOUSE_PRICES,+DNK+FIN+FRA+DEU+IRL+ITA+JPN+KOR+MEX+NOR+PRT+ESP+SWE+CHE+GBR+AUT+BEL+AUS+CAN+NZL+EA+USA+OECD.Q.HPI_YDH+RHP.IX.csv"

oecd_raw = pd.read_csv(oecd_file)

# Filter to price-to-income ratio (HPI_YDH)
pti = oecd_raw[oecd_raw['MEASURE'] == 'HPI_YDH'].copy()
pti['year'] = pti['TIME_PERIOD'].str[:4].astype(int)
pti['value'] = pd.to_numeric(pti['OBS_VALUE'], errors='coerce')

# Annual average
pti_annual = pti.groupby(['REF_AREA', 'Reference area', 'year'])['value'].mean().reset_index()
pti_annual.columns = ['iso3', 'country_oecd', 'year', 'pti_index']

# Also get real house prices (RHP)
rhp = oecd_raw[oecd_raw['MEASURE'] == 'RHP'].copy()
rhp['year'] = rhp['TIME_PERIOD'].str[:4].astype(int)
rhp['value'] = pd.to_numeric(rhp['OBS_VALUE'], errors='coerce')
rhp_annual = rhp.groupby(['REF_AREA', 'Reference area', 'year'])['value'].mean().reset_index()
rhp_annual.columns = ['iso3', 'country_oecd', 'year', 'rhp_index']

# Merge PTI and RHP
housing = pti_annual.merge(rhp_annual, on=['iso3', 'country_oecd', 'year'], how='outer')

print(f"Housing data: {len(housing)} rows, {housing['iso3'].nunique()} countries")
print(f"Year range: {housing['year'].min()}-{housing['year'].max()}")

# ── 2. Load happiness data ─────────────────────────────────────────────────
happiness = pd.read_csv(f"{DATA}/happiness_raw.csv")
print(f"\nHappiness data: {len(happiness)} rows, {happiness['country'].nunique()} countries")
print(f"Year range: {happiness['year'].min()}-{happiness['year'].max()}")

# ── 3. Country name mapping (OECD ISO3 → WHR country names) ───────────────
iso3_to_whr = {
    'AUS': 'Australia',
    'AUT': 'Austria',
    'BEL': 'Belgium',
    'CAN': 'Canada',
    'CHE': 'Switzerland',
    'DEU': 'Germany',
    'DNK': 'Denmark',
    'ESP': 'Spain',
    'FIN': 'Finland',
    'FRA': 'France',
    'GBR': 'United Kingdom',
    'IRL': 'Ireland',
    'ITA': 'Italy',
    'JPN': 'Japan',
    'KOR': 'South Korea',
    'MEX': 'Mexico',
    'NOR': 'Norway',
    'NZL': 'New Zealand',
    'PRT': 'Portugal',
    'SWE': 'Sweden',
    'USA': 'United States',
}

housing['country'] = housing['iso3'].map(iso3_to_whr)
# Drop OECD and EA aggregates
housing = housing.dropna(subset=['country'])

# ── 4. Merge ───────────────────────────────────────────────────────────────
merged = housing.merge(happiness[['country', 'year', 'cantril_ladder_score']],
                       on=['country', 'year'], how='inner')
print(f"\nMerged: {len(merged)} country-years, {merged['country'].nunique()} countries")
print(f"Year range: {merged['year'].min()}-{merged['year'].max()}")

# Mark Anglophone countries
anglophone = {'United States', 'United Kingdom', 'Canada', 'Australia', 'New Zealand', 'Ireland'}
merged['anglophone'] = merged['country'].isin(anglophone)

# ── 5. Analysis ────────────────────────────────────────────────────────────

results = {}

# --- A. Cross-sectional: PTI level vs happiness level (latest year) ---
latest = merged[merged['year'] == merged['year'].max()].copy()
print(f"\n{'='*60}")
print(f"ANALYSIS A: Price-to-Income Level vs Happiness ({latest['year'].iloc[0]})")
print(f"{'='*60}")
r, p = stats.pearsonr(latest['pti_index'].dropna(),
                       latest.loc[latest['pti_index'].notna(), 'cantril_ladder_score'])
print(f"Correlation: r={r:.3f}, p={p:.4f}")
print(f"N = {len(latest)}")
for _, row in latest.sort_values('pti_index', ascending=False).iterrows():
    flag = " *** ANGLOPHONE" if row['anglophone'] else ""
    print(f"  {row['country']:20s}  PTI={row['pti_index']:6.1f}  Happiness={row['cantril_ladder_score']:.2f}{flag}")

results['A_level_vs_level'] = {'r': r, 'p': p, 'n': len(latest), 'year': int(latest['year'].iloc[0])}

# --- B. Change in PTI vs Change in Happiness ---
print(f"\n{'='*60}")
print(f"ANALYSIS B: Change in PTI vs Change in Happiness")
print(f"{'='*60}")

# Use overlapping period (2011-2023 or similar)
min_yr = merged['year'].min()
max_yr = merged['year'].max()

# Get early period (average of first 3 years) vs late period (average of last 3 years)
early_years = range(min_yr, min_yr + 3)
late_years = range(max_yr - 2, max_yr + 1)

early = merged[merged['year'].isin(early_years)].groupby('country').agg(
    pti_early=('pti_index', 'mean'),
    happiness_early=('cantril_ladder_score', 'mean'),
    anglophone=('anglophone', 'first')
).reset_index()

late = merged[merged['year'].isin(late_years)].groupby('country').agg(
    pti_late=('pti_index', 'mean'),
    happiness_late=('cantril_ladder_score', 'mean'),
).reset_index()

changes = early.merge(late, on='country')
changes['pti_change'] = changes['pti_late'] - changes['pti_early']
changes['pti_pct_change'] = (changes['pti_late'] / changes['pti_early'] - 1) * 100
changes['happiness_change'] = changes['happiness_late'] - changes['happiness_early']
changes = changes.dropna(subset=['pti_change', 'happiness_change'])

print(f"Period: {list(early_years)} vs {list(late_years)}")

r2, p2 = stats.pearsonr(changes['pti_change'], changes['happiness_change'])
print(f"Correlation (PTI change vs happiness change): r={r2:.3f}, p={p2:.4f}")
print(f"N = {len(changes)}")

for _, row in changes.sort_values('happiness_change').iterrows():
    flag = " *** ANGLOPHONE" if row['anglophone'] else ""
    print(f"  {row['country']:20s}  ΔPTI={row['pti_change']:+6.1f} ({row['pti_pct_change']:+5.1f}%)  ΔHappiness={row['happiness_change']:+.3f}{flag}")

results['B_change_vs_change'] = {'r': r2, 'p': p2, 'n': len(changes),
                                  'early': list(early_years), 'late': list(late_years)}

# --- C. Panel: PTI vs happiness across all years ---
print(f"\n{'='*60}")
print(f"ANALYSIS C: Panel — PTI vs Happiness (all country-years)")
print(f"{'='*60}")

panel = merged.dropna(subset=['pti_index', 'cantril_ladder_score'])
r3, p3 = stats.pearsonr(panel['pti_index'], panel['cantril_ladder_score'])
print(f"Raw correlation: r={r3:.3f}, p={p3:.4f}, N={len(panel)}")

# Within-country (demean by country)
panel['pti_dm'] = panel.groupby('country')['pti_index'].transform(lambda x: x - x.mean())
panel['hap_dm'] = panel.groupby('country')['cantril_ladder_score'].transform(lambda x: x - x.mean())
r4, p4 = stats.pearsonr(panel['pti_dm'], panel['hap_dm'])
print(f"Within-country correlation: r={r4:.3f}, p={p4:.4f}")

results['C_panel_raw'] = {'r': r3, 'p': p3, 'n': len(panel)}
results['C_panel_within'] = {'r': r4, 'p': p4, 'n': len(panel)}

# --- D. Anglophone vs non-Anglophone comparison ---
print(f"\n{'='*60}")
print(f"ANALYSIS D: Anglophone vs Non-Anglophone Trends")
print(f"{'='*60}")

for group_name, group in merged.groupby('anglophone'):
    label = "ANGLOPHONE" if group_name else "Non-Anglophone"
    by_year = group.groupby('year').agg(
        avg_happiness=('cantril_ladder_score', 'mean'),
        avg_pti=('pti_index', 'mean'),
        n=('country', 'count')
    ).reset_index()

    print(f"\n{label} ({group['country'].nunique()} countries):")
    for _, row in by_year.iterrows():
        print(f"  {int(row['year'])}  Happiness={row['avg_happiness']:.3f}  PTI={row['avg_pti']:.1f}  (n={int(row['n'])})")

# --- E. Longer PTI horizon (use more OECD history) ---
print(f"\n{'='*60}")
print(f"ANALYSIS E: Longer-term PTI change (2005-2023) vs Latest Happiness")
print(f"{'='*60}")

pti_2005 = housing[housing['year'] == 2005][['country', 'pti_index']].rename(columns={'pti_index': 'pti_2005'})
pti_2023 = housing[housing['year'] == 2023][['country', 'pti_index']].rename(columns={'pti_index': 'pti_2023'})
hap_2023 = happiness[happiness['year'] == 2023][['country', 'cantril_ladder_score']].rename(columns={'cantril_ladder_score': 'happiness_2023'})

long_term = pti_2005.merge(pti_2023, on='country').merge(hap_2023, on='country')
long_term['pti_change_pct'] = (long_term['pti_2023'] / long_term['pti_2005'] - 1) * 100
long_term['anglophone'] = long_term['country'].isin(anglophone)
long_term = long_term.dropna(subset=['pti_change_pct', 'happiness_2023'])

if len(long_term) >= 5:
    r5, p5 = stats.pearsonr(long_term['pti_change_pct'], long_term['happiness_2023'])
    print(f"Correlation (PTI % change 2005→2023 vs happiness 2023): r={r5:.3f}, p={p5:.4f}")
    print(f"N = {len(long_term)}")
    for _, row in long_term.sort_values('pti_change_pct', ascending=False).iterrows():
        flag = " *** ANGLOPHONE" if row['anglophone'] else ""
        print(f"  {row['country']:20s}  PTI 2005={row['pti_2005']:6.1f}  2023={row['pti_2023']:6.1f}  Δ={row['pti_change_pct']:+5.1f}%  Happiness={row['happiness_2023']:.2f}{flag}")
    results['E_longterm'] = {'r': r5, 'p': p5, 'n': len(long_term)}

# Also check: happiness change 2018→2023 vs PTI change
print(f"\n{'='*60}")
print(f"ANALYSIS F: PTI change vs Happiness change (2018→2023)")
print(f"{'='*60}")

hap_2018 = happiness[happiness['year'] == 2018][['country', 'cantril_ladder_score']].rename(columns={'cantril_ladder_score': 'hap_2018'})
hap_late = happiness[happiness['year'] == 2023][['country', 'cantril_ladder_score']].rename(columns={'cantril_ladder_score': 'hap_2023'})
pti_2018 = housing[housing['year'] == 2018][['country', 'pti_index']].rename(columns={'pti_index': 'pti_2018'})

recent = pti_2018.merge(pti_2023, on='country').merge(hap_2018, on='country').merge(hap_late, on='country')
recent['pti_change'] = recent['pti_2023'] - recent['pti_2018']
recent['hap_change'] = recent['hap_2023'] - recent['hap_2018']
recent['anglophone'] = recent['country'].isin(anglophone)
recent = recent.dropna(subset=['pti_change', 'hap_change'])

if len(recent) >= 5:
    r6, p6 = stats.pearsonr(recent['pti_change'], recent['hap_change'])
    print(f"Correlation: r={r6:.3f}, p={p6:.4f}, N={len(recent)}")
    for _, row in recent.sort_values('hap_change').iterrows():
        flag = " *** ANGLOPHONE" if row['anglophone'] else ""
        print(f"  {row['country']:20s}  ΔPTI={row['pti_change']:+6.1f}  ΔHappiness={row['hap_change']:+.3f}{flag}")
    results['F_recent_change'] = {'r': r6, 'p': p6, 'n': len(recent)}

# ── 6. Save results ───────────────────────────────────────────────────────
with open(f"{DATA}/analysis_results.json", 'w') as f:
    json.dump(results, f, indent=2, default=str)

merged.to_csv(f"{DATA}/merged_panel.csv", index=False)
changes.to_csv(f"{DATA}/changes.csv", index=False)
if len(long_term) >= 5:
    long_term.to_csv(f"{DATA}/long_term_changes.csv", index=False)
if len(recent) >= 5:
    recent.to_csv(f"{DATA}/recent_changes.csv", index=False)

print(f"\n{'='*60}")
print("SUMMARY OF CORRELATIONS")
print(f"{'='*60}")
for key, val in results.items():
    print(f"  {key:30s}  r={val['r']:+.3f}  p={val['p']:.4f}  n={val['n']}")
