#!/usr/bin/env python3
"""Build the Anglophone vs Rest trends chart (two stacked panels)."""

import pandas as pd
import base64
import json
from pathlib import Path

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_03_31_HousingHappiness")
FONT_DIR = Path("/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop")
LOGO_PATH = Path("/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/HomeEconomics-Logo-versions/HE-Large-Black.png")

# ── ISO3 → country name mapping ──
ISO3_MAP = {
    "AUS": "Australia", "AUT": "Austria", "BEL": "Belgium", "CAN": "Canada",
    "CHE": "Switzerland", "DEU": "Germany", "DNK": "Denmark", "ESP": "Spain",
    "FIN": "Finland", "FRA": "France", "GBR": "United Kingdom", "IRL": "Ireland",
    "ITA": "Italy", "JPN": "Japan", "KOR": "South Korea", "MEX": "Mexico",
    "NOR": "Norway", "NZL": "New Zealand", "PRT": "Portugal", "SWE": "Sweden",
    "USA": "United States",
}
ANGLOPHONE = {"United States", "United Kingdom", "Canada", "Australia", "New Zealand", "Ireland"}

# WHR country name mapping
WHR_NAME_MAP = {"Republic of Korea": "South Korea"}

# ── 1. Load OECD PTI data ──
oecd_csv = PROJECT.parent / "GlobalHousingCrisis" / "OECD.ECO.MPD,DSD_AN_HOUSE_PRICES@DF_HOUSE_PRICES,+DNK+FIN+FRA+DEU+IRL+ITA+JPN+KOR+MEX+NOR+PRT+ESP+SWE+CHE+GBR+AUT+BEL+AUS+CAN+NZL+EA+USA+OECD.Q.HPI_YDH+RHP.IX.csv"
oecd = pd.read_csv(oecd_csv)

# Filter to HPI_YDH only, individual countries (not EA/OECD aggregates)
oecd = oecd[(oecd["MEASURE"] == "HPI_YDH") & (oecd["REF_AREA"].isin(ISO3_MAP.keys()))].copy()
oecd["year"] = oecd["TIME_PERIOD"].str[:4].astype(int)
oecd = oecd[(oecd["year"] >= 2011) & (oecd["year"] <= 2025)].copy()
oecd["country"] = oecd["REF_AREA"].map(ISO3_MAP)
oecd["anglophone"] = oecd["country"].isin(ANGLOPHONE)

# Annual average by country
pti_annual = oecd.groupby(["country", "year", "anglophone"])["OBS_VALUE"].mean().reset_index()

# Group means
pti_group = pti_annual.groupby(["anglophone", "year"])["OBS_VALUE"].mean().reset_index()
pti_group.columns = ["anglophone", "year", "pti"]

print("PTI data years:", sorted(pti_group["year"].unique()))
print("PTI countries (anglo):", sorted(pti_annual[pti_annual["anglophone"]]["country"].unique()))
print("PTI countries (other):", sorted(pti_annual[~pti_annual["anglophone"]]["country"].unique()))

# ── 2. Load happiness panel (2011-2023) ──
panel = pd.read_csv(PROJECT / "data" / "merged_panel.csv")
happy_panel = panel[["country", "year", "cantril_ladder_score", "anglophone"]].dropna(subset=["cantril_ladder_score"])
happy_panel = happy_panel[(happy_panel["year"] >= 2011) & (happy_panel["year"] <= 2023)]

# Map country names to match
happy_group = happy_panel.groupby(["anglophone", "year"])["cantril_ladder_score"].mean().reset_index()
happy_group.columns = ["anglophone", "year", "happiness"]

print("\nHappiness panel years:", sorted(happy_group["year"].unique()))

# ── 3. Load WHR 2026 for 2023-25 average ──
whr = pd.read_csv(PROJECT / "data" / "whr2026_rankings.csv")
whr["country"] = whr["country"].replace(WHR_NAME_MAP)

# Filter to our countries
our_countries = set(ISO3_MAP.values())
whr_ours = whr[whr["country"].isin(our_countries)].copy()
whr_ours["anglophone"] = whr_ours["country"].isin(ANGLOPHONE)

print("\nWHR matched countries:", sorted(whr_ours["country"].unique()))
print("WHR unmatched:", our_countries - set(whr_ours["country"].unique()))

whr_group = whr_ours.groupby("anglophone")["happiness_score"].mean().reset_index()
whr_group.columns = ["anglophone", "happiness"]
whr_group["year"] = 2024  # Plot position for the 2023-25 avg

print("\nWHR group means:")
print(whr_group)

# Combine happiness data
happy_all = pd.concat([happy_group, whr_group[["anglophone", "year", "happiness"]]], ignore_index=True)
happy_all = happy_all.sort_values(["anglophone", "year"])

