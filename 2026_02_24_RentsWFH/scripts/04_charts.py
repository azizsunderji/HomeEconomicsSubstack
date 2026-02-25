"""
04_charts.py — Generate all D3.js charts for the DC rent decline analysis.

Charts:
1. DC rent trajectory vs national + comparison metros (line chart)
2. Scatter: Permits per capita vs cumulative rent change
3. DC decomposition waterfall
4. DC metro permit dot map
5. DC metro ZIP-level rent change choropleth
6. WFH share scatter
"""

import sys
import json
import pandas as pd
import numpy as np
import duckdb

sys.path.insert(0, "/Users/azizsunderji/Dropbox/Home Economics/Scripts")
from templates.d3_base import html_wrapper, COLORS, font_faces

PROJECT = "/Users/azizsunderji/Dropbox/Home Economics/2026_02_23_DCRentDecline"
DATA = f"{PROJECT}/data"
OUTPUTS = f"{PROJECT}/outputs"

con = duckdb.connect()

# ═══════════════════════════════════════════════════════
# CHART 1: DC Rent Trajectory vs National + Peers
# ═══════════════════════════════════════════════════════
print("Chart 1: Rent trajectory...")

trajectory = con.execute(f"SELECT * FROM '{DATA}/rent_trajectory.parquet' ORDER BY RegionName, date").df()

# Prepare data for line chart
series_data = []
metro_order = ['Washington, DC', 'United States', 'Austin, TX', 'San Francisco, CA',
               'Nashville, TN', 'New York, NY', 'Phoenix, AZ', 'Seattle, WA',
               'Raleigh, NC', 'Denver, CO']

for metro in metro_order:
    mdf = trajectory[trajectory['RegionName'] == metro].dropna(subset=['rent_index'])
    if len(mdf) == 0:
        continue
    points = [{"date": r['date'].strftime('%Y-%m-%d'), "value": round(r['rent_index'], 1)}
              for _, r in mdf.iterrows()]
    series_data.append({"name": metro.replace(', ', ' '), "points": points})

# Custom colors — DC in red, US in black, others grey
line_colors = {
    'Washington DC': COLORS['red'],
    'United States': COLORS['black'],
}
other_color = '#C4C4C4'

data_json = json.dumps(series_data)

# Annotations
annotations = [
    {"date": "2020-03-15", "label": "COVID lockdowns", "y_offset": -80},
    {"date": "2021-06-01", "label": "WFH surge begins", "y_offset": -60},
    {"date": "2025-01-20", "label": "DOGE cuts begin", "y_offset": -40},
]

chart1_js = f"""
const DATA = {data_json};
const WIDTH = 900, HEIGHT = 600;
const MARGIN = {{top: 30, right: 140, bottom: 50, left: 55}};
const innerW = WIDTH - MARGIN.left - MARGIN.right;
const innerH = HEIGHT - MARGIN.top - MARGIN.bottom;

const LINE_COLORS = {json.dumps(line_colors)};
const OTHER_COLOR = "{other_color}";
const ANNOTATIONS = {json.dumps(annotations)};

const parseDate = d3.timeParse("%Y-%m-%d");

DATA.forEach(s => {{
    s.points.forEach(p => {{ p._date = parseDate(p.date) || new Date(p.date); p._value = +p.value; }});
    s.points.sort((a, b) => a._date - b._date);
}});

const svg = d3.select(".chart-container").append("svg").attr("width", WIDTH).attr("height", HEIGHT);
const g = svg.append("g").attr("transform", `translate(${{MARGIN.left}},${{MARGIN.top}})`);

const allDates = DATA.flatMap(s => s.points.map(p => p._date));
const allVals = DATA.flatMap(s => s.points.map(p => p._value));

const x = d3.scaleTime().domain(d3.extent(allDates)).range([0, innerW]);
const y = d3.scaleLinear().domain([95, Math.max(155, d3.max(allVals) * 1.05)]).range([innerH, 0]);

// Grid
g.append("g").attr("class", "grid").call(d3.axisLeft(y).tickSize(-innerW).tickFormat(""));

// 100 baseline
g.append("line").attr("x1", 0).attr("x2", innerW)
    .attr("y1", y(100)).attr("y2", y(100))
    .attr("stroke", "#999").attr("stroke-width", 1).attr("stroke-dasharray", "4,3");

// Axes
g.append("g").attr("class", "axis").attr("transform", `translate(0,${{innerH}})`)
    .call(d3.axisBottom(x).ticks(8));
const yAx = g.append("g").attr("class", "axis")
    .call(d3.axisLeft(y).ticks(6).tickSize(0));
yAx.select(".domain").remove();

// Lines
const line = d3.line().x(d => x(d._date)).y(d => y(d._value)).curve(d3.curveMonotoneX);

// Draw other metros first (background)
DATA.forEach(series => {{
    const color = LINE_COLORS[series.name] || OTHER_COLOR;
    if (color === OTHER_COLOR) {{
        g.append("path").datum(series.points).attr("d", line)
            .attr("fill", "none").attr("stroke", color).attr("stroke-width", 1.5).attr("opacity", 0.4);
    }}
}});

// Draw highlighted metros on top
DATA.forEach(series => {{
    const color = LINE_COLORS[series.name];
    if (color) {{
        g.append("path").datum(series.points).attr("d", line)
            .attr("fill", "none").attr("stroke", color).attr("stroke-width", 2.5);
    }}
}});

// End labels with collision avoidance
const endLabels = DATA.map(s => {{
    const last = s.points[s.points.length - 1];
    return {{ name: s.name, y: y(last._value), value: last._value, color: LINE_COLORS[s.name] || OTHER_COLOR }};
}}).sort((a, b) => a.y - b.y);

// Simple collision avoidance
const minGap = 13;
for (let i = 1; i < endLabels.length; i++) {{
    if (endLabels[i].y - endLabels[i - 1].y < minGap) {{
        endLabels[i].y = endLabels[i - 1].y + minGap;
    }}
}}

endLabels.forEach(d => {{
    const isHighlight = LINE_COLORS[d.name];
    g.append("text")
        .attr("x", innerW + 8).attr("y", d.y).attr("dy", "0.35em")
        .attr("font-size", isHighlight ? 12 : 10)
        .attr("font-weight", isHighlight ? 500 : 300)
        .attr("fill", d.color)
        .attr("opacity", isHighlight ? 1 : 0.6)
        .text(d.name + " " + d.value.toFixed(0));
}});

// Annotations
ANNOTATIONS.forEach(ann => {{
    const xPos = x(parseDate(ann.date));
    if (xPos >= 0 && xPos <= innerW) {{
        g.append("line").attr("x1", xPos).attr("x2", xPos)
            .attr("y1", 0).attr("y2", innerH)
            .attr("stroke", "#999").attr("stroke-width", 0.5).attr("stroke-dasharray", "3,3");
        g.append("text").attr("x", xPos).attr("y", ann.y_offset + innerH * 0.15)
            .attr("text-anchor", "middle").attr("font-size", 10)
            .attr("fill", "#999").attr("font-style", "italic")
            .text(ann.label);
    }}
}});

// Hover
const tooltip = d3.select("#tooltip");
const hoverLine = g.append("line").attr("class", "hover-line")
    .attr("y1", 0).attr("y2", innerH).style("opacity", 0)
    .attr("stroke", "#999").attr("stroke-width", 1).attr("stroke-dasharray", "4,3");

svg.append("rect").attr("width", innerW).attr("height", innerH)
    .attr("transform", `translate(${{MARGIN.left}},${{MARGIN.top}})`)
    .attr("fill", "transparent")
    .on("mousemove", function(event) {{
        const [mx] = d3.pointer(event, g.node());
        const dateAtMouse = x.invert(mx);
        hoverLine.attr("x1", mx).attr("x2", mx).style("opacity", 1);
        let html = `<strong>${{d3.timeFormat("%b %Y")(dateAtMouse)}}</strong>`;
        DATA.forEach(s => {{
            const bisect = d3.bisector(d => d._date).left;
            const idx = Math.min(bisect(s.points, dateAtMouse, 1), s.points.length - 1);
            const pt = s.points[idx];
            const c = LINE_COLORS[s.name] || OTHER_COLOR;
            html += `<br><span style="color:${{c}}">●</span> ${{s.name}}: ${{pt._value.toFixed(1)}}`;
        }});
        tooltip.html(html).style("left", (event.pageX + 12) + "px")
            .style("top", (event.pageY - 28) + "px").style("opacity", 1);
    }})
    .on("mouseout", function() {{
        hoverLine.style("opacity", 0);
        tooltip.style("opacity", 0);
    }});
"""

