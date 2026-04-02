"""
Rebuild scatter charts 1, 2, 3 with WHR 2026 data.
Uses D3.js with Oracle font, brand colors, collision-detected labels.
"""

import json
import csv
import os

BASE = "/Users/azizsunderji/Dropbox/Home Economics/2026_03_31_HousingHappiness"

# Load brand assets
with open(f"{BASE}/data/brand_assets_b64.json") as f:
    assets = json.load(f)

def font_faces():
    weights = {
        'Thin': 200, 'Light': 300, 'Book': 350,
        'Regular': 400, 'Medium': 500, 'Bold': 700
    }
    css = ""
    for name, w in weights.items():
        b64 = assets["fonts"][name]
        css += f"""
        @font-face {{
            font-family: 'ABC Oracle Edu';
            src: url('data:font/otf;base64,{b64}') format('opentype');
            font-weight: {w};
            font-style: normal;
        }}"""
    return css

def read_csv_file(filename):
    with open(f"{BASE}/data/{filename}") as f:
        reader = csv.DictReader(f)
        return list(reader)

def abbreviate_country(name):
    abbrevs = {
        'United States': 'US',
        'United Kingdom': 'UK',
        'New Zealand': 'NZ',
        'South Korea': 'S. Korea',
        'Switzerland': 'Switz.',
    }
    return abbrevs.get(name, name)

ZERO_LINES_JS = """
// Zero lines
if (xScale.domain()[0] < 0 && xScale.domain()[1] > 0) {
    svg.append("line")
        .attr("x1", xScale(0)).attr("x2", xScale(0))
        .attr("y1", plotTop).attr("y2", plotBottom)
        .attr("stroke", "#3D3733").attr("stroke-width", 1)
        .attr("stroke-dasharray", "6,4").attr("opacity", 0.5);
}
if (yScale.domain()[0] < 0 && yScale.domain()[1] > 0) {
    svg.append("line")
        .attr("x1", plotLeft).attr("x2", plotRight)
        .attr("y1", yScale(0)).attr("y2", yScale(0))
        .attr("stroke", "#3D3733").attr("stroke-width", 1)
        .attr("stroke-dasharray", "6,4").attr("opacity", 0.5);
}
"""

def scatter_html(config):
    data = config['data']
    x_col = config['x_col']
    y_col = config['y_col']

    points = []
    for row in data:
        points.append({
            'country': row['country'],
            'abbrev': abbreviate_country(row['country']),
            'x': float(row[x_col]),
            'y': float(row[y_col]),
            'anglophone': row.get('anglophone', 'False') == 'True'
        })

    points_json = json.dumps(points)
    title_json = json.dumps(config['title'])
    subtitle_json = json.dumps(config['subtitle'])
    corr_json = json.dumps(config['corr_text'])
    source_json = json.dumps(config.get('source', 'Source: OECD Analytical House Prices, World Happiness Report 2026'))
    x_format_js = config.get('x_format_js', 't.toFixed(0)')
    y_format_js = config.get('y_format_js', 't.toFixed(1)')
    zero_lines_block = ZERO_LINES_JS if config.get('zero_lines') else ''
    logo_b64 = assets['logo']
    ff = font_faces()

    html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
""" + ff + """
body {
    margin: 0;
    padding: 20px;
    background: #FFFFFF;
    font-family: 'ABC Oracle Edu', sans-serif;
}
</style>
</head>
<body>
<div id="chart"></div>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const data = """ + points_json + """;

const W = 960, H = 987;
const buffer = 40;
const gridLeft = buffer;
const gridRight = W - buffer;

const titleY = 40 + 32;
const subtitleY = titleY + 34;
const chartTop = subtitleY + 75;
const sourceLineH = 18;
const sourceBlockH = 2 * sourceLineH;
const sourceBottom = H - buffer;
const sourceTop = sourceBottom - sourceBlockH;
const chartBottom = sourceTop - 45 - 30;

const plotLeft = gridLeft + 70;
const plotRight = gridRight - 20;
const plotTop = chartTop;
const plotBottom = chartBottom;

