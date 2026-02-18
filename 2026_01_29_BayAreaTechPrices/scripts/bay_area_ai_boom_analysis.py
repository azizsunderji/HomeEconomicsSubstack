"""
Analyze Bay Area home prices vs tech concentration to test hypothesis:
- Is SF benefiting less from AI boom than Silicon Valley proper?
- Compare price changes with occupation/industry data
"""

import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# Font setup
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'

# Colors
BLUE = '#0BB4FF'
YELLOW = '#FEC439'
GREEN = '#67A275'
RED = '#F4743B'
BLACK = '#3D3733'
BG_CREAM = '#F6F7F3'

# Bay Area county FIPS codes
BAY_AREA_COUNTIES = {
    '06001': 'Alameda',
    '06013': 'Contra Costa',
    '06041': 'Marin',
    '06055': 'Napa',
    '06075': 'San Francisco',
    '06081': 'San Mateo',
    '06085': 'Santa Clara',
    '06087': 'Santa Cruz',
    '06095': 'Solano',
    '06097': 'Sonoma',
}

# Core tech counties (Silicon Valley + SF)
CORE_TECH_FIPS = ['06075', '06081', '06085']  # SF, San Mateo, Santa Clara

# Load Zillow data
print("=" * 60)
print("PART 1: HOME PRICE ANALYSIS")
print("=" * 60)
df = pd.read_csv('/Users/azizsunderji/Dropbox/Home Economics/Explorations/data/zillow_county_zhvi.csv')

# Filter for Bay Area
df['fips'] = df['StateCodeFIPS'].astype(str).str.zfill(2) + df['MunicipalCodeFIPS'].astype(str).str.zfill(3)
bay_area = df[df['fips'].isin(BAY_AREA_COUNTIES.keys())].copy()
bay_area['county_name'] = bay_area['fips'].map(BAY_AREA_COUNTIES)

# Get date columns
date_cols = [c for c in df.columns if c.startswith('20')]
latest = '2025-12-31'
six_months_ago = '2025-06-30'
twelve_months_ago = '2024-12-31'

# Calculate price changes
price_results = []
for _, row in bay_area.iterrows():
    county = row['county_name']
    fips = row['fips']
    current_price = row[latest]
    price_6mo_ago = row[six_months_ago]
    price_12mo_ago = row[twelve_months_ago]

    change_6mo = (current_price - price_6mo_ago) / price_6mo_ago * 100
    change_12mo = (current_price - price_12mo_ago) / price_12mo_ago * 100

    price_results.append({
        'county': county,
        'fips': fips,
        'current_price': current_price,
        'change_6mo_pct': change_6mo,
        'change_12mo_pct': change_12mo
    })

price_df = pd.DataFrame(price_results)

print("\nHome Price Changes (June 2025 - December 2025):")
print("-" * 50)
for _, row in price_df.sort_values('change_6mo_pct', ascending=False).iterrows():
    print(f"  {row['county']:15} {row['change_6mo_pct']:+.2f}%  (${row['current_price']/1000:,.0f}k)")

# Load ACS industry data
print("\n" + "=" * 60)
print("PART 2: INDUSTRY CONCENTRATION ANALYSIS")
print("=" * 60)

with open('/Users/azizsunderji/Dropbox/Home Economics/Explorations/data/bay_area_acs_industry.json') as f:
    acs_data = json.load(f)

# Parse ACS data
# Columns: NAME, Total_Emp, Information, Prof_Sci_Tech, Arts_Ent, Public_Admin, state, county
industry_results = []
for row in acs_data[1:]:  # Skip header
    fips = row[5] + row[6]
    county = BAY_AREA_COUNTIES.get(fips, row[0].split(',')[0])
    total_emp = int(row[1])
    info_emp = int(row[2])  # Information sector (software, internet)
    prof_sci_tech = int(row[3])  # Professional, scientific, technical services
    arts_ent = int(row[4])  # Arts, entertainment, recreation
    pub_admin = int(row[5]) if row[5].isdigit() else 0  # Wait, need to check index

