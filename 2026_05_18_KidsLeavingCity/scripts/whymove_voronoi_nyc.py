"""
Voronoi treemap of WHYMOVE reasons — NYC-commute-belt version.

Identical layout to outputs/whymove_voronoi.html (circular clip, hierarchical
cells, category outlines, big featured center label, rim labels with leaders).
The ONLY change is the SQL filter: destination must be in the NYC CSA
(METFIPS 35620 or 14860, or COUNTY in the 30 NYC-CSA counties), proxying
"people who work in NYC."

Output: outputs/whymove_voronoi_nyc.html. Does NOT overwrite the original.
"""
from __future__ import annotations
import json
from pathlib import Path
import duckdb

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
OUTPUTS = PROJECT / "outputs"
F = "/Users/azizsunderji/Dropbox/Home Economics/Data/CPS_ASEC/cps_asec_full.parquet"

# NYC CSA county FIPS (30 counties used elsewhere in the project)
NYC_CSA_FIPS = (34003,34013,34017,34019,34021,34023,34025,34027,34029,34031,34035,34037,34039,
                36005,36027,36047,36059,36061,36071,36079,36081,36085,36087,36103,36105,36111,36119,
                9001,9009,42103)

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

CATEGORY_COLOR = {
    "Housing":    "#0BB4FF",
    "Employment": "#0099E0",
    "Family":     "#7DD4FF",
    "Retirement": "#4FC4FF",
    "Education":  "#BCE8FF",
    "Other":      "#0077CC",
}

BG = "#F6F7F3"
TEXT = "#3D3733"


def main():
    df = duckdb.query(f"""
        SELECT WHYMOVE, ASECWT FROM '{F}'
        WHERE MIGSTA1=36 AND STATEFIP IN (34,9,42)
          AND MIGRATE1=5 AND NCHILD>0 AND WHYMOVE BETWEEN 1 AND 20
          AND (METFIPS IN (35620, 14860) OR COUNTY IN {NYC_CSA_FIPS})
    """).df()
    df.loc[df["WHYMOVE"] == 20, "WHYMOVE"] = 3
    agg = df.groupby("WHYMOVE")["ASECWT"].sum().sort_values(ascending=False)
    total = float(agg.sum())
    n_records = len(df)

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
<title>Why NYC commute-belt families with kids leave</title>
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

// Measurement helper
const _mc = document.createElement('canvas').getContext('2d');
function tw(str, fs, weight, ls) {{
  _mc.font = `${{weight}} ${{fs}}px 'ABC Oracle Edu', sans-serif`;
  return _mc.measureText(str).width + (ls || 0) * Math.max(0, str.length - 1);
}}

document.fonts.ready.then(() => draw());

