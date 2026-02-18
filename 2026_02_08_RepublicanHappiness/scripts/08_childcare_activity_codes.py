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

# Colors
BLUE = '#0BB4FF'
GREEN = '#67A275'
LIGHT_GREEN = '#C6DCCB'
RED = '#F4743B'
LIGHT_RED = '#FBCAB5'
YELLOW = '#FEC439'
BLACK = '#3D3733'
BG = '#F6F7F3'

con = duckdb.connect()

# First: understand what's in activity codes 03xxxx and 04xxxx
print("=== ACTIVITY CODE BREAKDOWN (first 2 digits of 6-digit code) ===")
codes = con.execute("""
    SELECT 
        ACTIVITY // 10000 as major,
        (ACTIVITY // 1000) as sub,
        COUNT(*) as n,
        SUM(CAST(AWBWT AS DOUBLE)) as total_wt
    FROM 'data/atus_ipums.parquet'
    WHERE CAST(SCHAPPY AS INT) BETWEEN 0 AND 6
      AND ACTIVITY // 10000 IN (3, 4)
    GROUP BY 1, 2
    ORDER BY 1, 2
""").df()
print(codes.to_string())

# True childcare = 0301xx-0303xx (HH children) + 0401xx-0403xx (non-HH children)
# Let's check: what fraction of 03xxxx is child care vs adult care?
print("\n=== 03xxxx: HH members breakdown ===")
hh = con.execute("""
    SELECT 
        CASE 
            WHEN ACTIVITY // 1000 BETWEEN 30 AND 33 THEN 'HH child care'
            WHEN ACTIVITY // 1000 BETWEEN 34 AND 39 THEN 'HH adult care'
            ELSE 'Other HH'
        END as subcat,
        COUNT(*) as n,
        SUM(CAST(AWBWT AS DOUBLE)) as total_wt
    FROM 'data/atus_ipums.parquet'
    WHERE CAST(SCHAPPY AS INT) BETWEEN 0 AND 6
      AND ACTIVITY // 10000 = 3
    GROUP BY 1
""").df()
print(hh.to_string())

print("\n=== 04xxxx: Non-HH members breakdown ===")
nonhh = con.execute("""
    SELECT 
        CASE 
            WHEN ACTIVITY // 1000 BETWEEN 40 AND 43 THEN 'Non-HH child care'
            WHEN ACTIVITY // 1000 BETWEEN 44 AND 49 THEN 'Non-HH adult care'
            ELSE 'Other Non-HH'
        END as subcat,
        COUNT(*) as n,
        SUM(CAST(AWBWT AS DOUBLE)) as total_wt
    FROM 'data/atus_ipums.parquet'
    WHERE CAST(SCHAPPY AS INT) BETWEEN 0 AND 6
      AND ACTIVITY // 10000 = 4
    GROUP BY 1
""").df()
print(nonhh.to_string())

# =====================================================================
# CHART 1: Time on childcare by age of youngest child (25-54 only)
# Use person-level diary (WT06 weights, DURATION in minutes)
# =====================================================================
print("\n=== CHILDCARE TIME BY AGE OF YOUNGEST (25-54) ===")

# Use ALL activities as denominator, childcare-specific activities as numerator
# Childcare = activity codes 030100-030399 (HH children)
childcare_by_age = con.execute("""
    WITH diary AS (
        SELECT 
            CASEID,
            AGEYCHILD as kid_age,
            CAST(DURATION AS DOUBLE) as dur,
            CAST(WT06 AS DOUBLE) as wt,
            CASE WHEN ACTIVITY // 1000 BETWEEN 30 AND 33 THEN 1 ELSE 0 END as is_childcare,
            AGE
        FROM 'data/atus_ipums.parquet'
        WHERE AGE BETWEEN 25 AND 54
    ),
    person AS (
        SELECT 
            CASEID, kid_age, wt,
            SUM(CASE WHEN is_childcare = 1 THEN dur ELSE 0 END) as cc_min,
            SUM(dur) as total_min
        FROM diary
        GROUP BY CASEID, kid_age, wt
    )
    SELECT 
        kid_age,
        SUM(cc_min * wt) / SUM(wt) as min_per_day,
        COUNT(*) as n_people
    FROM person
    WHERE kid_age < 90
    GROUP BY kid_age
    ORDER BY kid_age
""").df()
print(childcare_by_age.to_string())

# CHART 1: Childcare minutes by age of youngest
fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

ages = childcare_by_age['kid_age'].values
mins = childcare_by_age['min_per_day'].values

ax.bar(ages, mins, color=GREEN, width=0.8, zorder=3)

ax.set_xlabel('Age of youngest child', fontsize=11, color=BLACK)
ax.set_ylabel('', fontsize=11)
ax.set_xticks(range(0, 18, 2))