# ── 4. Prepare JSON data for D3 ──
def series_to_json(df, val_col, group_col="anglophone"):
    result = {}
    for ang in [True, False]:
        sub = df[df[group_col] == ang].sort_values("year")
        label = "Anglophone" if ang else "Other OECD"
        result[label] = [{"year": int(r["year"]), "value": round(float(r[val_col]), 2)} for _, r in sub.iterrows()]
    return result

pti_json = series_to_json(pti_group, "pti")
happy_json = series_to_json(happy_all, "happiness")

print("\nPTI Anglophone:", pti_json["Anglophone"])
print("PTI Other:", pti_json["Other OECD"])
print("Happy Anglophone:", happy_json["Anglophone"])
print("Happy Other:", happy_json["Other OECD"])

# ── 5. Encode fonts as base64 ──
font_files = {
    200: "ABCOracle-Thin.otf",
    300: "ABCOracle-Light.otf",
    400: "ABCOracle-Regular.otf",
    500: "ABCOracle-Medium.otf",
    700: "ABCOracle-Bold.otf",
}

font_faces = []
for weight, fname in font_files.items():
    fpath = FONT_DIR / fname
    b64 = base64.b64encode(fpath.read_bytes()).decode()
    font_faces.append(f"""@font-face {{
  font-family: 'ABC Oracle Edu';
  src: url('data:font/otf;base64,{b64}') format('opentype');
  font-weight: {weight};
  font-style: normal;
}}""")

font_css = "\n".join(font_faces)

# ── 6. Encode logo as base64 ──
logo_b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode()

# ── 7. Build the HTML ──
html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{font_css}
body {{
  margin: 0;
  background: #FFFFFF;
  display: flex;
  justify-content: center;
  padding: 20px;
}}
svg text {{
  font-family: 'ABC Oracle Edu', sans-serif;
}}
</style>
</head>
<body>
<svg id="chart" width="960" height="987" viewBox="0 0 960 987" xmlns="http://www.w3.org/2000/svg">
  <rect width="960" height="987" fill="#F6F7F3"/>
</svg>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const ptiData = {json.dumps(pti_json)};
const happyData = {json.dumps(happy_json)};

const W = 960, H = 987;
const buf = 40;
const gridLeft = buf;
const labelSpace = 120; // reserve space for inline end-labels
const gridRight = W - buf - labelSpace;
const gridW = gridRight - gridLeft;

// Layout
const titleY = 40 + 32;
const subtitleY = titleY + 34;
const chartTop = subtitleY + 75;
const sourceLineH = 18;
const sourceLines = 2;
const sourceBlockH = sourceLines * sourceLineH;
const sourceBottom = H - buf;
const sourceTop = sourceBottom - sourceBlockH;
const xAxisLabelH = 45;
const gapXtoSource = 45;
const chartBottom = sourceTop - gapXtoSource - xAxisLabelH;

// Two panels: split vertical space
const panelGap = 60;
const panelH = (chartBottom - chartTop - panelGap) / 2;
const panel1Top = chartTop;
const panel1Bottom = panel1Top + panelH;
const panel2Top = panel1Bottom + panelGap;
const panel2Bottom = panel2Top + panelH;

const svg = d3.select("#chart");

// Title
svg.append("text")
  .attr("x", gridLeft).attr("y", titleY)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 32).attr("font-weight", 500)
  .attr("fill", "#3D3733")
  .text("The Anglophone divergence");

// Subtitle
svg.append("text")
  .attr("x", gridLeft).attr("y", subtitleY)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 23).attr("font-weight", 400)
  .attr("fill", "#7F7570")
  .text("Average happiness and price-to-income index, Anglophone vs other OECD countries");

const colors = {{ "Anglophone": "#F4743B", "Other OECD": "#0BB4FF" }};

// X scale (shared): 2011-2025
const xAll = d3.scaleLinear().domain([2011, 2025]).range([gridLeft, gridRight]);

function formatYear(y) {{
  if (y === 2011) return "2011";
  return "\\u2018" + String(y).slice(2);
}}