chart1_css = """
.axis text { font-size: 12px; fill: #3D3733; font-family: 'ABC Oracle Edu', system-ui; }
.grid line { stroke: #D0D0D0; stroke-width: 0.5; opacity: 0.7; }
.grid .domain { display: none; }
"""

chart1_html = html_wrapper(
    title="DC Rents Lagged the Nation Since 2019",
    subtitle="Rent index (Jan 2019 = 100), Zillow ZORI, selected metros",
    source="Source: Zillow Observed Rent Index (ZORI)",
    body_content="", extra_css=chart1_css, extra_js=chart1_js,
    width=900, height=600)

with open(f"{OUTPUTS}/01_rent_trajectory.html", 'w') as f:
    f.write(chart1_html)
print("  Saved 01_rent_trajectory.html")

# ═══════════════════════════════════════════════════════
# CHART 2: Scatter — Permits per capita vs rent change
# ═══════════════════════════════════════════════════════
print("Chart 2: Permits scatter...")

cum_scatter = con.execute(f"SELECT * FROM '{DATA}/scatter_cumulative.parquet'").df()

scatter3_data = []
for _, r in cum_scatter.iterrows():
    if pd.isna(r['cum_permits_pc']) or pd.isna(r['rent_change_pct']):
        continue
    name = r['RegionName'].split(',')[0] if pd.notna(r.get('RegionName')) else r['cbsa']
    scatter3_data.append({
        "name": name,
        "x": round(r['cum_permits_pc'], 1),
        "y": round(r['rent_change_pct'], 1),
        "group": "highlight" if r['is_dc'] else "default",
        "size": float(r.get('employed_pop', 1000000)) if pd.notna(r.get('employed_pop')) else 500000
    })

scatter3_json = json.dumps(scatter3_data)

chart3_js = f"""
const DATA = {scatter3_json};
const WIDTH = 900, HEIGHT = 650;
const MARGIN = {{top: 30, right: 30, bottom: 65, left: 75}};
const innerW = WIDTH - MARGIN.left - MARGIN.right;
const innerH = HEIGHT - MARGIN.top - MARGIN.bottom;

const svg = d3.select(".chart-container").append("svg").attr("width", WIDTH).attr("height", HEIGHT);
const g = svg.append("g").attr("transform", `translate(${{MARGIN.left}},${{MARGIN.top}})`);

const x = d3.scaleLinear().domain([0, d3.max(DATA, d => d.x) * 1.1]).range([0, innerW]);
const y = d3.scaleLinear().domain([d3.min(DATA, d => d.y) * 0.9, d3.max(DATA, d => d.y) * 1.1]).range([innerH, 0]);
const r = d3.scaleSqrt().domain([0, d3.max(DATA, d => d.size)]).range([4, 18]);

g.append("g").attr("class", "grid").call(d3.axisLeft(y).tickSize(-innerW).tickFormat(""));

// Regression line
const xMean = d3.mean(DATA, d => d.x), yMean = d3.mean(DATA, d => d.y);
let num = 0, den = 0;
DATA.forEach(d => {{ num += (d.x - xMean) * (d.y - yMean); den += (d.x - xMean) ** 2; }});
const slope = num / den, intercept = yMean - slope * xMean;
const xRange = d3.extent(DATA, d => d.x);
g.append("line")
    .attr("x1", x(xRange[0])).attr("y1", y(intercept + slope * xRange[0]))
    .attr("x2", x(xRange[1])).attr("y2", y(intercept + slope * xRange[1]))
    .attr("stroke", "#999").attr("stroke-width", 1).attr("stroke-dasharray", "5,3");

g.append("g").attr("class", "axis").attr("transform", `translate(0,${{innerH}})`)
    .call(d3.axisBottom(x).ticks(6));
const yAx = g.append("g").attr("class", "axis")
    .call(d3.axisLeft(y).ticks(6).tickSize(0).tickFormat(d => d + "%"));
yAx.select(".domain").remove();

g.append("text").attr("class", "axis-label").attr("x", innerW / 2).attr("y", innerH + 50)
    .attr("text-anchor", "middle").attr("font-size", 13).attr("fill", "#3D3733").attr("font-weight", 300)
    .text("Cumulative 5+ Unit Permits per 1,000 Workers (2019-2024)");
g.append("text").attr("class", "axis-label").attr("transform", "rotate(-90)")
    .attr("x", -innerH / 2).attr("y", -55).attr("text-anchor", "middle")
    .attr("font-size", 13).attr("fill", "#3D3733").attr("font-weight", 300)
    .text("Cumulative Rent Change, 2019-2025 (%)");

const tooltip = d3.select("#tooltip");
g.selectAll(".dot").data(DATA).join("circle").attr("class", "dot")
    .attr("cx", d => x(d.x)).attr("cy", d => y(d.y))
    .attr("r", d => r(d.size))
    .attr("fill", d => d.group === "highlight" ? "{COLORS['red']}" : "{COLORS['blue']}")
    .attr("opacity", d => d.group === "highlight" ? 0.9 : 0.4)
    .attr("stroke", d => d.group === "highlight" ? "{COLORS['black']}" : "white")
    .attr("stroke-width", d => d.group === "highlight" ? 2 : 0.5)
    .on("mouseover", function(event, d) {{
        d3.select(this).attr("opacity", 1).attr("stroke-width", 2);
        tooltip.html(`<strong>${{d.name}}</strong><br>Permits/1K: ${{d.x.toFixed(1)}}<br>Rent change: ${{d.y.toFixed(1)}}%`)
            .style("left", (event.pageX + 12) + "px").style("top", (event.pageY - 28) + "px").style("opacity", 1);
    }})
    .on("mouseout", function() {{
        d3.select(this).attr("opacity", d => d.group === "highlight" ? 0.9 : 0.4).attr("stroke-width", d => d.group === "highlight" ? 2 : 0.5);
        tooltip.style("opacity", 0);
    }});

// Label DC
const dc = DATA.find(d => d.group === "highlight");
if (dc) {{
    g.append("text").attr("x", x(dc.x) + r(dc.size) + 6).attr("y", y(dc.y) - 2)
        .attr("font-size", 13).attr("font-weight", 500).attr("fill", "{COLORS['red']}")
        .text("Washington DC");
    g.append("text").attr("x", x(dc.x) + r(dc.size) + 6).attr("y", y(dc.y) + 14)
        .attr("font-size", 11).attr("font-weight", 300).attr("fill", "{COLORS['red']}")
        .text(`${{dc.x.toFixed(1)}} permits/1K, +${{dc.y.toFixed(0)}}% rent`);
}}

// Annotation: slope interpretation
g.append("text").attr("x", innerW - 10).attr("y", 15)
    .attr("text-anchor", "end").attr("font-size", 11).attr("fill", "#999").attr("font-style", "italic")
    .text("Slope: " + slope.toFixed(2) + "pp rent per permit/1K");
"""