const svg = d3.select("#chart")
    .append("svg")
    .attr("width", W)
    .attr("height", H)
    .attr("viewBox", "0 0 " + W + " " + H);

svg.append("rect")
    .attr("width", W)
    .attr("height", H)
    .attr("fill", "#F6F7F3");

svg.append("text")
    .attr("x", gridLeft)
    .attr("y", titleY)
    .attr("font-family", "ABC Oracle Edu")
    .attr("font-size", "32px")
    .attr("font-weight", 500)
    .attr("fill", "#3D3733")
    .text(""" + title_json + """);

svg.append("text")
    .attr("x", gridLeft)
    .attr("y", subtitleY)
    .attr("font-family", "ABC Oracle Edu")
    .attr("font-size", "23px")
    .attr("font-weight", 400)
    .attr("fill", "#7F7570")
    .text(""" + subtitle_json + """);

const xExtent = d3.extent(data, d => d.x);
const yExtent = d3.extent(data, d => d.y);
const xPad = (xExtent[1] - xExtent[0]) * 0.12;
const yPad = (yExtent[1] - yExtent[0]) * 0.12;

const xScale = d3.scaleLinear()
    .domain([xExtent[0] - xPad, xExtent[1] + xPad])
    .range([plotLeft, plotRight]);

const yScale = d3.scaleLinear()
    .domain([yExtent[0] - yPad, yExtent[1] + yPad])
    .range([plotBottom, plotTop]);

// Horizontal grid lines
const yTicks = yScale.ticks(6);
const gridG = svg.append("g").attr("id", "grid-lines");
yTicks.forEach(t => {
    gridG.append("line")
        .attr("x1", gridLeft)
        .attr("x2", gridRight)
        .attr("y1", yScale(t))
        .attr("y2", yScale(t))
        .attr("stroke", "#e1e2e3")
        .attr("stroke-width", 1);
});

// Vertical grid lines
const xTicks = xScale.ticks(6);
xTicks.forEach(t => {
    gridG.append("line")
        .attr("x1", xScale(t))
        .attr("x2", xScale(t))
        .attr("y1", plotTop)
        .attr("y2", plotBottom)
        .attr("stroke", "#e1e2e3")
        .attr("stroke-width", 1);
});

""" + zero_lines_block + """

// Y-axis labels
const yLabelsG = svg.append("g").attr("id", "y-axis-labels");
yTicks.forEach((t, i) => {
    let label = """ + y_format_js + """;
    yLabelsG.append("text")
        .attr("x", gridLeft)
        .attr("y", yScale(t))
        .attr("dy", "-0.5em")
        .attr("font-family", "ABC Oracle Edu")
        .attr("font-size", "22px")
        .attr("font-weight", 300)
        .attr("fill", "#333")
        .attr("text-anchor", "start")
        .text(label);
});

// X-axis ticks and labels
const xAxisG = svg.append("g").attr("id", "x-axis");
xTicks.forEach(t => {
    xAxisG.append("line")
        .attr("x1", xScale(t)).attr("x2", xScale(t))
        .attr("y1", plotBottom).attr("y2", plotBottom + 12)
        .attr("stroke", "#3D3733").attr("stroke-width", 0.5);

    let label = """ + x_format_js + """;
    xAxisG.append("text")
        .attr("x", xScale(t))
        .attr("y", plotBottom + 12)
        .attr("dy", "1.5em")
        .attr("font-family", "ABC Oracle Edu")
        .attr("font-size", "22px")
        .attr("font-weight", 300)
        .attr("fill", "#333")
        .attr("text-anchor", "middle")
        .text(label);
});

// Trend line (linear regression)
const n = data.length;
const xMean = d3.mean(data, d => d.x);
const yMean = d3.mean(data, d => d.y);
const ssXY = d3.sum(data, d => (d.x - xMean) * (d.y - yMean));
const ssXX = d3.sum(data, d => (d.x - xMean) ** 2);
const slope = ssXY / ssXX;
const intercept = yMean - slope * xMean;