function draw() {{
const svg = d3.select('#chart');
svg.append('rect').attr('width', W).attr('height', H).attr('fill', BG);

svg.append('text').attr('x', PAD).attr('y', PAD + 32)
  .attr('font-family','ABC Oracle Edu').attr('font-size',30).attr('font-weight',700).attr('fill',TEXT)
  .text('Why NYC families with kids leave for the suburbs');
svg.append('text').attr('x', PAD).attr('y', PAD + 32 + 28)
  .attr('font-family','ABC Oracle Edu').attr('font-size',17).attr('font-weight',400).attr('fill',TEXT)
  .text('Stated reasons — NYC commute-belt only (destination within the NYC CSA, proxy for "still works in NYC").');

// Container — circular polygon (60 sides ≈ smooth circle)
const cx = W / 2, cy = H / 2 + 20, R = 360, N = 60;
const clipPoly = [];
for (let i = 0; i < N; i++) {{
  const a = (i / N) * 2 * Math.PI - Math.PI / 2;
  clipPoly.push([cx + R * Math.cos(a), cy + R * Math.sin(a)]);
}}

const root = d3.hierarchy(P.hierarchy).sum(d => d.weight);
const vt = d3.voronoiTreemap()
  .clip(clipPoly)
  .convergenceRatio(0.001)
  .maxIterationCount(400)
  .minWeightRatio(0.005);
vt(root);

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

// Horizontal extent of polygon at a given y — find leftmost and rightmost edge intersections.
function horizExtentAt(pts, y) {{
  let xmin = Infinity, xmax = -Infinity;
  for (let i = 0; i < pts.length; i++) {{
    const [x0, y0] = pts[i];
    const [x1, y1] = pts[(i + 1) % pts.length];
    if ((y0 <= y && y1 > y) || (y1 <= y && y0 > y)) {{
      const t = (y - y0) / (y1 - y0);
      const xi = x0 + t * (x1 - x0);
      if (xi < xmin) xmin = xi;
      if (xi > xmax) xmax = xi;
    }}
  }}
  if (xmin === Infinity) return 0;
  return xmax - xmin;
}}

function fillLabel(hex) {{
  const h = hex.replace('#','');
  const r=parseInt(h.slice(0,2),16), g=parseInt(h.slice(2,4),16), b=parseInt(h.slice(4,6),16);
  const L = 0.299*r + 0.587*g + 0.114*b;
  return L > 160 ? '#3D3733' : '#F6F7F3';
}}

const g = svg.append('g');

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

const cats = root.children;
cats.forEach(cat => {{
  const pts = cat.polygon;
  if (!pts || pts.length === 0) return;
  const d = "M" + pts.map(p => p[0]+","+p[1]).join("L") + "Z";
  g.append('path').attr('d', d)
    .attr('fill', 'none')
    .attr('stroke', BG).attr('stroke-width', 5);
}});

const sortedLeaves = [...leaves].sort((a,b) => b.data.weight - a.data.weight);
const outsideLabels = [];

sortedLeaves.forEach((leaf, idx) => {{
  const pts = leaf.polygon;
  if (!pts) return;
  const [tx, ty] = centroid(pts);
  const bb = bbox(pts);
  const fc = fillLabel(leaf.data.color);
  const labelText = leaf.data.label.toUpperCase();

  if (idx === 0) {{
    // featured center cell
    g.append('text').attr('x', tx).attr('y', ty - 12)
      .attr('text-anchor','middle')
      .attr('font-family','ABC Oracle Edu').attr('font-size', 64).attr('font-weight', 700).attr('fill', fc)
      .text(`${{leaf.data.pct.toFixed(0)}}%`);
    g.append('text').attr('x', tx).attr('y', ty + 26)
      .attr('text-anchor','middle')
      .attr('font-family','ABC Oracle Edu').attr('font-size', 16).attr('font-weight', 700).attr('fill', fc).attr('letter-spacing','2')
      .text(labelText);
    return;
  }}

  // Try to fit inside the cell. Use horizontal extent AT the label's y, not the bbox width.
  const pad = 10;
  const localW = horizExtentAt(pts, ty);
  const maxW = Math.max(0, localW - pad);
  const maxH = bb.h - pad;
  let pctFs = Math.min(28, Math.max(11, Math.min(maxW, maxH) / 4.8));
  let lblFs = Math.max(9, pctFs * 0.45);

  const lblW = tw(labelText, lblFs, 500, 1.2);
  if (lblW > maxW * 0.88) {{
    const scale = (maxW * 0.85) / lblW;
    pctFs *= scale;
    lblFs *= scale;
  }}

  if (lblFs < 9.2 || maxW < 42 || maxH < 32) {{
    outsideLabels.push({{leaf, tx, ty}});
    return;
  }}

  g.append('text').attr('x', tx).attr('y', ty - 3)
    .attr('text-anchor','middle')
    .attr('font-family','ABC Oracle Edu').attr('font-size', pctFs).attr('font-weight', 700).attr('fill', fc)
    .text(`${{leaf.data.pct.toFixed(0)}}%`);
  g.append('text').attr('x', tx).attr('y', ty + pctFs - 5)
    .attr('text-anchor','middle')
    .attr('font-family','ABC Oracle Edu').attr('font-size', lblFs).attr('font-weight', 500).attr('fill', fc).attr('letter-spacing','1.2')
    .text(labelText);
}});

// ── Rim leader labels ──
// Push outside the category-arc ring so they don't collide with arc text.
const rLeader = R + 78;
const rimSlots = outsideLabels.map(({{leaf, tx, ty}}) => {{
  let ang = Math.atan2(ty - cy, tx - cx);
  return {{ leaf, tx, ty, angle: ang }};
}});
rimSlots.sort((a, b) => a.angle - b.angle);
const minGap = 0.14;
for (let i = 1; i < rimSlots.length; i++) {{
  if (rimSlots[i].angle - rimSlots[i-1].angle < minGap) {{
    rimSlots[i].angle = rimSlots[i-1].angle + minGap;
  }}
}}
if (rimSlots.length > 0) {{
  const last = rimSlots[rimSlots.length - 1].angle;
  const first = rimSlots[0].angle;
  if (last - first > 2 * Math.PI - minGap) {{
    const scale = (2 * Math.PI - minGap) / (last - first);
    for (let i = 0; i < rimSlots.length; i++) {{
      rimSlots[i].angle = first + (rimSlots[i].angle - first) * scale;
    }}
  }}
}}

rimSlots.forEach(({{leaf, tx, ty, angle}}) => {{
  const ux = Math.cos(angle), uy = Math.sin(angle);
  const xLabel = cx + ux * rLeader;
  const yLabel = cy + uy * rLeader;
  const isRight = ux >= 0;
  const x2 = xLabel + (isRight ? 6 : -6);
  const anchor = isRight ? 'start' : 'end';

  g.append('polyline')
    .attr('points', `${{tx}},${{ty}} ${{cx + ux * (R - 4)}},${{cy + uy * (R - 4)}} ${{xLabel}},${{yLabel}}`)
    .attr('fill', 'none').attr('stroke', TEXT).attr('stroke-width', 0.5).attr('opacity', 0.55);

  g.append('text').attr('x', x2).attr('y', yLabel - 3).attr('text-anchor', anchor)
    .attr('font-family','ABC Oracle Edu').attr('font-size', 13).attr('font-weight', 700).attr('fill', TEXT)
    .text(`${{leaf.data.pct.toFixed(1)}}%`);
  g.append('text').attr('x', x2).attr('y', yLabel + 13).attr('text-anchor', anchor)
    .attr('font-family','ABC Oracle Edu').attr('font-size', 11).attr('font-weight', 400).attr('fill', TEXT)
    .text(leaf.data.label);
}});

// ── Category labels along the circumference ──
const arcR = R + 32;
const defs = svg.append('defs');

function catArcRange(polygon) {{
  // Collect angles of polygon vertices that lie on the clip rim (radius ~= R).
  const eps = 2.0;
  const angles = [];
  polygon.forEach(([x, y]) => {{
    const dx = x - cx, dy = y - cy;
    const r = Math.hypot(dx, dy);
    if (Math.abs(r - R) < eps) angles.push(Math.atan2(dy, dx));
  }});
  if (angles.length < 2) return null;
  angles.sort((a, b) => a - b);
  // Largest angular gap → arc is its complement.
  let bestGap = -Infinity, bestI = 0;
  for (let i = 0; i < angles.length; i++) {{
    const nxt = i === angles.length - 1 ? angles[0] + 2 * Math.PI : angles[i + 1];
    const gap = nxt - angles[i];
    if (gap > bestGap) {{ bestGap = gap; bestI = i; }}
  }}
  let aStart = angles[(bestI + 1) % angles.length];
  let aEnd = angles[bestI];
  if (aEnd < aStart) aEnd += 2 * Math.PI;
  return {{ start: aStart, end: aEnd, span: aEnd - aStart }};
}}

cats.forEach(cat => {{
  const pts = cat.polygon;
  if (!pts || pts.length === 0) return;
  const arc = catArcRange(pts);
  if (!arc) return;

  // Pad the arc inwards a touch so text doesn't kiss the category dividers.
  const padFrac = 0.05;
  const aStart = arc.start + arc.span * padFrac;
  const aEnd = arc.end - arc.span * padFrac;
  const span = aEnd - aStart;
  const arcLen = arcR * span;

  const text = cat.data.name.toUpperCase();
  // Choose font size to fit arc length, clamped to a readable range.
  let fs = 24;
  let measured = tw(text, fs, 700, 3);
  if (measured > arcLen * 0.95) fs = fs * (arcLen * 0.9) / measured;
  fs = Math.max(11, Math.min(28, fs));
  // Final check — if still too long at min size, skip arc label (small category).
  if (tw(text, fs, 700, 3) > arcLen * 0.98) return;

  const x1 = cx + arcR * Math.cos(aStart);
  const y1 = cy + arcR * Math.sin(aStart);
  const x2 = cx + arcR * Math.cos(aEnd);
  const y2 = cy + arcR * Math.sin(aEnd);
  const largeArc = span > Math.PI ? 1 : 0;
  // Bottom-half arcs (midpoint y > cy) read upside-down if traced in increasing-angle direction.
  // Reverse the path so character tops face inward = up on screen.
  let mid = (aStart + aEnd) / 2;
  while (mid > Math.PI) mid -= 2 * Math.PI;
  while (mid <= -Math.PI) mid += 2 * Math.PI;
  const reverse = mid > 0;
  const id = `arc-${{cat.data.name.toLowerCase().replace(/[^a-z]/g, '')}}`;
  const pathD = reverse
    ? `M ${{x2}} ${{y2}} A ${{arcR}} ${{arcR}} 0 ${{largeArc}} 0 ${{x1}} ${{y1}}`
    : `M ${{x1}} ${{y1}} A ${{arcR}} ${{arcR}} 0 ${{largeArc}} 1 ${{x2}} ${{y2}}`;
  defs.append('path')
    .attr('id', id)
    .attr('d', pathD)
    .attr('fill', 'none').attr('stroke', 'none');

  const t = svg.append('text')
    .attr('font-family', 'ABC Oracle Edu')
    .attr('font-weight', 700)
    .attr('font-size', fs)
    .attr('letter-spacing', '3')
    .attr('fill', TEXT);
  t.append('textPath')
    .attr('href', `#${{id}}`)
    .attr('startOffset', '50%')
    .attr('text-anchor', 'middle')
    .text(text);
}});

svg.append('text').attr('x', PAD).attr('y', H - 32)
  .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',300).attr('fill',TEXT)
  .text(`n = ${{P.n_records.toLocaleString()}} unweighted records, ~${{(P.total/1000).toFixed(0)}}k weighted family-with-kids movers.`);
svg.append('text').attr('x', PAD).attr('y', H - 14)
  .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',300).attr('fill',TEXT)
  .text('Source: IPUMS CPS ASEC 1999-2025. NY-state residence 1 year ago, now in NJ/CT/PA, destination within NYC CSA (METFIPS 35620/14860 or county in the 30 NYC-CSA counties).');
}}
</script>
</body></html>"""
    (OUTPUTS / "whymove_voronoi_nyc.html").write_text(html)
    print(f"Wrote {OUTPUTS / 'whymove_voronoi_nyc.html'} (n={n_records})")


if __name__ == "__main__":
    main()