chart3_html = html_wrapper(
    title="New Apartments Alone Don't Explain DC's Rent Gap",
    subtitle="Apartment permits per capita vs. cumulative rent change, top ~50 metros, 2019-2025",
    source="Source: Census Building Permits Survey, Zillow ZORI",
    body_content="", extra_css=chart1_css, extra_js=chart3_js,
    width=900, height=650)

with open(f"{OUTPUTS}/02_permits_scatter.html", 'w') as f:
    f.write(chart3_html)
print("  Saved 02_permits_scatter.html")

# ═══════════════════════════════════════════════════════
# CHART 3: DC Decomposition Waterfall
# ═══════════════════════════════════════════════════════
print("Chart 3: Decomposition waterfall...")

# Load regression results
with open(f"{DATA}/regression_results.json") as f:
    results = json.load(f)

# Single-year decomposition (2025) — cleanest approach, residual is tiny
decomp = con.execute(f"SELECT * FROM '{DATA}/dc_decomposition.parquet'").df()
latest_yr = int(decomp['year'].max())
d = decomp[decomp['year'] == latest_yr].iloc[0]

# National trend = year fixed effect (what an average metro with zero characteristics would get)
nat_trend = round(d['year_fe'], 1)
supply_eff = round(d['supply_effect'], 1)
emp_eff = round(d['emp_effect'], 1)
wfh_eff = round(d['wfh_effect'], 1)
dc_actual = round(d['actual_yoy'], 1)
residual = round(d['residual'], 1)

print(f"  {latest_yr} decomposition: National trend={nat_trend}, Supply={supply_eff}, Emp={emp_eff}, WFH={wfh_eff}, Residual={residual}, Actual={dc_actual}")

waterfall_bars = [
    {"label": "National\ntrend", "value": nat_trend, "type": "absolute", "color": COLORS['blue']},
    {"label": "New apartment\nsupply", "value": supply_eff, "type": "delta", "color": COLORS['lt_green']},
    {"label": "Employment\ndecline", "value": emp_eff, "type": "delta", "color": COLORS['yellow']},
    {"label": "Remote work\n(WFH share)", "value": wfh_eff, "type": "delta", "color": COLORS['green']},
    {"label": "Unexplained", "value": residual, "type": "delta", "color": COLORS['lt_red']},
    {"label": "DC actual\nrent growth", "value": dc_actual, "type": "total", "color": COLORS['red']},
]

waterfall_json = json.dumps(waterfall_bars)

chart4_js = f"""
const BARS = {waterfall_json};
const WIDTH = 900, HEIGHT = 650;
const MARGIN = {{top: 30, right: 30, bottom: 90, left: 60}};
const innerW = WIDTH - MARGIN.left - MARGIN.right;
const innerH = HEIGHT - MARGIN.top - MARGIN.bottom;

const svg = d3.select(".chart-container").append("svg").attr("width", WIDTH).attr("height", HEIGHT);
const g = svg.append("g").attr("transform", `translate(${{MARGIN.left}},${{MARGIN.top}})`);

// Calculate positions
let cumulative = 0;
BARS.forEach((bar, i) => {{
    if (bar.type === "absolute") {{
        bar.start = 0;
        bar.end = bar.value;
        cumulative = bar.value;
    }} else if (bar.type === "delta") {{
        bar.start = cumulative;
        bar.end = cumulative + bar.value;
        cumulative = bar.end;
    }} else if (bar.type === "total") {{
        bar.start = 0;
        bar.end = bar.value;
    }}
}});

const x = d3.scaleBand()
    .domain(BARS.map(d => d.label))
    .range([0, innerW])
    .padding(0.3);

const allVals = BARS.flatMap(b => [b.start, b.end]);
const y = d3.scaleLinear()
    .domain([Math.min(0, d3.min(allVals)) - 5, d3.max(allVals) + 5])
    .range([innerH, 0]);

// Grid
g.append("g").attr("class", "grid").call(d3.axisLeft(y).tickSize(-innerW).tickFormat(""));

// Zero line
g.append("line").attr("x1", 0).attr("x2", innerW)
    .attr("y1", y(0)).attr("y2", y(0))
    .attr("stroke", "#999").attr("stroke-width", 1);

// Axes
g.append("g").attr("class", "axis").attr("transform", `translate(0,${{innerH}})`)
    .call(d3.axisBottom(x).tickSize(0))
    .selectAll("text")
    .attr("font-size", 11)
    .style("text-anchor", "middle");

const yAx = g.append("g").attr("class", "axis")
    .call(d3.axisLeft(y).ticks(8).tickSize(0).tickFormat((d, i, ticks) =>
        i === ticks.length - 1 ? d + "%" : d
    ));
yAx.select(".domain").remove();

// Bars
g.selectAll(".bar").data(BARS).join("rect").attr("class", "bar")
    .attr("x", d => x(d.label))
    .attr("y", d => y(Math.max(d.start, d.end)))
    .attr("width", x.bandwidth())
    .attr("height", d => Math.abs(y(d.start) - y(d.end)))
    .attr("fill", d => d.color)
    .attr("rx", 2);

// Connector lines between bars
BARS.forEach((bar, i) => {{
    if (i > 0 && i < BARS.length - 1 && bar.type === "delta") {{
        g.append("line")
            .attr("x1", x(BARS[i].label) + x.bandwidth())
            .attr("x2", x(BARS[i + 1] ? BARS[i + 1].label : BARS[i].label) + x.bandwidth())
            .attr("y1", y(bar.end))
            .attr("y2", y(bar.end))
            .attr("stroke", "#999")
            .attr("stroke-width", 0.5)
            .attr("stroke-dasharray", "3,2");
    }}
}});

// Value labels on bars
BARS.forEach(bar => {{
    const mid = (bar.start + bar.end) / 2;
    const isSmall = Math.abs(bar.end - bar.start) < 3;
    const prefix = bar.type === "delta" && bar.value > 0 ? "+" : "";
    g.append("text")
        .attr("x", x(bar.label) + x.bandwidth() / 2)
        .attr("y", isSmall ? y(Math.max(bar.start, bar.end)) - 8 : y(mid))
        .attr("text-anchor", "middle")
        .attr("dy", isSmall ? 0 : "0.35em")
        .attr("font-size", 13)
        .attr("font-weight", 500)
        .attr("fill", isSmall ? "{COLORS['black']}" : "white")
        .text(prefix + bar.value.toFixed(1) + "%");
}});
"""

