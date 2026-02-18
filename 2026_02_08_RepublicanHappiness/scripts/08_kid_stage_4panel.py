import duckdb
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

# Kid stage categories (25-54 only)
# AGEYCHILD: 0-17 = age of youngest child, 999 = no children
stage_data = con.execute("""
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

# 4-panel chart
fig, axes = plt.subplots(2, 2, figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG)

stages = stage_data['stage'].values
n_stages = len(stages)

metrics = [
    ('mean_happy', 'Happiness', (3.5, 5.0)),
    ('mean_meaning', 'Meaning', (3.5, 5.0)),
    ('mean_stress', 'Stress', (0.5, 2.5)),
    ('mean_tired', 'Tiredness', (1.0, 3.0)),
]

for idx, (col, title, ylim) in enumerate(metrics):
    ax = axes[idx // 2][idx % 2]
    ax.set_facecolor(BG)
    
    vals = stage_data[col].values
    
    # Color: green for parents, blue for no-kids
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
    
    # Add value labels on bars
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
plt.savefig('outputs/happiness_by_kid_stage.svg', bbox_inches='tight', facecolor=BG)
print("Saved kid stage 4-panel chart")
plt.close()
