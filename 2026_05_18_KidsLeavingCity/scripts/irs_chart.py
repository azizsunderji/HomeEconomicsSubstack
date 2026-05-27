"""
Time-series chart: annual net inner→outer exemption flow per MSA, 2011-12 → 2022-23.

One line per MSA. Markers on each year. Highlight the COVID acceleration (2019-20
through 2021-22). Source: IRS SOI county-to-county migration.
"""
from __future__ import annotations
from pathlib import Path
import json
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OUTPUTS = PROJECT / "outputs"

COLORS = {
    "bg": "#F6F7F3",
    "text": "#3D3733",
    "subtext": "#7F7570",
    "grid": "#e1e2e3",
    # Color per MSA (highlight a few, neutral for the rest)
    "New York": "#0BB4FF",
    "Los Angeles": "#F4743B",
    "Chicago": "#67A275",
    "Houston": "#FEC439",
    "Dallas": "#3F6E4B",
    "Atlanta": "#A32515",
    "Washington": "#7A1A0E",
    "Philadelphia": "#005C99",
    "Miami": "#C4301C",
    "Phoenix": "#003D66",
    "Austin": "#005C99",
    "Charlotte": "#67A275",
    "covid_band": "#FBCAB5",
}


def short(msa: str) -> str:
    return msa.split(",")[0].split("-")[0].strip()


def yp_to_xlabel(yp: str) -> str:
    """'1112' → '11–12'."""
    return f"'{yp[:2]}–'{yp[2:]}"


def main():
    d = pd.read_csv(DATA / "irs_inner_outer_flows.csv", dtype={"year_pair": str})
    d["year_pair"] = d["year_pair"].str.zfill(4)
    # Exclude 2016-17 — IRS methodology change creates a spurious one-year spike
    d = d[d["year_pair"] != "1617"].copy()
    d["msa_short"] = d["msa"].apply(short)
    d = d.sort_values(["msa_short", "year_pair"])

    msas = list(d["msa_short"].unique())
    year_pairs = sorted(d["year_pair"].unique())

    # Use DEPENDENTS (exemptions − 1.5×returns), not total exemptions
    series = []
    for m in msas:
        sub = d[d["msa_short"] == m].set_index("year_pair").reindex(year_pairs)
        series.append({
            "msa": m,
            "values": [int(v) if pd.notna(v) else 0 for v in sub["net_outflow_dependents"]],
            "color": COLORS.get(m, "#999"),
        })

    payload = {
        "year_pairs": year_pairs,
        "series": series,
    }
    js = json.dumps(payload)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Annual net out-flow from inner counties, 2011–2023</title>
