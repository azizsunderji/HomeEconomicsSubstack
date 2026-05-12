"""
Midwest migration: 4 lines on one chart.
- Inflows (ACS state-to-state, interstate, excludes intra-Midwest)
- Outflows (ACS state-to-state, interstate, excludes intra-Midwest)
- Net domestic migration (PEP, all years through 2025)
- International migration (PEP, all years through 2025)

ACS data 2005-2024 (no 2020 — survey not run). PEP data 2010-2025.
"""
import matplotlib
matplotlib.use("svg")
import matplotlib.pyplot as plt
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["font.family"] = "Oracle"

import duckdb
import pandas as pd

PEP = "/Users/azizsunderji/Dropbox/Home Economics/Data/PopulationEstimates/state_pop_estimates_long.parquet"
STM = "/Users/azizsunderji/Dropbox/Home Economics/Data/State_Migration/state_to_state_migration_2005_2024.parquet"
OUT = "/Users/azizsunderji/Dropbox/Home Economics/2026_05_11_MidwestMigration/outputs"

# Brand palette
BLUE   = "#0BB4FF"
YELLOW = "#FEC439"
GREEN  = "#67A275"
RED    = "#F4743B"
BLACK  = "#3D3733"
CREAM  = "#DADFCE"
BG     = "#F6F7F3"

midwest = ['Illinois','Indiana','Iowa','Kansas','Michigan','Minnesota','Missouri',
           'Nebraska','North Dakota','Ohio','South Dakota','Wisconsin']
m_in = ",".join(repr(s) for s in midwest)

con = duckdb.connect()

# ACS interstate flows (excludes intra-Midwest)
acs = con.execute(f"""
SELECT year::INT AS year,
       SUM(CASE WHEN destination IN ({m_in}) AND origin NOT IN ({m_in}) THEN flow END) AS inflow,
       SUM(CASE WHEN origin IN ({m_in}) AND destination NOT IN ({m_in}) THEN flow END) AS outflow
FROM '{STM}'
GROUP BY year ORDER BY year
""").fetchdf()

# PEP domestic + international, latest vintage per (year, measure)
pep_raw = con.execute(f"""
SELECT year::INT AS year, measure, value, vintage
FROM '{PEP}'
WHERE NAME = 'Midwest Region' AND measure IN ('domestic_migration','international_migration')
""").fetchdf()
pep_raw = pep_raw.sort_values(['year','measure','vintage']).drop_duplicates(['year','measure'], keep='last')
pep = pep_raw.pivot(index='year', columns='measure', values='value').reset_index()

# Merge
df = pd.merge(acs[['year','inflow','outflow']],
              pep[['year','domestic_migration','international_migration']],
              on='year', how='outer').sort_values('year').reset_index(drop=True)
df = df[df['year'] >= 2005]

# Convert to thousands
for c in ['inflow','outflow','domestic_migration','international_migration']:
    df[c] = df[c] / 1000.0

print(df.to_string(index=False))

# Plot
fig, ax = plt.subplots(figsize=(11, 6.5))
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

# Helper to plot a series with NaN gaps (so 2020 doesn't draw a line through)
def plot_series(ax, df, col, color, label, lw=2.5, marker='o'):
    sub = df[['year', col]].dropna()
    # Break the line at gaps > 1 year (to leave 2020 visually open)
    yrs = sub['year'].values
    vals = sub[col].values
    segs_x, segs_y = [[]], [[]]
    for i, y in enumerate(yrs):
        if i > 0 and y - yrs[i-1] > 1:
            segs_x.append([])
            segs_y.append([])
        segs_x[-1].append(y)
        segs_y[-1].append(vals[i])
    for i, (sx, sy) in enumerate(zip(segs_x, segs_y)):
        ax.plot(sx, sy, color=color, linewidth=lw,
                marker=marker, markersize=4,
                label=label if i == 0 else None)

plot_series(ax, df, 'outflow',                 RED,    'Outflow (interstate)')
plot_series(ax, df, 'inflow',                  GREEN,  'Inflow (interstate)')
plot_series(ax, df, 'international_migration', BLUE,   'International migration')
plot_series(ax, df, 'domestic_migration',      BLACK,  'Net domestic migration')

# Zero reference line
ax.axhline(0, color=BLACK, linewidth=0.6, alpha=0.4)

# Style
for sp in ax.spines.values():
    sp.set_visible(False)
ax.tick_params(colors=BLACK, length=0, labelsize=10)
ax.grid(axis='y', color='white', linewidth=1.0, alpha=0.9)
ax.set_axisbelow(True)
ax.set_xticks([2005, 2010, 2015, 2020, 2025])
ax.set_xlim(2004.6, 2025.6)
ax.set_ylabel('Thousands per year', fontsize=10, color=BLACK)

# Inline labels at the right end of each line
def end_label(df, col, color, text, dy=0):
    sub = df[['year', col]].dropna()
    if len(sub) == 0:
        return
    last_year = sub['year'].iloc[-1]
    last_val = sub[col].iloc[-1]
    ax.text(last_year + 0.3, last_val + dy, text,
            fontsize=10, color=color, va='center', ha='left',
            weight='medium')

end_label(df, 'outflow',                 RED,   'Outflow')
end_label(df, 'inflow',                  GREEN, 'Inflow')
end_label(df, 'international_migration', BLUE,  'Intl. migration')
end_label(df, 'domestic_migration',      BLACK, 'Net domestic')

# Title block
fig.text(0.06, 0.965, "The Midwest's migration, by component",
         fontsize=18, color=BLACK, ha='left', weight='bold')
fig.text(0.06, 0.925,
         "Annual flows in thousands. Interstate inflow/outflow exclude intra-Midwest moves.",
         fontsize=11, color=BLACK, ha='left', style='italic')
fig.text(0.06, 0.03,
         "Source: ACS state-to-state migration (interstate inflow/outflow, 2005–2024; 2020 not surveyed). "
         "Census PEP latest vintage (net domestic + international migration, 2010–2025).",
         fontsize=8, color=BLACK, ha='left')

plt.subplots_adjust(left=0.07, right=0.88, top=0.85, bottom=0.10)

fname = f"{OUT}/midwest_4series_migration"
fig.savefig(fname + ".svg", facecolor=BG, bbox_inches='tight')
fig.savefig(fname + ".png", facecolor=BG, dpi=170, bbox_inches='tight')
plt.close(fig)

# Save data alongside
df.to_csv(f"{OUT}/midwest_4series_migration.csv", index=False)

print(f"\nSaved {fname}.svg / .png")
print(f"Saved {OUT}/midwest_4series_migration.csv")
