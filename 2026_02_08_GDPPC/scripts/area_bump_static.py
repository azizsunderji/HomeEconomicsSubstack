"""
Static area bump chart: US States vs World Economies, 1997-2024.
Band width proportional to sqrt(GDP), ordered by rank.
Grouped by region: Americas (red), Asia (yellow), Europe (green).
"""
import json
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os

# --- Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "outputs")
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"

# --- Font setup ---
for f in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(os.path.join(FONT_DIR, f))
plt.rcParams['font.family'] = 'ABC Oracle Edu'
plt.rcParams['svg.fonttype'] = 'none'  # Editable text in SVG

# --- Load data ---
with open(os.path.join(DATA_DIR, "states_vs_world_gdp.json")) as f:
    entities = json.load(f)

# --- Color palette: grouped by region using brand color families ---
# Americas = Red family (#F4743B / #FBCAB5)
# Asia = Yellow family (#FEC439)
# Europe = Green family (#67A275 / #C6DCCB)
COLORS = {
    # Americas (Blue) — subtle gradations
    "California":     "#0BB4FF",  # Full blue (hero)
    "Texas":          "#2FC0FF",  # Slightly lighter
    "United States":  "#50CCFF",  # A touch lighter
    # Asia (Red) — subtle gradations
    "China":          "#F4743B",  # Full red
    "Japan":          "#F68858",  # Slightly lighter
    "India":          "#F89C74",  # A touch lighter
    # Europe (Green) — subtle gradations
    "Germany":        "#67A275",  # Full green
    "United Kingdom": "#74AC82",  # Slightly lighter
    "France":         "#81B68F",  # A touch lighter
    "Italy":          "#8EC09C",  # A shade lighter
}
STATES = {"California", "Texas"}

# --- Build data lookup (start from 2003) ---
years = [p["year"] for p in entities[0]["points"] if p["year"] >= 2003]
lookup = {e["name"]: {p["year"]: p for p in e["points"] if p["year"] >= 2003} for e in entities}

# --- Compute stacked layout (sqrt scaling) ---
GAP = 0.004
layout = {e["name"]: {"y0": [], "y1": [], "vals": [], "ranks": []} for e in entities}

for year in years:
    yd = sorted(
        [{"name": e["name"], "rank": lookup[e["name"]][year]["rank"],
          "value": lookup[e["name"]][year]["value"]} for e in entities],
        key=lambda d: d["rank"]
    )
    sv = [np.sqrt(d["value"]) for d in yd]
    ts = sum(sv)
    avail = 1.0 - GAP * (len(yd) - 1)

    cy = 0.0
    for i, d in enumerate(yd):
        h = (sv[i] / ts) * avail
        layout[d["name"]]["y0"].append(cy)
        layout[d["name"]]["y1"].append(cy + h)
        layout[d["name"]]["vals"].append(d["value"])
        layout[d["name"]]["ranks"].append(d["rank"])
        cy += h + GAP

# --- Bump-X interpolation (cubic Bezier S-curves) ---
def bump(xp, yp, n=30):
    xs, ys = [], []
    for i in range(len(xp) - 1):
        x0, x1 = xp[i], xp[i + 1]
        y0, y1 = yp[i], yp[i + 1]
        mx = (x0 + x1) / 2
        for j in range(n):
            t = j / n
            xs.append((1-t)**3*x0 + 3*(1-t)**2*t*mx + 3*(1-t)*t**2*mx + t**3*x1)
            ys.append((1-t)**3*y0 + 3*(1-t)**2*t*y0 + 3*(1-t)*t**2*y1 + t**3*y1)
    xs.append(xp[-1])
    ys.append(yp[-1])
    return np.array(xs), np.array(ys)

# --- Plot ---
fig, ax = plt.subplots(figsize=(9, 7.5))
fig.patch.set_facecolor('#F6F7F3')
ax.set_facecolor('#F6F7F3')
fig.subplots_adjust(left=0.165, right=0.815, top=0.88, bottom=0.08)

# Draw order: countries first, then states, California last
order = sorted(entities, key=lambda e: (
    0 if e["name"] not in STATES else 1,
    1 if e["name"] == "California" else 0
))

