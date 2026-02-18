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
        WHEN ACTIVITY // 100 IN (1201, 1202) THEN 'Socializing'
        WHEN ACTIVITY // 100 IN (1203, 1204, 1205, 1299) THEN 'TV & Leisure'
        WHEN ACTIVITY // 10000 = 13 THEN 'Sports & Exercise'
        WHEN ACTIVITY // 10000 = 14 THEN 'Religious'
        WHEN ACTIVITY // 10000 = 15 THEN 'Volunteering'
        WHEN ACTIVITY // 10000 = 16 THEN 'Phone Calls'
        WHEN ACTIVITY // 10000 = 18 THEN 'Travel'
        ELSE 'Other'
    END
"""

# Get activity-level data for 25-54
df = con.execute(f"""
    WITH base AS (
        SELECT
            {activity_map} as activity_cat,
            CAST(SCHAPPY AS DOUBLE) as happy,
            CAST(AWBWT AS DOUBLE) as wt,
            CASE WHEN AGEYCHILD < 999 THEN 1 ELSE 0 END as is_parent
        FROM 'data/atus_ipums.parquet'
        WHERE CAST(SCHAPPY AS INT) BETWEEN 0 AND 6
          AND {activity_map} NOT IN ('Other', 'Personal Care')
          AND AGE BETWEEN 25 AND 54
    )
    SELECT
        is_parent,
        activity_cat,
        SUM(wt) as total_wt,
        SUM(happy * wt) / SUM(wt) as mean_happy,
        COUNT(*) as n
    FROM base
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
        'activity': act,
        'delta_contrib': delta_contrib,
        'comp': comp, 'level': level,
        'p_time': p_time, 'np_time': np_time,
        'p_happy': p_happy, 'np_happy': np_happy,
    })

total_comp = sum(r['comp'] for r in results)
total_level = sum(r['level'] for r in results)
total_gap = total_comp + total_level

p_overall = sum(r['p_time'] * r['p_happy'] for r in results)
np_overall = sum(r['np_time'] * r['np_happy'] for r in results)

print(f"Parent happiness (25-54): {p_overall:.4f}")
print(f"Non-parent happiness (25-54): {np_overall:.4f}")
print(f"Gap: {p_overall - np_overall:.4f}")
print(f"Composition (time): {total_comp:.4f} ({total_comp/total_gap*100:.1f}%)")
print(f"Level (happiness): {total_level:.4f} ({total_level/total_gap*100:.1f}%)")

# Save decomposition data
decomp_data = []
for r in results:
    decomp_data.append({
        'activity': r['activity'],
        'parent_time': r['p_time'],
        'nonparent_time': r['np_time'],
        'parent_happy': r['p_happy'],
        'nonparent_happy': r['np_happy'],
        'delta_contrib': r['delta_contrib'],
        'comp_effect': r['comp'],
        'level_effect': r['level'],
    })
with open('data/parent_decomposition_25_54.json', 'w') as f:
    json.dump(decomp_data, f, indent=2)

print("\nBy activity:")
for r in sorted(results, key=lambda x: x['delta_contrib']):
    print(f"  {r['activity']:20s}  Δ={r['delta_contrib']:+.4f}  time={r['comp']:+.4f}  happy={r['level']:+.4f}")

# =====================================================================
# GROUPED DECOMPOSED WATERFALL CHART
# =====================================================================

# Group small activities
red_other_acts = ['Work', 'Sports & Exercise', 'Phone Calls', 'Education', 'Socializing', 'Prof. Services']
green_other_acts = ['Eating & Drinking', 'Volunteering', 'Religious', 'Travel', 'Shopping']

def sum_group(acts):
    return {
        'comp': sum(r['comp'] for r in results if r['activity'] in acts),
        'level': sum(r['level'] for r in results if r['activity'] in acts),
        'delta': sum(r['delta_contrib'] for r in results if r['activity'] in acts),
    }

def single(act_name):
    r = [r for r in results if r['activity'] == act_name][0]
    return {'comp': r['comp'], 'level': r['level'], 'delta': r['delta_contrib']}

red_other = sum_group(red_other_acts)
green_other = sum_group(green_other_acts)

grouped = [
    {'label': 'TV & Leisure',        **single('TV & Leisure')},
    {'label': 'Work, exercise,\nsocializing, etc.', **red_other},
    {'label': 'Eating, travel,\nreligion, etc.',    **green_other},
    {'label': 'Housework',           **single('Housework')},
    {'label': 'Childcare',           **single('Childcare')},
]

print("\nGrouped bars:")
for g in grouped:
    print(f"  {g['label']:30s}  Δ={g['delta']:+.4f}  time={g['comp']:+.4f}  happy={g['level']:+.4f}")