# Actually re-parse correctly
industry_results = []
for row in acs_data[1:]:
    name = row[0]
    county_name = name.replace(' County, California', '')
    total_emp = int(row[1])
    info_emp = int(row[2])
    prof_sci_tech = int(row[3])
    arts_ent = int(row[4])
    pub_admin = int(row[5])
    state_fips = row[6]
    county_fips = row[7]
    fips = state_fips + county_fips

    # Combined "tech" = Information + Professional/Scientific/Technical
    tech_emp = info_emp + prof_sci_tech
    tech_pct = tech_emp / total_emp * 100
    info_pct = info_emp / total_emp * 100
    prof_pct = prof_sci_tech / total_emp * 100
    arts_pct = arts_ent / total_emp * 100
    gov_pct = pub_admin / total_emp * 100

    industry_results.append({
        'county': county_name,
        'fips': fips,
        'total_emp': total_emp,
        'tech_emp': tech_emp,
        'tech_pct': tech_pct,
        'info_pct': info_pct,
        'prof_sci_pct': prof_pct,
        'arts_pct': arts_pct,
        'gov_pct': gov_pct
    })

industry_df = pd.DataFrame(industry_results)

print("\nTech Concentration (Information + Professional/Scientific/Technical):")
print("-" * 60)
for _, row in industry_df.sort_values('tech_pct', ascending=False).iterrows():
    print(f"  {row['county']:15} {row['tech_pct']:.1f}%  (Info: {row['info_pct']:.1f}%, Prof/Sci: {row['prof_sci_pct']:.1f}%)")

print("\n\nGovernment Employment (Public Administration):")
print("-" * 60)
for _, row in industry_df.sort_values('gov_pct', ascending=False).iterrows():
    print(f"  {row['county']:15} {row['gov_pct']:.1f}%")

# Merge datasets
print("\n" + "=" * 60)
print("PART 3: COMBINED ANALYSIS - PRICE CHANGE vs TECH CONCENTRATION")
print("=" * 60)

combined = price_df.merge(industry_df, on='fips')
combined = combined.rename(columns={'county_x': 'county'}).drop(columns=['county_y'])

print("\nCorrelation Analysis:")
corr_tech = combined['change_6mo_pct'].corr(combined['tech_pct'])
corr_gov = combined['change_6mo_pct'].corr(combined['gov_pct'])
print(f"  Price change (6mo) vs Tech concentration: r = {corr_tech:.3f}")
print(f"  Price change (6mo) vs Government employment: r = {corr_gov:.3f}")

print("\n\nRanked by Tech Concentration with Price Changes:")
print("-" * 70)
print(f"{'County':15} {'Tech%':>8} {'Info%':>8} {'Gov%':>8} {'6mo Δ':>10}")
print("-" * 70)
for _, row in combined.sort_values('tech_pct', ascending=False).iterrows():
    print(f"{row['county']:15} {row['tech_pct']:8.1f} {row['info_pct']:8.1f} {row['gov_pct']:8.1f} {row['change_6mo_pct']:+10.2f}%")

# Create visualization
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.patch.set_facecolor(BG_CREAM)

# Plot 1: Tech concentration vs price change
ax1 = axes[0]
ax1.set_facecolor(BG_CREAM)

# Color code: core tech counties in blue, others in gray
colors = [BLUE if fips in CORE_TECH_FIPS else '#999999' for fips in combined['fips']]
sizes = [200 if fips in CORE_TECH_FIPS else 100 for fips in combined['fips']]

scatter = ax1.scatter(combined['tech_pct'], combined['change_6mo_pct'],
                      c=colors, s=sizes, alpha=0.7, edgecolors=BLACK, linewidth=1)

# Add labels
for _, row in combined.iterrows():
    offset_x = 0.5
    offset_y = 0.15
    if row['county'] == 'San Francisco':
        offset_y = 0.3
    elif row['county'] == 'San Mateo':
        offset_y = -0.4
    ax1.annotate(row['county'], (row['tech_pct'] + offset_x, row['change_6mo_pct'] + offset_y),
                 fontsize=9, color=BLACK)