for e in order:
    name = e["name"]
    L = layout[name]
    xi, y0i = bump(years, L["y0"])
    _, y1i = bump(years, L["y1"])

    is_state = name in STATES
    alpha = 0.90 if name == "California" else 0.82 if is_state else 0.72
    zorder = 10 if name == "California" else 9 if is_state else 5

    ax.fill_between(xi, y0i, y1i,
                    facecolor=COLORS[name], alpha=alpha,
                    edgecolor='white', linewidth=0.3,
                    zorder=zorder)

# Axes
ax.set_xlim(2003, 2024)
ax.set_ylim(1.01, -0.01)  # Inverted: y=0 at top
ax.set_axis_off()

# Year labels along bottom
for yr in [2003, 2005, 2010, 2015, 2020, 2024]:
    ax.text(yr, 1.03, str(yr), ha='center', va='top',
            fontsize=10, color='#3D3733', alpha=0.5, clip_on=False)

# --- Label collision avoidance ---
def avoid(labels, spacing=0.026):
    labels.sort(key=lambda l: l['y'])
    labels[0]['ay'] = labels[0]['y']
    for i in range(1, len(labels)):
        labels[i]['ay'] = max(labels[i]['y'], labels[i - 1]['ay'] + spacing)
    return labels

# Label color: use darker version of fill for readability
LABEL_COLORS = {
    "California":     "#0890CC",
    "Texas":          "#1A9AD5",
    "United States":  "#2AA4DD",
    "China":          "#D0582A",
    "Japan":          "#D06838",
    "India":          "#D07848",
    "Germany":        "#4A7A55",
    "United Kingdom": "#528260",
    "France":         "#5A8A6A",
    "Italy":          "#629274",
}

# Left labels (2003 positions, with rank)
ll = [{"name": e["name"],
       "y": (layout[e["name"]]["y0"][0] + layout[e["name"]]["y1"][0]) / 2,
       "rank": layout[e["name"]]["ranks"][0]}
      for e in entities]
ll = avoid(ll)
for l in ll:
    s = l["name"] in STATES
    ax.text(2002.4, l['ay'], f"#{l['rank']}  {l['name']}", ha='right', va='center',
            fontsize=9, fontweight='bold' if s else 'normal',
            color=LABEL_COLORS[l['name']], clip_on=False)

# Right labels (2024 positions, with rank and GDP value)
rl = [{"name": e["name"],
       "y": (layout[e["name"]]["y0"][-1] + layout[e["name"]]["y1"][-1]) / 2,
       "val": layout[e["name"]]["vals"][-1],
       "rank": layout[e["name"]]["ranks"][-1]}
      for e in entities]
rl = avoid(rl)
for l in rl:
    s = l["name"] in STATES
    v = l["val"]
    vs = f"${v / 1000:.1f}T" if v >= 1000 else f"${v:.0f}B"
    ax.text(2024.6, l['ay'], f"#{l['rank']}  {l['name']}  {vs}", ha='left', va='center',
            fontsize=9, fontweight='bold' if s else 'normal',
            color=LABEL_COLORS[l['name']], clip_on=False)

# --- Title & subtitle ---
fig.text(0.165, 0.955, "US States vs. World Economies",
         fontsize=20, fontweight='bold', color='#3D3733')
fig.text(0.165, 0.92, "GDP by size, current USD, 2003\u20132024",
         fontsize=12, color='#3D3733', alpha=0.6)

# --- Source ---
fig.text(0.165, 0.025,
         "Source: BEA (state GDP), World Bank (country GDP). "
         "Band height proportional to GDP.",
         fontsize=8, color='#3D3733', alpha=0.45, style='italic')

# --- Save SVG and PNG ---
out_svg = os.path.join(OUTPUT_DIR, "states_vs_world_gdp_area_bump.svg")
fig.savefig(out_svg, format='svg', facecolor='#F6F7F3')
print(f"Saved SVG: {out_svg}")

out_png = os.path.join(OUTPUT_DIR, "states_vs_world_gdp_area_bump.png")
fig.savefig(out_png, dpi=150, facecolor='#F6F7F3')
print(f"Saved PNG: {out_png}")

plt.close()
