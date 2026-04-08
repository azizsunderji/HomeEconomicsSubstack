#!/usr/bin/env python3
"""Charts: which countries saw the biggest immigration increases?

1. Horizontal bar chart: change in net migration rate, all 30 countries
2. Line chart: immigration rate time series for top movers + Anglosphere
"""

import pandas as pd
import numpy as np
import json, base64, os
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
OUT = Path(__file__).parent.parent / "outputs"

BLACK = "#3D3733"
BG = "#F6F7F3"
BLUE = "#0BB4FF"
RED = "#F4743B"
GREEN = "#67A275"
YELLOW = "#FEC439"
SUBTITLE_COLOR = "#7F7570"
GRID_COLOR = "#e1e2e3"
LIGHT_RED = "#FBCAB5"

FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
LOGO_PATH = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/HomeEconomics-Logo-versions/HE-Large-Black.png"

ANGLOPHONE = ["USA", "CAN", "GBR", "AUS", "NZL", "IRL"]


def load_data():
    df = pd.read_csv(DATA / "oecd_immigration_net.csv")
    return df


def get_brand_assets():
    logo_b64 = ""
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()

    font_faces = ""
    for wname, wnum in [("Thin", 200), ("Light", 300), ("Regular", 400), ("Medium", 500), ("Bold", 700)]:
        otf = f"{FONT_DIR}/ABCOracle-{wname}.otf"
        if os.path.exists(otf):
            with open(otf, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            font_faces += f"@font-face {{ font-family:'ABC Oracle Edu'; src:url('data:font/otf;base64,{b64}'); font-weight:{wnum}; }}\n"
    return logo_b64, font_faces


def bar_chart(df):
    """Horizontal bar chart: change in immigration rate, all 30 countries."""
    early = df[df["year"].between(2013, 2015)].groupby("iso3")["rate_per1000"].mean()
    late = df[df["year"].between(2022, 2024)].groupby("iso3")["rate_per1000"].mean()
    change = (late - early).dropna().sort_values(ascending=True)

    names = df.drop_duplicates("iso3").set_index("iso3")["country"].to_dict()

    records = []
    for iso3, chg in change.items():
        records.append({
            "iso3": iso3,
            "country": names.get(iso3, iso3),
            "change": round(float(chg), 1),
            "anglo": iso3 in ANGLOPHONE,
        })

    data_json = json.dumps(records)
    logo_b64, font_faces = get_brand_assets()

    n = len(records)
    barH = 24
    gap = 4
    chartHeight = n * (barH + gap)
    H = 200 + chartHeight + 80

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
{font_faces}
body {{ margin:0; background:#FFFFFF; }}
svg {{ display:block; margin:0 auto; }}
</style>
<script src="d3.v7.min.js"></script>
</head><body>
<script>
const W = 960, H = {H};
const margin = {{top: 40, right: 40, bottom: 40, left: 40}};
const titleY = 72, subtitleY = 106;
const chartTop = subtitleY + 60;
const chartLeft = margin.left + 140;
const chartRight = W - margin.right - 60;
const barH = {barH}, gap = {gap};

const data = {data_json};

const svg = d3.select("body").append("svg")
  .attr("width", W).attr("height", H).attr("viewBox", `0 0 ${{W}} ${{H}}`);

svg.append("rect").attr("width", W).attr("height", H).attr("fill", "{BG}");

svg.append("text").attr("x", margin.left).attr("y", titleY)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 32).attr("font-weight", 500)
  .attr("fill", "{BLACK}").text("The immigration surge, by country");

svg.append("text").attr("x", margin.left).attr("y", subtitleY)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 23).attr("font-weight", 400)
  .attr("fill", "{SUBTITLE_COLOR}").text("Change in net migration rate per 1,000 population, 2013\u201315 avg \u2192 2022\u201324 avg");

const xMin = d3.min(data, d => d.change);
const xMax = d3.max(data, d => d.change);
const xPad = Math.max(Math.abs(xMin), xMax) * 0.08;

const x = d3.scaleLinear()
  .domain([Math.min(xMin - xPad, -5), xMax + xPad])
  .range([chartLeft, chartRight]);

// Gridlines
const xTicks = x.ticks(8);
xTicks.forEach(t => {{
  svg.append("line")
    .attr("x1", x(t)).attr("x2", x(t))
    .attr("y1", chartTop - 5).attr("y2", chartTop + data.length * (barH + gap))
    .attr("stroke", "{GRID_COLOR}").attr("stroke-width", 0.5);
}});

// Zero line
svg.append("line")
  .attr("x1", x(0)).attr("x2", x(0))
  .attr("y1", chartTop - 5).attr("y2", chartTop + data.length * (barH + gap))
  .attr("stroke", "{BLACK}").attr("stroke-width", 1).attr("opacity", 0.4);

// X-axis labels at top
xTicks.forEach(t => {{
  svg.append("text").attr("x", x(t)).attr("y", chartTop - 12)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", 14).attr("font-weight", 300)
    .attr("fill", "#999").attr("text-anchor", "middle")
    .text((t > 0 ? "+" : "") + t.toFixed(0));
}});

// Bars
data.forEach((d, i) => {{
  const y = chartTop + i * (barH + gap);
  const barWidth = Math.abs(x(d.change) - x(0));
  const barX = d.change >= 0 ? x(0) : x(d.change);
  const color = d.anglo ? "{RED}" : (d.change >= 0 ? "{BLUE}" : "#999");
  const opacity = d.anglo ? 0.85 : 0.6;

  svg.append("rect")
    .attr("x", barX).attr("y", y)
    .attr("width", barWidth).attr("height", barH)
    .attr("fill", color).attr("opacity", opacity)
    .attr("rx", 2);

  // Country label
  svg.append("text")
    .attr("x", chartLeft - 8).attr("y", y + barH / 2 + 5)
    .attr("font-family", "ABC Oracle Edu")
    .attr("font-size", d.anglo ? 14 : 13)
    .attr("font-weight", d.anglo ? 500 : 300)
    .attr("fill", d.anglo ? "{BLACK}" : "#666")
    .attr("text-anchor", "end")
    .text(d.country);

  // Value label
  const valX = d.change >= 0 ? x(d.change) + 5 : x(d.change) - 5;
  const anchor = d.change >= 0 ? "start" : "end";
  svg.append("text")
    .attr("x", valX).attr("y", y + barH / 2 + 5)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", 12).attr("font-weight", 400)
    .attr("fill", "{BLACK}").attr("text-anchor", anchor)
    .text((d.change > 0 ? "+" : "") + d.change.toFixed(1));
}});

// Source
const sourceY = H - 45;
svg.append("text").attr("x", margin.left).attr("y", sourceY)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 15).attr("font-weight", 200)
  .attr("fill", "{BLACK}")
  .text("Sources: CBO (US), Statistics Canada, ONS (UK), ABS (AUS), Stats NZ, Eurostat CNMIGRAT, national stats offices");

