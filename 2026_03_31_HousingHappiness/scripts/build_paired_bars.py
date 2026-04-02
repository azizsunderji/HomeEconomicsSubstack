#!/usr/bin/env python3
"""Build paired bar chart: PTI change vs happiness change for 37 OECD countries."""

import json, os

BASE = "/Users/azizsunderji/Dropbox/Home Economics/2026_03_31_HousingHappiness"
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"

with open(f"{BASE}/data/paired_bar_data.json") as f:
    data = json.load(f)

with open("/tmp/logo_b64_oneline.txt") as f:
    logo_b64 = f.read().strip()

data_json = json.dumps(data)

html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@font-face {{ font-family:'ABC Oracle Edu'; src:url('{FONT_DIR}/ABCOracle-Thin.otf'); font-weight:200; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('{FONT_DIR}/ABCOracle-Light.otf'); font-weight:300; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('{FONT_DIR}/ABCOracle-Regular.otf'); font-weight:400; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('{FONT_DIR}/ABCOracle-Medium.otf'); font-weight:500; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('{FONT_DIR}/ABCOracle-Bold.otf'); font-weight:700; }}
body {{ margin:0; background:#fff; display:flex; justify-content:center; padding:20px 0; }}
</style>
<script src="https://d3js.org/d3.v7.min.js"></script>
</head>
<body>
<script>
const data = {data_json};

const W = 960, H = 987;
const margin = {{ top: 40, right: 40, bottom: 40, left: 40 }};

// Layout
const titleY = 40 + 32;
const subtitleY = titleY + 34;
const chartTop = subtitleY + 50;
const sourceBottomY = H - 40;
const sourceLineH = 18;
const sourceTopY = sourceBottomY - sourceLineH;
const chartBottom = sourceTopY - 45;

// Chart area
const labelWidth = 145;
const chartLeft = margin.left + labelWidth;
const chartRight = W - margin.right;
const chartWidth = chartRight - chartLeft;
const chartMid = chartLeft + chartWidth / 2; // zero line

const barGroupHeight = (chartBottom - chartTop) / data.length;
const barHeight = Math.min(barGroupHeight * 0.35, 9);
const barGap = 2;

// Scales - map both to same pixel range so they're visually comparable
// PTI range: about -60 to +60
// Happiness range: about -1 to +2, but we scale to same pixel width
const ptiMax = 60;
const hapMax = 2.0; // happiness change max for scaling

const halfWidth = chartWidth / 2;

// PTI: pixels per unit
const ptiScale = d3.scaleLinear().domain([-ptiMax, ptiMax]).range([chartLeft, chartRight]);
// Happiness: scaled to same visual width
const hapScale = d3.scaleLinear().domain([-hapMax, hapMax]).range([chartLeft, chartRight]);

const svg = d3.select("body").append("svg")
  .attr("width", W).attr("height", H)
  .attr("viewBox", `0 0 ${{W}} ${{H}}`)
  .style("font-family", "'ABC Oracle Edu', sans-serif");

// Background
svg.append("rect").attr("width", W).attr("height", H).attr("fill", "#F6F7F3");

// Title
svg.append("text").attr("x", margin.left).attr("y", titleY)
  .attr("font-size", 32).attr("font-weight", 500).attr("fill", "#3D3733")
  .text("Housing costs rose most where happiness");
svg.append("text").attr("x", margin.left).attr("y", titleY + 34)
  .attr("font-size", 32).attr("font-weight", 500).attr("fill", "#3D3733")
  .text("fell \\u2014 and where it didn\\u2019t");

// Subtitle
const realSubtitleY = titleY + 34 + 34;
svg.append("text").attr("x", margin.left).attr("y", realSubtitleY)
  .attr("font-size", 23).attr("font-weight", 400).attr("fill", "#7F7570")
  .text("Countries sorted by change in price-to-income index, 2013\\u201315 to 2023\\u201325");

const realChartTop = realSubtitleY + 55;
const realBarGroupHeight = (chartBottom - realChartTop) / data.length;
const realBarHeight = Math.min(realBarGroupHeight * 0.33, 8);

// Zero line
svg.append("line")
  .attr("x1", chartMid).attr("x2", chartMid)
  .attr("y1", realChartTop - 10).attr("y2", chartBottom + 5)
  .attr("stroke", "#3D3733").attr("stroke-width", 0.75);

// Gridlines (vertical, light)
const ptiTicks = [-40, -20, 20, 40];
ptiTicks.forEach(t => {{
  const x = ptiScale(t);
  svg.append("line")
    .attr("x1", x).attr("x2", x)
    .attr("y1", realChartTop - 10).attr("y2", chartBottom + 5)
    .attr("stroke", "#e1e2e3").attr("stroke-width", 0.5);
}});

// Top axis labels (PTI scale)
const ptiAxisTicks = [-60, -40, -20, 0, 20, 40, 60];
ptiAxisTicks.forEach(t => {{
  const x = ptiScale(t);
  svg.append("text")
    .attr("x", x).attr("y", realChartTop - 18)
    .attr("text-anchor", "middle")
    .attr("font-size", 13).attr("font-weight", 300).attr("fill", "#0BB4FF")
    .text(t > 0 ? "+" + t : t);
}});

// Top axis label - placed above left side
svg.append("text")
  .attr("x", chartLeft).attr("y", realChartTop - 32)
  .attr("text-anchor", "start")
  .attr("font-size", 13).attr("font-weight", 400).attr("fill", "#0BB4FF")
  .text("\\u25A0 PTI change");

// Bottom axis labels (Happiness scale)
const hapAxisTicks = [-1.5, -1.0, -0.5, 0, 0.5, 1.0, 1.5];
hapAxisTicks.forEach(t => {{
  const x = hapScale(t);
  if (x >= chartLeft - 5 && x <= chartRight + 5) {{
    svg.append("text")
      .attr("x", x).attr("y", chartBottom + 20)
      .attr("text-anchor", "middle")
      .attr("font-size", 13).attr("font-weight", 300).attr("fill", "#F4743B")
      .text(t > 0 ? "+" + t.toFixed(1) : t.toFixed(1));
  }}
}});

// Bottom axis label - placed above right side
svg.append("text")
  .attr("x", chartRight).attr("y", realChartTop - 32)
  .attr("text-anchor", "end")
  .attr("font-size", 13).attr("font-weight", 400).attr("fill", "#F4743B")
  .text("Happiness change \\u25A0");

// Draw bars for each country
data.forEach((d, i) => {{
  const yCenter = realChartTop + i * realBarGroupHeight + realBarGroupHeight / 2;
  const yPti = yCenter - realBarHeight / 2 - barGap / 2;
  const yHap = yCenter + realBarHeight / 2 + barGap / 2 - realBarHeight;

  // Actually: top bar = PTI, bottom bar = happiness, slightly offset
  const yTop = yCenter - barGap / 2 - realBarHeight;
  const yBot = yCenter + barGap / 2;

  // PTI bar (blue)
  const ptiX0 = ptiScale(0);
  const ptiX1 = ptiScale(d.pti_change);
  svg.append("rect")
    .attr("x", Math.min(ptiX0, ptiX1))
    .attr("y", yTop)
    .attr("width", Math.abs(ptiX1 - ptiX0))
    .attr("height", realBarHeight)
    .attr("fill", "#0BB4FF")
    .attr("opacity", 0.85);

  // Happiness bar (red)
  const hapX0 = hapScale(0);
  const hapX1 = hapScale(d.happiness_change);
  svg.append("rect")
    .attr("x", Math.min(hapX0, hapX1))
    .attr("y", yBot)
    .attr("width", Math.abs(hapX1 - hapX0))
    .attr("height", realBarHeight)
    .attr("fill", "#F4743B")
    .attr("opacity", 0.85);

  // Country label
  svg.append("text")
    .attr("x", margin.left + labelWidth - 8)
    .attr("y", yCenter)
    .attr("text-anchor", "end")
    .attr("dominant-baseline", "central")
    .attr("font-size", 14)
    .attr("font-weight", d.anglo ? 700 : 400)
    .attr("fill", d.anglo ? "#F4743B" : "#3D3733")
    .text(d.country === "Republic of Korea" ? "South Korea" : d.country);
}});

// Legend
const legendX = chartLeft + 10;
const legendY = chartBottom + 32;

svg.append("rect").attr("x", legendX).attr("y", legendY - 8).attr("width", 14).attr("height", 8).attr("fill", "#0BB4FF").attr("opacity", 0.85);
svg.append("text").attr("x", legendX + 18).attr("y", legendY)
  .attr("font-size", 13).attr("font-weight", 400).attr("fill", "#3D3733")
  .attr("dominant-baseline", "auto")
  .text("PTI change (price-to-income index)");

svg.append("rect").attr("x", legendX + 260).attr("y", legendY - 8).attr("width", 14).attr("height", 8).attr("fill", "#F4743B").attr("opacity", 0.85);
svg.append("text").attr("x", legendX + 282).attr("y", legendY)
  .attr("font-size", 13).attr("font-weight", 400).attr("fill", "#3D3733")
  .attr("dominant-baseline", "auto")
  .text("Happiness change (Cantril ladder)");

// Source
svg.append("text")
  .attr("x", margin.left).attr("y", sourceBottomY)
  .attr("font-size", 15).attr("font-weight", 200).attr("fill", "#3D3733")
  .text("Source: OECD Analytical House Prices, World Happiness Report 2026");

// Logo
svg.append("image")
  .attr("x", chartRight - 130).attr("y", sourceBottomY - 22)
  .attr("width", 130)
  .attr("opacity", 0.6)
  .attr("href", "data:image/png;base64,{logo_b64}");

</script>
</body>
</html>"""

outpath = f"{BASE}/outputs/paired_bars_pti_vs_happiness.html"
with open(outpath, "w") as f:
    f.write(html)
print(f"Written to {outpath}")
