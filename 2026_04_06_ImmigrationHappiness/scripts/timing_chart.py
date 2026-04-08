#!/usr/bin/env python3
"""Timing chart: when did happiness decline vs when did immigration accelerate?

Small multiples for 6 Anglosphere countries showing both series on dual axes.
"""

import pandas as pd
import numpy as np
import json, base64, os
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
OUT = Path(__file__).parent.parent / "outputs"

BLACK = "#3D3733"; BG = "#F6F7F3"; BLUE = "#0BB4FF"; RED = "#F4743B"
GREEN = "#67A275"; SUBTITLE_COLOR = "#7F7570"; GRID_COLOR = "#e1e2e3"
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
LOGO_PATH = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/HomeEconomics-Logo-versions/HE-Large-Black.png"


def main():
    imm = pd.read_csv(DATA / "oecd_immigration_net.csv")
    hap = pd.read_csv(DATA / "happiness_combined.csv")

    countries = [
        ("United States", "USA"),
        ("Canada", "CAN"),
        ("United Kingdom", "GBR"),
        ("Australia", "AUS"),
        ("New Zealand", "NZL"),
        ("Ireland", "IRL"),
    ]

    series = []
    for name, iso3 in countries:
        h = hap[hap["iso3"] == iso3].sort_values("year")
        i = imm[imm["iso3"] == iso3].sort_values("year")

        # Find peak happiness (smoothed)
        h_smooth = h.copy()
        h_smooth["smooth"] = h_smooth["cantril"].rolling(3, center=True, min_periods=2).mean()
        peak_idx = h_smooth["smooth"].idxmax()
        peak_yr = int(h_smooth.loc[peak_idx, "year"])

        series.append({
            "name": name,
            "iso3": iso3,
            "peak_yr": peak_yr,
            "happiness": [{"year": int(r["year"]), "val": round(float(r["cantril"]), 2)}
                          for _, r in h.iterrows()],
            "immigration": [{"year": int(r["year"]), "val": round(float(r["rate_per1000"]), 1)}
                            for _, r in i.iterrows() if pd.notna(r["rate_per1000"])],
        })

    data_json = json.dumps(series)

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
const W = 960, H = 850;
const cols = 2, rows = 3;
const cellW = 420, cellH = 200;
const cellPadL = 55, cellPadR = 55, cellPadT = 40, cellPadB = 25;
const gridLeft = 50, gridTop = 140;
const gapX = 30, gapY = 20;

const data = {data_json};

const svg = d3.select("body").append("svg")
  .attr("width", W).attr("height", H).attr("viewBox", `0 0 ${{W}} ${{H}}`);

svg.append("rect").attr("width", W).attr("height", H).attr("fill", "{BG}");

svg.append("text").attr("x", 40).attr("y", 72)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 32).attr("font-weight", 500)
  .attr("fill", "{BLACK}").text("When did happiness decline?");

svg.append("text").attr("x", 40).attr("y", 106)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 23).attr("font-weight", 400)
  .attr("fill", "{SUBTITLE_COLOR}")
  .text("Life satisfaction (blue) and net migration rate (orange), Anglosphere");

// Legend
svg.append("line").attr("x1", 600).attr("x2", 630).attr("y1", 72).attr("y2", 72)
  .attr("stroke", "{BLUE}").attr("stroke-width", 2.5);
svg.append("text").attr("x", 635).attr("y", 77)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 13).attr("font-weight", 400)
  .attr("fill", "{BLACK}").text("Happiness (left axis)");
svg.append("line").attr("x1", 600).attr("x2", 630).attr("y1", 94).attr("y2", 94)
  .attr("stroke", "{RED}").attr("stroke-width", 2.5);
svg.append("text").attr("x", 635).attr("y", 99)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 13).attr("font-weight", 400)
  .attr("fill", "{BLACK}").text("Immigration rate (right axis)");

