"""
Voronoi treemap of WHYMOVE reasons. Hierarchical layout — cells of the same
parent category cluster together. Brand palette: each category gets a hue,
sub-cells get shades within that hue.

NY → NJ/CT/PA family-with-kids movers, CPS ASEC 1999-2025.
"""
from __future__ import annotations
import json
from pathlib import Path
import duckdb

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
OUTPUTS = PROJECT / "outputs"
F = "/Users/azizsunderji/Dropbox/Home Economics/Data/CPS_ASEC/cps_asec_full.parquet"

WHYMOVE_LABELS = {
    1:  "Marital status change",      2: "Establish own household",   3: "Other family reason",
    4:  "New job / transfer",          5: "Lost job / looking",         6: "Easier commute",
    7:  "Retired",                     8: "Other job-related",          9: "Wanted to own",
    10: "Better housing",             11: "Better neighborhood",       12: "Cheaper housing",
    13: "Other housing",              14: "College",                   15: "Climate",
    16: "Health",                     17: "Natural disaster",          18: "Foreclosure / eviction",
    19: "Other reason",               20: "Other family reason",
}
CATEGORIES = {
    "Employment": [4, 5, 8],
    "Housing":    [6, 9, 10, 11, 12, 13],
    "Family":     [1, 2, 3, 20],
    "Retirement": [7],
    "Education":  [14],
    "Other":      [15, 16, 17, 18, 19],
}
CODE_TO_CAT = {c: cat for cat, codes in CATEGORIES.items() for c in codes}

# All-blue palette. Housing = the most vivid brand blue (it's the chart's topic).
# Other categories are subtle shades of the same blue family — all cells within
# a category share the SAME color. Within-category boundaries come from BG-stroke.
CATEGORY_COLOR = {
    "Housing":    "#0BB4FF",  # brand vivid (headline)
    "Employment": "#0099E0",  # between brand vivid and the cap
    "Family":     "#7DD4FF",  # pale
    "Retirement": "#4FC4FF",  # mid-light, distinct from Family
    "Education":  "#BCE8FF",  # palest
    "Other":      "#0077CC",  # cap — darkest allowed
}

BG     = "#F6F7F3"   # brand cream background
TEXT   = "#3D3733"
DARK_LABEL  = "#3D3733"
LIGHT_LABEL = "#F6F7F3"


def label_color(hex_fill: str) -> str:
    """Pick dark or light text based on fill luminance."""
    h = hex_fill.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    L = (0.299 * r + 0.587 * g + 0.114 * b)
    return DARK_LABEL if L > 160 else LIGHT_LABEL