chart4_css = """
.axis text { font-size: 12px; fill: #3D3733; font-family: 'ABC Oracle Edu', system-ui; white-space: pre-line; }
.grid line { stroke: #D0D0D0; stroke-width: 0.5; opacity: 0.7; }
.grid .domain { display: none; }
"""

chart4_html = html_wrapper(
    title="Why DC Rents Barely Grew in 2025",
    subtitle=f"Decomposing DC's {latest_yr} rent change: national trend minus local headwinds. Each bar = model coefficient x DC's value.",
    source="Source: Zillow ZORI, BLS CES, Census BPS, ACS 1-Year. OLS with year FEs, clustered SEs, ~50 metros.",
    body_content="", extra_css=chart4_css, extra_js=chart4_js,
    width=900, height=650)

with open(f"{OUTPUTS}/03_decomposition_waterfall.html", 'w') as f:
    f.write(chart4_html)
print("  Saved 03_decomposition_waterfall.html")

# ═══════════════════════════════════════════════════════
# CHART 4: DC Metro — Building Permit Dots
# ═══════════════════════════════════════════════════════
print("Chart 4: DC permit dot map...")

# Load DC building permits
dc_permits = con.execute(f"""
    SELECT *,
        CAST(ISSUE_DATE AS VARCHAR) as issue_str
    FROM '{DATA}/dc_building_permits_raw.parquet'
    LIMIT 5
""").df()
print(f"DC permit columns: {list(dc_permits.columns)[:20]}")

# Filter to new construction, multifamily
dc_permits_full = con.execute(f"""
    SELECT
        \"ï»¿X\" as x_coord,
        Y as y_coord,
        LATITUDE,
        LONGITUDE,
        ISSUE_DATE,
        PERMIT_TYPE_NAME,
        PERMIT_SUBTYPE_NAME,
        PERMIT_CATEGORY_NAME,
        DESC_OF_WORK,
        FULL_ADDRESS,
        WARD,
        ZIPCODE
    FROM '{DATA}/dc_building_permits_raw.parquet'
    WHERE ISSUE_DATE >= '2019/01/01'
        AND (
            LOWER(PERMIT_TYPE_NAME) LIKE '%construction%'
            OR LOWER(PERMIT_TYPE_NAME) LIKE '%new%'
            OR LOWER(PERMIT_SUBTYPE_NAME) LIKE '%new%'
            OR LOWER(PERMIT_CATEGORY_NAME) LIKE '%new%'
        )
        AND LATITUDE IS NOT NULL
        AND LONGITUDE IS NOT NULL
""").df()
print(f"DC new construction permits (2019+): {len(dc_permits_full)}")
print(f"Permit types: {dc_permits_full['PERMIT_TYPE_NAME'].value_counts().head(10).to_string()}")

# Also check for multifamily keywords
dc_mf = con.execute(f"""
    SELECT
        LATITUDE, LONGITUDE, ISSUE_DATE, FULL_ADDRESS, DESC_OF_WORK,
        PERMIT_TYPE_NAME, PERMIT_SUBTYPE_NAME, PERMIT_CATEGORY_NAME,
        WARD, ZIPCODE
    FROM '{DATA}/dc_building_permits_raw.parquet'
    WHERE ISSUE_DATE >= '2019/01/01'
        AND LATITUDE IS NOT NULL AND LONGITUDE IS NOT NULL
        AND (
            LOWER(DESC_OF_WORK) LIKE '%apartment%'
            OR LOWER(DESC_OF_WORK) LIKE '%multi%'
            OR LOWER(DESC_OF_WORK) LIKE '%residential%'
            OR LOWER(DESC_OF_WORK) LIKE '%dwelling%'
            OR LOWER(DESC_OF_WORK) LIKE '%unit%'
            OR LOWER(PERMIT_CATEGORY_NAME) LIKE '%new%'
        )
""").df()
print(f"DC multifamily/residential permits (2019+): {len(dc_mf)}")
print(f"Subtypes: {dc_mf['PERMIT_SUBTYPE_NAME'].value_counts().head(10).to_string()}")

# For the map, let's use ALL construction permits (not just multifamily) since DC's database
# doesn't cleanly separate multifamily. We'll color by whether description mentions apartment/multi.
map_permits = con.execute(f"""
    SELECT
        LATITUDE, LONGITUDE,
        EXTRACT(YEAR FROM CAST(ISSUE_DATE AS DATE)) as year,
        FULL_ADDRESS,
        DESC_OF_WORK,
        WARD,
        CASE
            WHEN LOWER(DESC_OF_WORK) LIKE '%apartment%' OR LOWER(DESC_OF_WORK) LIKE '%multi%'
                OR LOWER(DESC_OF_WORK) LIKE '%dwelling%' OR LOWER(DESC_OF_WORK) LIKE '%condo%'
            THEN 'multifamily'
            ELSE 'other'
        END as permit_type
    FROM '{DATA}/dc_building_permits_raw.parquet'
    WHERE ISSUE_DATE >= '2019/01/01'
        AND LATITUDE IS NOT NULL AND LONGITUDE IS NOT NULL
        AND (
            LOWER(PERMIT_TYPE_NAME) LIKE '%construction%'
            OR LOWER(PERMIT_TYPE_NAME) LIKE '%new%'
            OR LOWER(PERMIT_SUBTYPE_NAME) LIKE '%new%'
            OR LOWER(PERMIT_CATEGORY_NAME) LIKE '%new%'
        )
""").df()

print(f"\nMap permit data: {len(map_permits)} permits")
print(f"  Multifamily: {(map_permits['permit_type']=='multifamily').sum()}")
print(f"  Other construction: {(map_permits['permit_type']=='other').sum()}")
print(f"  Year range: {map_permits['year'].min()}-{map_permits['year'].max()}")

# Convert to JSON for D3
permit_points = []
for _, r in map_permits.iterrows():
    if pd.notna(r['LATITUDE']) and pd.notna(r['LONGITUDE']):
        permit_points.append({
            "lat": round(float(r['LATITUDE']), 5),
            "lon": round(float(r['LONGITUDE']), 5),
            "year": int(r['year']) if pd.notna(r['year']) else 2020,
            "type": r['permit_type'],
            "address": str(r['FULL_ADDRESS'])[:60] if pd.notna(r['FULL_ADDRESS']) else "",
        })