const trendX1 = xScale.domain()[0];
const trendX2 = xScale.domain()[1];
svg.append("line")
    .attr("x1", xScale(trendX1))
    .attr("x2", xScale(trendX2))
    .attr("y1", yScale(slope * trendX1 + intercept))
    .attr("y2", yScale(slope * trendX2 + intercept))
    .attr("stroke", "#3D3733")
    .attr("stroke-width", 1.5)
    .attr("stroke-dasharray", "8,5")
    .attr("opacity", 0.4);

// Dots
const dotsG = svg.append("g").attr("id", "dots");
data.forEach(d => {
    dotsG.append("circle")
        .attr("cx", xScale(d.x))
        .attr("cy", yScale(d.y))
        .attr("r", 6)
        .attr("fill", d.anglophone ? "#F4743B" : "#0BB4FF")
        .attr("opacity", 0.85);
});

// Labels with collision detection
const labelFontSize = 16;
const charWidth = 5.5;
const labelPadX = 6;
const labelPadY = 4;

let labels = data.map(d => {
    const textWidth = d.abbrev.length * charWidth;
    return {
        text: d.abbrev,
        cx: xScale(d.x),
        cy: yScale(d.y),
        x: xScale(d.x) + 10,
        y: yScale(d.y) - 10,
        width: textWidth + labelPadX * 2,
        height: labelFontSize + labelPadY * 2,
        color: d.anglophone ? "#F4743B" : "#0BB4FF"
    };
});

function labelsOverlap(a, b) {
    return !(a.x + a.width < b.x || b.x + b.width < a.x ||
             a.y - a.height > b.y || b.y - b.height > a.y);
}

const positions = [
    [10, -10], [10, 20], [-10 - 60, -10], [-10 - 60, 20],
    [10, -25], [10, 35], [-10 - 60, -25], [-10 - 60, 35],
    [0, -30], [0, 30], [20, 0], [-80, 0],
    [10, -40], [10, 45], [-10 - 60, -40], [-10 - 60, 45],
];

for (let iter = 0; iter < 30; iter++) {
    let changed = false;
    for (let i = 0; i < labels.length; i++) {
        let hasOverlap = false;
        for (let j = 0; j < labels.length; j++) {
            if (i !== j && labelsOverlap(labels[i], labels[j])) {
                hasOverlap = true;
                break;
            }
        }
        if (hasOverlap) {
            for (const [dx, dy] of positions) {
                const oldX = labels[i].x;
                const oldY = labels[i].y;
                labels[i].x = labels[i].cx + dx;
                labels[i].y = labels[i].cy + dy;
                let stillOverlaps = false;
                for (let j = 0; j < labels.length; j++) {
                    if (i !== j && labelsOverlap(labels[i], labels[j])) {
                        stillOverlaps = true;
                        break;
                    }
                }
                if (!stillOverlaps) {
                    changed = true;
                    break;
                }
                labels[i].x = oldX;
                labels[i].y = oldY;
            }
        }
    }
    if (!changed) break;
}

// Draw labels with leader lines
const labelsG = svg.append("g").attr("id", "labels");
labels.forEach(l => {
    const dist = Math.sqrt((l.x - l.cx) ** 2 + (l.y - l.cy) ** 2);
    if (dist > 15) {
        labelsG.append("line")
            .attr("x1", l.cx)
            .attr("y1", l.cy)
            .attr("x2", l.x + (l.x < l.cx ? l.width / 2 : 0))
            .attr("y2", l.y - labelFontSize / 3)
            .attr("stroke", l.color)
            .attr("stroke-width", 0.7)
            .attr("opacity", 0.4);
    }
    // Halo
    labelsG.append("text")
        .attr("x", l.x)
        .attr("y", l.y)
        .attr("font-family", "ABC Oracle Edu")
        .attr("font-size", labelFontSize + "px")
        .attr("font-weight", 500)
        .attr("fill", "#F6F7F3")
        .attr("stroke", "#F6F7F3")
        .attr("stroke-width", 4)
        .attr("stroke-linejoin", "round")
        .attr("paint-order", "stroke")
        .text(l.text);
    // Colored label
    labelsG.append("text")
        .attr("x", l.x)
        .attr("y", l.y)
        .attr("font-family", "ABC Oracle Edu")
        .attr("font-size", labelFontSize + "px")
        .attr("font-weight", 500)
        .attr("fill", l.color)
        .text(l.text);
});

