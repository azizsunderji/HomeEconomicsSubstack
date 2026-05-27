"""
Render 12 thumbnail maps of NYC MSA under-18 change 2020-2024, each using
a different diverging palette (green = growth, orange/red = decline).

Output: outputs/nyc_pct_change_palette_picker.html

Palette references — Economist/WSJ/Bloomberg/FT idioms:
- Earth-tone muted (Economist)
- Heritage forest + brick (WSJ)
- Vivid teal + amber (Bloomberg)
- Coral + pine (FT)
- Modern green + persimmon (NYT)
"""
import json
from pathlib import Path

import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
GEO = DATA / "geo"
OUT = PROJECT / "outputs"

BOROUGHS = {"36005", "36047", "36061", "36081", "36085"}

# ---- Load data ----
df = pd.read_csv(DATA / "nyc_county_under18_pep_seamless.csv", dtype={"county_fips": str})
pivot = df[df['year'].isin([2020, 2024])].pivot_table(
    values='under18', index='county_fips', columns='year').reset_index()
pivot['pct'] = (pivot[2024] / pivot[2020] - 1) * 100
pct_by_fips = dict(zip(pivot['county_fips'], pivot['pct']))

# ---- Load geojson (will let D3 project in browser) ----
with open(GEO / "metro10_counties.geojson") as f:
    g = json.load(f)
nyc_features = [f for f in g['features'] if f['properties'].get('cbsa_code') == 35620]
geo = {"type": "FeatureCollection", "features": nyc_features}

# ---- Palettes: 5-step diverging (strongest neg → mid → strongest pos) ----
# Mid is the SAME cream across all (#F6F2EA-ish) — diverging requires neutral mid.
# Index 0 = strongest decline. Index 4 = strongest growth.
PALETTES = [
    # 12 diverging palettes across the FULL HUE SPECTRUM. Negative (decline)
    # and positive (growth) ends pair very different hues. Cream midpoint
    # held constant so palette is the only visual variable.
    {
        "name": "1. RED + BLUE (Economist classic)",
        "note": "The iconic Economist diverging. Pure red decline, pure blue growth.",
        "colors": ["#D03A2E", "#F0A39A", "#F4F0E7", "#7BA7C6", "#1E5A8C"],
    },
    {
        "name": "2. RED + GREEN (WSJ finance)",
        "note": "Classic markets up/down. Red decline, deep green growth.",
        "colors": ["#C8102E", "#EE9CA7", "#F4F0E7", "#6FB07F", "#1E6F3A"],
    },
    {
        "name": "3. ORANGE + NAVY (Bloomberg ETF)",
        "note": "Bloomberg signature. Bright orange decline, deep navy growth.",
        "colors": ["#E55934", "#F8B091", "#F4F0E7", "#6A8FB8", "#0F3D6E"],
    },
    {
        "name": "4. ORANGE + TEAL (Bloomberg modern)",
        "note": "High-energy modern Bloomberg. Bright orange + bright teal.",
        "colors": ["#E55934", "#F8B091", "#F4F0E7", "#3FA8B5", "#0E5E70"],
    },
    {
        "name": "5. PINK + TEAL (FT signature)",
        "note": "FT pink decline + teal growth. Distinctive, editorial.",
        "colors": ["#D9405A", "#F0A0B0", "#F4F0E7", "#5BB0AA", "#1F6E70"],
    },
    {
        "name": "6. RUST + STEEL BLUE (heritage)",
        "note": "Heritage rust decline + cool steel blue growth. Muted, sober.",
        "colors": ["#A0531D", "#D2A382", "#F4F0E7", "#7895AB", "#34556E"],
    },
    {
        "name": "7. CRIMSON + SKY BLUE",
        "note": "Punchy editorial. Crimson decline, bright sky-blue growth.",
        "colors": ["#9D1B27", "#E48993", "#F4F0E7", "#7BC2E0", "#1E7DAB"],
    },
    {
        "name": "8. MAGENTA + EMERALD (vivid modern)",
        "note": "Bold data-viz. Magenta decline, emerald growth. Max contrast.",
        "colors": ["#C3286B", "#EA92B5", "#F4F0E7", "#5EBE8C", "#0F7048"],
    },
    {
        "name": "9. PURPLE + MUSTARD",
        "note": "Unconventional. Deep purple decline + mustard yellow growth.",
        "colors": ["#5E2A6E", "#A485B5", "#F4F0E7", "#D9B038", "#8F6F1A"],
    },
    {
        "name": "10. BROWN + TEAL (NYT data desk)",
        "note": "NYT-style brown decline + teal growth. Editorial, sober.",
        "colors": ["#7A4A2B", "#C49977", "#F4F0E7", "#5FAEAA", "#1F5F6A"],
    },
    {
        "name": "11. CORAL + INDIGO",
        "note": "Mid-century clean. Warm coral decline + deep indigo growth.",
        "colors": ["#FF6B6B", "#FFB3B3", "#F4F0E7", "#7E89C7", "#2A3680"],
    },
    {
        "name": "12. YELLOW + PURPLE (BIV extremes)",
        "note": "Maximum hue separation. Yellow-amber decline + violet growth.",
        "colors": ["#D9A028", "#EBCB80", "#F4F0E7", "#A88BC9", "#5C3D80"],
    },
]

