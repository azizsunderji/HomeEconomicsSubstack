"""
Austin vs Dallas deep comparison (2015-2024).
Austin = treatment (rents fell -4.6% from 2022 peak), Dallas = control (rents +1.5%).
Three panel chart: mover rate, avg bedrooms for movers, mover burden over time.
Also includes income-controlled version.
"""

import pandas as pd
import numpy as np
import duckdb
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# === Font setup ===
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'

# === Colors ===
BLUE = '#0BB4FF'
BLACK = '#3D3733'
RED = '#F4743B'
CREAM_BG = '#F6F7F3'
GREEN = '#67A275'
YELLOW = '#FEC439'

# === Data ===
ACS_PATH = '/Users/azizsunderji/Dropbox/Home Economics/Data/ACS_1Y/acs_1y.parquet'
AUSTIN_MET = 12420
DALLAS_MET = 19100

con = duckdb.connect()

# Query renters in Austin and Dallas, 2015-2024 (skip 2020)
acs = con.execute(f"""
    SELECT YEAR, MET2013, MIGRATE1, BEDROOMS, ROOMS, RENTGRS, HHINCOME, HHWT, TRANTIME
    FROM '{ACS_PATH}'
    WHERE OWNERSHP = 2
      AND HHINCOME > 0
      AND RENTGRS > 0
      AND MET2013 IN ({AUSTIN_MET}, {DALLAS_MET})
      AND YEAR BETWEEN 2015 AND 2024
      AND YEAR != 2020
      AND PERNUM = 1
""").df()

acs['burden'] = acs['RENTGRS'] * 12 / acs['HHINCOME'] * 100
acs['is_mover'] = (acs['MIGRATE1'] > 1).astype(int)
acs['metro'] = acs['MET2013'].map({AUSTIN_MET: 'Austin', DALLAS_MET: 'Dallas'})

print(f"Loaded {len(acs)} records")
print(f"Austin: {len(acs[acs['metro'] == 'Austin'])}, Dallas: {len(acs[acs['metro'] == 'Dallas'])}")

# === Compute yearly stats ===
results = []
for (year, metro), grp in acs.groupby(['YEAR', 'metro']):
    total_wt = grp['HHWT'].sum()
    mover_wt = grp.loc[grp['is_mover'] == 1, 'HHWT'].sum()
    mover_rate = mover_wt / total_wt * 100

    movers = grp[grp['is_mover'] == 1]
    nonmovers = grp[grp['is_mover'] == 0]

    if len(movers) > 0 and movers['HHWT'].sum() > 0:
        mover_avg_bed = np.average(movers['BEDROOMS'], weights=movers['HHWT'])

        m_sorted = movers.sort_values('burden')
        m_cumwt = m_sorted['HHWT'].cumsum()
        m_total = m_sorted['HHWT'].sum()
        mover_med_burden = m_sorted.loc[m_cumwt >= m_total / 2, 'burden'].iloc[0]

        mover_commuters = movers[movers['TRANTIME'] > 0]
        mover_avg_trantime = np.average(mover_commuters['TRANTIME'], weights=mover_commuters['HHWT']) if len(mover_commuters) > 10 else np.nan
    else:
        mover_avg_bed = np.nan
        mover_med_burden = np.nan
        mover_avg_trantime = np.nan

    if len(nonmovers) > 0:
        nm_sorted = nonmovers.sort_values('burden')
        nm_cumwt = nm_sorted['HHWT'].cumsum()
        nm_total = nm_sorted['HHWT'].sum()
        nonmover_med_burden = nm_sorted.loc[nm_cumwt >= nm_total / 2, 'burden'].iloc[0]
    else:
        nonmover_med_burden = np.nan

    results.append({
        'year': year, 'metro': metro,
        'mover_rate': mover_rate,
        'mover_avg_bedrooms': mover_avg_bed,
        'mover_median_burden': mover_med_burden,
        'nonmover_median_burden': nonmover_med_burden,
        'mover_avg_trantime': mover_avg_trantime,
        'n': len(grp), 'n_movers': len(movers),
    })

panel = pd.DataFrame(results)
austin = panel[panel['metro'] == 'Austin'].sort_values('year')
dallas = panel[panel['metro'] == 'Dallas'].sort_values('year')

print("\nAustin yearly stats:")
print(austin[['year', 'mover_rate', 'mover_avg_bedrooms', 'mover_median_burden', 'n']].to_string(index=False))
print("\nDallas yearly stats:")
print(dallas[['year', 'mover_rate', 'mover_avg_bedrooms', 'mover_median_burden', 'n']].to_string(index=False))