permit_json = json.dumps(permit_points)

chart5_js = f"""
const PERMITS = {permit_json};
const WIDTH = 900, HEIGHT = 750;

const svg = d3.select(".chart-container").append("svg").attr("width", WIDTH).attr("height", HEIGHT);

// DC metro center and projection
const projection = d3.geoMercator()
    .center([-77.02, 38.905])
    .scale(95000)
    .translate([WIDTH / 2, HEIGHT / 2]);

// Draw DC boundary (approximate rectangle for now — we'll use actual boundary if available)
// For simplicity, draw just the permit dots on a clean background

// Background rect
svg.append("rect").attr("width", WIDTH).attr("height", HEIGHT).attr("fill", "{COLORS['bg_cream']}");

// Permit dots
PERMITS.forEach(p => {{
    const [px, py] = projection([p.lon, p.lat]);
    if (px > 0 && px < WIDTH && py > 0 && py < HEIGHT) {{
        svg.append("circle")
            .attr("cx", px).attr("cy", py)
            .attr("r", p.type === "multifamily" ? 4 : 2.5)
            .attr("fill", p.type === "multifamily" ? "{COLORS['red']}" : "{COLORS['blue']}")
            .attr("opacity", p.type === "multifamily" ? 0.7 : 0.3)
            .attr("stroke", "white").attr("stroke-width", 0.3);
    }}
}});

// Legend
const legend = svg.append("g").attr("transform", "translate(30, " + (HEIGHT - 80) + ")");
legend.append("rect").attr("width", 200).attr("height", 65).attr("fill", "white").attr("opacity", 0.85).attr("rx", 4);
legend.append("circle").attr("cx", 15).attr("cy", 20).attr("r", 4).attr("fill", "{COLORS['red']}").attr("opacity", 0.7);
legend.append("text").attr("x", 25).attr("y", 24).attr("font-size", 12).attr("fill", "{COLORS['black']}").text("Multifamily/apartment");
legend.append("circle").attr("cx", 15).attr("cy", 42).attr("r", 2.5).attr("fill", "{COLORS['blue']}").attr("opacity", 0.3);
legend.append("text").attr("x", 25).attr("y", 46).attr("font-size", 12).attr("fill", "{COLORS['black']}").text("Other new construction");

// Tooltip
const tooltip = d3.select("#tooltip");
svg.selectAll("circle").on("mouseover", function(event) {{
    const idx = PERMITS.findIndex(p => {{
        const [px, py] = projection([p.lon, p.lat]);
        return Math.abs(px - +d3.select(this).attr("cx")) < 1 && Math.abs(py - +d3.select(this).attr("cy")) < 1;
    }});
    if (idx >= 0) {{
        const p = PERMITS[idx];
        tooltip.html(`<strong>${{p.address}}</strong><br>Year: ${{p.year}}<br>Type: ${{p.type}}`)
            .style("left", (event.pageX + 12) + "px").style("top", (event.pageY - 28) + "px").style("opacity", 1);
    }}
}}).on("mouseout", () => tooltip.style("opacity", 0));
"""

chart5_html = html_wrapper(
    title="Where DC Built New Apartments (2019-2025)",
    subtitle="Each dot = one building permit. Red = multifamily/apartment, blue = other new construction.",
    source="Source: DC Open Data, Building Permits",
    body_content="", extra_css="", extra_js=chart5_js,
    width=900, height=750)

with open(f"{OUTPUTS}/04_dc_permit_map.html", 'w') as f:
    f.write(chart5_html)
print("  Saved 04_dc_permit_map.html")

# ═══════════════════════════════════════════════════════
# CHART 5: DC Metro ZIP-Level Rent Changes (Choropleth)
# ═══════════════════════════════════════════════════════
print("Chart 5: ZIP-level rent change map...")

# Compute rent change by ZIP (2019 → latest)
zip_rents = con.execute(f"""
    WITH base AS (
        SELECT RegionName as zip, zori as zori_2019
        FROM '{DATA}/zori_zip_dc_metro_region.parquet'
        WHERE date = '2019-01-31'
    ),
    latest AS (
        SELECT RegionName as zip, zori as zori_latest, date
        FROM '{DATA}/zori_zip_dc_metro_region.parquet'
        WHERE date = (SELECT MAX(date) FROM '{DATA}/zori_zip_dc_metro_region.parquet')
    )
    SELECT b.zip, b.zori_2019, l.zori_latest, l.date,
           (l.zori_latest / b.zori_2019 - 1) * 100 as rent_change_pct
    FROM base b
    JOIN latest l ON b.zip = l.zip
    ORDER BY rent_change_pct
""").df()

print(f"ZIP rent changes: {len(zip_rents)} ZIPs")
print(f"DC area ZIPs with rent data: {len(zip_rents)}")
print(f"Rent change range: {zip_rents['rent_change_pct'].min():.1f}% to {zip_rents['rent_change_pct'].max():.1f}%")
print(f"Median change: {zip_rents['rent_change_pct'].median():.1f}%")

# For DC metro, filter to ZIPs near DC (approximate lat/lon bounds)
# DC metro roughly: lat 38.5-39.3, lon -77.6 to -76.6
# We need ZIP centroids — use the Zillow data which has metro info

zip_with_metro = con.execute(f"""
    SELECT DISTINCT RegionName as zip, Metro, City, CountyName, State
    FROM '{DATA}/zori_zip_dc_metro_region.parquet'
    WHERE Metro LIKE '%Washington%'
""").df()
print(f"\nDC metro ZIPs in Zillow: {len(zip_with_metro)}")

# Merge rent changes with metro filter
dc_zip_changes = zip_rents.merge(zip_with_metro, on='zip', how='inner')
print(f"DC metro ZIPs with rent data: {len(dc_zip_changes)}")
print(f"\nBottom 10 rent changes (DC metro):")
print(dc_zip_changes.nsmallest(10, 'rent_change_pct')[['zip', 'City', 'rent_change_pct', 'zori_2019', 'zori_latest']].to_string(index=False))
print(f"\nTop 10 rent changes (DC metro):")
print(dc_zip_changes.nlargest(10, 'rent_change_pct')[['zip', 'City', 'rent_change_pct', 'zori_2019', 'zori_latest']].to_string(index=False))

# Save for use
dc_zip_changes.to_parquet(f"{DATA}/dc_zip_rent_changes.parquet", index=False)

# For the D3 choropleth, we need ZIP boundaries (GeoJSON)
# We'll use a D3 map with ZIP centroids as sized/colored circles instead of a full choropleth
# since we don't have ZIP boundary GeoJSON readily available

# Use approximate ZIP centroids from the Census
# For now, create a bubble map using known ZIP centroids
# We'll load a ZIP centroid file or compute from data

# Actually, let's try to get ZIP centroids from a public source
import requests
print("\nFetching ZIP centroid data...")

# Use Census ZCTA centroids — these are available in the data lake reference
# Or compute from the data we have

# For now, use a static approach: map ZIP to approximate lat/lon
# We can use the Zillow ZIP data which might have lat/lon, or use a lookup

