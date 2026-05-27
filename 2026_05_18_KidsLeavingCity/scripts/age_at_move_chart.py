"""
Chart: age distribution of children who moved from inner-county to outer-county
within each MSA in the past year. Small multiples, one panel per MSA.

Note: ACS reports current age. Actual age at move ≈ age − 1 (move happened up
to 12 months before the survey reference date).
"""
from __future__ import annotations
from pathlib import Path
import json
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OUTPUTS = PROJECT / "outputs"

COLORS = {
    "bar":     "#0BB4FF",  # blue — inner→outer move
    "bar_dim": "#C6DCCB",  # light green — outer→inner (reverse flow, for context)
    "text":    "#3D3733",
    "subtext": "#7F7570",
    "bg":      "#F6F7F3",
    "grid":    "#e1e2e3",
    "peak":    "#F4743B",  # red — peak annotation
}

# Order in chart layout (left→right, top→bottom). Big MSAs first.
PANEL_ORDER = [
    "New York-Newark-Jersey City, NY-NJ",
    "Los Angeles-Long Beach-Anaheim, CA",
    "Chicago-Naperville-Elgin, IL-IN",
    "Dallas-Fort Worth-Arlington, TX",
    "Houston-The Woodlands-Sugar Land, TX",
    "Atlanta-Sandy Springs-Roswell, GA",
    "Washington-Arlington-Alexandria, DC-VA-MD-WV",
    "Philadelphia-Camden-Wilmington, PA-NJ-DE-MD",
    "Austin-Round Rock-San Marcos, TX",
]


def short(msa: str) -> str:
    return msa.split(",")[0].split("-")[0].strip()


def main():
    d = pd.read_csv(DATA / "age_at_move.csv")
    # Make sure all ages 0-17 are present for each MSA
    panels = []
    for msa in PANEL_ORDER:
        sub = d[d["msa"] == msa].copy()
        full = pd.DataFrame({"AGE": range(0, 18)})
        sub = full.merge(sub, on="AGE", how="left").fillna(0)
        sub["msa"] = msa
        panels.append({
            "msa_full": msa,
            "msa_short": short(msa),
            "ages": list(sub["AGE"].astype(int)),
            "inner_to_outer": list(sub["inner_to_outer"].astype(int)),
            "outer_to_inner": list(sub["outer_to_inner"].astype(int)),
            "total_io": int(sub["inner_to_outer"].sum()),
        })
    js_data = json.dumps(panels)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>When do families leave the city?</title>
