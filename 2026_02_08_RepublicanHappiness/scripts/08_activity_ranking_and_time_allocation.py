import duckdb
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# Font setup
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for f in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{f}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'

BLUE = '#0BB4FF'
GREEN = '#67A275'
LIGHT_GREEN = '#C6DCCB'
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
        WHEN ACTIVITY // 10000 = 3 THEN 'Caring for Others'
        WHEN ACTIVITY // 10000 IN (4, 10) THEN 'Childcare'
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
# CHART 1: Activity Happiness Ranking (25-54 only)
# =====================================================================
ranking = con.execute(f"""
    WITH tagged AS (
        SELECT 
            {activity_map} as activity,
            CAST(SCHAPPY AS DOUBLE) as happy,
            CAST(MEANING AS DOUBLE) as meaning_val,
            CAST(AWBWT AS DOUBLE) as wt,
            AGE
        FROM 'data/atus_ipums.parquet'
        WHERE CAST(SCHAPPY AS INT) BETWEEN 0 AND 6
          AND AGE BETWEEN 25 AND 54
    )
    SELECT 
        activity,
        SUM(happy * wt) / SUM(wt) as mean_happy,
        SUM(meaning_val * wt) / NULLIF(SUM(CASE WHEN meaning_val BETWEEN 0 AND 6 THEN wt END), 0) as mean_meaning,
        COUNT(*) as n
    FROM tagged
    WHERE activity NOT IN ('Other', 'Personal Care')
    GROUP BY activity
    ORDER BY mean_happy
""").df()

print("Activity ranking (25-54):")
print(ranking.to_string())

fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

activities = ranking['activity'].values
happy = ranking['mean_happy'].values
meaning = ranking['mean_meaning'].values

y_pos = np.arange(len(activities))
bars = ax.barh(y_pos, happy, height=0.6, color=GREEN, zorder=3)
ax.scatter(meaning, y_pos, color=YELLOW, s=60, zorder=4, edgecolors='white', linewidth=0.5)

ax.set_yticks(y_pos)
ax.set_yticklabels(activities, fontsize=10)
ax.set_xlim(2.5, 5.8)

ax.tick_params(axis='y', length=0)
ax.tick_params(axis='x', length=4, color='#999')
ax.spines['left'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.grid(axis='x', alpha=0.3, color='#999', zorder=0)

# Legend
ax.barh([], [], color=GREEN, label='Happiness')
ax.scatter([], [], color=YELLOW, s=60, label='Meaning', edgecolors='white', linewidth=0.5)
ax.legend(loc='lower right', frameon=False, fontsize=9)

ax.set_title('What makes us happy (and what feels meaningful)', 
             fontsize=14, fontweight='bold', color=BLACK, pad=30, loc='left')
ax.text(0, 1.02, 'Activity-weighted scores (0-6 scale), respondents aged 25-54', 
        transform=ax.transAxes, fontsize=11, color='#888', style='italic')
ax.text(0, -0.06, 'Source: American Time Use Survey Well-Being Module (2010-2021)', 
        transform=ax.transAxes, fontsize=8, color='#999', style='italic')

plt.tight_layout()
plt.savefig('outputs/activity_happiness_ranking.png', dpi=100, bbox_inches='tight', facecolor=BG)
plt.savefig('outputs/activity_happiness_ranking.svg', bbox_inches='tight', facecolor=BG)
print("Saved activity ranking chart")
plt.close()

# =====================================================================
# CHART 2: Time Allocation Parents vs Non-Parents (25-54 only)
# =====================================================================
time_alloc = con.execute(f"""
    WITH tagged AS (
        SELECT 
            CASEID,
            {activity_map} as activity_cat,
            CAST(AWBWT AS DOUBLE) as wt,
            CASE WHEN AGEYCHILD < 999 THEN 'Parents' ELSE 'No children' END as grp
        FROM 'data/atus_ipums.parquet'
        WHERE CAST(SCHAPPY AS INT) BETWEEN 0 AND 6
          AND AGE BETWEEN 25 AND 54
    )
    SELECT 
        grp,
        activity_cat,
        SUM(wt) as total_wt
    FROM tagged
    WHERE activity_cat NOT IN ('Other', 'Personal Care')
    GROUP BY grp, activity_cat
""").df()

# Compute shares
for g in ['Parents', 'No children']:
    mask = time_alloc['grp'] == g
    total = time_alloc.loc[mask, 'total_wt'].sum()
    time_alloc.loc[mask, 'share'] = time_alloc.loc[mask, 'total_wt'] / total

pivot = time_alloc.pivot(index='activity_cat', columns='grp', values='share').fillna(0)
pivot['diff'] = pivot['Parents'] - pivot['No children']
pivot = pivot.sort_values('diff')

print("\nTime allocation (25-54):")
print(pivot.to_string())

fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

activities = pivot.index.values
y_pos = np.arange(len(activities))
bar_height = 0.35

ax.barh(y_pos + bar_height/2, pivot['Parents'].values * 100, height=bar_height, color=GREEN, label='Parents', zorder=3)
ax.barh(y_pos - bar_height/2, pivot['No children'].values * 100, height=bar_height, color=BLUE, label='No children', zorder=3)

ax.set_yticks(y_pos)
ax.set_yticklabels(activities, fontsize=10)

# Add diff annotations on right
for i, act in enumerate(activities):
    d = pivot.loc[act, 'diff'] * 100
    if abs(d) > 1:
        sign = '+' if d > 0 else ''
        ax.text(max(pivot.loc[act, 'Parents'], pivot.loc[act, 'No children']) * 100 + 0.5, i,
                f'{sign}{d:.1f}pp', fontsize=8, va='center', color=BLACK, alpha=0.7)

ax.tick_params(axis='y', length=0)
ax.tick_params(axis='x', length=4, color='#999')
ax.spines['left'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.grid(axis='x', alpha=0.3, color='#999', zorder=0)

# X-axis: percent with % on top label
xticks = ax.get_xticks()
xlabels = [f'{int(x)}' for x in xticks]
if len(xlabels) > 0:
    xlabels[-1] = f'{int(xticks[-1])}%'
ax.set_xticklabels(xlabels)

ax.legend(loc='lower right', frameon=False, fontsize=9)

ax.set_title('How parents spend their time differently', 
             fontsize=14, fontweight='bold', color=BLACK, pad=30, loc='left')
ax.text(0, 1.02, 'Share of waking time by activity, respondents aged 25-54', 
        transform=ax.transAxes, fontsize=11, color='#888', style='italic')
ax.text(0, -0.06, 'Source: American Time Use Survey Well-Being Module (2010-2021)', 
        transform=ax.transAxes, fontsize=8, color='#999', style='italic')

plt.tight_layout()
plt.savefig('outputs/time_allocation_parents.png', dpi=100, bbox_inches='tight', facecolor=BG)
plt.savefig('outputs/time_allocation_parents.svg', bbox_inches='tight', facecolor=BG)
print("Saved time allocation chart")
plt.close()
