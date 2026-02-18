"""
Build cross-metro panel: ACS renter outcomes + ZORI rent changes.
For 50-80 large metros, compute mover rate, mover bedrooms, mover burden,
mover commute time in 2022 and 2024. Match to ZORI rent changes (2022->2024
captures the actual rent decline period; 2022 was peak rents nationally).
Output: data/metro_year_panel.csv
"""

import pandas as pd
import numpy as np
import duckdb

# === Paths ===
ACS_PATH = '/Users/azizsunderji/Dropbox/Home Economics/Data/ACS_1Y/acs_1y.parquet'
ZORI_PATH = 'data/zillow_zori_metro.csv'
MET_CODES_PATH = '/Users/azizsunderji/Dropbox/Home Economics/Reference/Codes/MET2013.xlsx'
OUTPUT_PATH = 'data/metro_year_panel.csv'

con = duckdb.connect()

# === Step 1: Build MET2013 -> ZORI crosswalk ===
met = pd.read_excel(MET_CODES_PATH)
met.columns = ['MET2013', 'CBSA_Name']
met = met[met['MET2013'] > 0].copy()

zori_names = con.execute("""
    SELECT RegionName, RegionID
    FROM 'data/zillow_zori_metro.csv'
    WHERE RegionType = 'msa'
""").df()

def extract_primary_city_state(cbsa_name):
    parts = cbsa_name.split(',')
    if len(parts) < 2:
        return None
    state = parts[-1].strip().split('-')[0].strip()
    city = parts[0].split('-')[0].strip()
    return f"{city}, {state}"

met['zori_name'] = met['CBSA_Name'].apply(extract_primary_city_state)

# Manual fixes for known mismatches
manual_fixes = {
    31140: 'Louisville, KY',  # Louisville/Jefferson County
}
for code, name in manual_fixes.items():
    met.loc[met['MET2013'] == code, 'zori_name'] = name

# Merge to get ZORI RegionID
crosswalk = met.merge(zori_names, left_on='zori_name', right_on='RegionName', how='inner')
crosswalk = crosswalk[['MET2013', 'CBSA_Name', 'zori_name', 'RegionID']].copy()
print(f"Crosswalk: {len(crosswalk)} metros matched")

# === Step 2: Compute ZORI annual averages and 2022->2024 change ===
# Read ZORI data, melt to long format
zori_raw = pd.read_csv(ZORI_PATH)
zori_msa = zori_raw[zori_raw['RegionType'] == 'msa'].copy()

# Get date columns
date_cols = [c for c in zori_msa.columns if c.startswith('20')]

# Melt to long
zori_long = zori_msa[['RegionName', 'RegionID'] + date_cols].melt(
    id_vars=['RegionName', 'RegionID'],
    var_name='date',
    value_name='zori'
)
zori_long['date'] = pd.to_datetime(zori_long['date'])
zori_long['year'] = zori_long['date'].dt.year

# Annual averages
zori_annual = zori_long.groupby(['RegionName', 'RegionID', 'year'])['zori'].mean().reset_index()

# Compute 2022->2024 % change
zori_2022 = zori_annual[zori_annual['year'] == 2022].set_index('RegionID')['zori']
zori_2024 = zori_annual[zori_annual['year'] == 2024].set_index('RegionID')['zori']
zori_change = ((zori_2024 - zori_2022) / zori_2022 * 100).reset_index()
zori_change.columns = ['RegionID', 'zori_pct_change_2022_2024']

# Also get absolute levels
zori_2022_df = zori_annual[zori_annual['year'] == 2022][['RegionID', 'zori']].rename(columns={'zori': 'zori_2022'})
zori_2024_df = zori_annual[zori_annual['year'] == 2024][['RegionID', 'zori']].rename(columns={'zori': 'zori_2024'})

zori_summary = zori_change.merge(zori_2022_df, on='RegionID').merge(zori_2024_df, on='RegionID')
print(f"ZORI change computed for {len(zori_summary)} metros")

# === Step 3: Compute ACS renter outcomes per metro-year ===
# For years 2022 and 2024, compute per metro:
# - mover_rate: % with MIGRATE1 > 1
# - mover_avg_bedrooms: mean BEDROOMS for movers (weighted)
# - mover_avg_rooms: mean ROOMS for movers (weighted)
# - mover_median_burden: median (RENTGRS*12/HHINCOME*100) for movers
# - nonmover_median_burden: same for non-movers
# - mover_avg_trantime: mean TRANTIME for movers (exclude 0 = not applicable)
# - n_unweighted: sample size