<style>
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Regular.otf') format('opentype'); font-weight:400; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Medium.otf') format('opentype'); font-weight:500; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Light.otf') format('opentype'); font-weight:300; }}
body {{ margin:0; background:#fff; font-family:'ABC Oracle Edu',sans-serif; }}
svg {{ display:block; margin:20px auto; }}
</style></head><body>
<svg id="chart" viewBox="0 0 1280 1200" xmlns="http://www.w3.org/2000/svg"></svg>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const PANELS = {js_data};
const C = {json.dumps(COLORS)};
const W = 1280, H = 1200;
const PAD = 40;
const COLS = 3, ROWS = 3;
const titleY = PAD + 32, subY = titleY + 30;
const panelTop = subY + 50;
const panelGridBottom = H - PAD - 70;       // room for source
const panelW = (W - 2*PAD) / COLS;
const panelH = (panelGridBottom - panelTop) / ROWS;
const innerPad = 12;

const svg = d3.select('#chart');
svg.append('rect').attr('width', W).attr('height', H).attr('fill', C.bg);

// Title
svg.append('text')
   .attr('x', PAD).attr('y', titleY)
   .attr('font-family', 'ABC Oracle Edu').attr('font-size', 28).attr('font-weight', 500)
   .attr('fill', C.text)
   .text('When do families leave the city?');

svg.append('text')
   .attr('x', PAD).attr('y', subY)
   .attr('font-family', 'ABC Oracle Edu').attr('font-size', 18).attr('font-weight', 400)
   .attr('fill', C.subtext)
   .text('Age distribution of kids who moved from inner→outer county within their MSA in the past year (ACS 5-year PUMS, 2019–2023)');

// Find global max y for shared scale
const globalMax = d3.max(PANELS, p => d3.max(p.inner_to_outer));

PANELS.forEach((p, i) => {{
  const col = i % COLS, row = Math.floor(i / COLS);
  const px = PAD + col * panelW + innerPad;
  const py = panelTop + row * panelH + 28;  // 28px for panel title
  const pw = panelW - 2 * innerPad;
  const ph = panelH - 48;  // leave room for title + x-axis labels

  // Panel title
  svg.append('text')
     .attr('x', px).attr('y', panelTop + row * panelH + 18)
     .attr('font-family', 'ABC Oracle Edu').attr('font-size', 16).attr('font-weight', 500)
     .attr('fill', C.text)
     .text(p.msa_short);

  svg.append('text')
     .attr('x', px + pw).attr('y', panelTop + row * panelH + 18)
     .attr('text-anchor', 'end')
     .attr('font-family', 'ABC Oracle Edu').attr('font-size', 12).attr('font-weight', 300)
     .attr('fill', C.subtext)
     .text(p.total_io.toLocaleString() + ' kids/yr');

  // Scales
  const x = d3.scaleBand().domain(d3.range(18)).range([px, px + pw]).padding(0.15);
  const y = d3.scaleLinear().domain([0, globalMax]).range([py + ph, py]);

  // Zero line
  svg.append('line').attr('x1', px).attr('x2', px + pw)
     .attr('y1', py + ph).attr('y2', py + ph)
     .attr('stroke', C.text).attr('stroke-width', 0.5);

  // Find peak age (single peak — argmax)
  let peakAge = 0, peakVal = 0;
  p.inner_to_outer.forEach((v, a) => {{ if (v > peakVal) {{ peakVal = v; peakAge = a; }} }});

  // Bars
  p.ages.forEach(age => {{
    const v = p.inner_to_outer[age];
    if (v <= 0) return;
    svg.append('rect')
       .attr('x', x(age)).attr('width', x.bandwidth())
       .attr('y', y(v)).attr('height', py + ph - y(v))
       .attr('fill', age === peakAge ? C.peak : C.bar);
  }});

  // Peak label
  if (peakVal > 0) {{
    svg.append('text')
       .attr('x', x(peakAge) + x.bandwidth() / 2)
       .attr('y', y(peakVal) - 4)
       .attr('text-anchor', 'middle')
       .attr('font-family', 'ABC Oracle Edu').attr('font-size', 11).attr('font-weight', 500)
       .attr('fill', C.peak)
       .text(`age ${{peakAge}}`);
  }}

  // X-axis tick labels (just 0, 5, 10, 15)
  [0, 5, 10, 15].forEach(t => {{
    svg.append('text')
       .attr('x', x(t) + x.bandwidth() / 2).attr('y', py + ph + 14)
       .attr('text-anchor', 'middle')
       .attr('font-family', 'ABC Oracle Edu').attr('font-size', 11).attr('font-weight', 300)
       .attr('fill', '#666')
       .text(t);
  }});
}});

// Footnote on age semantics
svg.append('text')
   .attr('x', PAD).attr('y', H - PAD - 36)
   .attr('font-family', 'ABC Oracle Edu').attr('font-size', 12).attr('font-weight', 400)
   .attr('fill', C.text)
   .text('Note: AGE is the survey age. Since ACS asks "where lived 1 year ago", the actual age at move is approximately AGE − 1. A peak at age 2 means the move happened when the kid was ~1.');

svg.append('text')
   .attr('x', PAD).attr('y', H - PAD - 18)
   .attr('font-family', 'ABC Oracle Edu').attr('font-size', 12).attr('font-weight', 200)
   .attr('fill', C.text)
   .text('Source: IPUMS ACS 5-year PUMS, latest 5-year window (2019–2023). Inner = MSA central county/counties; outer = other MSA counties.');

svg.append('text')
   .attr('x', PAD).attr('y', H - PAD - 2)
   .attr('font-family', 'ABC Oracle Edu').attr('font-size', 12).attr('font-weight', 200)
   .attr('fill', C.subtext)
   .text('Miami and Phoenix excluded — Miami-Dade COUNTYFIP suppressed in PUMS; Phoenix sample too small.');
</script>
</body></html>"""
    out = OUTPUTS / "age_at_move.html"
    out.write_text(html)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
