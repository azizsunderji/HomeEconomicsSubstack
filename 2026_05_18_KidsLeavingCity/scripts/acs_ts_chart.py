"""
ACS time series chart — annual outflow of children from MSA inner counties.
Each YEAR = end year of a 5-year ACS PUMS window. Y-axis = kids leaving inner
counties per year (gross). Hover to highlight.
"""
from __future__ import annotations
from pathlib import Path
import json
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OUTPUTS = PROJECT / "outputs"

COLORS = {
    "bg": "#F6F7F3", "text": "#3D3733", "subtext": "#7F7570", "grid": "#e1e2e3",
    "covid_band": "#FBCAB5",
    "New York": "#0BB4FF", "Los Angeles": "#F4743B", "Chicago": "#67A275",
    "Houston": "#FEC439", "Dallas": "#3F6E4B", "Atlanta": "#A32515",
    "Washington": "#7A1A0E", "Philadelphia": "#005C99",
    "Phoenix": "#003D66", "Austin": "#C4301C", "Charlotte": "#8FC19E",
}


def short(msa: str) -> str:
    return msa.split(",")[0].split("-")[0].strip()


def main():
    d = pd.read_csv(DATA / "acs_kid_migration_ts.csv")
    d["msa_short"] = d["msa"].apply(short)
    d = d.sort_values(["msa_short", "YEAR"])

    msas = list(d["msa_short"].unique())
    years = [int(y) for y in sorted(d["YEAR"].unique())]

    series = []
    for m in msas:
        sub = d[d["msa_short"] == m].set_index("YEAR").reindex(years)
        series.append({
            "msa": m,
            "values": [int(v) if pd.notna(v) else 0 for v in sub["kids_leaving_inner"]],
            "color": COLORS.get(m, "#999"),
        })

    payload = {"years": years, "series": series}
    js = json.dumps(payload)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Children leaving city centers, ACS 5-year PUMS</title>
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

svg.append('text').attr('x', PAD).attr('y', PAD + 32)
  .attr('font-family', 'ABC Oracle Edu').attr('font-size', 30).attr('font-weight', 500)
  .attr('fill', C.text)
  .text('Children leaving inner-city counties, per year');
svg.append('text').attr('x', PAD).attr('y', PAD + 32 + 30)
  .attr('font-family', 'ABC Oracle Edu').attr('font-size', 18).attr('font-weight', 400)
  .attr('fill', C.subtext)
  .text('Kids under 18 who lived in an MSA s central county/counties 1 year before the survey. ACS 5-year PUMS (each point = 5-year window ending in that year).');

const chartLeft = 100, chartRight = W - PAD - 230;
const chartTop = PAD + 32 + 30 + 50;
const chartBottom = H - PAD - 70;
const x = d3.scalePoint().domain(P.years).range([chartLeft, chartRight]).padding(0.5);
const ymax = d3.max(P.series.flatMap(s => s.values));
const y = d3.scaleLinear().domain([0, ymax * 1.05]).range([chartBottom, chartTop]);

// COVID shading — 5-year windows that cover the pandemic substantially: 2020,2021,2022
const covidYears = P.years.filter(y => y >= 2020 && y <= 2022);
if (covidYears.length) {{
  const xs = x(covidYears[0]) - 18, xe = x(covidYears[covidYears.length-1]) + 18;
  svg.append('rect')
    .attr('x', xs).attr('y', chartTop)
    .attr('width', xe - xs).attr('height', chartBottom - chartTop)
    .attr('fill', C.covid_band).attr('opacity', 0.4);
  svg.append('text').attr('x', (xs+xe)/2).attr('y', chartTop + 14).attr('text-anchor', 'middle')
    .attr('font-family', 'ABC Oracle Edu').attr('font-size', 13).attr('font-weight', 500)
    .attr('fill', '#7A1A0E').text('COVID windows');
}}

const yTicks = y.ticks(8);
yTicks.forEach(t => {{
  svg.append('line').attr('x1', chartLeft).attr('x2', chartRight)
    .attr('y1', y(t)).attr('y2', y(t))
    .attr('stroke', t === 0 ? C.text : C.grid).attr('stroke-width', t === 0 ? 1 : 0.5);
  svg.append('text').attr('x', chartLeft - 8).attr('y', y(t))
    .attr('text-anchor', 'end').attr('dy', '0.32em')
    .attr('font-family', 'ABC Oracle Edu').attr('font-size', 14).attr('font-weight', 300)
    .attr('fill', '#333').text(t === 0 ? '0' : (t/1000).toFixed(0) + 'k');
}});
P.years.forEach(yr => {{
  svg.append('line').attr('x1', x(yr)).attr('x2', x(yr))
    .attr('y1', chartBottom).attr('y2', chartBottom + 6)
    .attr('stroke', '#3D3733').attr('stroke-width', 0.5);
  svg.append('text').attr('x', x(yr)).attr('y', chartBottom + 22).attr('text-anchor', 'middle')
    .attr('font-family', 'ABC Oracle Edu').attr('font-size', 13).attr('font-weight', 300)
    .attr('fill', '#333').text(yr);
}});

