import duckdb
import json
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for f in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{f}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'

GREEN = '#67A275'
LIGHT_GREEN = '#C6DCCB'
BLUE = '#0BB4FF'
RED = '#F4743B'
LIGHT_RED = '#FBCAB5'
YELLOW = '#FEC439'
BLACK = '#3D3733'
BG = '#F6F7F3'

con = duckdb.connect()

# CORRECTED activity mapping
activity_map = """
    CASE 
        WHEN ACTIVITY // 10000 = 1 THEN 'Personal Care'
        WHEN ACTIVITY // 10000 IN (2, 9) THEN 'Housework'
        WHEN ACTIVITY // 10000 IN (3, 4, 10) THEN 'Childcare'
        WHEN ACTIVITY // 10000 = 5 THEN 'Work'
        WHEN ACTIVITY // 10000 = 6 THEN 'Education'
        WHEN ACTIVITY // 10000 = 7 THEN 'Shopping'
        WHEN ACTIVITY // 10000 = 8 THEN 'Prof. Services'
        WHEN ACTIVITY // 10000 = 11 THEN 'Eating & Drinking'
        WHEN ACTIVITY // 10000 = 12 THEN 'Socializing'
        WHEN ACTIVITY // 10000 = 13 THEN 'Sports & Leisure'
        WHEN ACTIVITY // 10000 = 14 THEN 'Religious'
        WHEN ACTIVITY // 10000 = 15 THEN 'Volunteering'
        WHEN ACTIVITY // 10000 = 16 THEN 'Phone Calls'
        WHEN ACTIVITY // 10000 = 18 THEN 'Travel'
        ELSE 'Other'
    END
"""

# =====================================================================
# CHART 3: Kid Stage 4-Panel (25-54)
# AGEYCHILD: 0-17 = age of youngest child, 999 = no children
# =====================================================================
stage_data = con.execute(f"""
    SELECT 
        CASE 
            WHEN AGEYCHILD = 0 THEN 'Baby (0)'
            WHEN AGEYCHILD BETWEEN 1 AND 2 THEN 'Toddler (1-2)'
            WHEN AGEYCHILD BETWEEN 3 AND 5 THEN 'Preschool (3-5)'
            WHEN AGEYCHILD BETWEEN 6 AND 9 THEN 'Early school (6-9)'
            WHEN AGEYCHILD BETWEEN 10 AND 12 THEN 'Preteen (10-12)'
            WHEN AGEYCHILD BETWEEN 13 AND 17 THEN 'Teen (13-17)'
            WHEN AGEYCHILD >= 999 THEN 'No children'
            ELSE 'Other'
        END as stage,
        CASE 
            WHEN AGEYCHILD = 0 THEN 1
            WHEN AGEYCHILD BETWEEN 1 AND 2 THEN 2
            WHEN AGEYCHILD BETWEEN 3 AND 5 THEN 3
            WHEN AGEYCHILD BETWEEN 6 AND 9 THEN 4
            WHEN AGEYCHILD BETWEEN 10 AND 12 THEN 5
            WHEN AGEYCHILD BETWEEN 13 AND 17 THEN 6
            WHEN AGEYCHILD >= 999 THEN 7
            ELSE 0
        END as stage_order,
        SUM(CAST(SCHAPPY AS DOUBLE) * CAST(AWBWT AS DOUBLE)) / SUM(CAST(AWBWT AS DOUBLE)) as mean_happy,
        SUM(CASE WHEN CAST(MEANING AS INT) BETWEEN 0 AND 6 THEN CAST(MEANING AS DOUBLE) * CAST(AWBWT AS DOUBLE) END) / 
            NULLIF(SUM(CASE WHEN CAST(MEANING AS INT) BETWEEN 0 AND 6 THEN CAST(AWBWT AS DOUBLE) END), 0) as mean_meaning,
        SUM(CASE WHEN CAST(SCSTRESS AS INT) BETWEEN 0 AND 6 THEN CAST(SCSTRESS AS DOUBLE) * CAST(AWBWT AS DOUBLE) END) / 
            NULLIF(SUM(CASE WHEN CAST(SCSTRESS AS INT) BETWEEN 0 AND 6 THEN CAST(AWBWT AS DOUBLE) END), 0) as mean_stress,
        SUM(CASE WHEN CAST(SCTIRED AS INT) BETWEEN 0 AND 6 THEN CAST(SCTIRED AS DOUBLE) * CAST(AWBWT AS DOUBLE) END) / 
            NULLIF(SUM(CASE WHEN CAST(SCTIRED AS INT) BETWEEN 0 AND 6 THEN CAST(AWBWT AS DOUBLE) END), 0) as mean_tired,
        COUNT(*) as n,
        COUNT(DISTINCT CASEID) as n_people
    FROM 'data/atus_ipums.parquet'
    WHERE CAST(SCHAPPY AS INT) BETWEEN 0 AND 6
      AND AGE BETWEEN 25 AND 54
    GROUP BY stage, stage_order
    HAVING stage != 'Other'
    ORDER BY stage_order
""").df()

