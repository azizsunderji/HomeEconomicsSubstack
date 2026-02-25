"""
DC vs. National: 4-Metric Cumulative Indexed Comparison (small multiples D3 chart)
Compares DC metro vs. national on permits, rents, employment, and WFH.
All series rebased to 100 in their first year.
"""

import sys
import os
import json
import requests
import pandas as pd
import duckdb
import io

sys.path.insert(0, "/Users/azizsunderji/Dropbox/Home Economics/Scripts")
from templates.d3_base import html_wrapper, COLORS

BASE = "/Users/azizsunderji/Dropbox/Home Economics/2026_02_23_DCRentDecline"
DATA = f"{BASE}/data"
OUT = f"{BASE}/outputs"

FRED_KEY = "936c7e9922072dbab8e2632a67e93ac9"
DC_CBSA = "47900"

# ─────────────────────────────────────────────────────────
# 1. PERMITS — Census BPS metro annual files (2015-2023)
#    + CBSA year-to-date Dec (2024-2025)
# ─────────────────────────────────────────────────────────
print("=" * 60)
print("PERMITS")
print("=" * 60)

def parse_metro_annual(text, year):
    """Parse a Census BPS metro annual file. Returns rows with CBSA, units_5plus, units_total."""
    rows = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("Survey") or line.startswith("Date"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 16:
            continue
        try:
            cbsa = parts[2].strip()
            name = parts[4].strip()
            units_1 = int(parts[6]) if parts[6].strip() else 0
            units_2 = int(parts[9]) if parts[9].strip() else 0
            units_34 = int(parts[12]) if parts[12].strip() else 0
            units_5p = int(parts[15]) if parts[15].strip() else 0
            units_total = units_1 + units_2 + units_34 + units_5p
            rows.append({
                "year": year,
                "cbsa": cbsa,
                "name": name,
                "units_5plus": units_5p,
                "units_total": units_total,
            })
        except (ValueError, IndexError):
            continue
    return rows


def parse_cbsa_ytd(text, year):
    """Parse a Census BPS CBSA year-to-date file (2024+ format). Same output as metro annual."""
    rows = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("Survey") or line.startswith("Date"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 16:
            continue
        try:
            cbsa = parts[2].strip()
            name = parts[4].strip()
            units_1 = int(parts[6]) if parts[6].strip() else 0
            units_2 = int(parts[9]) if parts[9].strip() else 0
            units_34 = int(parts[12]) if parts[12].strip() else 0
            units_5p = int(parts[15]) if parts[15].strip() else 0
            units_total = units_1 + units_2 + units_34 + units_5p
            rows.append({
                "year": year,
                "cbsa": cbsa,
                "name": name,
                "units_5plus": units_5p,
                "units_total": units_total,
            })
        except (ValueError, IndexError):
            continue
    return rows


all_permit_rows = []

# 2015-2023: Metro annual files
for year in range(2015, 2024):
    url = f"https://www2.census.gov/econ/bps/Metro%20(ending%202023)/ma{year}a.txt"
    r = requests.get(url)
    if r.status_code == 200:
        rows = parse_metro_annual(r.text, year)
        all_permit_rows.extend(rows)
        print(f"  {year}: {len(rows)} CBSAs")
    else:
        print(f"  {year}: FAILED ({r.status_code})")

# 2024-2025: CBSA year-to-date December files
for year in [2024, 2025]:
    yy = str(year)[2:]
    url = f"https://www2.census.gov/econ/bps/CBSA%20(beginning%20Jan%202024)/cbsa{yy}12y.txt"
    r = requests.get(url)
    if r.status_code == 200:
        rows = parse_cbsa_ytd(r.text, year)
        all_permit_rows.extend(rows)
        print(f"  {year}: {len(rows)} CBSAs (CBSA YTD Dec)")
    else:
        print(f"  {year}: FAILED ({r.status_code})")

permits_df = pd.DataFrame(all_permit_rows)

# DC metro
dc_permits = permits_df[permits_df["cbsa"] == DC_CBSA][["year", "units_5plus"]].rename(
    columns={"units_5plus": "dc"}
)
# National: sum all CBSAs per year
nat_permits = permits_df.groupby("year")["units_5plus"].sum().reset_index().rename(
    columns={"units_5plus": "national"}
)
permits = dc_permits.merge(nat_permits, on="year").sort_values("year")

# Cumulative sum, then index to 100 at base year
permits["dc_cum"] = permits["dc"].cumsum()
permits["national_cum"] = permits["national"].cumsum()
base_dc = permits.iloc[0]["dc_cum"]
base_nat = permits.iloc[0]["national_cum"]
permits["dc_idx"] = permits["dc_cum"] / base_dc * 100
permits["national_idx"] = permits["national_cum"] / base_nat * 100

print(f"\nPermits cumulative indexed (base {int(permits.iloc[0]['year'])} = 100):")
print(permits[["year", "dc", "dc_cum", "dc_idx", "national", "national_cum", "national_idx"]].to_string(index=False))

# ─────────────────────────────────────────────────────────
# 2. RENTS — ZORI from parquet
# ─────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("RENTS (ZORI)")
print("=" * 60)

con = duckdb.connect()

# DC metro: filter by Metro name
dc_rents = con.execute(f"""
    SELECT YEAR(date) as year, AVG(zori) as dc
    FROM '{DATA}/zori_zip_all.parquet'
    WHERE Metro = 'Washington-Arlington-Alexandria, DC-VA-MD-WV'
    GROUP BY YEAR(date)
    ORDER BY year
""").df()

# National: all ZIPs
nat_rents = con.execute(f"""
    SELECT YEAR(date) as year, AVG(zori) as national
    FROM '{DATA}/zori_zip_all.parquet'
    GROUP BY YEAR(date)
    ORDER BY year
""").df()

rents = dc_rents.merge(nat_rents, on="year").sort_values("year")
# Drop 2026 partial year if present
rents = rents[rents["year"] <= 2025]

base_dc = rents.iloc[0]["dc"]
base_nat = rents.iloc[0]["national"]
rents["dc_idx"] = rents["dc"] / base_dc * 100
rents["national_idx"] = rents["national"] / base_nat * 100

print(f"Rents indexed (base {int(rents.iloc[0]['year'])} = 100):")
print(rents[["year", "dc_idx", "national_idx"]].to_string(index=False))

# ─────────────────────────────────────────────────────────
# 3. EMPLOYMENT — FRED API
# ─────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("EMPLOYMENT (FRED)")
print("=" * 60)


def fred_series_annual(series_id, start="2015-01-01"):
    """Pull FRED monthly series and compute annual averages."""
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": FRED_KEY,
        "file_type": "json",
        "observation_start": start,
        "observation_end": "2025-12-31",
    }
    r = requests.get(url, params=params)
    resp = r.json()
    if "observations" not in resp:
        print(f"  FRED error for {series_id}: {resp.get('error_message', resp)}")
        return pd.DataFrame(columns=["year", "value"])
    data = resp["observations"]
    df = pd.DataFrame(data)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    annual = df.groupby("year")["value"].mean().reset_index()
    return annual


dc_emp = fred_series_annual("WASH911NA")  # DC metro total nonfarm
us_emp = fred_series_annual("PAYEMS")     # US total nonfarm

emp = dc_emp.rename(columns={"value": "dc"}).merge(
    us_emp.rename(columns={"value": "national"}), on="year"
).sort_values("year")

base_dc = emp.iloc[0]["dc"]
base_nat = emp.iloc[0]["national"]
emp["dc_idx"] = emp["dc"] / base_dc * 100
emp["national_idx"] = emp["national"] / base_nat * 100

print(f"Employment indexed (base {int(emp.iloc[0]['year'])} = 100):")
print(emp[["year", "dc_idx", "national_idx"]].to_string(index=False))

# ─────────────────────────────────────────────────────────
# 4. WFH — Nick Bloom / WFH Research SWAA (monthly, by city)
# ─────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("WORK FROM HOME (Bloom SWAA)")
print("=" * 60)

wfh_xlsx = f"{BASE}/WFHtimeseries_monthly.xlsx"
wfh_city = pd.read_excel(wfh_xlsx, sheet_name="WFH by city")
wfh_city["date"] = pd.to_datetime(wfh_city["date"])
wfh_city["year"] = wfh_city["date"].dt.year

# Annual averages: DC metro vs national proxy (avg of top10 + 11-50 + other tiers)
wfh = wfh_city.groupby("year").agg(
    dc=("wfhcovid_series_MA6_DC", "mean"),
    top10=("wfhcovid_series_top10_MA6_", "mean"),
    mid=("wfhcovid_series_11to50_MA6_", "mean"),
    other=("wfhcovid_series_other_MA6_", "mean"),
).reset_index()
wfh["national"] = (wfh["top10"] + wfh["mid"] + wfh["other"]) / 3

# Drop 2026 if only 1 month of data
if wfh.iloc[-1]["year"] == 2026:
    n_months_2026 = len(wfh_city[wfh_city["year"] == 2026])
    if n_months_2026 < 6:
        print(f"  Note: 2026 has only {n_months_2026} month(s). Dropping.")
        wfh = wfh[wfh["year"] < 2026]

# Index to 100 in base year (2021 = first full year)
wfh_base = wfh[wfh["year"] == 2021]
base_dc = wfh_base.iloc[0]["dc"]
base_nat = wfh_base.iloc[0]["national"]
wfh["dc_idx"] = wfh["dc"] / base_dc * 100
wfh["national_idx"] = wfh["national"] / base_nat * 100
# Start from 2021 (first full year of SWAA data)
wfh = wfh[wfh["year"] >= 2021].reset_index(drop=True)

print(f"WFH indexed (base 2021 = 100, source: Bloom SWAA):")
print(wfh[["year", "dc", "national", "dc_idx", "national_idx"]].to_string(index=False))


# ─────────────────────────────────────────────────────────
# BUILD D3 CHART
# ─────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("BUILDING D3 CHART")
print("=" * 60)

# Prepare JSON data for D3 — indexed to 100
chart_data = {
    "permits": {
        "title": "Multifamily permits",
        "base_year": int(permits.iloc[0]["year"]),
        "dc": [{"year": int(r.year), "value": round(r.dc_idx, 1)} for _, r in permits.iterrows()],
        "national": [{"year": int(r.year), "value": round(r.national_idx, 1)} for _, r in permits.iterrows()],
    },
    "rents": {
        "title": "Rents",
        "base_year": int(rents.iloc[0]["year"]),
        "dc": [{"year": int(r.year), "value": round(r.dc_idx, 1)} for _, r in rents.iterrows()],
        "national": [{"year": int(r.year), "value": round(r.national_idx, 1)} for _, r in rents.iterrows()],
    },
    "employment": {
        "title": "Employment",
        "base_year": int(emp.iloc[0]["year"]),
        "dc": [{"year": int(r.year), "value": round(r.dc_idx, 1)} for _, r in emp.iterrows()],
        "national": [{"year": int(r.year), "value": round(r.national_idx, 1)} for _, r in emp.iterrows()],
    },
    "wfh": {
        "title": "Work from home",
        "base_year": int(wfh.iloc[0]["year"]),
        "dc": [{"year": int(r.year), "value": round(r.dc_idx, 1)} for _, r in wfh.iterrows()],
        "national": [{"year": int(r.year), "value": round(r.national_idx, 1)} for _, r in wfh.iterrows()],
    },
}

data_json = json.dumps(chart_data)

extra_css = """
.panel-title {
    font-size: 14px;
    font-weight: 500;
    fill: #3D3733;
}
.axis text {
    font-size: 11px;
    fill: #3D3733;
    opacity: 0.7;
}
.axis line, .axis path {
    stroke: #ccc;
}
.grid line {
    stroke: #e0e0e0;
    stroke-dasharray: 2,2;
}
.zero-line {
    stroke: #3D3733;
    stroke-width: 1;
    opacity: 0.3;
}
.end-label {
    font-size: 11px;
    font-weight: 500;
}
.covid-band {
    fill: #3D3733;
    opacity: 0.05;
}
.legend-text {
    font-size: 11px;
    fill: #3D3733;
}
"""

extra_js = f"""
const data = {data_json};
const panels = ["permits", "rents", "employment", "wfh"];

const W = 900, H = 750;
const margin = {{top: 35, right: 55, bottom: 45, left: 45}};
const gapX = 60, gapY = 70;
const panelW = (W - margin.left - margin.right - gapX) / 2;
const panelH = (H - margin.top - margin.bottom - gapY) / 2;

const svg = d3.select("#chart")
    .append("svg")
    .attr("width", W)
    .attr("height", H)
    .attr("viewBox", `0 0 ${{W}} ${{H}}`);

// Legend at top — centered above panels
const legend = svg.append("g").attr("transform", `translate(${{W/2 - 80}}, 12)`);
legend.append("line").attr("x1", 0).attr("x2", 25).attr("y1", 5).attr("y2", 5)
    .attr("stroke", "{COLORS['blue']}").attr("stroke-width", 2.5);
legend.append("text").attr("x", 30).attr("y", 9).text("DC metro")
    .attr("class", "legend-text");
legend.append("line").attr("x1", 100).attr("x2", 125).attr("y1", 5).attr("y2", 5)
    .attr("stroke", "{COLORS['black']}").attr("stroke-width", 2.5);
legend.append("text").attr("x", 130).attr("y", 9).text("National")
    .attr("class", "legend-text");

panels.forEach((key, i) => {{
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x0 = margin.left + col * (panelW + gapX);
    const y0 = margin.top + 30 + row * (panelH + gapY);

    const panel = data[key];
    const dcData = panel.dc;
    const natData = panel.national;

    // Find common year range
    const allYears = [...dcData.map(d => d.year), ...natData.map(d => d.year)];
    const minYear = d3.min(allYears);
    const maxYear = d3.max(allYears);

    const allValues = [...dcData.map(d => d.value), ...natData.map(d => d.value)];
    const yMin = d3.min(allValues);
    const yMax = d3.max(allValues);
    const yPad = (yMax - yMin) * 0.12;

    const xScale = d3.scaleLinear()
        .domain([minYear, maxYear])
        .range([0, panelW]);

    const yScale = d3.scaleLinear()
        .domain([yMin - yPad, yMax + yPad])
        .range([panelH, 0]);

    const g = svg.append("g").attr("transform", `translate(${{x0}}, ${{y0}})`);

    // Panel title
    g.append("text")
        .attr("class", "panel-title")
        .attr("x", 0)
        .attr("y", -10)
        .text(panel.title);

    // Horizontal gridlines
    const yTicks = yScale.ticks(5);
    yTicks.forEach(tick => {{
        g.append("line")
            .attr("x1", 0).attr("x2", panelW)
            .attr("y1", yScale(tick)).attr("y2", yScale(tick))
            .style("stroke", "#e0e0e0")
            .style("stroke-dasharray", "2,2");
    }});

    // Baseline 100 reference line
    if (yScale.domain()[0] <= 100 && yScale.domain()[1] >= 100) {{
        g.append("line")
            .attr("x1", 0).attr("x2", panelW)
            .attr("y1", yScale(100)).attr("y2", yScale(100))
            .attr("stroke", "{COLORS['black']}")
            .attr("stroke-width", 1)
            .attr("opacity", 0.25);
    }}

    // Y axis
    const yAxis = d3.axisLeft(yScale).ticks(5).tickSize(0)
        .tickFormat(d => d3.format(",")(d));
    const yAxisG = g.append("g").attr("class", "axis").call(yAxis);
    yAxisG.select(".domain").remove();

    // X axis — show every other year, always include first and last
    const allYearRange = d3.range(minYear, maxYear + 1);
    let xTicks;
    if (allYearRange.length <= 7) {{
        xTicks = allYearRange;  // show all if few years
    }} else {{
        xTicks = allYearRange.filter(y => y % 2 === 1);  // odd years
        if (!xTicks.includes(minYear)) xTicks.unshift(minYear);
        if (!xTicks.includes(maxYear)) xTicks.push(maxYear);
    }}
    const xAxis = d3.axisBottom(xScale)
        .tickValues(xTicks)
        .tickFormat(d => "'" + String(d).slice(2))
        .tickSize(4);
    g.append("g")
        .attr("class", "axis")
        .attr("transform", `translate(0, ${{panelH}})`)
        .call(xAxis)
        .select(".domain").attr("stroke", "#ccc");

    // Line generator
    const line = d3.line()
        .x(d => xScale(d.year))
        .y(d => yScale(d.value));

    // Draw lines
    g.append("path").datum(dcData).attr("d", line)
        .attr("fill", "none").attr("stroke", "{COLORS['blue']}").attr("stroke-width", 2.5);
    g.append("path").datum(natData).attr("d", line)
        .attr("fill", "none").attr("stroke", "{COLORS['black']}").attr("stroke-width", 2.5);

    // End labels with collision avoidance
    const dcLast = dcData[dcData.length - 1];
    const natLast = natData[natData.length - 1];

    let dcLabelY = yScale(dcLast.value);
    let natLabelY = yScale(natLast.value);
    const minGap = 14;
    if (Math.abs(dcLabelY - natLabelY) < minGap) {{
        const mid = (dcLabelY + natLabelY) / 2;
        if (dcLast.value >= natLast.value) {{
            dcLabelY = mid - minGap / 2;
            natLabelY = mid + minGap / 2;
        }} else {{
            dcLabelY = mid + minGap / 2;
            natLabelY = mid - minGap / 2;
        }}
    }}

    g.append("text")
        .attr("class", "end-label")
        .attr("x", panelW + 6)
        .attr("y", dcLabelY + 4)
        .attr("fill", "{COLORS['blue']}")
        .text("DC " + Math.round(dcLast.value));

    g.append("text")
        .attr("class", "end-label")
        .attr("x", panelW + 6)
        .attr("y", natLabelY + 4)
        .attr("fill", "{COLORS['black']}")
        .text("US " + Math.round(natLast.value));

    // Dots on endpoints
    g.append("circle").attr("cx", xScale(dcLast.year)).attr("cy", yScale(dcLast.value))
        .attr("r", 3).attr("fill", "{COLORS['blue']}");
    g.append("circle").attr("cx", xScale(natLast.year)).attr("cy", yScale(natLast.value))
        .attr("r", 3).attr("fill", "{COLORS['black']}");
}});
"""

body_content = '<div id="chart"></div>'

html = html_wrapper(
    title="DC's rent problem isn't about supply",
    subtitle="Indexed to 100 in base year, DC metro vs. national",
    source="Source: Census Bureau BPS, Zillow ZORI, BLS/FRED, WFH Research (Bloom, Barrero, Davis)",
    body_content=body_content,
    width=900,
    height=750,
    extra_css=extra_css,
    extra_js=extra_js,
)

outpath = f"{OUT}/10_dc_vs_national_yoy.html"
with open(outpath, "w") as f:
    f.write(html)

print(f"\nSaved to {outpath}")