const line = d3.line().x((_, i) => x(P.years[i])).y(d => y(d));
const lineGroup = svg.append('g').attr('id', 'lines');
const slug = s => s.replace(/[^a-z0-9]+/gi, '_');

P.series.forEach(s => {{
  const id = slug(s.msa);
  lineGroup.append('path').attr('d', line(s.values))
    .attr('fill', 'none').attr('stroke', s.color).attr('stroke-width', 2.5).attr('opacity', 0.85)
    .attr('class', 'series-line').attr('data-msa', id)
    .attr('style', 'mix-blend-mode: multiply');
  lineGroup.append('path').attr('d', line(s.values))
    .attr('fill', 'none').attr('stroke', 'transparent').attr('stroke-width', 18)
    .attr('class', 'series-hit').attr('data-msa', id).style('cursor', 'pointer');
}});

const lastIdx = P.years.length - 1;
P.series.forEach(s => {{
  lineGroup.append('circle').attr('cx', x(P.years[lastIdx])).attr('cy', y(s.values[lastIdx]))
    .attr('r', 3.5).attr('fill', s.color)
    .attr('class', 'series-dot').attr('data-msa', slug(s.msa));
}});

const labelData = P.series.map(s => ({{
  msa: s.msa, color: s.color, y: y(s.values[lastIdx]), v: s.values[lastIdx]
}})).sort((a,b) => a.y - b.y);
const minGap = 18;
for (let i = 1; i < labelData.length; i++) {{
  if (labelData[i].y - labelData[i-1].y < minGap) labelData[i].y = labelData[i-1].y + minGap;
}}
const labelGroup = svg.append('g').attr('id', 'labels');
labelData.forEach(d => {{
  const id = slug(d.msa);
  labelGroup.append('line').attr('x1', chartRight + 4).attr('x2', chartRight + 14)
    .attr('y1', d.y).attr('y2', d.y).attr('stroke', d.color).attr('stroke-width', 2)
    .attr('class', 'series-label-line').attr('data-msa', id);
  labelGroup.append('text').attr('x', chartRight + 18).attr('y', d.y).attr('dy', '0.32em')
    .attr('font-family', 'ABC Oracle Edu').attr('font-size', 13).attr('font-weight', 500)
    .attr('fill', d.color).attr('class', 'series-label-text').attr('data-msa', id)
    .style('cursor', 'pointer').text(`${{d.msa}}  ${{(d.v/1000).toFixed(0)}}k`);
}});

function focus(targetId) {{
  d3.selectAll('.series-line, .series-dot, .series-label-line, .series-label-text').each(function() {{
    const el = d3.select(this);
    const myId = el.attr('data-msa');
    const isT = myId === targetId;
    const isLine = el.classed('series-line');
    const isDot = el.classed('series-dot');
    const isLabLine = el.classed('series-label-line');
    const isLabText = el.classed('series-label-text');
    if (targetId === null) {{
      if (isLine) el.attr('opacity', 0.85).attr('stroke-width', 2.5);
      if (isDot) el.attr('opacity', 1).attr('r', 3.5);
      if (isLabLine) el.attr('opacity', 1).attr('stroke-width', 2);
      if (isLabText) el.attr('opacity', 1).attr('font-weight', 500);
    }} else {{
      if (isLine) el.attr('opacity', isT ? 1 : 0.08).attr('stroke-width', isT ? 4 : 2.5);
      if (isDot) el.attr('opacity', isT ? 1 : 0.15).attr('r', isT ? 5 : 3.5);
      if (isLabLine) el.attr('opacity', isT ? 1 : 0.2).attr('stroke-width', isT ? 3 : 2);
      if (isLabText) el.attr('opacity', isT ? 1 : 0.3).attr('font-weight', isT ? 700 : 500);
    }}
  }});
}}
d3.selectAll('.series-hit, .series-label-text, .series-dot')
  .on('mouseenter', function() {{ focus(d3.select(this).attr('data-msa')); }})
  .on('mouseleave', function() {{ focus(null); }});

svg.append('text').attr('x', PAD).attr('y', H - PAD - 16)
  .attr('font-family', 'ABC Oracle Edu').attr('font-size', 13).attr('font-weight', 200).attr('fill', C.text)
  .text('Source: IPUMS ACS 5-year PUMS. "Kids leaving" = under-18s who lived in an MSA s inner county/counties one year before the survey and moved out-of-county.');
svg.append('text').attr('x', PAD).attr('y', H - PAD - 0)
  .attr('font-family', 'ABC Oracle Edu').attr('font-size', 13).attr('font-weight', 200).attr('fill', C.subtext)
  .text('Each year = endpoint of a 5-year window (e.g., 2023 = 2019-2023). Values are 5-year annual-average kid outflows.');
</script>
</body></html>"""
    (OUTPUTS / "acs_kid_outflow.html").write_text(html)
    print(f"Wrote {OUTPUTS / 'acs_kid_outflow.html'}")


if __name__ == "__main__":
    main()