svg.append("image")
  .attr("xlink:href", "data:image/png;base64,{logo_b64}")
  .attr("width", 130).attr("opacity", 0.6)
  .attr("x", W - 40 - 130).attr("y", sourceY - 15);

</script></body></html>"""

    with open(OUT / "bar_immigration_change.html", "w") as f:
        f.write(html)
    print("Saved bar_immigration_change.html")


def line_chart(df):
    """Line chart: immigration rate over time for top movers + Anglosphere."""
    # Countries to show: top 5 + all Anglosphere
    show = ["LTU", "ESP", "PRT", "CAN", "EST", "USA", "GBR", "AUS", "NZL", "IRL"]
    show = list(dict.fromkeys(show))  # dedupe preserving order

    names = df.drop_duplicates("iso3").set_index("iso3")["country"].to_dict()

    series = []
    for iso3 in show:
        sub = df[df["iso3"] == iso3].sort_values("year")
        pts = [{"year": int(r["year"]), "rate": round(float(r["rate_per1000"]), 1)}
               for _, r in sub.iterrows() if pd.notna(r["rate_per1000"])]
        series.append({
            "iso3": iso3,
            "country": names.get(iso3, iso3),
            "anglo": iso3 in ANGLOPHONE,
            "points": pts,
        })

    data_json = json.dumps(series)
    logo_b64, font_faces = get_brand_assets()

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
{font_faces}
body {{ margin:0; background:#FFFFFF; }}
svg {{ display:block; margin:0 auto; }}
</style>
<script src="d3.v7.min.js"></script>
</head><body>
<script>
const W = 960, H = 700;
const margin = {{top: 40, right: 160, bottom: 40, left: 40}};
const titleY = 72, subtitleY = 106;
const chartTop = subtitleY + 75;
const chartLeft = margin.left + 50;
const chartRight = W - margin.right;
const sourceY = H - 55;
const chartBottom = sourceY - 70;

const data = {data_json};

const svg = d3.select("body").append("svg")
  .attr("width", W).attr("height", H).attr("viewBox", `0 0 ${{W}} ${{H}}`);

svg.append("rect").attr("width", W).attr("height", H).attr("fill", "{BG}");

svg.append("text").attr("x", margin.left).attr("y", titleY)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 32).attr("font-weight", 500)
  .attr("fill", "{BLACK}").text("Immigration surges and reversals");

svg.append("text").attr("x", margin.left).attr("y", subtitleY)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 23).attr("font-weight", 400)
  .attr("fill", "{SUBTITLE_COLOR}").text("Net migration rate per 1,000 population, top movers and Anglosphere");

const allPts = data.flatMap(s => s.points);
const x = d3.scaleLinear().domain([2000, 2025]).range([chartLeft, chartRight]);
const yMin = Math.min(-5, d3.min(allPts, d => d.rate));
const yMax = d3.max(allPts, d => d.rate);
const y = d3.scaleLinear().domain([yMin - 1, yMax + 2]).range([chartBottom, chartTop]);

// Grid
const yTicks = y.ticks(8);
yTicks.forEach((t, i) => {{
  svg.append("line").attr("x1", margin.left).attr("x2", chartRight)
    .attr("y1", y(t)).attr("y2", y(t))
    .attr("stroke", "{GRID_COLOR}").attr("stroke-width", 1);
  let label = t.toFixed(0);
  if (i === yTicks.length - 1) label += "/1,000";
  svg.append("text").attr("x", margin.left).attr("y", y(t) - 6)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", 22).attr("font-weight", 300)
    .attr("fill", "#333").attr("text-anchor", "start").text(label);
}});

// Zero line
svg.append("line").attr("x1", margin.left).attr("x2", chartRight)
  .attr("y1", y(0)).attr("y2", y(0))
  .attr("stroke", "{BLACK}").attr("stroke-width", 1.5).attr("opacity", 0.3);

// X-axis
[2000, 2005, 2010, 2015, 2020, 2025].forEach(yr => {{
  svg.append("line").attr("x1", x(yr)).attr("x2", x(yr))
    .attr("y1", chartBottom).attr("y2", chartBottom + 12)
    .attr("stroke", "{BLACK}").attr("stroke-width", 0.5);
  svg.append("text").attr("x", x(yr)).attr("y", chartBottom + 37)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", 22).attr("font-weight", 300)
    .attr("fill", "#333").attr("text-anchor", "middle").text(yr);
}});

// Color assignments
const angloColors = {{
  "USA": "{RED}", "CAN": "#C4301C", "GBR": "#A32515",
  "AUS": "#F4743B", "NZL": "#FBCAB5", "IRL": "#7A1A0E"
}};
const otherColors = ["{BLUE}", "{GREEN}", "#0077CC", "#7DD4FF", "#BCE8FF"];
let otherIdx = 0;

const line = d3.line().x(d => x(d.year)).y(d => y(d.rate));

data.forEach(s => {{
  const color = s.anglo ? (angloColors[s.iso3] || "{RED}") : otherColors[otherIdx++ % otherColors.length];
  const width = s.anglo ? 2.5 : 2;
  const opacity = s.anglo ? 1 : 0.7;

  svg.append("path").datum(s.points)
    .attr("d", line).attr("fill", "none")
    .attr("stroke", color).attr("stroke-width", width)
    .attr("opacity", opacity);

  // End label
  const last = s.points[s.points.length - 1];
  svg.append("text")
    .attr("x", x(last.year) + 6).attr("y", y(last.rate) + 4)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", 13).attr("font-weight", s.anglo ? 500 : 300)
    .attr("fill", color).text(s.country);
}});

// Source
svg.append("text").attr("x", margin.left).attr("y", sourceY)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 15).attr("font-weight", 200)
  .attr("fill", "{BLACK}")
  .text("Sources: CBO, Statistics Canada, ONS, ABS, Stats NZ, Eurostat CNMIGRAT, national stats offices");
svg.append("image")
  .attr("xlink:href", "data:image/png;base64,{logo_b64}")
  .attr("width", 130).attr("opacity", 0.6)
  .attr("x", W - margin.right + 30 - 130).attr("y", sourceY - 5);

</script></body></html>"""

    with open(OUT / "line_immigration_surges.html", "w") as f:
        f.write(html)
    print("Saved line_immigration_surges.html")


def main():
    df = load_data()
    bar_chart(df)
    line_chart(df)


if __name__ == "__main__":
    main()