# Query all renter households in 2022 and 2024 with valid metro codes
acs_df = con.execute(f"""
    SELECT
        YEAR, MET2013, MIGRATE1, BEDROOMS, ROOMS, RENTGRS, HHINCOME, HHWT, TRANTIME
    FROM '{ACS_PATH}'
    WHERE OWNERSHP = 2
      AND HHINCOME > 0
      AND RENTGRS > 0
      AND MET2013 > 0
      AND YEAR IN (2022, 2024)
      AND PERNUM = 1
""").df()

# Compute burden
acs_df['burden'] = acs_df['RENTGRS'] * 12 / acs_df['HHINCOME'] * 100
acs_df['is_mover'] = (acs_df['MIGRATE1'] > 1).astype(int)

print(f"ACS records loaded: {len(acs_df)}")

# Compute weighted stats per metro-year
results = []
for (year, met2013), grp in acs_df.groupby(['YEAR', 'MET2013']):
    n = len(grp)
    if n < 100:  # skip tiny metros
        continue

    total_wt = grp['HHWT'].sum()
    mover_wt = grp.loc[grp['is_mover'] == 1, 'HHWT'].sum()
    mover_rate = mover_wt / total_wt * 100

    movers = grp[grp['is_mover'] == 1]
    nonmovers = grp[grp['is_mover'] == 0]

    # Weighted mean bedrooms for movers
    if len(movers) > 0 and movers['HHWT'].sum() > 0:
        mover_avg_bed = np.average(movers['BEDROOMS'], weights=movers['HHWT'])
        mover_avg_rooms = np.average(movers['ROOMS'], weights=movers['HHWT'])

        # Weighted median burden for movers (approximate using sorted weighted percentile)
        m_sorted = movers.sort_values('burden')
        m_cumwt = m_sorted['HHWT'].cumsum()
        m_total = m_sorted['HHWT'].sum()
        mover_med_burden = m_sorted.loc[m_cumwt >= m_total / 2, 'burden'].iloc[0]

        # Commute time for movers (exclude 0 = not working / n/a)
        mover_commuters = movers[movers['TRANTIME'] > 0]
        if len(mover_commuters) > 10:
            mover_avg_trantime = np.average(mover_commuters['TRANTIME'], weights=mover_commuters['HHWT'])
        else:
            mover_avg_trantime = np.nan
    else:
        mover_avg_bed = np.nan
        mover_avg_rooms = np.nan
        mover_med_burden = np.nan
        mover_avg_trantime = np.nan

    # Non-mover median burden
    if len(nonmovers) > 0 and nonmovers['HHWT'].sum() > 0:
        nm_sorted = nonmovers.sort_values('burden')
        nm_cumwt = nm_sorted['HHWT'].cumsum()
        nm_total = nm_sorted['HHWT'].sum()
        nonmover_med_burden = nm_sorted.loc[nm_cumwt >= nm_total / 2, 'burden'].iloc[0]
    else:
        nonmover_med_burden = np.nan

    results.append({
        'year': year,
        'MET2013': met2013,
        'n_unweighted': n,
        'n_movers_unweighted': len(movers),
        'mover_rate': mover_rate,
        'mover_avg_bedrooms': mover_avg_bed,
        'mover_avg_rooms': mover_avg_rooms,
        'mover_median_burden': mover_med_burden,
        'nonmover_median_burden': nonmover_med_burden,
        'mover_avg_trantime': mover_avg_trantime,
    })

panel = pd.DataFrame(results)
print(f"Panel: {len(panel)} metro-year observations")

# === Step 4: Pivot to compute 2022->2024 changes ===
panel_2022 = panel[panel['year'] == 2022].set_index('MET2013')
panel_2024 = panel[panel['year'] == 2024].set_index('MET2013')

# Only keep metros with data in both years
common_metros = panel_2022.index.intersection(panel_2024.index)
print(f"Metros with data in both 2022 and 2024: {len(common_metros)}")

changes = pd.DataFrame(index=common_metros)
changes['mover_rate_2022'] = panel_2022.loc[common_metros, 'mover_rate']
changes['mover_rate_2024'] = panel_2024.loc[common_metros, 'mover_rate']
changes['delta_mover_rate'] = changes['mover_rate_2024'] - changes['mover_rate_2022']

changes['mover_avg_bed_2022'] = panel_2022.loc[common_metros, 'mover_avg_bedrooms']
changes['mover_avg_bed_2024'] = panel_2024.loc[common_metros, 'mover_avg_bedrooms']
changes['delta_mover_avg_bed'] = changes['mover_avg_bed_2024'] - changes['mover_avg_bed_2022']