# --- Draw ---
fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

start = np_overall
n_bars = len(grouped)
labels = [g['label'] for g in grouped] + ['Net']
x_pos = np.arange(n_bars + 1)
bar_width = 0.65

TIME_COLOR = BLUE       # composition / time allocation
HAPPY_COLOR = YELLOW     # level / happiness during activity

cumulative = start

for i, g in enumerate(grouped):
    comp_val = g['comp']
    level_val = g['level']

    # Draw comp (time) sub-bar: from cumulative
    ax.bar(x_pos[i], comp_val, bottom=cumulative, color=TIME_COLOR,
           width=bar_width, zorder=3, alpha=0.85)

    # Draw level (happiness) sub-bar: stacked on top of comp
    ax.bar(x_pos[i], level_val, bottom=cumulative + comp_val, color=HAPPY_COLOR,
           width=bar_width, zorder=3, alpha=0.85)

    # Value label for total delta
    total = comp_val + level_val
    if total >= 0:
        y_label = cumulative + total + 0.005
        va = 'bottom'
    else:
        y_label = cumulative + total - 0.005
        va = 'top'
    ax.text(x_pos[i], y_label, f'{total:+.3f}', ha='center', va=va,
            fontsize=9, color=BLACK, fontweight='medium')

    # Connector line to next bar
    new_cumulative = cumulative + total
    if i < n_bars - 1:
        ax.plot([x_pos[i] + bar_width/2, x_pos[i+1] - bar_width/2],
                [new_cumulative, new_cumulative],
                color='#999', linewidth=0.5, zorder=2)

    cumulative = new_cumulative

# Net bar — show parent level
net = p_overall - np_overall
ax.bar(x_pos[-1], p_overall - start, bottom=start, color=GREEN,
       width=bar_width, zorder=3, alpha=0.5)
ax.text(x_pos[-1], p_overall + 0.005, f'+{net:.3f}', ha='center', va='bottom',
        fontsize=9, color=BLACK, fontweight='medium')

# Reference lines
ax.axhline(y=start, color=BLACK, linestyle=':', linewidth=0.8, alpha=0.4, zorder=1)
ax.text(-0.6, start + 0.003, f'No children: {start:.2f}', fontsize=9, color=BLACK, va='bottom', ha='left')

ax.axhline(y=p_overall, color=GREEN, linestyle=':', linewidth=0.8, alpha=0.4, zorder=1)
ax.text(n_bars + 0.6, p_overall + 0.003, f'Parents: {p_overall:.2f}', fontsize=9, color=GREEN, va='bottom', ha='right')

# Connector from last activity bar to net bar
ax.plot([x_pos[-2] + bar_width/2, x_pos[-1] - bar_width/2],
        [cumulative, cumulative], color='#999', linewidth=0.5, zorder=2)

# Axes
ax.set_xticks(x_pos)
ax.set_xticklabels(labels, fontsize=9)

# Y-axis: zoom to waterfall range
all_tops = [start]
all_bottoms = [start]
cum = start
for g in grouped:
    t = g['delta']
    c = g['comp']
    # Track the extremes within each bar (comp might overshoot before level pulls back)
    all_tops.append(cum + max(c, 0, c + g['level'], t))
    all_bottoms.append(cum + min(c, 0, c + g['level'], t))
    cum += t
all_tops.append(p_overall)

ax.set_ylim(min(all_bottoms) - 0.06, max(all_tops) + 0.08)

ax.tick_params(axis='y', length=0)
ax.tick_params(axis='x', length=0)
ax.spines['left'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.spines['bottom'].set_visible(False)
ax.grid(axis='y', alpha=0.3, color='#999', zorder=0)

# Legend
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor=TIME_COLOR, alpha=0.85, label='Time allocation'),
    Patch(facecolor=HAPPY_COLOR, alpha=0.85, label='Happiness during activity'),
]
ax.legend(handles=legend_elements, loc='lower left', frameon=False, fontsize=9)

# Titles
ax.set_title("What explains the parent happiness gap?",
             fontsize=14, fontweight='bold', color=BLACK, pad=30, loc='left')
ax.text(0, 1.02, "Decomposition: how much is from doing different things vs. being happier doing them (ages 25-54)",
        transform=ax.transAxes, fontsize=10, color='#888', style='italic')
ax.text(0, -0.10, 'Source: American Time Use Survey Well-Being Module (2010-2021)',
        transform=ax.transAxes, fontsize=8, color='#999', style='italic')

plt.tight_layout()
plt.savefig('outputs/parent_waterfall.png', dpi=100, bbox_inches='tight', facecolor=BG)
print("\nSaved waterfall chart")
plt.close()