function drawPanel(panelTop, panelBottom, data, panelLabel, yDomain, yFormat, isHappiness) {{
  const yScale = d3.scaleLinear().domain(yDomain).range([panelBottom, panelTop]);

  // Panel sub-header
  svg.append("text")
    .attr("x", gridLeft).attr("y", panelTop - 14)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", 18).attr("font-weight", 500)
    .attr("fill", "#3D3733")
    .text(panelLabel);

  // Grid lines
  const yTicks = yScale.ticks(5);
  yTicks.forEach((t, i) => {{
    svg.append("line")
      .attr("x1", gridLeft).attr("x2", gridRight)
      .attr("y1", yScale(t)).attr("y2", yScale(t))
      .attr("stroke", "#e1e2e3").attr("stroke-width", 1);
  }});

  // Y-axis labels
  yTicks.forEach((t, i) => {{
    svg.append("text")
      .attr("x", gridLeft).attr("y", yScale(t))
      .attr("dy", "-0.35em")
      .attr("font-family", "ABC Oracle Edu").attr("font-size", 22).attr("font-weight", 300)
      .attr("fill", "#333").attr("text-anchor", "start")
      .text(yFormat(t, i === yTicks.length - 1));
  }});

  // Lines
  const line = d3.line()
    .x(d => xAll(d.year))
    .y(d => yScale(d.value))
    .curve(d3.curveMonotoneX);

  for (const [label, pts] of Object.entries(data)) {{
    svg.append("path")
      .datum(pts)
      .attr("d", line)
      .attr("fill", "none")
      .attr("stroke", colors[label])
      .attr("stroke-width", 2.5)
      .style("mix-blend-mode", "multiply");

    // End label
    const last = pts[pts.length - 1];
    svg.append("text")
      .attr("x", xAll(last.year) + 8).attr("y", yScale(last.value))
      .attr("dy", "0.35em")
      .attr("font-family", "ABC Oracle Edu").attr("font-size", 16).attr("font-weight", 500)
      .attr("fill", colors[label])
      .style("paint-order", "stroke")
      .attr("stroke", "#F6F7F3").attr("stroke-width", 4).attr("stroke-linejoin", "round")
      .text(label);
  }}
}}

// Happiness panel
const happyValues = [...happyData["Anglophone"], ...happyData["Other OECD"]].map(d => d.value);
const happyMin = Math.floor(d3.min(happyValues) * 10) / 10;
const happyMax = Math.ceil(d3.max(happyValues) * 10) / 10;
const happyPad = (happyMax - happyMin) * 0.1;

drawPanel(panel1Top, panel1Bottom, happyData,
  "Happiness (Cantril ladder)",
  [happyMin - happyPad, happyMax + happyPad],
  (v, isTop) => {{
    const s = v.toFixed(1);
    return isTop ? s + " pts" : s;
  }},
  true
);

// PTI panel
const ptiValues = [...ptiData["Anglophone"], ...ptiData["Other OECD"]].map(d => d.value);
const ptiMin = Math.floor(d3.min(ptiValues));
const ptiMax = Math.ceil(d3.max(ptiValues));
const ptiPad = (ptiMax - ptiMin) * 0.1;

drawPanel(panel2Top, panel2Bottom, ptiData,
  "Price-to-income index (2015 = 100)",
  [ptiMin - ptiPad, ptiMax + ptiPad],
  (v, isTop) => {{
    const s = Math.round(v).toString();
    return isTop ? s + " idx" : s;
  }},
  false
);

// X-axis ticks and labels (shared, at bottom of panel 2)
const xTicks = d3.range(2011, 2026);
xTicks.forEach(y => {{
  // Tick
  svg.append("line")
    .attr("x1", xAll(y)).attr("x2", xAll(y))
    .attr("y1", panel2Bottom).attr("y2", panel2Bottom + 12)
    .attr("stroke", "#3D3733").attr("stroke-width", 0.5);
  // Label
  let label = formatYear(y);
  // Special: 2024 shows as '24*
  if (y === 2024) label = "\\u2018" + "24*";
  svg.append("text")
    .attr("x", xAll(y)).attr("y", panel2Bottom + 12)
    .attr("dy", "1.5em").attr("text-anchor", "middle")
    .attr("font-family", "ABC Oracle Edu").attr("font-size", 22).attr("font-weight", 300)
    .attr("fill", "#333")
    .text(label);
}});

// Source
const sourceText = svg.append("text")
  .attr("x", gridLeft).attr("y", sourceTop)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 15).attr("font-weight", 200)
  .attr("fill", "#3D3733");
sourceText.append("tspan")
  .attr("x", gridLeft)
  .text("Source: OECD Analytical House Prices, World Happiness Report 2026.");
sourceText.append("tspan")
  .attr("x", gridLeft).attr("dy", sourceLineH)
  .text("*Happiness 2024 point = 2023\\u20132025 average.");

// Logo
svg.append("image")
  .attr("xlink:href", "data:image/png;base64,{logo_b64}")
  .attr("width", 130)
  .attr("x", W - buf - 130)
  .attr("y", sourceTop - 5)
  .attr("height", sourceBlockH + 10)
  .attr("opacity", 0.6)
  .attr("preserveAspectRatio", "xMidYMid meet");

</script>
</body>
</html>"""

out_path = PROJECT / "outputs" / "anglophone_vs_rest_trends.html"
out_path.write_text(html)
print(f"\nWrote {out_path}")