changes['mover_avg_rooms_2022'] = panel_2022.loc[common_metros, 'mover_avg_rooms']
changes['mover_avg_rooms_2024'] = panel_2024.loc[common_metros, 'mover_avg_rooms']
changes['delta_mover_avg_rooms'] = changes['mover_avg_rooms_2024'] - changes['mover_avg_rooms_2022']

changes['mover_burden_2022'] = panel_2022.loc[common_metros, 'mover_median_burden']
changes['mover_burden_2024'] = panel_2024.loc[common_metros, 'mover_median_burden']
changes['delta_mover_burden'] = changes['mover_burden_2024'] - changes['mover_burden_2022']

changes['nonmover_burden_2022'] = panel_2022.loc[common_metros, 'nonmover_median_burden']
changes['nonmover_burden_2024'] = panel_2024.loc[common_metros, 'nonmover_median_burden']
changes['delta_nonmover_burden'] = changes['nonmover_burden_2024'] - changes['nonmover_burden_2022']

changes['mover_trantime_2022'] = panel_2022.loc[common_metros, 'mover_avg_trantime']
changes['mover_trantime_2024'] = panel_2024.loc[common_metros, 'mover_avg_trantime']
changes['delta_mover_trantime'] = changes['mover_trantime_2024'] - changes['mover_trantime_2022']

changes['n_2022'] = panel_2022.loc[common_metros, 'n_unweighted']
changes['n_2024'] = panel_2024.loc[common_metros, 'n_unweighted']
changes['n_movers_2022'] = panel_2022.loc[common_metros, 'n_movers_unweighted']
changes['n_movers_2024'] = panel_2024.loc[common_metros, 'n_movers_unweighted']
changes['min_n'] = changes[['n_2022', 'n_2024']].min(axis=1)

changes = changes.reset_index()

# === Step 5: Merge with crosswalk and ZORI ===
changes = changes.merge(crosswalk[['MET2013', 'CBSA_Name', 'zori_name', 'RegionID']], on='MET2013', how='inner')
changes = changes.merge(zori_summary, on='RegionID', how='inner')

print(f"\nFinal panel with ZORI match: {len(changes)} metros")

# Filter to metros with >=500 renter HHs per year (stable estimates)
reliable = changes[changes['min_n'] >= 500].copy()
print(f"After min_n >= 500 filter: {len(reliable)} metros")

# Sort by rent change
reliable = reliable.sort_values('zori_pct_change_2022_2024')

# Print summary
print(f"\nRent change range: {reliable['zori_pct_change_2022_2024'].min():.1f}% to {reliable['zori_pct_change_2022_2024'].max():.1f}%")
print(f"\nTop 10 metros by RENT DECLINE:")
for _, row in reliable.head(10).iterrows():
    print(f"  {row['zori_name']}: ZORI {row['zori_pct_change_2022_2024']:.1f}%, "
          f"Δ mover rate {row['delta_mover_rate']:+.1f}pp, "
          f"Δ bedrooms {row['delta_mover_avg_bed']:+.2f}, "
          f"n={row['min_n']}")

print(f"\nTop 10 metros by RENT INCREASE:")
for _, row in reliable.tail(10).iterrows():
    print(f"  {row['zori_name']}: ZORI {row['zori_pct_change_2022_2024']:.1f}%, "
          f"Δ mover rate {row['delta_mover_rate']:+.1f}pp, "
          f"Δ bedrooms {row['delta_mover_avg_bed']:+.2f}, "
          f"n={row['min_n']}")

# Austin check
austin = reliable[reliable['MET2013'] == 12420]
if len(austin) > 0:
    a = austin.iloc[0]
    print(f"\nAUSTIN: ZORI {a['zori_pct_change_2022_2024']:.1f}%, "
          f"mover rate {a['mover_rate_2022']:.1f}% -> {a['mover_rate_2024']:.1f}% (Δ{a['delta_mover_rate']:+.1f}pp), "
          f"bed {a['mover_avg_bed_2022']:.2f} -> {a['mover_avg_bed_2024']:.2f} (Δ{a['delta_mover_avg_bed']:+.2f}), "
          f"burden {a['mover_burden_2022']:.1f}% -> {a['mover_burden_2024']:.1f}% (Δ{a['delta_mover_burden']:+.1f}pp)")

# Save
reliable.to_csv(OUTPUT_PATH, index=False)
print(f"\nSaved to {OUTPUT_PATH}")

# Also save the full panel (both years, all metros) for reference
panel_merged = panel.merge(crosswalk[['MET2013', 'CBSA_Name', 'zori_name']], on='MET2013', how='inner')
panel_merged.to_csv('data/metro_year_panel_full.csv', index=False)
print(f"Full panel saved to data/metro_year_panel_full.csv")
