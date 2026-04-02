import base64
import csv
import json

FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
LOGO_PATH = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/HomeEconomics-Logo-versions/HE-Large-Black.png"
DATA_PATH = "/Users/azizsunderji/Dropbox/Home Economics/2026_03_31_HousingHappiness/data/recent_changes.csv"
OUT_PATH = "/Users/azizsunderji/Dropbox/Home Economics/2026_03_31_HousingHappiness/outputs/scatter_recent_pti_vs_happiness_change.html"

def encode_file(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# Encode fonts
fonts = {}
for name in ["Thin", "Light", "Book", "Regular", "Medium", "Bold"]:
    fonts[name] = encode_file(f"{FONT_DIR}/ABCOracle-{name}.otf")

logo_b64 = encode_file(LOGO_PATH)

# Read data
data = []
with open(DATA_PATH) as f:
    reader = csv.DictReader(f)
    for row in reader:
        data.append({
            "country": row["country"],
            "pti_change": float(row["pti_change"]),
            "hap_change": float(row["hap_change"]),
            "anglophone": row["anglophone"] == "True"
        })

data_json = json.dumps(data)

html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@font-face {{ font-family:'ABC Oracle Edu'; src:url('data:font/otf;base64,{fonts["Thin"]}') format('opentype'); font-weight:200; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('data:font/otf;base64,{fonts["Light"]}') format('opentype'); font-weight:300; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('data:font/otf;base64,{fonts["Book"]}') format('opentype'); font-weight:350; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('data:font/otf;base64,{fonts["Regular"]}') format('opentype'); font-weight:400; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('data:font/otf;base64,{fonts["Medium"]}') format('opentype'); font-weight:500; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('data:font/otf;base64,{fonts["Bold"]}') format('opentype'); font-weight:700; }}
body {{ margin: 0; background: #FFFFFF; display: flex; justify-content: center; padding: 20px; }}
</style>
</head>
<body>
<script src="https://d3js.org/d3.js"></script>
<script>
const data = {data_json};

const W = 960, H = 987;
const buf = 40;
const gridLeft = buf;
const gridRight = W - buf;
const titleY = 40 + 32;
const subtitleY = titleY + 34;
const chartTop = subtitleY + 75;

// Source/logo at bottom
const sourceSize = 15;
const sourceY = H - buf;
const xAxisLabelGap = 45;

// Chart bottom: sourceY - xAxisLabelGap - space for x-axis labels
const xLabelSpace = 50; // space for x-axis tick labels
const chartBottom = sourceY - xAxisLabelGap - xLabelSpace;

const chartLeft = gridLeft + 60; // room for y-axis labels
const chartRight = gridRight;
const chartWidth = chartRight - chartLeft;
const chartHeight = chartBottom - chartTop;

const svg = d3.select("body").append("svg")
    .attr("width", W)
    .attr("height", H)
    .attr("viewBox", `0 0 ${{W}} ${{H}}`);

// Background
svg.append("rect").attr("width", W).attr("height", H).attr("fill", "#F6F7F3");

// Title
svg.append("text")
    .attr("x", gridLeft).attr("y", titleY)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", 32).attr("font-weight", 500)
    .attr("fill", "#3D3733").text("The recent picture");

// Subtitle
svg.append("text")
    .attr("x", gridLeft).attr("y", subtitleY)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", 23).attr("font-weight", 400)
    .attr("fill", "#7F7570").text("Change in price-to-income index vs change in happiness, 2018 to 2023");

// Scales
const xExtent = d3.extent(data, d => d.pti_change);
const yExtent = d3.extent(data, d => d.hap_change);
const xPad = (xExtent[1] - xExtent[0]) * 0.1;
const yPad = (yExtent[1] - yExtent[0]) * 0.1;

const xScale = d3.scaleLinear()
    .domain([xExtent[0] - xPad, xExtent[1] + xPad])
    .range([chartLeft, chartRight]);

const yScale = d3.scaleLinear()
    .domain([yExtent[0] - yPad, yExtent[1] + yPad])
    .range([chartBottom, chartTop]);

// Grid lines
const xTicks = xScale.ticks(8);
const yTicks = yScale.ticks(8);

// Horizontal grid
const gridG = svg.append("g").attr("id", "grid-lines");
yTicks.forEach(t => {{
    gridG.append("line")
        .attr("x1", chartLeft).attr("x2", chartRight)
        .attr("y1", yScale(t)).attr("y2", yScale(t))
        .attr("stroke", "#e1e2e3").attr("stroke-width", 1);
}});
// Vertical grid
xTicks.forEach(t => {{
    gridG.append("line")
        .attr("x1", xScale(t)).attr("x2", xScale(t))
        .attr("y1", chartTop).attr("y2", chartBottom)
        .attr("stroke", "#e1e2e3").attr("stroke-width", 1);
}});

// Zero lines (dashed)
if (xScale.domain()[0] < 0 && xScale.domain()[1] > 0) {{
    svg.append("line")
        .attr("x1", xScale(0)).attr("x2", xScale(0))
        .attr("y1", chartTop).attr("y2", chartBottom)
        .attr("stroke", "#3D3733").attr("stroke-width", 0.5)
        .attr("stroke-dasharray", "4,3");
}}
if (yScale.domain()[0] < 0 && yScale.domain()[1] > 0) {{
    svg.append("line")
        .attr("x1", chartLeft).attr("x2", chartRight)
        .attr("y1", yScale(0)).attr("y2", yScale(0))
        .attr("stroke", "#3D3733").attr("stroke-width", 0.5)
        .attr("stroke-dasharray", "4,3");
}}

// Y-axis labels
const yLabelsG = svg.append("g").attr("id", "y-axis-labels");
yTicks.forEach((t, i) => {{
    yLabelsG.append("text")
        .attr("x", gridLeft).attr("y", yScale(t))
        .attr("dy", "-0.5em")
        .attr("font-family", "ABC Oracle Edu").attr("font-size", 22).attr("font-weight", 300)
        .attr("fill", "#333").attr("text-anchor", "start")
        .text(t.toFixed(1));
}});

// X-axis ticks and labels
const xTicksG = svg.append("g").attr("id", "x-axis-ticks");
const xLabelsG = svg.append("g").attr("id", "x-axis-labels");
xTicks.forEach(t => {{
    xTicksG.append("line")
        .attr("x1", xScale(t)).attr("x2", xScale(t))
        .attr("y1", chartBottom).attr("y2", chartBottom + 12)
        .attr("stroke", "#3D3733").attr("stroke-width", 0.5);
    xLabelsG.append("text")
        .attr("x", xScale(t)).attr("y", chartBottom + 12)
        .attr("dy", "1.5em")
        .attr("font-family", "ABC Oracle Edu").attr("font-size", 22).attr("font-weight", 300)
        .attr("fill", "#333").attr("text-anchor", "middle")
        .text(t);
}});

// Axis labels
svg.append("text")
    .attr("x", (chartLeft + chartRight) / 2).attr("y", chartBottom + 12 + 22 + 30)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", 22).attr("font-weight", 300)
    .attr("fill", "#333").attr("text-anchor", "middle")
    .text("Change in price-to-income index");

// Y-axis label (rotated)
svg.append("text")
    .attr("transform", `translate(${{gridLeft - 10}}, ${{(chartTop + chartBottom) / 2}}) rotate(-90)`)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", 22).attr("font-weight", 300)
    .attr("fill", "#333").attr("text-anchor", "middle")
    .text("Change in happiness score");

// Regression line
const n = data.length;
const xMean = d3.mean(data, d => d.pti_change);
const yMean = d3.mean(data, d => d.hap_change);
let ssXX = 0, ssXY = 0;
data.forEach(d => {{
    ssXX += (d.pti_change - xMean) ** 2;
    ssXY += (d.pti_change - xMean) * (d.hap_change - yMean);
}});
const slope = ssXY / ssXX;
const intercept = yMean - slope * xMean;

const regX1 = xScale.domain()[0];
const regX2 = xScale.domain()[1];
svg.append("line")
    .attr("x1", xScale(regX1)).attr("y1", yScale(slope * regX1 + intercept))
    .attr("x2", xScale(regX2)).attr("y2", yScale(slope * regX2 + intercept))
    .attr("stroke", "#3D3733").attr("stroke-width", 1)
    .attr("stroke-dasharray", "6,4");

// Dots
const dotsG = svg.append("g").attr("id", "data-series");
data.forEach(d => {{
    dotsG.append("circle")
        .attr("cx", xScale(d.pti_change))
        .attr("cy", yScale(d.hap_change))
        .attr("r", 6)
        .attr("fill", d.anglophone ? "#F4743B" : "#0BB4FF")
        .attr("opacity", 0.9);
}});

// Labels with collision detection
const labelData = data.map(d => ({{
    country: d.country,
    x: xScale(d.pti_change),
    y: yScale(d.hap_change),
    color: d.anglophone ? "#F4743B" : "#0BB4FF",
    pti: d.pti_change,
    hap: d.hap_change
}}));

// Estimate label dimensions
const charWidth = 5.5; // approx px per char at 16px
const labelHeight = 18;
const labelPadX = 8;  // offset from dot
const labelPadY = 5;

// Initial label positions (to the right of dot)
labelData.forEach(d => {{
    d.labelX = d.x + labelPadX + 6;
    d.labelY = d.y + labelHeight / 4;
    d.labelW = d.country.length * charWidth;
    d.useLeader = false;
}});

// Collision detection - greedy approach
function overlaps(a, b) {{
    return !(a.labelX + a.labelW < b.labelX - 4 ||
             b.labelX + b.labelW < a.labelX - 4 ||
             a.labelY - labelHeight > b.labelY + 2 ||
             b.labelY - labelHeight > a.labelY + 2);
}}

// Sort by x position for greedy placement
labelData.sort((a, b) => a.x - b.x);

// Try to resolve overlaps with offsets
for (let iter = 0; iter < 5; iter++) {{
    for (let i = 0; i < labelData.length; i++) {{
        for (let j = i + 1; j < labelData.length; j++) {{
            if (overlaps(labelData[i], labelData[j])) {{
                // Try moving j above or below
                const offsets = [-labelHeight - 6, labelHeight + 6, -2 * labelHeight - 12, 2 * labelHeight + 12,
                                 -3 * labelHeight - 18, 3 * labelHeight + 18];
                let resolved = false;
                for (const off of offsets) {{
                    const newY = labelData[j].y + labelHeight / 4 + off;
                    const old = labelData[j].labelY;
                    labelData[j].labelY = newY;
                    let anyOverlap = false;
                    for (let k = 0; k < labelData.length; k++) {{
                        if (k !== j && overlaps(labelData[j], labelData[k])) {{
                            anyOverlap = true;
                            break;
                        }}
                    }}
                    if (!anyOverlap && newY > chartTop && newY < chartBottom) {{
                        labelData[j].useLeader = Math.abs(off) > labelHeight;
                        resolved = true;
                        break;
                    }}
                    labelData[j].labelY = old;
                }}
                // If still overlapping, try left side
                if (!resolved) {{
                    const oldX = labelData[j].labelX;
                    labelData[j].labelX = labelData[j].x - labelPadX - 6 - labelData[j].labelW;
                    let anyOverlap = false;
                    for (let k = 0; k < labelData.length; k++) {{
                        if (k !== j && overlaps(labelData[j], labelData[k])) {{
                            anyOverlap = true;
                            break;
                        }}
                    }}
                    if (!anyOverlap && labelData[j].labelX > chartLeft) {{
                        labelData[j].useLeader = false;
                        resolved = true;
                    }} else {{
                        labelData[j].labelX = oldX;
                    }}
                }}
                // If still not resolved, try left side with y offsets
                if (!resolved) {{
                    for (const off of offsets) {{
                        const oldX = labelData[j].labelX;
                        const oldY = labelData[j].labelY;
                        labelData[j].labelX = labelData[j].x - labelPadX - 6 - labelData[j].labelW;
                        labelData[j].labelY = labelData[j].y + labelHeight / 4 + off;
                        let anyOverlap = false;
                        for (let k = 0; k < labelData.length; k++) {{
                            if (k !== j && overlaps(labelData[j], labelData[k])) {{
                                anyOverlap = true;
                                break;
                            }}
                        }}
                        if (!anyOverlap && labelData[j].labelX > chartLeft && labelData[j].labelY > chartTop && labelData[j].labelY < chartBottom) {{
                            labelData[j].useLeader = Math.abs(off) > labelHeight;
                            resolved = true;
                            break;
                        }}
                        labelData[j].labelX = oldX;
                        labelData[j].labelY = oldY;
                    }}
                }}
            }}
        }}
    }}
}}

// Draw labels and leader lines
const labelsG = svg.append("g").attr("id", "labels");
labelData.forEach(d => {{
    if (d.useLeader) {{
        labelsG.append("line")
            .attr("x1", d.x).attr("y1", d.y)
            .attr("x2", d.labelX).attr("y2", d.labelY)
            .attr("stroke", "#999").attr("stroke-width", 0.5);
    }}
    // Halo
    labelsG.append("text")
        .attr("x", d.labelX).attr("y", d.labelY)
        .attr("font-family", "ABC Oracle Edu").attr("font-size", 16).attr("font-weight", 500)
        .attr("fill", "#F6F7F3").attr("stroke", "#F6F7F3").attr("stroke-width", 4)
        .attr("stroke-linejoin", "round").attr("paint-order", "stroke")
        .text(d.country);
    // Text
    labelsG.append("text")
        .attr("x", d.labelX).attr("y", d.labelY)
        .attr("font-family", "ABC Oracle Edu").attr("font-size", 16).attr("font-weight", 500)
        .attr("fill", d.color)
        .text(d.country);
}});

// Correlation annotation
svg.append("text")
    .attr("x", chartRight - 10).attr("y", chartTop + 20)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", 14).attr("font-weight", 300)
    .attr("fill", "#7F7570").attr("text-anchor", "end").attr("font-style", "italic")
    .text("r = \\u22120.16, not significant");

// Source note
svg.append("text")
    .attr("x", gridLeft).attr("y", sourceY)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", 15).attr("font-weight", 200)
    .attr("fill", "#3D3733")
    .text("Source: OECD Analytical House Prices, World Happiness Report via Our World in Data");

// Logo
svg.append("image")
    .attr("xlink:href", "data:image/png;base64,{logo_b64}")
    .attr("width", 130)
    .attr("x", chartRight - 130)
    .attr("y", sourceY - 25)
    .attr("opacity", 0.6);

</script>
</body>
</html>"""

with open(OUT_PATH, "w") as f:
    f.write(html)

print("Done:", OUT_PATH)