# === Three-panel chart ===
fig, axes = plt.subplots(1, 3, figsize=(16, 6), dpi=100)
fig.patch.set_facecolor(CREAM_BG)

# Shared x-axis years
years = sorted(panel['year'].unique())

# Panel 1: Mover Rate
ax = axes[0]
ax.plot(austin['year'], austin['mover_rate'], color=BLUE, linewidth=2.5, marker='o', markersize=5, label='Austin')
ax.plot(dallas['year'], dallas['mover_rate'], color=BLACK, linewidth=2.5, marker='s', markersize=5, label='Dallas')
ax.axvspan(2022, 2024, alpha=0.1, color=BLUE, zorder=0)
ax.set_title('Mover Rate (%)', fontsize=13, fontweight='bold', color=BLACK, pad=10)
ax.set_ylabel('%', fontsize=10)
ax.legend(frameon=False, fontsize=10)

# Panel 2: Avg Bedrooms (Movers)
ax = axes[1]
ax.plot(austin['year'], austin['mover_avg_bedrooms'], color=BLUE, linewidth=2.5, marker='o', markersize=5, label='Austin')
ax.plot(dallas['year'], dallas['mover_avg_bedrooms'], color=BLACK, linewidth=2.5, marker='s', markersize=5, label='Dallas')
ax.axvspan(2022, 2024, alpha=0.1, color=BLUE, zorder=0)
ax.set_title('Avg Bedrooms (Movers)', fontsize=13, fontweight='bold', color=BLACK, pad=10)
ax.legend(frameon=False, fontsize=10)

# Panel 3: Mover Median Burden
ax = axes[2]
ax.plot(austin['year'], austin['mover_median_burden'], color=BLUE, linewidth=2.5, marker='o', markersize=5, label='Austin')
ax.plot(dallas['year'], dallas['mover_median_burden'], color=BLACK, linewidth=2.5, marker='s', markersize=5, label='Dallas')
ax.axhline(30, color=RED, linewidth=1, linestyle='--', alpha=0.6, label='30% threshold')
ax.axvspan(2022, 2024, alpha=0.1, color=BLUE, zorder=0)
ax.set_title('Mover Median Burden (%)', fontsize=13, fontweight='bold', color=BLACK, pad=10)
ax.legend(frameon=False, fontsize=10)

# Style all panels
for ax in axes:
    ax.set_facecolor(CREAM_BG)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.tick_params(axis='y', length=0)
    ax.grid(axis='y', color='white', linewidth=0.8)
    ax.set_xticks([2015, 2017, 2019, 2021, 2023])

fig.suptitle('Austin (treatment) vs Dallas (control)', fontsize=16, fontweight='bold',
             color=BLACK, y=1.02)
fig.text(0.5, 0.97, 'Shaded area: ZORI rent decline period (Austin -4.6%, Dallas +1.5%)',
         ha='center', fontsize=10, color='#888888')
fig.text(0.5, -0.02, 'Source: ACS 1-Year PUMS (2015-2024, excl. 2020), Zillow ZORI',
         ha='center', fontsize=8, color='#999999', fontstyle='italic')

plt.tight_layout()
plt.savefig('outputs/austin_vs_dallas_movers.png', dpi=150, bbox_inches='tight', facecolor=CREAM_BG)
plt.rcParams['svg.fonttype'] = 'none'
plt.savefig('outputs/austin_vs_dallas_movers.svg', bbox_inches='tight', facecolor=CREAM_BG)
plt.close()
print("\nSaved austin_vs_dallas_movers.svg/png")

# === Income-controlled comparison ===
# Repeat for fixed real-income bins to rule out composition effects
# Use $40K-$80K income band (roughly middle of renter distribution)
acs_mid = acs[(acs['HHINCOME'] >= 40000) & (acs['HHINCOME'] <= 80000)].copy()

results_ctrl = []
for (year, metro), grp in acs_mid.groupby(['YEAR', 'metro']):
    total_wt = grp['HHWT'].sum()
    mover_wt = grp.loc[grp['is_mover'] == 1, 'HHWT'].sum()
    mover_rate = mover_wt / total_wt * 100

    movers = grp[grp['is_mover'] == 1]
    if len(movers) > 10 and movers['HHWT'].sum() > 0:
        mover_avg_bed = np.average(movers['BEDROOMS'], weights=movers['HHWT'])
        m_sorted = movers.sort_values('burden')
        m_cumwt = m_sorted['HHWT'].cumsum()
        m_total = m_sorted['HHWT'].sum()
        mover_med_burden = m_sorted.loc[m_cumwt >= m_total / 2, 'burden'].iloc[0]
    else:
        mover_avg_bed = np.nan
        mover_med_burden = np.nan

    results_ctrl.append({
        'year': year, 'metro': metro,
        'mover_rate': mover_rate,
        'mover_avg_bedrooms': mover_avg_bed,
        'mover_median_burden': mover_med_burden,
        'n': len(grp), 'n_movers': len(movers),
    })