data.forEach((c, i) => {{
  const col = i % cols, row = Math.floor(i / cols);
  const cx = gridLeft + col * (cellW + gapX);
  const cy = gridTop + row * (cellH + gapY);
  const g = svg.append("g").attr("transform", `translate(${{cx}},${{cy}})`);

  g.append("rect").attr("width", cellW).attr("height", cellH)
    .attr("fill", "#FFFFFF").attr("rx", 4).attr("opacity", 0.4);

  // Country name
  g.append("text").attr("x", cellPadL).attr("y", 22)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", 16).attr("font-weight", 700)
    .attr("fill", "{BLACK}").text(c.name);

  // Peak marker text
  g.append("text").attr("x", cellW - cellPadR).attr("y", 22)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", 12).attr("font-weight", 400)
    .attr("fill", "{SUBTITLE_COLOR}").attr("text-anchor", "end")
    .text("Peak: " + c.peak_yr);

  // Scales
  const x = d3.scaleLinear().domain([2000, 2025]).range([cellPadL, cellW - cellPadR]);

  // Happiness y-axis (left)
  const hVals = c.happiness.map(d => d.val);
  const hMin = d3.min(hVals) - 0.15;
  const hMax = d3.max(hVals) + 0.15;
  const yH = d3.scaleLinear().domain([hMin, hMax]).range([cellH - cellPadB, cellPadT]);

  // Immigration y-axis (right)
  const iVals = c.immigration.map(d => d.val);
  const iMin = Math.min(d3.min(iVals), -2);
  const iMax = d3.max(iVals) + 2;
  const yI = d3.scaleLinear().domain([iMin, iMax]).range([cellH - cellPadB, cellPadT]);

  // Light gridlines for happiness
  const hTicks = yH.ticks(4);
  hTicks.forEach(t => {{
    g.append("line").attr("x1", cellPadL).attr("x2", cellW - cellPadR)
      .attr("y1", yH(t)).attr("y2", yH(t))
      .attr("stroke", "{GRID_COLOR}").attr("stroke-width", 0.5);
  }});

  // Left axis labels (happiness)
  hTicks.forEach(t => {{
    g.append("text").attr("x", cellPadL - 5).attr("y", yH(t) + 4)
      .attr("font-family", "ABC Oracle Edu").attr("font-size", 10).attr("font-weight", 300)
      .attr("fill", "{BLUE}").attr("text-anchor", "end").text(t.toFixed(1));
  }});

  // Right axis labels (immigration)
  const iTicks = yI.ticks(4);
  iTicks.forEach(t => {{
    g.append("text").attr("x", cellW - cellPadR + 5).attr("y", yI(t) + 4)
      .attr("font-family", "ABC Oracle Edu").attr("font-size", 10).attr("font-weight", 300)
      .attr("fill", "{RED}").attr("text-anchor", "start").text(t.toFixed(0));
  }});

  // X-axis labels
  [2005, 2010, 2015, 2020, 2025].forEach(yr => {{
    g.append("text").attr("x", x(yr)).attr("y", cellH - cellPadB + 14)
      .attr("font-family", "ABC Oracle Edu").attr("font-size", 10).attr("font-weight", 300)
      .attr("fill", "#999").attr("text-anchor", "middle")
      .text(yr === 2005 ? "2005" : "'" + String(yr).slice(2));
  }});

  // Peak happiness vertical line
  g.append("line").attr("x1", x(c.peak_yr)).attr("x2", x(c.peak_yr))
    .attr("y1", cellPadT).attr("y2", cellH - cellPadB)
    .attr("stroke", "{BLUE}").attr("stroke-width", 1).attr("stroke-dasharray", "3,3").attr("opacity", 0.4);

  // Immigration line (orange, behind)
  const iLine = d3.line().x(d => x(d.year)).y(d => yI(d.val));
  g.append("path").datum(c.immigration)
    .attr("d", iLine).attr("fill", "none")
    .attr("stroke", "{RED}").attr("stroke-width", 2).attr("opacity", 0.6);

  // Happiness line (blue, on top)
  const hLine = d3.line().x(d => x(d.year)).y(d => yH(d.val));
  g.append("path").datum(c.happiness)
    .attr("d", hLine).attr("fill", "none")
    .attr("stroke", "{BLUE}").attr("stroke-width", 2.5);
}});

// Source
const sourceY = H - 45;
svg.append("text").attr("x", 40).attr("y", sourceY)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 14).attr("font-weight", 200)
  .attr("fill", "{BLACK}")
  .text("Sources: Gallup World Poll via WHR 2019/2026; CBO, Statistics Canada, ONS, ABS, Stats NZ, CSO");

svg.append("image")
  .attr("xlink:href", "data:image/png;base64,{logo_b64}")
  .attr("width", 120).attr("opacity", 0.6)
  .attr("x", W - 40 - 120).attr("y", sourceY - 10);

</script></body></html>"""

    with open(OUT / "timing_happiness_vs_immigration.html", "w") as f:
        f.write(html)
    print("Saved timing_happiness_vs_immigration.html")


if __name__ == "__main__":
    main()