<style>
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Regular.otf') format('opentype'); font-weight:400; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Medium.otf') format('opentype'); font-weight:500; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Light.otf') format('opentype'); font-weight:300; }}
body {{ margin:0; background:#fff; font-family:'ABC Oracle Edu',sans-serif; }}
svg {{ display:block; margin:20px auto; }}
</style></head><body>
<svg id="chart" viewBox="0 0 1280 800" xmlns="http://www.w3.org/2000/svg"></svg>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const P = {js};
const C = {json.dumps(COLORS)};
const W = 1280, H = 800;
const PAD = 40;

const svg = d3.select('#chart');
svg.append('rect').attr('width', W).attr('height', H).attr('fill', C.bg);

// Title
svg.append('text')
  .attr('x', PAD).attr('y', PAD + 32)
  .attr('font-family', 'ABC Oracle Edu').attr('font-size', 30).attr('font-weight', 500)
  .attr('fill', C.text)
  .text('Net out-migration of DEPENDENTS from inner counties to MSA suburbs');

svg.append('text')
  .attr('x', PAD).attr('y', PAD + 32 + 30)
  .attr('font-family', 'ABC Oracle Edu').attr('font-size', 18).attr('font-weight', 400)
  .attr('fill', C.subtext)
  .text('Dependents ≈ exemptions − 1.5 × returns (proxy for kids+). 2016-17 excluded — IRS methodology break.');

// Plot area
const chartLeft = 100, chartRight = W - PAD - 200;  // room for inline labels
const chartTop = PAD + 32 + 30 + 50;
const chartBottom = H - PAD - 70;

const x = d3.scalePoint().domain(P.year_pairs).range([chartLeft, chartRight]).padding(0.5);

const ymax = d3.max(P.series.flatMap(s => s.values));
const ymin = Math.min(0, d3.min(P.series.flatMap(s => s.values)));
const y = d3.scaleLinear().domain([ymin, ymax * 1.05]).range([chartBottom, chartTop]);

// Shade COVID band 1920..2122 (tax years 2019-20 to 2021-22)
const covidYears = ['1920','2021','2122'];
const xCovidStart = x(covidYears[0]) - 18;
const xCovidEnd = x(covidYears[covidYears.length - 1]) + 18;
svg.append('rect')
  .attr('x', xCovidStart).attr('y', chartTop)
  .attr('width', xCovidEnd - xCovidStart)
  .attr('height', chartBottom - chartTop)
  .attr('fill', C.covid_band).attr('opacity', 0.4);

svg.append('text')
  .attr('x', (xCovidStart + xCovidEnd) / 2).attr('y', chartTop + 14)
  .attr('text-anchor', 'middle')
  .attr('font-family', 'ABC Oracle Edu').attr('font-size', 13).attr('font-weight', 500)
  .attr('fill', '#7A1A0E')
  .text('COVID surge');

// Gridlines
const yTicks = y.ticks(8);
yTicks.forEach(t => {{
  svg.append('line')
    .attr('x1', chartLeft).attr('x2', chartRight)
    .attr('y1', y(t)).attr('y2', y(t))
    .attr('stroke', t === 0 ? C.text : C.grid)
    .attr('stroke-width', t === 0 ? 1 : 0.5);
  svg.append('text')
    .attr('x', chartLeft - 8).attr('y', y(t))
    .attr('text-anchor', 'end').attr('dy', '0.32em')
    .attr('font-family', 'ABC Oracle Edu').attr('font-size', 14).attr('font-weight', 300)
    .attr('fill', '#333')
    .text(t === 0 ? '0' : ((t/1000).toFixed(0)) + 'k');
}});

// X-axis labels
P.year_pairs.forEach(yp => {{
  svg.append('line')
    .attr('x1', x(yp)).attr('x2', x(yp))
    .attr('y1', chartBottom).attr('y2', chartBottom + 6)
    .attr('stroke', '#3D3733').attr('stroke-width', 0.5);
  svg.append('text')
    .attr('x', x(yp)).attr('y', chartBottom + 22)
    .attr('text-anchor', 'middle')
    .attr('font-family', 'ABC Oracle Edu').attr('font-size', 13).attr('font-weight', 300)
    .attr('fill', '#333')
    .text(yp.substring(0,2) + '–' + yp.substring(2));
}});

// Lines — each MSA gets a visible line + a wider invisible hit area for easier hover
const line = d3.line()
  .x((_, i) => x(P.year_pairs[i]))
  .y(d => y(d));

const lineGroup = svg.append('g').attr('id', 'lines');
const slug = s => s.replace(/[^a-z0-9]+/gi, '_');

P.series.forEach(s => {{
  const id = slug(s.msa);
  // visible line
  lineGroup.append('path')
    .attr('d', line(s.values))
    .attr('fill', 'none').attr('stroke', s.color)
    .attr('stroke-width', 2.5)
    .attr('opacity', 0.85)
    .attr('class', 'series-line')
    .attr('data-msa', id)
    .attr('style', 'mix-blend-mode: multiply');
  // invisible thick hit area
  lineGroup.append('path')
    .attr('d', line(s.values))
    .attr('fill', 'none').attr('stroke', 'transparent')
    .attr('stroke-width', 18)
    .attr('class', 'series-hit')
    .attr('data-msa', id)
    .style('cursor', 'pointer');
}});

// Endpoint markers — one circle per MSA at the last data point, for visual anchor
P.series.forEach(s => {{
  const id = slug(s.msa);
  const lastIdx = P.year_pairs.length - 1;
  lineGroup.append('circle')
    .attr('cx', x(P.year_pairs[lastIdx])).attr('cy', y(s.values[lastIdx]))
    .attr('r', 3.5).attr('fill', s.color)
    .attr('class', 'series-dot')
    .attr('data-msa', id);
}});

// Inline labels at right edge — stack with greedy nudging
const lastIdx = P.year_pairs.length - 1;
const labelData = P.series.map(s => ({{
  msa: s.msa,
  color: s.color,
  y: y(s.values[lastIdx]),
  v: s.values[lastIdx],
}})).sort((a, b) => a.y - b.y);

// Force-separate by 18px
const minGap = 18;
for (let i = 1; i < labelData.length; i++) {{
  if (labelData[i].y - labelData[i-1].y < minGap) {{
    labelData[i].y = labelData[i-1].y + minGap;
  }}
}}

const labelGroup = svg.append('g').attr('id', 'labels');
labelData.forEach(d => {{
  const id = slug(d.msa);
  labelGroup.append('line')
    .attr('x1', chartRight + 4).attr('x2', chartRight + 14)
    .attr('y1', d.y).attr('y2', d.y)
    .attr('stroke', d.color).attr('stroke-width', 2)
    .attr('class', 'series-label-line')
    .attr('data-msa', id);
  labelGroup.append('text')
    .attr('x', chartRight + 18).attr('y', d.y).attr('dy', '0.32em')
    .attr('font-family', 'ABC Oracle Edu').attr('font-size', 13).attr('font-weight', 500)
    .attr('fill', d.color)
    .attr('class', 'series-label-text')
    .attr('data-msa', id)
    .style('cursor', 'pointer')
    .text(`${{d.msa}}  ${{(d.v/1000).toFixed(0)}}k`);
}});

// Hover interaction — highlight one series, dim the rest
function focusSeries(targetId) {{
  d3.selectAll('.series-line, .series-dot, .series-label-line, .series-label-text')
    .each(function() {{
      const el = d3.select(this);
      const myId = el.attr('data-msa');
      const isTarget = (myId === targetId);
      const isLine = el.classed('series-line');
      const isDot = el.classed('series-dot');
      const isLabLine = el.classed('series-label-line');
      const isLabText = el.classed('series-label-text');
      if (targetId === null) {{
        // restore default
        if (isLine) el.attr('opacity', 0.85).attr('stroke-width', 2.5);
        if (isDot) el.attr('opacity', 1).attr('r', 3.5);
        if (isLabLine) el.attr('opacity', 1).attr('stroke-width', 2);
        if (isLabText) el.attr('opacity', 1).attr('font-weight', 500);
      }} else {{
        if (isLine) el.attr('opacity', isTarget ? 1 : 0.08).attr('stroke-width', isTarget ? 4 : 2.5);
        if (isDot) el.attr('opacity', isTarget ? 1 : 0.15).attr('r', isTarget ? 5 : 3.5);
        if (isLabLine) el.attr('opacity', isTarget ? 1 : 0.2).attr('stroke-width', isTarget ? 3 : 2);
        if (isLabText) el.attr('opacity', isTarget ? 1 : 0.3).attr('font-weight', isTarget ? 700 : 500);
      }}
    }});
}}

d3.selectAll('.series-hit, .series-label-text, .series-dot')
  .on('mouseenter', function() {{
    focusSeries(d3.select(this).attr('data-msa'));
  }})
  .on('mouseleave', function() {{
    focusSeries(null);
  }});

// Source
svg.append('text')
  .attr('x', PAD).attr('y', H - PAD - 16)
  .attr('font-family', 'ABC Oracle Edu').attr('font-size', 13).attr('font-weight', 200)
  .attr('fill', C.text)
  .text('Source: IRS SOI county-to-county migration, tax years 2011-12 through 2022-23 (excl. 2016-17 due to IRS matching-methodology break).');

svg.append('text')
  .attr('x', PAD).attr('y', H - PAD - 0)
  .attr('font-family', 'ABC Oracle Edu').attr('font-size', 13).attr('font-weight', 200)
  .attr('fill', C.subtext)
  .text('Dependents = exemptions − 1.5 × returns (rough proxy assuming ~50% joint filers). Removes most adult-only movers.');
</script>
</body></html>"""

    out = OUTPUTS / "irs_flows.html"
    out.write_text(html)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