panel_ctrl = pd.DataFrame(results_ctrl)
austin_ctrl = panel_ctrl[panel_ctrl['metro'] == 'Austin'].sort_values('year')
dallas_ctrl = panel_ctrl[panel_ctrl['metro'] == 'Dallas'].sort_values('year')

print("\n=== Income-controlled ($40K-$80K) ===")
print("Austin:")
print(austin_ctrl[['year', 'mover_rate', 'mover_avg_bedrooms', 'mover_median_burden', 'n']].to_string(index=False))
print("Dallas:")
print(dallas_ctrl[['year', 'mover_rate', 'mover_avg_bedrooms', 'mover_median_burden', 'n']].to_string(index=False))

# Income-controlled chart
fig, axes = plt.subplots(1, 3, figsize=(16, 6), dpi=100)
fig.patch.set_facecolor(CREAM_BG)

ax = axes[0]
ax.plot(austin_ctrl['year'], austin_ctrl['mover_rate'], color=BLUE, linewidth=2.5, marker='o', markersize=5, label='Austin')
ax.plot(dallas_ctrl['year'], dallas_ctrl['mover_rate'], color=BLACK, linewidth=2.5, marker='s', markersize=5, label='Dallas')
ax.axvspan(2022, 2024, alpha=0.1, color=BLUE, zorder=0)
ax.set_title('Mover Rate (%)', fontsize=13, fontweight='bold', color=BLACK, pad=10)
ax.set_ylabel('%', fontsize=10)
ax.legend(frameon=False, fontsize=10)

ax = axes[1]
ax.plot(austin_ctrl['year'], austin_ctrl['mover_avg_bedrooms'], color=BLUE, linewidth=2.5, marker='o', markersize=5, label='Austin')
ax.plot(dallas_ctrl['year'], dallas_ctrl['mover_avg_bedrooms'], color=BLACK, linewidth=2.5, marker='s', markersize=5, label='Dallas')
ax.axvspan(2022, 2024, alpha=0.1, color=BLUE, zorder=0)
ax.set_title('Avg Bedrooms (Movers)', fontsize=13, fontweight='bold', color=BLACK, pad=10)
ax.legend(frameon=False, fontsize=10)

ax = axes[2]
ax.plot(austin_ctrl['year'], austin_ctrl['mover_median_burden'], color=BLUE, linewidth=2.5, marker='o', markersize=5, label='Austin')
ax.plot(dallas_ctrl['year'], dallas_ctrl['mover_median_burden'], color=BLACK, linewidth=2.5, marker='s', markersize=5, label='Dallas')
ax.axhline(30, color=RED, linewidth=1, linestyle='--', alpha=0.6, label='30% threshold')
ax.axvspan(2022, 2024, alpha=0.1, color=BLUE, zorder=0)
ax.set_title('Mover Median Burden (%)', fontsize=13, fontweight='bold', color=BLACK, pad=10)
ax.legend(frameon=False, fontsize=10)

for ax in axes:
    ax.set_facecolor(CREAM_BG)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.tick_params(axis='y', length=0)
    ax.grid(axis='y', color='white', linewidth=0.8)
    ax.set_xticks([2015, 2017, 2019, 2021, 2023])

fig.suptitle('Austin vs Dallas: Income-Controlled ($40K-$80K)', fontsize=16, fontweight='bold',
             color=BLACK, y=1.02)
fig.text(0.5, 0.97, 'Middle-income renters only, ruling out composition effects',
         ha='center', fontsize=10, color='#888888')
fig.text(0.5, -0.02, 'Source: ACS 1-Year PUMS (2015-2024, excl. 2020), Zillow ZORI',
         ha='center', fontsize=8, color='#999999', fontstyle='italic')

plt.tight_layout()
plt.savefig('outputs/austin_vs_dallas_income_controlled.png', dpi=150, bbox_inches='tight', facecolor=CREAM_BG)
plt.rcParams['svg.fonttype'] = 'none'
plt.savefig('outputs/austin_vs_dallas_income_controlled.svg', bbox_inches='tight', facecolor=CREAM_BG)
plt.close()
print("Saved austin_vs_dallas_income_controlled.svg/png")