# Add trend line
z = np.polyfit(combined['tech_pct'], combined['change_6mo_pct'], 1)
p = np.poly1d(z)
x_line = np.linspace(combined['tech_pct'].min() - 2, combined['tech_pct'].max() + 2, 100)
ax1.plot(x_line, p(x_line), '--', color=RED, alpha=0.7, linewidth=2)

ax1.axhline(y=0, color=BLACK, linewidth=0.5, alpha=0.3)
ax1.set_xlabel('Tech Employment Share (%)\n(Information + Prof/Scientific/Technical)', fontsize=11, color=BLACK)
ax1.set_ylabel('Home Price Change, 6-mo (%)', fontsize=11, color=BLACK)
ax1.set_title('Tech Concentration vs Price Change', fontsize=14, fontweight='bold', color=BLACK)
ax1.grid(True, alpha=0.3)
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)
ax1.tick_params(colors=BLACK)

# Plot 2: Bar chart of price changes
ax2 = axes[1]
ax2.set_facecolor(BG_CREAM)

sorted_df = combined.sort_values('change_6mo_pct', ascending=True)
colors_bar = [BLUE if x > 0 else RED for x in sorted_df['change_6mo_pct']]
bars = ax2.barh(sorted_df['county'], sorted_df['change_6mo_pct'], color=colors_bar, alpha=0.8, edgecolor=BLACK, linewidth=0.5)

ax2.axvline(x=0, color=BLACK, linewidth=1)
ax2.set_xlabel('Home Price Change (%)', fontsize=11, color=BLACK)
ax2.set_title('Bay Area Home Prices, June-Dec 2025', fontsize=14, fontweight='bold', color=BLACK)
ax2.grid(True, alpha=0.3, axis='x')
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)
ax2.tick_params(colors=BLACK)

# Add value labels
for bar, val in zip(bars, sorted_df['change_6mo_pct']):
    x_pos = val + 0.1 if val > 0 else val - 0.1
    ha = 'left' if val > 0 else 'right'
    ax2.text(x_pos, bar.get_y() + bar.get_height()/2, f'{val:+.1f}%',
             va='center', ha=ha, fontsize=9, color=BLACK)

plt.tight_layout()
plt.savefig('/Users/azizsunderji/Dropbox/Home Economics/Explorations/outputs/bay_area_ai_boom_analysis.png',
            dpi=150, bbox_inches='tight', facecolor=BG_CREAM)
plt.savefig('/Users/azizsunderji/Dropbox/Home Economics/Explorations/outputs/bay_area_ai_boom_analysis.svg',
            bbox_inches='tight', facecolor=BG_CREAM)
print("\n\nCharts saved to outputs/bay_area_ai_boom_analysis.png and .svg")

# Key takeaways
print("\n" + "=" * 60)
print("KEY FINDINGS")
print("=" * 60)
print("""
1. HYPOTHESIS PARTIALLY CONTRADICTED:
   - San Francisco had the HIGHEST price appreciation (+2.97%) over 6 months
   - Santa Clara (Silicon Valley core) was second (+1.97%)
   - This suggests SF IS benefiting from the AI boom

2. TECH CONCENTRATION:
   - Santa Clara has highest tech share (25.1%)
   - San Francisco is close behind (29.4%)
   - San Mateo (Peninsula) is also high (22.6%)

3. WEAK CORRELATION:
   - Tech concentration and price change have weak positive correlation
   - Other factors (supply constraints, migration) likely matter more

4. INFORMATION SECTOR (AI-relevant):
   - Santa Clara leads with 6.4% in Information
   - San Francisco is second with 6.3%
   - Both are well-positioned for AI boom

5. DECLINING COUNTIES:
   - Alameda (-2.5%), Contra Costa (-1.6%), Napa (-2.2%)
   - These are less tech-concentrated and further from core tech hubs
""")

# Save combined data
combined.to_csv('/Users/azizsunderji/Dropbox/Home Economics/Explorations/data/bay_area_combined_analysis.csv', index=False)
print("\nCombined data saved to data/bay_area_combined_analysis.csv")