# Let's check if there's a ZIP shapefile in the reference directory
import os
ref_files = os.listdir("/Users/azizsunderji/Dropbox/Home Economics/Reference/")
zip_files = [f for f in ref_files if 'zip' in f.lower() or 'zcta' in f.lower()]
print(f"ZIP reference files: {zip_files}")

# Load ZIP centroids from Census Gazetteer
gazetteer_url = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_zcta5_national.zip"
try:
    import zipfile
    import io as io_mod
    resp = requests.get(gazetteer_url, timeout=30)
    if resp.status_code == 200:
        zf = zipfile.ZipFile(io_mod.BytesIO(resp.content))
        fname = zf.namelist()[0]
        with zf.open(fname) as f:
            gaz = pd.read_csv(f, sep='\t', dtype={'GEOID': str})
        gaz.columns = [c.strip() for c in gaz.columns]
        print(f"Gazetteer loaded: {len(gaz)} ZCTAs, columns: {list(gaz.columns)}")

        # Merge with our rent change data
        gaz_dc = gaz[['GEOID', 'INTPTLAT', 'INTPTLONG']].rename(
            columns={'GEOID': 'zip', 'INTPTLAT': 'lat', 'INTPTLONG': 'lon'})

        dc_zip_map = dc_zip_changes.merge(gaz_dc, on='zip', how='inner')
        print(f"DC ZIPs with coordinates: {len(dc_zip_map)}")
    else:
        print(f"Gazetteer download failed: {resp.status_code}")
        dc_zip_map = pd.DataFrame()
except Exception as e:
    print(f"Error loading gazetteer: {e}")
    dc_zip_map = pd.DataFrame()

if len(dc_zip_map) > 0:
    # Build bubble map
    zip_points = []
    for _, r in dc_zip_map.iterrows():
        zip_points.append({
            "zip": str(r['zip']),
            "lat": round(float(r['lat']), 4),
            "lon": round(float(r['lon']), 4),
            "change": round(float(r['rent_change_pct']), 1),
            "rent_2019": round(float(r['zori_2019']), 0),
            "rent_latest": round(float(r['zori_latest']), 0),
            "city": str(r.get('City', ''))
        })

    zip_json = json.dumps(zip_points)

    chart6_js = f"""
    const ZIPS = {zip_json};
    const WIDTH = 900, HEIGHT = 750;

    const svg = d3.select(".chart-container").append("svg").attr("width", WIDTH).attr("height", HEIGHT);
    svg.append("rect").attr("width", WIDTH).attr("height", HEIGHT).attr("fill", "{COLORS['bg_cream']}");

    const projection = d3.geoMercator()
        .center([-77.15, 38.92])
        .scale(60000)
        .translate([WIDTH / 2, HEIGHT / 2]);

    // Color scale: blue (decline) → white (0) → red (increase)
    const changeExtent = d3.extent(ZIPS, d => d.change);
    const maxAbs = Math.max(Math.abs(changeExtent[0]), Math.abs(changeExtent[1]));
    const color = d3.scaleDiverging()
        .domain([-maxAbs * 0.3, 20, maxAbs])
        .interpolator(d3.interpolateRdBu)
        .clamp(true);

    // Draw ZIP bubbles
    const tooltip = d3.select("#tooltip");

    // Sort so smallest changes (closest to avg) are drawn first, extremes on top
    const sorted = ZIPS.slice().sort((a, b) => Math.abs(a.change - 20) - Math.abs(b.change - 20));

    sorted.forEach(z => {{
        const [px, py] = projection([z.lon, z.lat]);
        if (px > 0 && px < WIDTH && py > 0 && py < HEIGHT) {{
            svg.append("circle")
                .datum(z)
                .attr("cx", px).attr("cy", py)
                .attr("r", 8)
                .attr("fill", color(z.change))
                .attr("opacity", 0.7)
                .attr("stroke", "white").attr("stroke-width", 0.5)
                .on("mouseover", function(event, d) {{
                    d3.select(this).attr("stroke", "{COLORS['black']}").attr("stroke-width", 2).attr("opacity", 1);
                    tooltip.html(`<strong>ZIP ${{d.zip}}</strong> (${{d.city}})<br>Rent change: ${{d.change > 0 ? "+" : ""}}${{d.change.toFixed(1)}}%<br>2019: $${{d.rent_2019.toLocaleString()}}<br>Latest: $${{d.rent_latest.toLocaleString()}}`)
                        .style("left", (event.pageX + 12) + "px").style("top", (event.pageY - 28) + "px").style("opacity", 1);
                }})
                .on("mouseout", function() {{
                    d3.select(this).attr("stroke", "white").attr("stroke-width", 0.5).attr("opacity", 0.7);
                    tooltip.style("opacity", 0);
                }});
        }}
    }});

    // Color legend
    const legendW = 200, legendH = 15;
    const legendG = svg.append("g").attr("transform", `translate(${{WIDTH - legendW - 40}}, ${{HEIGHT - 70}})`);

    // Gradient
    const defs = svg.append("defs");
    const gradient = defs.append("linearGradient").attr("id", "legend-gradient");
    gradient.append("stop").attr("offset", "0%").attr("stop-color", color(-maxAbs * 0.3));
    gradient.append("stop").attr("offset", "50%").attr("stop-color", color(20));
    gradient.append("stop").attr("offset", "100%").attr("stop-color", color(maxAbs));

    legendG.append("rect").attr("width", legendW).attr("height", legendH).attr("fill", "url(#legend-gradient)").attr("rx", 2);
    legendG.append("text").attr("x", 0).attr("y", legendH + 15).attr("font-size", 10).attr("fill", "{COLORS['black']}").text("Lower growth");
    legendG.append("text").attr("x", legendW).attr("y", legendH + 15).attr("text-anchor", "end").attr("font-size", 10).attr("fill", "{COLORS['black']}").text("Higher growth");
    legendG.append("text").attr("x", legendW / 2).attr("y", -5).attr("text-anchor", "middle").attr("font-size", 11).attr("fill", "{COLORS['black']}").text("Rent change since Jan 2019");
    """

    chart6_html = html_wrapper(
        title="Where DC Metro Rents Changed Most",
        subtitle="Each circle = one ZIP code. Blue = below-average rent growth, red = above-average.",
        source="Source: Zillow ZORI (ZIP-level), Census ZCTA Gazetteer",
        body_content="", extra_css="", extra_js=chart6_js,
        width=900, height=750)

    with open(f"{OUTPUTS}/05_dc_zip_rent_map.html", 'w') as f:
        f.write(chart6_html)
    print("  Saved 05_dc_zip_rent_map.html")
else:
    print("  Skipping ZIP map — no centroid data")

# ═══════════════════════════════════════════════════════
# CHART 6: WFH share scatter (the big explanatory variable)
# ═══════════════════════════════════════════════════════
print("\nChart 6: WFH scatter...")

