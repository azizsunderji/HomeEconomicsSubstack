import duckdb
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd

# Register Oracle font
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'

# Query the data
con = duckdb.connect()
df = con.execute('''
    SELECT
        YEAR as year,
        SUM(PERWT) as canadians_arrived
    FROM "/Users/azizsunderji/Dropbox/Home Economics/Data/ACS_1Y/acs_1y.parquet"
    WHERE BPL = 150
      AND YRIMMIG = YEAR
    GROUP BY YEAR
    ORDER BY YEAR
''').df()

# Save data
df.to_csv("/Users/azizsunderji/Dropbox/Home Economics/Explorations/2026_01_27_ComponentsofPopChange/data/canadian_immigration_annual.csv", index=False)

# Create chart
fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor('#F6F7F3')
ax.set_facecolor('#F6F7F3')

# Plot line
ax.plot(df['year'], df['canadians_arrived'] / 1000,
        color='#0BB4FF', linewidth=2.5, marker='o', markersize=6)

# Styling
ax.set_xlabel('')
ax.set_ylabel('')
ax.set_title('Canadians Moving to the US', fontsize=18, fontweight='bold',
             color='#3D3733', pad=20)

# Y-axis formatting
ax.set_ylim(0, df['canadians_arrived'].max() / 1000 * 1.1)
yticks = ax.get_yticks()
ax.set_yticklabels([f'{int(y)}k' if i == len(yticks)-1 else f'{int(y)}'
                    for i, y in enumerate(yticks)], color='#3D3733')

# X-axis
ax.set_xticks(df['year'])
ax.set_xticklabels(df['year'].astype(int), rotation=45, ha='right', color='#3D3733')

# Grid and spines
ax.yaxis.grid(True, color='#DADFCE', linewidth=0.8)
ax.xaxis.grid(False)
ax.set_axisbelow(True)

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.spines['bottom'].set_color('#3D3733')

# Remove y-axis tick marks
ax.tick_params(axis='y', length=0)
ax.tick_params(axis='x', colors='#3D3733')

# Source
ax.text(0.0, -0.12, 'Source: American Community Survey 1-Year (IPUMS)',
        transform=ax.transAxes, fontsize=9, color='#888888', style='italic')

# Note about 2020
ax.annotate('No 2020\nsurvey', xy=(2020, 0), xytext=(2020, 15),
            fontsize=8, color='#888888', ha='center',
            arrowprops=dict(arrowstyle='-', color='#888888', lw=0.5))

plt.tight_layout()
plt.savefig("/Users/azizsunderji/Dropbox/Home Economics/Explorations/2026_01_27_ComponentsofPopChange/outputs/canadian_immigration_annual.png",
            facecolor='#F6F7F3', bbox_inches='tight')
plt.savefig("/Users/azizsunderji/Dropbox/Home Economics/Explorations/2026_01_27_ComponentsofPopChange/outputs/canadian_immigration_annual.svg",
            facecolor='#F6F7F3', bbox_inches='tight')
print("Chart saved!")
print(df.to_string())
