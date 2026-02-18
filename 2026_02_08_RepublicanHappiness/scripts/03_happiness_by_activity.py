"""
03_happiness_by_activity.py
Core analysis: Weighted mean happiness and time allocation by activity x political lean.
Also performs the composition/level decomposition.
"""
import pandas as pd
import numpy as np

DATA_DIR = '/Users/azizsunderji/Dropbox/Home Economics/2026_02_08_RepublicanHappiness/data'

# Load merged data
df = pd.read_parquet(f'{DATA_DIR}/atus_wb_politics.parquet')
print(f"Loaded {len(df)} observations")

# Focus on major activity categories with enough sample
KEEP_CATS = [
    'Socializing & Leisure', 'Housework', 'Eating & Drinking', 'Work',
    'Caring for Household Members', 'Shopping', 'Sports & Exercise',
    'Religious & Spiritual', 'Education', 'Travel',
    'Volunteering', 'Telephone Calls'
]
df = df[df['activity_category'].isin(KEEP_CATS)].copy()

# =========================================================
# 1. Weighted mean HAPPINESS by activity x political lean
# =========================================================
# Use AWBWT (activity-level WB weight) for happiness means
print("\n" + "="*70)
print("HAPPINESS BY ACTIVITY x POLITICAL LEAN (weighted by AWBWT)")
print("="*70)

def weighted_mean(group, val_col, wt_col):
    w = group[wt_col]
    v = group[val_col]
    mask = w.notna() & v.notna() & (w > 0)
    if mask.sum() == 0:
        return np.nan
    return np.average(v[mask], weights=w[mask])

happiness_results = []
for cat in KEEP_CATS:
    for lean in ['Blue', 'Purple', 'Red']:
        sub = df[(df['activity_category'] == cat) & (df['political_lean'] == lean)]
        if len(sub) < 30:
            continue
        wm = weighted_mean(sub, 'SCHAPPY', 'AWBWT')
        happiness_results.append({
            'activity': cat,
            'political_lean': lean,
            'mean_happiness': round(wm, 3),
            'n': len(sub),
            'unweighted_mean': round(sub['SCHAPPY'].mean(), 3)
        })

happy_df = pd.DataFrame(happiness_results)
pivot_happy = happy_df.pivot(index='activity', columns='political_lean', values='mean_happiness')
pivot_happy = pivot_happy[['Blue', 'Purple', 'Red']]
pivot_happy['Red-Blue Gap'] = pivot_happy['Red'] - pivot_happy['Blue']
pivot_happy = pivot_happy.sort_values('Red-Blue Gap', ascending=False)

# Also get sample sizes
pivot_n = happy_df.pivot(index='activity', columns='political_lean', values='n')

print("\nWeighted Mean Happiness (0-6 scale):")
print(pivot_happy.round(3).to_string())
print("\nSample sizes:")
print(pivot_n.to_string())

# =========================================================
# 2. TIME ALLOCATION by political lean
# =========================================================
# For time allocation, use WT06 and DURATION at person level
# Total minutes per day in each category, weighted
print("\n" + "="*70)
print("TIME ALLOCATION BY POLITICAL LEAN (weighted minutes/day)")
print("="*70)

# Aggregate duration by person x category
person_time = df.groupby(['CASEID', 'activity_category', 'political_lean', 'WT06'], observed=True).agg(
    total_minutes=('DURATION', 'sum')
).reset_index()

time_results = []
for cat in KEEP_CATS:
    for lean in ['Blue', 'Purple', 'Red']:
        sub = person_time[(person_time['activity_category'] == cat) & (person_time['political_lean'] == lean)]
        if len(sub) < 30:
            continue
        wm = np.average(sub['total_minutes'], weights=sub['WT06'])
        time_results.append({
            'activity': cat,
            'political_lean': lean,
            'minutes_per_day': round(wm, 1),
            'n_persons': len(sub)
        })

time_df = pd.DataFrame(time_results)
pivot_time = time_df.pivot(index='activity', columns='political_lean', values='minutes_per_day')
pivot_time = pivot_time[['Blue', 'Purple', 'Red']]
pivot_time['Red-Blue Diff'] = pivot_time['Red'] - pivot_time['Blue']
pivot_time = pivot_time.sort_values('Red-Blue Diff', ascending=False)

print("\nWeighted Minutes per Day (among those doing activity):")
print(pivot_time.round(1).to_string())