scatter7_data = []
for _, r in cum_scatter.iterrows():
    if pd.isna(r['avg_wfh']) or pd.isna(r['rent_change_pct']):
        continue
    name = r['RegionName'].split(',')[0] if pd.notna(r.get('RegionName')) else r['cbsa']
    scatter7_data.append({
        "name": name,
        "x": round(r['avg_wfh'], 1),
        "y": round(r['rent_change_pct'], 1),
        "group": "highlight" if r['is_dc'] else "default",
        "size": float(r.get('employed_pop', 1000000)) if pd.notna(r.get('employed_pop')) else 500000
    })

scatter7_json = json.dumps(scatter7_data)

chart7_js = f"""
const DATA = {scatter7_json};
const WIDTH = 900, HEIGHT = 650;
const MARGIN = {{top: 30, right: 30, bottom: 65, left: 75}};
const innerW = WIDTH - MARGIN.left - MARGIN.right;
const innerH = HEIGHT - MARGIN.top - MARGIN.bottom;

const svg = d3.select(".chart-container").append("svg").attr("width", WIDTH).attr("height", HEIGHT);
const g = svg.append("g").attr("transform", `translate(${{MARGIN.left}},${{MARGIN.top}})`);

const x = d3.scaleLinear().domain([d3.min(DATA, d => d.x) * 0.9, d3.max(DATA, d => d.x) * 1.1]).range([0, innerW]);
const y = d3.scaleLinear().domain([d3.min(DATA, d => d.y) * 0.9, d3.max(DATA, d => d.y) * 1.1]).range([innerH, 0]);
const r = d3.scaleSqrt().domain([0, d3.max(DATA, d => d.size)]).range([4, 18]);

g.append("g").attr("class", "grid").call(d3.axisLeft(y).tickSize(-innerW).tickFormat(""));

// Regression line
const xMean = d3.mean(DATA, d => d.x), yMean = d3.mean(DATA, d => d.y);
let num = 0, den = 0;
DATA.forEach(d => {{ num += (d.x - xMean) * (d.y - yMean); den += (d.x - xMean) ** 2; }});
const slope = num / den, intercept = yMean - slope * xMean;
const xRange = d3.extent(DATA, d => d.x);
g.append("line")
    .attr("x1", x(xRange[0])).attr("y1", y(intercept + slope * xRange[0]))
    .attr("x2", x(xRange[1])).attr("y2", y(intercept + slope * xRange[1]))
    .attr("stroke", "#999").attr("stroke-width", 1).attr("stroke-dasharray", "5,3");

g.append("g").attr("class", "axis").attr("transform", `translate(0,${{innerH}})`)
    .call(d3.axisBottom(x).ticks(6).tickFormat(d => d + "%"));
const yAx = g.append("g").attr("class", "axis")
    .call(d3.axisLeft(y).ticks(6).tickSize(0).tickFormat(d => d + "%"));
yAx.select(".domain").remove();

g.append("text").attr("class", "axis-label").attr("x", innerW / 2).attr("y", innerH + 50)
    .attr("text-anchor", "middle").attr("font-size", 13).attr("fill", "#3D3733").attr("font-weight", 300)
    .text("Average WFH Share (2019-2025)");
g.append("text").attr("class", "axis-label").attr("transform", "rotate(-90)")
    .attr("x", -innerH / 2).attr("y", -55).attr("text-anchor", "middle")
    .attr("font-size", 13).attr("fill", "#3D3733").attr("font-weight", 300)
    .text("Cumulative Rent Change, 2019-2025 (%)");

const tooltip = d3.select("#tooltip");
g.selectAll(".dot").data(DATA).join("circle").attr("class", "dot")
    .attr("cx", d => x(d.x)).attr("cy", d => y(d.y))
    .attr("r", d => r(d.size))
    .attr("fill", d => d.group === "highlight" ? "{COLORS['red']}" : "{COLORS['blue']}")
    .attr("opacity", d => d.group === "highlight" ? 0.9 : 0.4)
    .attr("stroke", d => d.group === "highlight" ? "{COLORS['black']}" : "white")
    .attr("stroke-width", d => d.group === "highlight" ? 2 : 0.5)
    .on("mouseover", function(event, d) {{
        d3.select(this).attr("opacity", 1).attr("stroke-width", 2);
        tooltip.html(`<strong>${{d.name}}</strong><br>WFH share: ${{d.x.toFixed(1)}}%<br>Rent change: ${{d.y.toFixed(1)}}%`)
            .style("left", (event.pageX + 12) + "px").style("top", (event.pageY - 28) + "px").style("opacity", 1);
    }})
    .on("mouseout", function() {{
        d3.select(this).attr("opacity", d => d.group === "highlight" ? 0.9 : 0.4).attr("stroke-width", d => d.group === "highlight" ? 2 : 0.5);
        tooltip.style("opacity", 0);
    }});

// Label DC + SF
DATA.filter(d => d.group === "highlight" || d.name === "San Francisco" || d.name === "San Jose" || d.name === "Austin").forEach(d => {{
    g.append("text").attr("x", x(d.x) + r(d.size) + 6).attr("y", y(d.y))
        .attr("dy", "0.35em")
        .attr("font-size", d.group === "highlight" ? 13 : 11)
        .attr("font-weight", d.group === "highlight" ? 500 : 400)
        .attr("fill", d.group === "highlight" ? "{COLORS['red']}" : "{COLORS['black']}")
        .text(d.name);
}});

// Annotation
g.append("text").attr("x", innerW - 10).attr("y", 15)
    .attr("text-anchor", "end").attr("font-size", 11).attr("fill", "#999").attr("font-style", "italic")
    .text("β = " + slope.toFixed(2) + "pp rent per 1pp WFH (p=0.03)");
"""

chart7_html = html_wrapper(
    title="Remote Work Is the Strongest Predictor of Weak Rents",
    subtitle="WFH share vs. cumulative rent change across ~50 metros, 2019-2025. DC is an outlier on both axes.",
    source="Source: ACS 1-Year (TRANWORK=80), Zillow ZORI",
    body_content="", extra_css=chart1_css, extra_js=chart7_js,
    width=900, height=650)

with open(f"{OUTPUTS}/06_wfh_scatter.html", 'w') as f:
    f.write(chart7_html)
print("  Saved 06_wfh_scatter.html")

# ═══════════════════════════════════════════════════════
# CHART 7: Dual-panel actual vs predicted (cumulative 2019-2025)
# Permits-only vs full model, one dot per metro
# ═══════════════════════════════════════════════════════
print("\nChart 7: Actual vs predicted (cumulative, dual panel)...")

cum = con.execute(f"SELECT * FROM '{DATA}/scatter_cumulative.parquet'").df()

# Load regression results for R² values
with open(f"{DATA}/regression_results.json") as f:
    reg_results = json.load(f)

r2_permits = reg_results.get('cum_permits_r2', 0.27)
r2_full = reg_results.get('cum_full_r2', 0.40)

# Build data for both panels
panel_data = []
for _, r in cum.iterrows():
    if pd.isna(r.get('pred_permits')) or pd.isna(r.get('pred_full')):
        continue
    name = r['RegionName'].split(',')[0] if pd.notna(r.get('RegionName')) else r['cbsa']
    panel_data.append({
        "name": name,
        "actual": round(float(r['rent_change_pct']), 1),
        "pred_permits": round(float(r['pred_permits']), 1),
        "pred_full": round(float(r['pred_full']), 1),
        "is_dc": bool(r['is_dc']),
    })

