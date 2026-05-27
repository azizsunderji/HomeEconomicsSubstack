"""
Polygon-pie chart of WHYMOVE reasons for NY families with kids leaving for
NJ / CT / PA — Bloomberg-style faceted polygon with weighted angular wedges.

Output: outputs/whymove_polygon.html
"""
from __future__ import annotations
import json
import math
from pathlib import Path
import duckdb
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
OUTPUTS = PROJECT / "outputs"
F = "/Users/azizsunderji/Dropbox/Home Economics/Data/CPS_ASEC/cps_asec_full.parquet"

WHYMOVE_LABELS = {
    1: "Marital status change",     2: "Establish own household",  3: "Other family reason",
    4: "New job / transfer",         5: "Lost job / looking",        6: "Easier commute",
    7: "Retired",                    8: "Other job-related",         9: "Wanted to own / stop owning",
    10: "New / better housing",     11: "Better neighborhood",     12: "Cheaper housing",
    13: "Other housing",            14: "College",                  15: "Climate",
    16: "Health",                   17: "Natural disaster",         18: "Foreclosure / eviction",
    19: "Other reason",             20: "Other family reason",
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

# Shades of red for the Bloomberg-style chart. Biggest = darkest saturated red.
RED_SHADES = {
    "Employment": "#C4301C",  # deep red
    "Housing":    "#F4743B",  # red-orange (brand red)
    "Family":     "#A32515",  # dark red
    "Retirement": "#FBCAB5",  # light red
    "Education":  "#FDE8DD",  # very light red
    "Other":      "#7A1A0E",  # darkest red
}

BG = "#EFE6D8"     # warm cream like Bloomberg
TEXT = "#3D3733"
SUBTEXT = "#7F7570"


def main():
    # Pull NY → NJ/CT/PA with kids
    df = duckdb.query(f"""
        SELECT WHYMOVE, ASECWT FROM '{F}'
        WHERE MIGSTA1 = 36 AND STATEFIP IN (34, 9, 42)
          AND MIGRATE1 = 5 AND NCHILD > 0
          AND WHYMOVE BETWEEN 1 AND 20
    """).df()

    agg = df.groupby("WHYMOVE")["ASECWT"].sum().sort_values(ascending=False)
    total = agg.sum()

    # Build wedge data, sorted by size (largest first)
    wedges = []
    for code, w in agg.items():
        code = int(code)
        cat = CODE_TO_CAT.get(code, "Other")
        wedges.append({
            "code": code,
            "label": WHYMOVE_LABELS[code],
            "category": cat,
            "weight": float(w),
            "pct": float(w / total * 100),
            "color": RED_SHADES[cat],
        })

    payload = json.dumps({
        "title": "Why NY families with kids leave the state",
        "subtitle": "Stated reasons (CPS ASEC 1999-2025), NY → NJ/CT/PA, householders with own children",
        "total_weight": int(total),
        "n_records": len(df),
        "wedges": wedges,
    })

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Why NY families leave</title>
<style>
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Regular.otf') format('opentype'); font-weight:400; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Medium.otf') format('opentype'); font-weight:500; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Bold.otf') format('opentype'); font-weight:700; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Light.otf') format('opentype'); font-weight:300; }}
body {{ margin:0; background:#fff; font-family:'ABC Oracle Edu',sans-serif; }}
svg {{ display:block; margin:20px auto; }}
</style></head><body>
<svg id="chart" viewBox="0 0 1200 1000" xmlns="http://www.w3.org/2000/svg"></svg>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const P = {payload};
const BG = {json.dumps(BG)};
const TEXT = {json.dumps(TEXT)};
const SUBTEXT = {json.dumps(SUBTEXT)};
const W = 1200, H = 1000;
const PAD = 40;

const svg = d3.select('#chart');
svg.append('rect').attr('width', W).attr('height', H).attr('fill', BG);

// Title
svg.append('text')
  .attr('x', PAD).attr('y', PAD + 32)
  .attr('font-family','ABC Oracle Edu').attr('font-size',28).attr('font-weight',700).attr('fill',TEXT)
  .text(P.title);
svg.append('text')
  .attr('x', PAD).attr('y', PAD + 32 + 26)
  .attr('font-family','ABC Oracle Edu').attr('font-size',16).attr('font-weight',400).attr('fill',TEXT)
  .text(P.subtitle);

// Subtle film-grain filter for the wedge fills (Bloomberg-esque texture)
const defs = svg.append('defs');
const filt = defs.append('filter').attr('id','grain').attr('x','-20%').attr('y','-20%').attr('width','140%').attr('height','140%');
filt.append('feTurbulence').attr('type','fractalNoise').attr('baseFrequency','0.95').attr('numOctaves','2').attr('seed','3').attr('result','noise');
filt.append('feColorMatrix').attr('in','noise').attr('type','matrix').attr('values','0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.18 0').attr('result','noiseAlpha');
filt.append('feComposite').attr('in','SourceGraphic').attr('in2','noiseAlpha').attr('operator','arithmetic').attr('k1','0').attr('k2','1').attr('k3','1').attr('k4','0');

// Polygon-pie geometry
const cx = W / 2 - 40;
const cy = H / 2 + 40;
const R = 320;
const N_SIDES = 28;  // 28-gon — visibly faceted but smooth

// Polygon vertex positions
function polygonVertex(i) {{
  const ang = (i / N_SIDES) * 2 * Math.PI - Math.PI / 2;  // start at top
  return [Math.cos(ang) * R, Math.sin(ang) * R];
}}
// Distance from origin to polygon edge along ray at angle θ (θ measured from +x, math convention)
function polygonRadiusAt(theta) {{
  // Normalize theta to [-PI, PI]
  const T = 2 * Math.PI;
  let t = ((theta % T) + T) % T;  // [0, 2π]
  // Polygon vertices are at angles (i/N) * 2π - π/2 (we shifted to start at top)
  // For edge index k, edge connects vertex k to vertex (k+1) mod N
  // Edge endpoints at angles a_k = k * 2π/N - π/2, a_{{k+1}} = a_k + 2π/N
  // We need to find which edge contains angle t.
  // Convert t into the rotated frame: add π/2 so that polygon starts at 0
  let tr = (t + Math.PI / 2) % T;
  if (tr < 0) tr += T;
  const dAng = T / N_SIDES;
  const k = Math.floor(tr / dAng);
  const a0 = k * dAng - Math.PI / 2;          // angle of vertex k
  const a1 = a0 + dAng;                        // angle of vertex k+1
  const v0 = [R * Math.cos(a0), R * Math.sin(a0)];
  const v1 = [R * Math.cos(a1), R * Math.sin(a1)];
  // Ray: r * (cos t, sin t)
  // Solve r * cos t = v0.x + s * (v1.x - v0.x); r * sin t = v0.y + s * (v1.y - v0.y)
  // [cos t  -(v1.x-v0.x)] [r]   [v0.x]
  // [sin t  -(v1.y-v0.y)] [s] = [v0.y]
  const a = Math.cos(t), b = -(v1[0] - v0[0]);
  const c = Math.sin(t), d = -(v1[1] - v0[1]);
  const det = a * d - b * c;
  const r = (d * v0[0] - b * v0[1]) / det;
  return r;
}}

// Compute wedge angles. Total = 2π. Start at top (12 o'clock), go clockwise.
const total = d3.sum(P.wedges, d => d.weight);
let startAngle = -Math.PI / 2;  // 12 o'clock
const wedgePaths = [];
P.wedges.forEach(w => {{
  const arc = (w.weight / total) * 2 * Math.PI;
  const endAngle = startAngle + arc;

  // Build path: center → ray at startAngle to polygon edge → polygon vertices between → ray at endAngle to edge → center
  const r0 = polygonRadiusAt(startAngle);
  const p0 = [r0 * Math.cos(startAngle), r0 * Math.sin(startAngle)];
  const r1 = polygonRadiusAt(endAngle);
  const p1 = [r1 * Math.cos(endAngle), r1 * Math.sin(endAngle)];

  // Polygon vertices between startAngle and endAngle (clockwise = increasing angle in our convention)
  // Vertex i angle: i * (2π/N) - π/2. We need indices i with startAngle < angle_i < endAngle.
  const dAng = 2 * Math.PI / N_SIDES;
  let i0 = Math.ceil((startAngle + Math.PI / 2) / dAng);
  let i1 = Math.floor((endAngle + Math.PI / 2) / dAng);
  const verts = [];
  for (let i = i0; i <= i1; i++) {{
    const a = i * dAng - Math.PI / 2;
    verts.push([R * Math.cos(a), R * Math.sin(a)]);
  }}

  let d = `M0,0 L${{p0[0]}},${{p0[1]}}`;
  verts.forEach(v => {{ d += ` L${{v[0]}},${{v[1]}}`; }});
  d += ` L${{p1[0]}},${{p1[1]}} Z`;
  wedgePaths.push({{ w, d, midAngle: (startAngle + endAngle) / 2, arc }});
  startAngle = endAngle;
}});

// Draw wedges
const g = svg.append('g').attr('transform', `translate(${{cx}}, ${{cy}})`);
wedgePaths.forEach(({{w, d}}, i) => {{
  g.append('path')
    .attr('d', d)
    .attr('fill', w.color)
    .attr('stroke', BG)
    .attr('stroke-width', 1.5)
    .attr('filter', 'url(#grain)');
}});

// Labels — biggest wedge gets centered inside; others get outside w/ leader lines
const minLabelArc = 0.18;  // radians; below this → outside label
const outsideLabels = [];

wedgePaths.forEach(({{w, midAngle, arc}}, i) => {{
  if (i === 0) {{
    // Biggest wedge — label inside the polygon, near the centroid
    const cxL = Math.cos(midAngle) * R * 0.18;
    const cyL = Math.sin(midAngle) * R * 0.18;
    g.append('text')
      .attr('x', cxL).attr('y', cyL - 10)
      .attr('text-anchor','middle')
      .attr('font-family','ABC Oracle Edu').attr('font-size',56).attr('font-weight',700).attr('fill','#FBCAB5')
      .text(`${{w.pct.toFixed(0)}}%`);
    g.append('text')
      .attr('x', cxL).attr('y', cyL + 28)
      .attr('text-anchor','middle')
      .attr('font-family','ABC Oracle Edu').attr('font-size',18).attr('font-weight',700).attr('fill','#FBCAB5').attr('letter-spacing','3')
      .text(w.label.toUpperCase());
  }} else if (arc > minLabelArc) {{
    // Medium wedge — inside label
    const r = R * 0.65;
    const xL = Math.cos(midAngle) * r;
    const yL = Math.sin(midAngle) * r;
    const fontC = (w.category === 'Education' || w.category === 'Retirement') ? '#3D3733' : '#FBCAB5';
    g.append('text')
      .attr('x', xL).attr('y', yL - 6)
      .attr('text-anchor','middle')
      .attr('font-family','ABC Oracle Edu').attr('font-size',22).attr('font-weight',700).attr('fill',fontC)
      .text(`${{w.pct.toFixed(0)}}%`);
    g.append('text')
      .attr('x', xL).attr('y', yL + 14)
      .attr('text-anchor','middle')
      .attr('font-family','ABC Oracle Edu').attr('font-size',11).attr('font-weight',500).attr('fill',fontC).attr('letter-spacing','1.5')
      .text(w.label.toUpperCase());
  }} else {{
    outsideLabels.push({{ w, midAngle, arc }});
  }}
}});

// Outside labels with leader lines
outsideLabels.forEach(({{w, midAngle}}) => {{
  const r0 = polygonRadiusAt(midAngle);
  const x0 = Math.cos(midAngle) * r0;
  const y0 = Math.sin(midAngle) * r0;
  const x1 = Math.cos(midAngle) * (r0 + 30);
  const y1 = Math.sin(midAngle) * (r0 + 30);
  const isRight = Math.cos(midAngle) >= 0;
  const x2 = x1 + (isRight ? 18 : -18);
  const anchor = isRight ? 'start' : 'end';

  g.append('line').attr('x1', x0).attr('y1', y0).attr('x2', x1).attr('y2', y1)
    .attr('stroke', TEXT).attr('stroke-width', 0.5);

  g.append('text').attr('x', x2).attr('y', y1 - 4).attr('text-anchor', anchor)
    .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',700).attr('fill',TEXT)
    .text(`${{w.pct.toFixed(1)}}%`);
  g.append('text').attr('x', x2).attr('y', y1 + 12).attr('text-anchor', anchor)
    .attr('font-family','ABC Oracle Edu').attr('font-size',11).attr('font-weight',400).attr('fill',TEXT)
    .text(w.label);
}});

// Legend (categories → colors)
const legendY = H - 90;
const cats = ['Employment','Housing','Family','Retirement','Education','Other'];
const colorMap = {{
  Employment: '#C4301C', Housing: '#F4743B', Family: '#A32515',
  Retirement: '#FBCAB5', Education: '#FDE8DD', Other: '#7A1A0E',
}};
let lx = 40;
cats.forEach(c => {{
  svg.append('rect').attr('x', lx).attr('y', legendY).attr('width', 16).attr('height', 16)
    .attr('fill', colorMap[c]);
  svg.append('text').attr('x', lx + 22).attr('y', legendY + 13)
    .attr('font-family','ABC Oracle Edu').attr('font-size',14).attr('font-weight',400).attr('fill',TEXT)
    .text(c);
  lx += 22 + (c.length * 9) + 24;
}});

// Source / caption
svg.append('text').attr('x', PAD).attr('y', H - 40)
  .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',300).attr('fill',TEXT)
  .text(`n = ${{P.n_records.toLocaleString()}} unweighted records, ~${{(P.total_weight/1000).toFixed(0)}}k weighted family-with-kids out-of-state movers.`);
svg.append('text').attr('x', PAD).attr('y', H - 22)
  .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',300).attr('fill',TEXT)
  .text('Source: IPUMS CPS ASEC 1999-2025, WHYMOVE variable. NY householders with own children moving to NJ, CT, or PA.');
</script>
</body></html>"""
    (OUTPUTS / "whymove_polygon.html").write_text(html)
    print(f"Wrote {OUTPUTS / 'whymove_polygon.html'}")


if __name__ == "__main__":
    main()