# Y-axis: top label only gets "min"
yticks = ax.get_yticks()
ylabels = [f'{int(y)}' for y in yticks]
if len(ylabels) > 0:
    ylabels[-1] = f'{int(yticks[-1])} min'
ax.set_yticklabels(ylabels)

ax.tick_params(axis='y', length=0)
ax.tick_params(axis='x', length=4, color='#999')
ax.spines['left'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.grid(axis='y', alpha=0.3, color='#999', zorder=0)

ax.set_title('Time spent on childcare drops steeply with child age', 
             fontsize=14, fontweight='bold', color=BLACK, pad=30, loc='left')
ax.text(0, 1.02, 'Minutes per day, respondents aged 25-54', transform=ax.transAxes,
        fontsize=11, color='#888', style='italic')

# Source
ax.text(0, -0.08, 'Source: American Time Use Survey Well-Being Module (2010-2021)', 
        transform=ax.transAxes, fontsize=8, color='#999', style='italic')

plt.tight_layout()
plt.savefig('outputs/childcare_time_by_child_age.png', dpi=100, bbox_inches='tight', facecolor=BG)
plt.savefig('outputs/childcare_time_by_child_age.svg', bbox_inches='tight', facecolor=BG)
print("Saved childcare time chart")
plt.close()


# =====================================================================
# CHART 2: Overall happiness by age of youngest child (granular, 25-54)
# =====================================================================
print("\n=== OVERALL HAPPINESS BY AGE OF YOUNGEST (25-54) ===")
happy_by_age = con.execute("""
    SELECT 
        AGEYCHILD as kid_age,
        SUM(CAST(SCHAPPY AS DOUBLE) * CAST(AWBWT AS DOUBLE)) / SUM(CAST(AWBWT AS DOUBLE)) as mean_happy,
        COUNT(*) as n_activities,
        COUNT(DISTINCT CASEID) as n_people
    FROM 'data/atus_ipums.parquet'
    WHERE CAST(SCHAPPY AS INT) BETWEEN 0 AND 6
      AND AGE BETWEEN 25 AND 54
      AND AGEYCHILD < 90
    GROUP BY kid_age
    ORDER BY kid_age
""").df()
print(happy_by_age.to_string())

# Also get no-kids reference line
nokids = con.execute("""
    SELECT 
        SUM(CAST(SCHAPPY AS DOUBLE) * CAST(AWBWT AS DOUBLE)) / SUM(CAST(AWBWT AS DOUBLE)) as mean_happy
    FROM 'data/atus_ipums.parquet'
    WHERE CAST(SCHAPPY AS INT) BETWEEN 0 AND 6
      AND AGE BETWEEN 25 AND 54
      AND AGEYCHILD >= 98
""").df()
nokids_happy = nokids['mean_happy'].values[0]
print(f"\nNo-kids (25-54) happiness: {nokids_happy:.3f}")

fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

ages = happy_by_age['kid_age'].values
happy = happy_by_age['mean_happy'].values

# Color bars: green if above no-kids, light red if below
colors = [GREEN if h > nokids_happy else LIGHT_RED for h in happy]
ax.bar(ages, happy, color=colors, width=0.8, zorder=3)

# Reference line for no-kids
ax.axhline(y=nokids_happy, color=BLACK, linestyle='--', linewidth=1, alpha=0.7, zorder=4)
ax.text(17.5, nokids_happy + 0.02, f'No children: {nokids_happy:.2f}', 
        fontsize=9, color=BLACK, ha='right', va='bottom')

ax.set_xlabel('Age of youngest child', fontsize=11, color=BLACK)
ax.set_xticks(range(0, 18, 2))
ax.set_ylim(3.8, 4.7)

ax.tick_params(axis='y', length=0)
ax.tick_params(axis='x', length=4, color='#999')
ax.spines['left'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.grid(axis='y', alpha=0.3, color='#999', zorder=0)

ax.set_title('Parents of young children are happiest', 
             fontsize=14, fontweight='bold', color=BLACK, pad=30, loc='left')
ax.text(0, 1.02, 'Activity-weighted happiness (0-6 scale), respondents aged 25-54', 
        transform=ax.transAxes, fontsize=11, color='#888', style='italic')

ax.text(0, -0.08, 'Source: American Time Use Survey Well-Being Module (2010-2021)', 
        transform=ax.transAxes, fontsize=8, color='#999', style='italic')

plt.tight_layout()
plt.savefig('outputs/happiness_by_child_age_granular.png', dpi=100, bbox_inches='tight', facecolor=BG)
plt.savefig('outputs/happiness_by_child_age_granular.svg', bbox_inches='tight', facecolor=BG)
print("Saved granular happiness chart")
plt.close()
