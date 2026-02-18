import sys
sys.path.insert(0, "/Users/azizsunderji/Dropbox/Home Economics/Scripts")

# Data from ATUS analysis: WFH day minus Office day (minutes)
# BA+, full-time, ages 25-54, weekdays, 2022-2024 pooled
# Office days n=1,219 | WFH days n=804

data = [
    # Savings (negative = less time on WFH day)
    ("Commuting", -49.0),
    ("Working", -46.2),
    ("Grooming", -16.2),
    # Gains (positive = more time on WFH day)
    ("Sleeping", 26.7),
    ("TV", 15.5),
    ("Cooking & eating", 7.0 + 6.4),
    ("Childcare", 11.8),
    ("Socializing", 3.6 + 3.5),  # Socializing + Phone calls
    ("Other travel", 6.9),
    ("Exercise", 5.8),
    ("Housework", 2.6 + 2.1),  # Housework + Yard & pets
    ("Shopping", 4.2),
    ("Other", 14.6 + 1.3 - 0.8),  # Other + Relaxing - Computer leisure
]

import json

items = []
running = 0
for label, val in data:
    start = running
    running += val
    items.append({
        "label": label,
        "value": round(val, 1),
        "start": round(start, 1),
        "end": round(running, 1)
    })

FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"

html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@font-face {{
    font-family: 'ABC Oracle Edu';
    src: url('{FONT_DIR}/ABCOracle-Regular.otf') format('opentype');
    font-weight: 400;
}}
@font-face {{
    font-family: 'ABC Oracle Edu';
    src: url('{FONT_DIR}/ABCOracle-Bold.otf') format('opentype');
    font-weight: 700;
}}
@font-face {{
    font-family: 'ABC Oracle Edu';
    src: url('{FONT_DIR}/ABCOracle-Light.otf') format('opentype');
    font-weight: 300;
}}
@font-face {{
    font-family: 'ABC Oracle Edu';
    src: url('{FONT_DIR}/ABCOracle-Medium.otf') format('opentype');
    font-weight: 500;
}}
body {{
    font-family: 'ABC Oracle Edu', sans-serif;
    background: #F6F7F3;
    margin: 0;
    display: flex;
    justify-content: center;
    padding-top: 20px;
}}
</style>
<script src="https://d3js.org/d3.v7.min.js"></script>
</head>
<body>
<script>
const data = {json.dumps(items)};

const width = 900;
const height = 750;
const margin = {{top: 100, right: 40, bottom: 80, left: 180}};
const innerW = width - margin.left - margin.right;
const innerH = height - margin.top - margin.bottom;

const svg = d3.select("body").append("svg")
    .attr("width", width)
    .attr("height", height)
    .style("background", "#F6F7F3");

const g = svg.append("g")
    .attr("transform", `translate(${{margin.left}},${{margin.top}})`);

// Title
svg.append("text")
    .attr("x", margin.left)
    .attr("y", 35)
    .attr("font-family", "ABC Oracle Edu, sans-serif")
    .attr("font-weight", 700)
    .attr("font-size", 22)
    .attr("fill", "#3D3733")
    .text("The Work-From-Home Day");

svg.append("text")
    .attr("x", margin.left)
    .attr("y", 58)
    .attr("font-family", "ABC Oracle Edu, sans-serif")
    .attr("font-weight", 400)
    .attr("font-size", 14)
    .attr("fill", "#888")
    .text("How a WFH day differs from an office day, in minutes");

svg.append("text")
    .attr("x", margin.left)
    .attr("y", 76)
    .attr("font-family", "ABC Oracle Edu, sans-serif")
    .attr("font-weight", 300)
    .attr("font-size", 11.5)
    .attr("fill", "#aaa")
    .text("College-educated, full-time workers ages 25–54, weekdays, 2022–2024");

// Scales
const allVals = data.flatMap(d => [d.start, d.end]);
const xMin = Math.min(...allVals) - 5;
const xMax = Math.max(...allVals) + 5;