# =========================================================
# 3. OVERALL HAPPINESS by political lean
# =========================================================
print("\n" + "="*70)
print("OVERALL HAPPINESS BY POLITICAL LEAN")
print("="*70)

for lean in ['Blue', 'Purple', 'Red']:
    sub = df[df['political_lean'] == lean]
    wm = weighted_mean(sub, 'SCHAPPY', 'AWBWT')
    n_people = sub['CASEID'].nunique()
    print(f"  {lean:8s}: {wm:.3f} (n={len(sub):,}, {n_people:,} people)")

# =========================================================
# 4. DECOMPOSITION: Composition vs Level effects
# =========================================================
print("\n" + "="*70)
print("OAXACA-STYLE DECOMPOSITION")
print("="*70)
print("ΔHappiness = Σ(Δtime_i × avg_happiness_i) + Σ(avg_time_i × Δhappiness_i)")
print("           = Composition effect          + Level effect\n")

# Need: for each activity i, the share of happiness-weighted time, and the happiness level
# Use activity-observation shares (not person-day minutes, since WB module samples 3 activities)
# Share of WB observations in each category = proxy for time allocation

red = df[df['political_lean'] == 'Red']
blue = df[df['political_lean'] == 'Blue']

# Get weighted shares and happiness for each group
def get_shares_and_happiness(group, wt_col='AWBWT'):
    """Get time share and mean happiness per activity category."""
    results = {}
    total_wt = group[wt_col].sum()
    for cat in KEEP_CATS:
        sub = group[group['activity_category'] == cat]
        if len(sub) < 10:
            continue
        share = sub[wt_col].sum() / total_wt
        happiness = np.average(sub['SCHAPPY'], weights=sub[wt_col])
        results[cat] = {'share': share, 'happiness': happiness}
    return pd.DataFrame(results).T

red_stats = get_shares_and_happiness(red)
blue_stats = get_shares_and_happiness(blue)

# Align categories
common_cats = red_stats.index.intersection(blue_stats.index)
red_stats = red_stats.loc[common_cats]
blue_stats = blue_stats.loc[common_cats]

# Means across groups
avg_happiness = (red_stats['happiness'] + blue_stats['happiness']) / 2
avg_share = (red_stats['share'] + blue_stats['share']) / 2

# Differences
delta_share = red_stats['share'] - blue_stats['share']
delta_happiness = red_stats['happiness'] - blue_stats['happiness']

# Decomposition
composition_effect = (delta_share * avg_happiness).sum()
level_effect = (avg_share * delta_happiness).sum()
total_gap = composition_effect + level_effect

# Actual overall gap for comparison
red_overall = np.average(red['SCHAPPY'], weights=red['AWBWT'])
blue_overall = np.average(blue['SCHAPPY'], weights=blue['AWBWT'])
actual_gap = red_overall - blue_overall

print(f"Red overall happiness:  {red_overall:.3f}")
print(f"Blue overall happiness: {blue_overall:.3f}")
print(f"Actual gap (Red-Blue):  {actual_gap:.3f}")
print()
print(f"Decomposition:")
print(f"  Composition effect (what people do):  {composition_effect:+.4f}")
print(f"  Level effect (how happy doing it):    {level_effect:+.4f}")
print(f"  Sum:                                  {composition_effect + level_effect:+.4f}")
print()
pct_composition = abs(composition_effect) / (abs(composition_effect) + abs(level_effect)) * 100
pct_level = abs(level_effect) / (abs(composition_effect) + abs(level_effect)) * 100
print(f"  Composition share: {pct_composition:.1f}%")
print(f"  Level share:       {pct_level:.1f}%")

# Detail by activity
print("\nDecomposition by activity:")
decomp_detail = pd.DataFrame({
    'Red_share': red_stats['share'],
    'Blue_share': blue_stats['share'],
    'Δshare': delta_share,
    'Red_happy': red_stats['happiness'],
    'Blue_happy': blue_stats['happiness'],
    'Δhappy': delta_happiness,
    'Composition': delta_share * avg_happiness,
    'Level': avg_share * delta_happiness,
}).round(4)
decomp_detail = decomp_detail.sort_values('Level', ascending=False)
print(decomp_detail.to_string())

# Save results for charting
happy_df.to_parquet(f'{DATA_DIR}/happiness_by_activity_lean.parquet', index=False)
time_df.to_parquet(f'{DATA_DIR}/time_by_activity_lean.parquet', index=False)
decomp_detail.to_parquet(f'{DATA_DIR}/decomposition_detail.parquet')

print("\nSaved analysis results.")