// Correlation annotation
svg.append("text")
    .attr("x", plotRight)
    .attr("y", plotTop + 20)
    .attr("text-anchor", "end")
    .attr("font-family", "ABC Oracle Edu")
    .attr("font-size", "18px")
    .attr("font-weight", 300)
    .attr("fill", "#7F7570")
    .attr("font-style", "italic")
    .text(""" + corr_json + """);

// Source
const sourceG = svg.append("g").attr("id", "source");
sourceG.append("text")
    .attr("x", gridLeft)
    .attr("y", sourceTop)
    .attr("font-family", "ABC Oracle Edu")
    .attr("font-size", "15px")
    .attr("font-weight", 200)
    .attr("fill", "#3D3733")
    .text(""" + source_json + """);

// Logo
svg.append("image")
    .attr("x", gridRight - 130)
    .attr("y", sourceTop - 10)
    .attr("width", 130)
    .attr("opacity", 0.6)
    .attr("href", "data:image/png;base64,""" + logo_b64 + """");

</script>
</body>
</html>"""

    outpath = f"{BASE}/outputs/{config['filename']}"
    with open(outpath, 'w') as f:
        f.write(html)
    print(f"Wrote {outpath}")
    return outpath


# ── Chart 1: PTI Change vs Happiness Change ──
changes_data = read_csv_file('whr2026_changes.csv')
scatter_html({
    'data': changes_data,
    'x_col': 'pti_change',
    'y_col': 'happiness_change_2006_2025',
    'title': 'Housing costs and happiness',
    'subtitle': 'Change in price-to-income index vs change in happiness, OECD countries',
    'corr_text': 'r = \u22120.34, p = 0.15',
    'source': 'Source: OECD Analytical House Prices, World Happiness Report 2026',
    'zero_lines': True,
    'x_format_js': "t.toFixed(0)",
    'y_format_js': "t.toFixed(1)",
    'filename': 'scatter_pti_change_vs_happiness_change.html'
})

# ── Chart 2: PTI Level vs Happiness (2023-25) ──
merged_data = read_csv_file('whr2026_merged_with_pti.csv')
scatter_html({
    'data': merged_data,
    'x_col': 'pti_2023_25',
    'y_col': 'happiness_score',
    'title': 'Housing costs and happiness today',
    'subtitle': 'OECD price-to-income index vs happiness score, 2023\u20132025 average',
    'corr_text': 'r = \u22120.27, not significant',
    'source': 'Source: OECD Analytical House Prices, World Happiness Report 2026',
    'zero_lines': False,
    'x_format_js': "t.toFixed(0)",
    'y_format_js': "t.toFixed(1)",
    'filename': 'scatter_pti_level_vs_happiness_2023.html'
})

# ── Chart 3: Long-term PTI Change vs Happiness ──
longterm_data = read_csv_file('whr2026_longterm.csv')
scatter_html({
    'data': longterm_data,
    'x_col': 'pti_change_pct',
    'y_col': 'happiness_score',
    'title': 'Long-term housing costs vs happiness today',
    'subtitle': 'Percent change in price-to-income index (2005\u20132025) vs happiness (2023\u20132025)',
    'corr_text': 'r = +0.13, not significant',
    'source': 'Source: OECD Analytical House Prices, World Happiness Report 2026',
    'zero_lines': False,
    'x_format_js': "t > 0 ? '+' + t.toFixed(0) + '%' : t.toFixed(0) + '%'",
    'y_format_js': "t.toFixed(1)",
    'filename': 'scatter_longterm_pti_vs_happiness.html'
})

print("All 3 charts generated.")