# Diverging breaks (same for all palettes for fair comparison)
# Range: -9.5% to +7.1%. Want symmetric-ish breaks around 0.
BREAKS = [-9.5, -5, -1, 1, 4, 7.1]  # 5 bins: <-5, -5..-1, -1..1, 1..4, >4

P = {
    "geo": geo,
    "pct": pct_by_fips,
    "boroughs": list(BOROUGHS),
    "palettes": PALETTES,
    "breaks": BREAKS,
}

HTML = r"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>NYC under-18 2020→2024 — palette picker</title>
<style>
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Light.otf') format('opentype'); font-weight:300; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Regular.otf') format('opentype'); font-weight:400; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Bold.otf') format('opentype'); font-weight:700; }
body { margin:0; padding:24px; background:#F6F7F3; font-family:'ABC Oracle Edu',sans-serif; color:#3D3733; }
h1 { font-size:24px; font-weight:700; margin:0 0 4px; }
.sub { color:#7F7570; font-size:14px; margin-bottom:18px; max-width:1200px; line-height:1.5; }
.grid { display:grid; grid-template-columns:repeat(4, 1fr); gap:18px 18px; max-width:1400px; }
.card { background:#fff; border:0.5px solid #e1e2e3; padding:12px 14px 14px; }
.card .pname { font-size:13px; font-weight:700; margin-bottom:2px; line-height:1.25; }
.card .pnote { font-size:11px; color:#7F7570; margin-bottom:8px; line-height:1.35; min-height:30px; }
.swatches { display:flex; height:14px; margin-top:8px; border:0.5px solid #DADFCE; }
.swatches .sw { flex:1; }
.swatch-row { display:flex; gap:4px; font-size:9.5px; color:#7F7570; margin-top:4px; font-variant-numeric:tabular-nums; }
.swatch-row .lbl { flex:1; text-align:center; }
.minimap { width:100%; aspect-ratio: 5 / 4; display:block; }
</style></head>
<body>
<h1>Pick a diverging palette — NYC MSA under-18, 2020 → 2024</h1>
<div class="sub">12 candidates, each rendered on the same map (22 NYC MSA counties). All use identical 5-step diverging breaks: <strong>&lt;−5%</strong> · <strong>−5 to −1%</strong> · <strong>−1 to +1%</strong> · <strong>+1 to +4%</strong> · <strong>&gt;+4%</strong>. Green ramp = growth; orange/rust ramp = decline. Hover a county to see its name and value.</div>

<div class="grid" id="grid"></div>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const P = __DATA__;
const grid = d3.select('#grid');

const W = 280, H = 224;
const proj = d3.geoMercator().fitExtent([[6,6],[W-6,H-6]], P.geo);
const path = d3.geoPath(proj);

function colorFor(pct, colors) {
  if (pct == null) return '#eee';
  const b = P.breaks;
  for (let i = 0; i < 5; i++) {
    if (pct <= b[i+1]) return colors[i];
  }
  return colors[colors.length - 1];
}

P.palettes.forEach((p, idx) => {
  const card = grid.append('div').attr('class','card');
  card.append('div').attr('class','pname').text(p.name);
  card.append('div').attr('class','pnote').text(p.note);

  const svg = card.append('svg').attr('class','minimap')
    .attr('viewBox', `0 0 ${W} ${H}`)
    .style('background','#F8F9F5');

  // Counties
  svg.append('g').selectAll('path').data(P.geo.features).join('path')
    .attr('d', path)
    .attr('fill', d => colorFor(P.pct[d.properties.county_fips], p.colors))
    .attr('stroke', '#F6F7F3').attr('stroke-width', 0.6)
    .append('title')
    .text(d => `${d.properties.NAME}: ${P.pct[d.properties.county_fips]?.toFixed(1)}%`);

  // Swatch strip
  const sw = card.append('div').attr('class','swatches');
  p.colors.forEach(c => sw.append('div').attr('class','sw').style('background', c));

  const row = card.append('div').attr('class','swatch-row');
  ['<−5%','−5 to −1','−1 to 1','1 to 4','>+4%'].forEach(l => row.append('div').attr('class','lbl').text(l));
});
</script>
</body></html>
"""

html = HTML.replace("__DATA__", json.dumps(P))
out = OUT / "nyc_pct_change_palette_picker.html"
out.write_text(html)
print(f"Wrote {out}")