panel_json = json.dumps(panel_data)

chart_avp_js = f"""
const DATA = {panel_json};
const WIDTH = 900, HEIGHT = 500;
const MARGIN = {{top: 40, right: 20, bottom: 60, left: 60}};
const GAP = 70;
const panelW = (WIDTH - MARGIN.left - MARGIN.right - GAP) / 2;
const panelH = HEIGHT - MARGIN.top - MARGIN.bottom;

const svg = d3.select(".chart-container").append("svg").attr("width", WIDTH).attr("height", HEIGHT);

// Shared scales — use same domain for both panels
const allVals = DATA.flatMap(d => [d.actual, d.pred_permits, d.pred_full]);
const lo = Math.floor(d3.min(allVals) / 5) * 5;
const hi = Math.ceil(d3.max(allVals) / 5) * 5 + 5;

const tooltip = d3.select("#tooltip");

function drawPanel(xOffset, predKey, panelTitle, r2Val, showYLabel) {{
    const g = svg.append("g").attr("transform", `translate(${{xOffset}},${{MARGIN.top}})`);

    const x = d3.scaleLinear().domain([lo, hi]).range([0, panelW]);
    const y = d3.scaleLinear().domain([lo, hi]).range([panelH, 0]);

    // Grid
    g.append("g").attr("class", "grid").call(d3.axisLeft(y).tickSize(-panelW).tickFormat(""));

    // 45-degree line
    g.append("line")
        .attr("x1", x(lo)).attr("y1", y(lo))
        .attr("x2", x(hi)).attr("y2", y(hi))
        .attr("stroke", "#999").attr("stroke-width", 1.5).attr("stroke-dasharray", "5,3");

    // Axes
    g.append("g").attr("class", "axis").attr("transform", `translate(0,${{panelH}})`)
        .call(d3.axisBottom(x).ticks(5).tickFormat(d => d + "%"));
    const yAx = g.append("g").attr("class", "axis")
        .call(d3.axisLeft(y).ticks(5).tickSize(0).tickFormat(d => d + "%"));
    yAx.select(".domain").remove();

    // Axis labels
    g.append("text").attr("x", panelW / 2).attr("y", panelH + 45)
        .attr("text-anchor", "middle").attr("font-size", 12).attr("fill", "#3D3733").attr("font-weight", 300)
        .text("Model predicted (%)");
    if (showYLabel) {{
        g.append("text").attr("transform", "rotate(-90)").attr("x", -panelH / 2).attr("y", -45)
            .attr("text-anchor", "middle").attr("font-size", 12).attr("fill", "#3D3733").attr("font-weight", 300)
            .text("Actual cumulative rent change (%)");
    }}

    // Panel title
    g.append("text").attr("x", panelW / 2).attr("y", -15)
        .attr("text-anchor", "middle").attr("font-size", 14).attr("font-weight", 500).attr("fill", "#3D3733")
        .text(panelTitle);

    // R² annotation
    g.append("text").attr("x", panelW - 5).attr("y", panelH - 5)
        .attr("text-anchor", "end").attr("font-size", 12).attr("fill", "#999").attr("font-style", "italic")
        .text("R\\u00B2 = " + r2Val.toFixed(2));

    // Dots — draw non-DC first, DC on top
    const sorted = DATA.slice().sort((a, b) => a.is_dc - b.is_dc);
    sorted.forEach(d => {{
        const px = x(d[predKey]);
        const py = y(d.actual);
        g.append("circle")
            .attr("cx", px).attr("cy", py)
            .attr("r", d.is_dc ? 7 : 5)
            .attr("fill", d.is_dc ? "{COLORS['red']}" : "{COLORS['blue']}")
            .attr("opacity", d.is_dc ? 0.9 : 0.35)
            .attr("stroke", d.is_dc ? "{COLORS['black']}" : "white")
            .attr("stroke-width", d.is_dc ? 2 : 0.5)
            .on("mouseover", function(event) {{
                d3.select(this).attr("opacity", 1).attr("r", 8);
                tooltip.html(`<strong>${{d.name}}</strong><br>Actual: +${{d.actual.toFixed(1)}}%<br>Predicted: +${{d[predKey].toFixed(1)}}%`)
                    .style("left", (event.pageX + 12) + "px").style("top", (event.pageY - 28) + "px").style("opacity", 1);
            }})
            .on("mouseout", function() {{
                d3.select(this).attr("opacity", d.is_dc ? 0.9 : 0.35).attr("r", d.is_dc ? 7 : 5);
                tooltip.style("opacity", 0);
            }});
    }});

    // Label DC
    const dc = DATA.find(d => d.is_dc);
    if (dc) {{
        const cx = x(dc[predKey]);
        const cy = y(dc.actual);
        // Arrow line from label to dot
        const labelX = cx - 10;
        const labelY = cy - 18;
        g.append("text").attr("x", labelX).attr("y", labelY)
            .attr("text-anchor", "end")
            .attr("font-size", 12).attr("font-weight", 500).attr("fill", "{COLORS['red']}")
            .text("Washington DC");
        g.append("text").attr("x", labelX).attr("y", labelY + 14)
            .attr("text-anchor", "end")
            .attr("font-size", 10).attr("font-weight", 300).attr("fill", "{COLORS['red']}")
            .text("Actual +${{dc.actual.toFixed(0)}}%, predicted +${{dc[predKey].toFixed(0)}}%");
    }}
}}

// Left panel: permits only
drawPanel(MARGIN.left, "pred_permits", "Supply Only", {r2_permits}, true);

// Right panel: full model
drawPanel(MARGIN.left + panelW + GAP, "pred_full", "Supply + Jobs + WFH", {r2_full}, false);
"""

chart_avp_css = """
.axis text { font-size: 11px; fill: #3D3733; font-family: 'ABC Oracle Edu', system-ui; }
.grid line { stroke: #D0D0D0; stroke-width: 0.5; opacity: 0.7; }
.grid .domain { display: none; }
"""

chart_avp_html = html_wrapper(
    title="Supply Alone Can't Explain DC's Rent Gap",
    subtitle="Predicted vs. actual cumulative rent change (2019-2025), ~50 metros. Each dot = one metro.",
    source="Source: Zillow ZORI, BLS CES, Census BPS, ACS 1-Year. Cross-sectional OLS.",
    body_content="", extra_css=chart_avp_css, extra_js=chart_avp_js,
    width=900, height=500)

with open(f"{OUTPUTS}/07_actual_vs_predicted.html", 'w') as f:
    f.write(chart_avp_html)
print("  Saved 07_actual_vs_predicted.html")

print("\n" + "=" * 60)
print("ALL CHARTS COMPLETE")
print("=" * 60)
import os
for f in sorted(os.listdir(OUTPUTS)):
    size = os.path.getsize(f"{OUTPUTS}/{f}") / 1024
    print(f"  {f}: {size:.0f} KB")