const x = d3.scaleLinear()
    .domain([xMin, xMax])
    .range([0, innerW]);

const y = d3.scaleBand()
    .domain(data.map(d => d.label))
    .range([0, innerH])
    .padding(0.25);

// Zero line
g.append("line")
    .attr("x1", x(0))
    .attr("x2", x(0))
    .attr("y1", -5)
    .attr("y2", innerH + 5)
    .attr("stroke", "#3D3733")
    .attr("stroke-width", 1.5);

// Connector lines between bars
for (let i = 0; i < data.length - 1; i++) {{
    g.append("line")
        .attr("x1", x(data[i].end))
        .attr("x2", x(data[i].end))
        .attr("y1", y(data[i].label) + y.bandwidth())
        .attr("y2", y(data[i+1].label))
        .attr("stroke", "#ccc")
        .attr("stroke-width", 1)
        .attr("stroke-dasharray", "3,3");
}}

// Bars
g.selectAll(".bar")
    .data(data)
    .join("rect")
    .attr("x", d => x(Math.min(d.start, d.end)))
    .attr("y", d => y(d.label))
    .attr("width", d => Math.abs(x(d.end) - x(d.start)))
    .attr("height", y.bandwidth())
    .attr("fill", d => d.value < 0 ? "#0BB4FF" : "#F4743B")
    .attr("rx", 2);

// Value labels on bars
g.selectAll(".val-label")
    .data(data)
    .join("text")
    .attr("x", d => {{
        if (d.value < 0) return x(Math.min(d.start, d.end)) - 5;
        return x(Math.max(d.start, d.end)) + 5;
    }})
    .attr("y", d => y(d.label) + y.bandwidth() / 2)
    .attr("dy", "0.35em")
    .attr("text-anchor", d => d.value < 0 ? "end" : "start")
    .attr("font-family", "ABC Oracle Edu, sans-serif")
    .attr("font-weight", 500)
    .attr("font-size", 12)
    .attr("fill", "#3D3733")
    .text(d => (d.value > 0 ? "+" : "") + d.value.toFixed(0) + " min");

// Y-axis labels
g.selectAll(".y-label")
    .data(data)
    .join("text")
    .attr("x", -10)
    .attr("y", d => y(d.label) + y.bandwidth() / 2)
    .attr("dy", "0.35em")
    .attr("text-anchor", "end")
    .attr("font-family", "ABC Oracle Edu, sans-serif")
    .attr("font-weight", 400)
    .attr("font-size", 13)
    .attr("fill", "#3D3733")
    .text(d => d.label);

// Legend
const legendY = innerH + 45;
[["Time freed up", "#0BB4FF"], ["Time gained", "#F4743B"]].forEach(([label, color], i) => {{
    g.append("rect")
        .attr("x", i * 140)
        .attr("y", legendY)
        .attr("width", 14)
        .attr("height", 14)
        .attr("fill", color)
        .attr("rx", 2);
    g.append("text")
        .attr("x", i * 140 + 20)
        .attr("y", legendY + 7)
        .attr("dy", "0.35em")
        .attr("font-family", "ABC Oracle Edu, sans-serif")
        .attr("font-weight", 400)
        .attr("font-size", 12)
        .attr("fill", "#666")
        .text(label);
}});

// Source
svg.append("text")
    .attr("x", margin.left)
    .attr("y", height - 12)
    .attr("font-family", "ABC Oracle Edu, sans-serif")
    .attr("font-style", "italic")
    .attr("font-weight", 300)
    .attr("font-size", 10)
    .attr("fill", "#aaa")
    .text("Source: American Time Use Survey (IPUMS), 2022–2024. n = 2,023 diary days.");
</script>
</body>
</html>"""

output_path = "/Users/azizsunderji/Dropbox/Home Economics/2026_02_17_HardestWorkingCity/outputs/wfh_vs_office_waterfall.html"
with open(output_path, "w") as f:
    f.write(html)

print(f"Chart saved to {output_path}")