print("Kid stage data (25-54):")
print(stage_data.to_string())

fig, axes = plt.subplots(2, 2, figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG)

stages = stage_data['stage'].values
n_stages = len(stages)

metrics = [
    ('mean_happy', 'Happiness', (3.5, 5.0)),
    ('mean_meaning', 'Meaning', (3.5, 5.0)),
    ('mean_stress', 'Stress', (0.5, 2.5)),
    ('mean_tired', 'Tiredness', (1.0, 3.2)),
]

for idx, (col, title, ylim) in enumerate(metrics):
    ax = axes[idx // 2][idx % 2]
    ax.set_facecolor(BG)
    
    vals = stage_data[col].values
    colors = [GREEN if s != 'No children' else BLUE for s in stages]
    
    x_pos = np.arange(n_stages)
    ax.bar(x_pos, vals, color=colors, width=0.7, zorder=3)
    
    ax.set_xticks(x_pos)
    ax.set_xticklabels(stages, fontsize=7, rotation=35, ha='right')
    ax.set_ylim(ylim)
    
    ax.tick_params(axis='y', length=0)
    ax.tick_params(axis='x', length=3, color='#999')
    ax.spines['left'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.grid(axis='y', alpha=0.3, color='#999', zorder=0)
    
    ax.set_title(title, fontsize=12, fontweight='bold', color=BLACK, pad=8)
    
    for i, v in enumerate(vals):
        if not np.isnan(v):
            ax.text(i, v + (ylim[1]-ylim[0])*0.02, f'{v:.2f}', ha='center', fontsize=7, color=BLACK)

fig.suptitle('Parenthood by the numbers: happiness, meaning, stress, tiredness',
             fontsize=14, fontweight='bold', color=BLACK, y=0.98)
fig.text(0.5, 0.93, 'Activity-weighted scores (0-6 scale), respondents aged 25-54',
         ha='center', fontsize=11, color='#888', style='italic')
fig.text(0.02, 0.01, 'Source: American Time Use Survey Well-Being Module (2010-2021)', 
         fontsize=8, color='#999', style='italic')

plt.tight_layout(rect=[0, 0.03, 1, 0.91])
plt.savefig('outputs/happiness_by_kid_stage.png', dpi=100, bbox_inches='tight', facecolor=BG)
print("Saved kid stage 4-panel chart")
plt.close()

# =====================================================================
# CHART 4: Waterfall (25-54)
# =====================================================================
df = con.execute(f"""
    WITH base AS (
        SELECT 
            {activity_map} as activity_cat,
            CAST(SCHAPPY AS DOUBLE) as happy,
            CAST(AWBWT AS DOUBLE) as wt,
            CASE WHEN AGEYCHILD < 999 THEN 1 ELSE 0 END as is_parent
        FROM 'data/atus_ipums.parquet'
        WHERE CAST(SCHAPPY AS INT) BETWEEN 0 AND 6
          AND AGE BETWEEN 25 AND 54
    )
    SELECT 
        is_parent,
        activity_cat,
        SUM(wt) as total_wt,
        SUM(happy * wt) / SUM(wt) as mean_happy,
        COUNT(*) as n
    FROM base
    WHERE activity_cat NOT IN ('Other', 'Personal Care')
    GROUP BY is_parent, activity_cat
""").df()

parents = df[df['is_parent']==1].set_index('activity_cat')
nonparents = df[df['is_parent']==0].set_index('activity_cat')

p_total_wt = parents['total_wt'].sum()
np_total_wt = nonparents['total_wt'].sum()

activities = sorted(set(parents.index) & set(nonparents.index))

results = []
for act in activities:
    p_time = parents.loc[act, 'total_wt'] / p_total_wt
    np_time = nonparents.loc[act, 'total_wt'] / np_total_wt
    p_happy = parents.loc[act, 'mean_happy']
    np_happy = nonparents.loc[act, 'mean_happy']
    
    p_contrib = p_time * p_happy
    np_contrib = np_time * np_happy
    delta_contrib = p_contrib - np_contrib
    
    avg_time = (p_time + np_time) / 2
    avg_happy = (p_happy + np_happy) / 2
    comp = (p_time - np_time) * avg_happy
    level = avg_time * (p_happy - np_happy)
    
    results.append({
        'activity': act, 'delta_contrib': delta_contrib,
        'comp': comp, 'level': level,
        'p_time': p_time, 'np_time': np_time,
        'p_happy': p_happy, 'np_happy': np_happy,
    })

results.sort(key=lambda x: x['delta_contrib'])

total_comp = sum(r['comp'] for r in results)
total_level = sum(r['level'] for r in results)
total_gap = total_comp + total_level

p_overall = sum(r['p_time'] * r['p_happy'] for r in results)
np_overall = sum(r['np_time'] * r['np_happy'] for r in results)

print(f"\nParent happiness (25-54): {p_overall:.4f}")
print(f"Non-parent happiness (25-54): {np_overall:.4f}")
print(f"Gap: {p_overall - np_overall:.4f}")
print(f"Composition: {total_comp:.4f} ({total_comp/total_gap*100:.1f}%)")
print(f"Level: {total_level:.4f} ({total_level/total_gap*100:.1f}%)")
print("\nBy activity:")
for r in sorted(results, key=lambda x: x['delta_contrib']):
    print(f"  {r['activity']:20s}  Δcontrib={r['delta_contrib']:+.4f}  comp={r['comp']:+.4f}  level={r['level']:+.4f}")

# Save decomposition
decomp_data = []
for r in results:
    decomp_data.append({
        'activity': r['activity'],
        'parent_time': r['p_time'], 'nonparent_time': r['np_time'],
        'parent_happy': r['p_happy'], 'nonparent_happy': r['np_happy'],
        'delta_contrib': r['delta_contrib'],
        'comp_effect': r['comp'], 'level_effect': r['level'],
    })
with open('data/parent_decomposition_25_54.json', 'w') as f:
    json.dump(decomp_data, f, indent=2)

# WATERFALL CHART
fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

labels = [r['activity'] for r in results] + ['Net']
deltas = [r['delta_contrib'] for r in results]
net = sum(deltas)

start = np_overall
cumulative = start
bottoms = []
heights = []

for d in deltas:
    if d >= 0:
        bottoms.append(cumulative)
        heights.append(d)
    else:
        bottoms.append(cumulative + d)
        heights.append(-d)
    cumulative += d

n_bars = len(results)
x_pos = np.arange(n_bars + 1)

for i in range(n_bars):
    color = GREEN if deltas[i] >= 0 else LIGHT_RED
    ax.bar(x_pos[i], heights[i], bottom=bottoms[i], color=color, width=0.7, zorder=3)

# Net bar
net_color = GREEN if net >= 0 else RED
ax.bar(x_pos[-1], start + net, bottom=0, color=net_color, width=0.7, zorder=3, alpha=0.7)

# Connector lines
running = start
for i in range(n_bars - 1):
    running += deltas[i]
    ax.plot([x_pos[i] + 0.35, x_pos[i+1] - 0.35], [running, running], 
            color='#999', linewidth=0.5, zorder=2)

# Reference lines
ax.axhline(y=start, color=BLACK, linestyle=':', linewidth=0.8, alpha=0.5, zorder=1)
ax.text(-0.5, start, f'No children: {start:.2f}', fontsize=8, color=BLACK, va='bottom', ha='left')
ax.axhline(y=start + net, color=GREEN, linestyle=':', linewidth=0.8, alpha=0.5, zorder=1)
ax.text(n_bars + 0.5, start + net, f'Parents: {start+net:.2f}', fontsize=8, color=GREEN, va='bottom', ha='right')

ax.set_xticks(x_pos)
ax.set_xticklabels(labels, fontsize=8, rotation=45, ha='right')

ymin = min(bottoms) - 0.1
ymax = max(b + h for b, h in zip(bottoms, heights)) + 0.15
ax.set_ylim(ymin, ymax)

ax.tick_params(axis='y', length=0)
ax.tick_params(axis='x', length=3, color='#999')
ax.spines['left'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.grid(axis='y', alpha=0.3, color='#999', zorder=0)

for i in range(n_bars):
    d = deltas[i]
    if abs(d) > 0.008:
        y_label = bottoms[i] + heights[i] + 0.005 if d >= 0 else bottoms[i] - 0.015
        va = 'bottom' if d >= 0 else 'top'
        ax.text(x_pos[i], y_label, f'{d:+.3f}', ha='center', va=va, fontsize=7, color=BLACK)

ax.set_title("What explains the parent happiness gap?", 
             fontsize=14, fontweight='bold', color=BLACK, pad=30, loc='left')
ax.text(0, 1.02, "Each activity's contribution to the parent vs. non-parent gap, ages 25-54",
        transform=ax.transAxes, fontsize=11, color='#888', style='italic')
ax.text(0, -0.18, 'Source: American Time Use Survey Well-Being Module (2010-2021)', 
        transform=ax.transAxes, fontsize=8, color='#999', style='italic')

plt.tight_layout()
plt.savefig('outputs/parent_waterfall.png', dpi=100, bbox_inches='tight', facecolor=BG)
print("Saved waterfall chart")
plt.close()
