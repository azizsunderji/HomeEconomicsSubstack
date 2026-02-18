"""
ATUS Work Time - Year by Year Time Series
"""

import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# Register Oracle font
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'

# Colors
BLUE = '#0BB4FF'
BLACK = '#3D3733'
BG_CREAM = '#F6F7F3'

con = duckdb.connect()

# Get work time by year with sample sizes
df = con.execute("""
    WITH person_day AS (
        SELECT DISTINCT
            CASEID,
            YEAR,
            BLS_WORK as work,
            WT06 as weight
        FROM '/Users/azizsunderji/Dropbox/Home Economics/Data/atus_ipums.parquet'
        WHERE PRESENCE = 1
    )
    SELECT
        YEAR,
        count(*) as n,
        round(sum(work * weight) / sum(weight), 1) as work_min
    FROM person_day
    GROUP BY YEAR
    ORDER BY YEAR
""").df()

# Print the data
print("WORK TIME BY YEAR (minutes per day, all respondents)")
print("=" * 50)
print(df.to_string(index=False))
print()
print(f"Sample sizes range from {df['n'].min():,} to {df['n'].max():,}")
print(f"Work time ranges from {df['work_min'].min():.0f} to {df['work_min'].max():.0f} min")

# Create time series chart
fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG_CREAM)
ax.set_facecolor(BG_CREAM)

# Plot line
ax.plot(df['YEAR'], df['work_min'], color=BLUE, linewidth=2.5, marker='o', markersize=6)

# Styling
ax.set_xlim(2002.5, 2024.5)
ax.set_ylim(195, 235)

# Add gridlines
ax.yaxis.grid(True, color='white', linewidth=1.5)
ax.set_axisbelow(True)

# Remove spines except bottom
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.spines['bottom'].set_color(BLACK)

# Tick styling
ax.tick_params(axis='y', length=0)
ax.tick_params(axis='x', colors=BLACK)

# Labels
ax.set_xlabel('')
ax.set_ylabel('')

# Y-axis labels - only top one has units
yticks = [200, 210, 220, 230]
ax.set_yticks(yticks)
yticklabels = ['200', '210', '220', '230 min']
ax.set_yticklabels(yticklabels, fontsize=11, color=BLACK)

# X-axis
ax.set_xticks([2003, 2006, 2009, 2012, 2015, 2018, 2021, 2024])

# Title and subtitle
ax.text(0.0, 1.12, 'Americans Are Working Less', transform=ax.transAxes,
        fontsize=20, fontweight='bold', color=BLACK)
ax.text(0.0, 1.06, 'Average minutes of work per day, all Americans 15+',
        transform=ax.transAxes, fontsize=12, color=BLACK)

# Annotate key points
ax.annotate('2009\nRecession', xy=(2009, 212), xytext=(2009, 200),
            fontsize=9, color=BLACK, ha='center',
            arrowprops=dict(arrowstyle='->', color=BLACK, lw=0.8))

ax.annotate('COVID\n2020', xy=(2020, 210), xytext=(2020, 198),
            fontsize=9, color=BLACK, ha='center',
            arrowprops=dict(arrowstyle='->', color=BLACK, lw=0.8))

# Note about 2020 missing
ax.text(2020, 210, '?', fontsize=14, color=BLUE, ha='center', va='center', fontweight='bold')

# Source
ax.text(0.0, -0.08, 'Source: American Time Use Survey (IPUMS)', transform=ax.transAxes,
        fontsize=9, color='gray', style='italic')

plt.tight_layout()
plt.savefig('/Users/azizsunderji/Dropbox/Home Economics/Explorations/outputs/work_time_series.png',
            dpi=150, bbox_inches='tight', facecolor=BG_CREAM)
plt.savefig('/Users/azizsunderji/Dropbox/Home Economics/Explorations/outputs/work_time_series.svg',
            bbox_inches='tight', facecolor=BG_CREAM)
print("\nSaved to outputs/work_time_series.png")