def main():
    df = duckdb.query(f"""
        SELECT WHYMOVE, ASECWT FROM '{F}'
        WHERE MIGSTA1=36 AND STATEFIP IN (34,9,42)
          AND MIGRATE1=5 AND NCHILD>0 AND WHYMOVE BETWEEN 1 AND 20
    """).df()
    # Codes 3 and 20 are both "Other family reason" (IPUMS expanded the code
    # in later years). Merge them.
    df.loc[df["WHYMOVE"] == 20, "WHYMOVE"] = 3
    agg = df.groupby("WHYMOVE")["ASECWT"].sum().sort_values(ascending=False)
    total = float(agg.sum())
    n_records = len(df)

    # Build hierarchical structure: root → categories → codes.
    # All cells within a category share ONE color (subtle shade of blue).
    children = []
    for cat, codes in CATEGORIES.items():
        cat_cells = []
        cat_color = CATEGORY_COLOR[cat]
        for code in codes:
            w = float(agg.get(code, 0))
            if w <= 0:
                continue
            cat_cells.append({
                "code": code,
                "label": WHYMOVE_LABELS[code],
                "category": cat,
                "weight": w,
                "pct": w / total * 100,
                "color": cat_color,
            })
        cat_cells.sort(key=lambda x: -x["weight"])
        cat_weight = sum(c["weight"] for c in cat_cells)
        if cat_weight > 0:
            children.append({
                "name": cat,
                "weight": cat_weight,
                "pct_total": cat_weight / total * 100,
                "children": cat_cells,
            })

    hierarchy_data = {"name": "root", "children": children}
    payload = json.dumps({"hierarchy": hierarchy_data, "n_records": n_records, "total": int(total)})

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Why NY families with kids leave</title>
<style>
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Regular.otf') format('opentype'); font-weight:400; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Medium.otf') format('opentype'); font-weight:500; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Bold.otf') format('opentype'); font-weight:700; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Light.otf') format('opentype'); font-weight:300; }}
body {{ margin:0; background:#fff; font-family:'ABC Oracle Edu',sans-serif; }}
svg {{ display:block; margin:20px auto; }}
</style></head><body>
<svg id="chart" viewBox="0 0 1200 1100" xmlns="http://www.w3.org/2000/svg"></svg>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script src="https://unpkg.com/d3-weighted-voronoi@1"></script>
<script src="https://unpkg.com/d3-voronoi-map@2"></script>
<script src="https://unpkg.com/d3-voronoi-treemap@1"></script>
<script>
const P = {payload};
const BG = {json.dumps(BG)};
const TEXT = {json.dumps(TEXT)};
const W = 1200, H = 1100;
const PAD = 40;

const svg = d3.select('#chart');
svg.append('rect').attr('width', W).attr('height', H).attr('fill', BG);

svg.append('text').attr('x', PAD).attr('y', PAD + 32)
  .attr('font-family','ABC Oracle Edu').attr('font-size',30).attr('font-weight',700).attr('fill',TEXT)
  .text('Why NYC-area families with kids are leaving');
svg.append('text').attr('x', PAD).attr('y', PAD + 32 + 28)
  .attr('font-family','ABC Oracle Edu').attr('font-size',17).attr('font-weight',400).attr('fill',TEXT)
  .text('Stated reasons for families moving from NY state to NJ, CT, or PA — 63% originate in the 5 boroughs, another 21% in NY-state NYC suburbs.');

// Container — circular polygon (60 sides ≈ smooth circle)
const cx = W / 2, cy = H / 2 + 30, R = 380, N = 60;
const clipPoly = [];
for (let i = 0; i < N; i++) {{
  const a = (i / N) * 2 * Math.PI - Math.PI / 2;
  clipPoly.push([cx + R * Math.cos(a), cy + R * Math.sin(a)]);
}}

// Build hierarchy. d3-voronoi-treemap will lay out cat-level regions first, then sub-cells.
const root = d3.hierarchy(P.hierarchy).sum(d => d.weight);
const vt = d3.voronoiTreemap()
  .clip(clipPoly)
  .convergenceRatio(0.001)
  .maxIterationCount(400)
  .minWeightRatio(0.005);
vt(root);

// Polygon helpers
function centroid(pts) {{
  let cxx=0, cyy=0, A=0;
  for (let i=0; i<pts.length; i++) {{
    const [x0,y0]=pts[i], [x1,y1]=pts[(i+1)%pts.length];
    const cross = x0*y1 - x1*y0;
    A += cross; cxx += (x0+x1)*cross; cyy += (y0+y1)*cross;
  }}
  A *= 0.5;
  return [cxx/(6*A), cyy/(6*A)];
}}
function bbox(pts) {{
  let xmin=Infinity, ymin=Infinity, xmax=-Infinity, ymax=-Infinity;
  pts.forEach(([x,y]) => {{ if (x<xmin) xmin=x; if (x>xmax) xmax=x; if (y<ymin) ymin=y; if (y>ymax) ymax=y; }});
  return {{xmin, ymin, xmax, ymax, w: xmax-xmin, h: ymax-ymin}};
}}

function fillLabel(hex) {{
  const h = hex.replace('#','');
  const r=parseInt(h.slice(0,2),16), g=parseInt(h.slice(2,4),16), b=parseInt(h.slice(4,6),16);
  const L = 0.299*r + 0.587*g + 0.114*b;
  return L > 160 ? '#3D3733' : '#F6F7F3';
}}

const g = svg.append('g');

// Draw individual LEAF cells, filled with their category's shade.
// Stroke is thin (subtle separator between sub-cells within a category).
const leaves = root.leaves();
leaves.forEach(leaf => {{
  const pts = leaf.polygon;
  if (!pts || pts.length === 0) return;
  const d = "M" + pts.map(p => p[0]+","+p[1]).join("L") + "Z";
  g.append('path').attr('d', d)
    .attr('fill', leaf.data.color)
    .attr('stroke', BG)
    .attr('stroke-width', 0.8);
}});

// Draw thicker category outlines (parent polygons) to reinforce grouping —
// these visually separate one color region from the next.
const cats = root.children;
cats.forEach(cat => {{
  const pts = cat.polygon;
  if (!pts || pts.length === 0) return;
  const d = "M" + pts.map(p => p[0]+","+p[1]).join("L") + "Z";
  g.append('path').attr('d', d)
    .attr('fill', 'none')
    .attr('stroke', BG).attr('stroke-width', 5);
}});

// Sort leaves by share for label priority
const sortedLeaves = [...leaves].sort((a,b) => b.data.weight - a.data.weight);

const outsideLabels = [];
// Force-edge: cells from these categories ALWAYS get outside labels regardless of size.
const FORCE_EDGE_CATS = new Set(['Education', 'Retirement']);

sortedLeaves.forEach((leaf, idx) => {{
  const pts = leaf.polygon;
  if (!pts) return;
  const [tx, ty] = centroid(pts);
  const bb = bbox(pts);
  // Light or dark label depending on fill luminance
  const fc = fillLabel(leaf.data.color);

  const forceOutside = FORCE_EDGE_CATS.has(leaf.data.category);

  if (!forceOutside && idx === 0) {{
    g.append('text').attr('x', tx).attr('y', ty - 12)
      .attr('text-anchor','middle')
      .attr('font-family','ABC Oracle Edu').attr('font-size', 64).attr('font-weight', 700).attr('fill', fc)
      .text(`${{leaf.data.pct.toFixed(0)}}%`);
    g.append('text').attr('x', tx).attr('y', ty + 26)
      .attr('text-anchor','middle')
      .attr('font-family','ABC Oracle Edu').attr('font-size', 16).attr('font-weight', 700).attr('fill', fc).attr('letter-spacing','2')
      .text(leaf.data.label.toUpperCase());
  }} else if (!forceOutside && Math.min(bb.w, bb.h) > 55) {{
    const fs = Math.min(28, Math.max(13, Math.min(bb.w, bb.h) / 5.5));
    g.append('text').attr('x', tx).attr('y', ty - 3)
      .attr('text-anchor','middle')
      .attr('font-family','ABC Oracle Edu').attr('font-size', fs).attr('font-weight', 700).attr('fill', fc)
      .text(`${{leaf.data.pct.toFixed(0)}}%`);
    g.append('text').attr('x', tx).attr('y', ty + fs - 5)
      .attr('text-anchor','middle')
      .attr('font-family','ABC Oracle Edu').attr('font-size', Math.max(9, fs * 0.42)).attr('font-weight', 500).attr('fill', fc).attr('letter-spacing','1.2')
      .text(leaf.data.label.toUpperCase());
  }} else {{
    outsideLabels.push({{leaf, tx, ty}});
  }}
}});

// Outside labels — distribute around the rim with collision avoidance.
// For each small cell: compute its angle from container center.
// Pull the rim position toward that angle, but enforce a minimum angular gap.
const rimSlots = outsideLabels.map(({{leaf, tx, ty}}) => {{
  let ang = Math.atan2(ty - cy, tx - cx);  // [-π, π]
  return {{ leaf, tx, ty, angle: ang }};
}});
// Sort by angle, then space them out so each has ≥ minGap radians from neighbors
rimSlots.sort((a, b) => a.angle - b.angle);
const minGap = 0.13;  // ~7.5°
for (let i = 1; i < rimSlots.length; i++) {{
  if (rimSlots[i].angle - rimSlots[i-1].angle < minGap) {{
    rimSlots[i].angle = rimSlots[i-1].angle + minGap;
  }}
}}
// One more pass — if total spread exceeds 2π we have too many labels for the rim;
// gracefully clamp the last few. Otherwise rotate back if angles drifted off 2π.
if (rimSlots.length > 0) {{
  const last = rimSlots[rimSlots.length - 1].angle;
  const first = rimSlots[0].angle;
  if (last - first > 2 * Math.PI - minGap) {{
    // shift all proportionally
    const scale = (2 * Math.PI - minGap) / (last - first);
    for (let i = 0; i < rimSlots.length; i++) {{
      rimSlots[i].angle = first + (rimSlots[i].angle - first) * scale;
    }}
  }}
}}

rimSlots.forEach(({{leaf, tx, ty, angle}}) => {{
  const ux = Math.cos(angle), uy = Math.sin(angle);
  const x1 = cx + ux * (R + 16);
  const y1 = cy + uy * (R + 16);
  const isRight = ux >= 0;
  const x2 = x1 + (isRight ? 14 : -14);
  const anchor = isRight ? 'start' : 'end';

  // Leader: from cell centroid → straight elbow at the rim → flat to label
  g.append('polyline')
    .attr('points', `${{tx}},${{ty}} ${{cx + ux * (R - 4)}},${{cy + uy * (R - 4)}} ${{x1}},${{y1}}`)
    .attr('fill', 'none').attr('stroke', TEXT).attr('stroke-width', 0.5);

  g.append('text').attr('x', x2).attr('y', y1 - 4).attr('text-anchor', anchor)
    .attr('font-family','ABC Oracle Edu').attr('font-size', 13).attr('font-weight', 700).attr('fill', TEXT)
    .text(`${{leaf.data.pct.toFixed(1)}}%`);
  g.append('text').attr('x', x2).attr('y', y1 + 12).attr('text-anchor', anchor)
    .attr('font-family','ABC Oracle Edu').attr('font-size', 11).attr('font-weight', 400).attr('fill', TEXT)
    .text(leaf.data.label);
}});

// Category legend (just the categories, hue swatches)
const legendY = H - 95;
const cats2 = ['Employment','Housing','Family','Retirement','Education','Other'];
const catSwatch = {{
  Housing: '#0BB4FF', Employment: '#0099E0', Family: '#7DD4FF',
  Retirement: '#4FC4FF', Education: '#BCE8FF', Other: '#0077CC',
}};
let lx = 40;
cats2.forEach(c => {{
  svg.append('rect').attr('x', lx).attr('y', legendY).attr('width', 16).attr('height', 16).attr('fill', catSwatch[c]);
  svg.append('text').attr('x', lx + 22).attr('y', legendY + 13)
    .attr('font-family','ABC Oracle Edu').attr('font-size',14).attr('font-weight',500).attr('fill',TEXT)
    .text(c);
  lx += 22 + (c.length * 9) + 24;
}});

svg.append('text').attr('x', PAD).attr('y', H - 38)
  .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',300).attr('fill',TEXT)
  .text(`n = ${{P.n_records.toLocaleString()}} unweighted records, ~${{(P.total/1000).toFixed(0)}}k weighted family-with-kids out-of-state movers.`);
svg.append('text').attr('x', PAD).attr('y', H - 20)
  .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',300).attr('fill',TEXT)
  .text('Source: IPUMS CPS ASEC 1999-2025, WHYMOVE variable. CPS lacks county-level previous residence — NY → NJ/CT/PA is the closest proxy for NYC suburb flight (84% of these moves originate in the NY metro area per ACS).');
</script>
</body></html>"""
    (OUTPUTS / "whymove_voronoi.html").write_text(html)
    print(f"Wrote {OUTPUTS / 'whymove_voronoi.html'}")


if __name__ == "__main__":
    main()
