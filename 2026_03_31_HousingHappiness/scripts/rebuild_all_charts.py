"""
Rebuild ALL scatter charts with proper axis labels, titles, subtitles, and time periods.
Uses WHR 2026 data (2023-2025 averages).
"""

import pandas as pd
import numpy as np
from scipy import stats
import base64, os, json

PROJECT = "/Users/azizsunderji/Dropbox/Home Economics/2026_03_31_HousingHappiness"
DATA = f"{PROJECT}/data"
OUTPUTS = f"{PROJECT}/outputs"
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
LOGO_PATH = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/HomeEconomics-Logo-versions/HE-Large-Black.png"

# ── Load fonts and logo as base64 ──────────────────────────────────────────
def b64(path):
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode()

font_light = b64(f"{FONT_DIR}/ABCOracle-Light.otf")
font_regular = b64(f"{FONT_DIR}/ABCOracle-Regular.otf")
font_medium = b64(f"{FONT_DIR}/ABCOracle-Medium.otf")
font_bold = b64(f"{FONT_DIR}/ABCOracle-Bold.otf")
logo_b64 = b64(LOGO_PATH)

FONT_FACES = f"""
@font-face {{ font-family: 'ABC Oracle Edu'; src: url(data:font/opentype;base64,{font_light}) format('opentype'); font-weight: 300; }}
@font-face {{ font-family: 'ABC Oracle Edu'; src: url(data:font/opentype;base64,{font_regular}) format('opentype'); font-weight: 400; }}
@font-face {{ font-family: 'ABC Oracle Edu'; src: url(data:font/opentype;base64,{font_medium}) format('opentype'); font-weight: 500; }}
@font-face {{ font-family: 'ABC Oracle Edu'; src: url(data:font/opentype;base64,{font_bold}) format('opentype'); font-weight: 700; }}
"""

def scatter_chart(data, title, subtitle, x_label, y_label, corr_text, source, filename,
                  x_col='x', y_col='y', country_col='country', anglo_col='anglophone',
                  show_zero_lines=True, show_trend=True):
    """Generate a complete D3 scatter chart with all labels."""

    # Compute regression
    valid = [(d[x_col], d[y_col]) for d in data if pd.notna(d[x_col]) and pd.notna(d[y_col])]
    xs = [v[0] for v in valid]
    ys = [v[1] for v in valid]

    data_json = json.dumps([{
        'x': float(d[x_col]),
        'y': float(d[y_col]),
        'country': d[country_col],
        'anglophone': bool(d[anglo_col])
    } for d in data if pd.notna(d[x_col]) and pd.notna(d[y_col])])

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>{FONT_FACES}
body {{ margin: 0; padding: 0; background: white; }}
</style>
<script src="https://d3js.org/d3.v7.min.js"></script>
</head><body>
<script>
const W = 960, H = 987;
const buffer = 40;
const titleY = buffer + 32;
const subtitleY = titleY + 34;
const chartTop = subtitleY + 75;
const sourceBottom = H - buffer;
const sourceLineH = 18;
const sourceTop = sourceBottom - sourceLineH;
const xAxisLabelH = 30;
const chartBottom = sourceTop - 45 - xAxisLabelH;
const gridLeft = buffer;
const gridRight = W - buffer;

const data = {data_json};

const svg = d3.select("body").append("svg")
    .attr("width", W).attr("height", H)
    .attr("viewBox", `0 0 ${{W}} ${{H}}`);

// Background
svg.append("rect").attr("width", W).attr("height", H).attr("fill", "#F6F7F3");

// Title
svg.append("text").attr("x", gridLeft).attr("y", titleY)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", "32px")
    .attr("font-weight", 500).attr("fill", "#3D3733")
    .text("{title}");

// Subtitle
svg.append("text").attr("x", gridLeft).attr("y", subtitleY)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", "23px")
    .attr("font-weight", 400).attr("fill", "#7F7570")
    .text("{subtitle}");

// Scales
const xExtent = d3.extent(data, d => d.x);
const yExtent = d3.extent(data, d => d.y);
const xPad = (xExtent[1] - xExtent[0]) * 0.12;
const yPad = (yExtent[1] - yExtent[0]) * 0.12;

const xScale = d3.scaleLinear()
    .domain([xExtent[0] - xPad, xExtent[1] + xPad])
    .range([gridLeft + 40, gridRight - 20]);

const yScale = d3.scaleLinear()
    .domain([yExtent[0] - yPad, yExtent[1] + yPad])
    .range([chartBottom, chartTop]);

// Grid lines
const yTicks = yScale.ticks(6);
yTicks.forEach(t => {{
    svg.append("line")
        .attr("x1", gridLeft).attr("x2", gridRight)
        .attr("y1", yScale(t)).attr("y2", yScale(t))
        .attr("stroke", "#e1e2e3").attr("stroke-width", 1);

    let label = t % 1 === 0 ? t.toFixed(0) : t.toFixed(1);
    svg.append("text")
        .attr("x", gridLeft).attr("y", yScale(t)).attr("dy", "-0.5em")
        .attr("font-family", "ABC Oracle Edu").attr("font-size", "22px")
        .attr("font-weight", 300).attr("fill", "#333")
        .attr("text-anchor", "start").text(label);
}});

// X-axis ticks
const xTicks = xScale.ticks(7);
xTicks.forEach(t => {{
    svg.append("line")
        .attr("x1", xScale(t)).attr("x2", xScale(t))
        .attr("y1", chartBottom).attr("y2", chartBottom + 12)
        .attr("stroke", "#3D3733").attr("stroke-width", 0.5);

    svg.append("text")
        .attr("x", xScale(t)).attr("y", chartBottom + 12).attr("dy", "1.5em")
        .attr("font-family", "ABC Oracle Edu").attr("font-size", "22px")
        .attr("font-weight", 300).attr("fill", "#333")
        .attr("text-anchor", "middle").text(t);
}});

// ── AXIS TITLE LABELS ──
// X-axis title
svg.append("text")
    .attr("x", (gridLeft + gridRight) / 2)
    .attr("y", chartBottom + 65)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", "18px")
    .attr("font-weight", 400).attr("fill", "#7F7570")
    .attr("text-anchor", "middle")
    .text("{x_label}");

// Y-axis title (rotated)
svg.append("text")
    .attr("transform", `rotate(-90,${{gridLeft - 5}},${{(chartTop + chartBottom) / 2}})`)
    .attr("x", gridLeft - 5)
    .attr("y", (chartTop + chartBottom) / 2)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", "18px")
    .attr("font-weight", 400).attr("fill", "#7F7570")
    .attr("text-anchor", "middle")
    .text("{y_label}");

{"" if not show_zero_lines else '''
// Zero lines
if (xScale.domain()[0] < 0 && xScale.domain()[1] > 0) {
    svg.append("line")
        .attr("x1", xScale(0)).attr("x2", xScale(0))
        .attr("y1", chartTop).attr("y2", chartBottom)
        .attr("stroke", "#3D3733").attr("stroke-width", 0.5)
        .attr("stroke-dasharray", "4,3");
}
if (yScale.domain()[0] < 0 && yScale.domain()[1] > 0) {
    svg.append("line")
        .attr("x1", gridLeft).attr("x2", gridRight)
        .attr("y1", yScale(0)).attr("y2", yScale(0))
        .attr("stroke", "#3D3733").attr("stroke-width", 0.5)
        .attr("stroke-dasharray", "4,3");
}
'''}

{"" if not show_trend else '''
// Trend line
const n = data.length;
const xMean = d3.mean(data, d => d.x);
const yMean = d3.mean(data, d => d.y);
const ssXY = d3.sum(data, d => (d.x - xMean) * (d.y - yMean));
const ssXX = d3.sum(data, d => (d.x - xMean) ** 2);
const slope = ssXY / ssXX;
const intercept = yMean - slope * xMean;
svg.append("line")
    .attr("x1", xScale(xScale.domain()[0]))
    .attr("x2", xScale(xScale.domain()[1]))
    .attr("y1", yScale(slope * xScale.domain()[0] + intercept))
    .attr("y2", yScale(slope * xScale.domain()[1] + intercept))
    .attr("stroke", "#3D3733").attr("stroke-width", 1.5)
    .attr("stroke-dasharray", "8,5").attr("opacity", 0.35);
'''}

// Correlation annotation
svg.append("text")
    .attr("x", gridRight - 10).attr("y", chartTop + 20)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", "15px")
    .attr("font-weight", 300).attr("fill", "#999")
    .attr("font-style", "italic").attr("text-anchor", "end")
    .text("{corr_text}");

// Dots
data.forEach(d => {{
    svg.append("circle")
        .attr("cx", xScale(d.x)).attr("cy", yScale(d.y))
        .attr("r", 6).attr("fill", d.anglophone ? "#F4743B" : "#0BB4FF")
        .attr("opacity", 0.85);
}});

// Labels with collision detection
const labelSize = 16;
const cw = 5.5;
let labels = data.map(d => ({{
    text: d.country, cx: xScale(d.x), cy: yScale(d.y),
    x: xScale(d.x) + 10, y: yScale(d.y) - 10,
    w: d.country.length * cw + 12, h: labelSize + 8,
    color: d.anglophone ? "#F4743B" : "#0BB4FF"
}}));

function overlaps(a, b) {{
    return !(a.x + a.w < b.x || b.x + b.w < a.x || a.y + a.h < b.y - a.h || b.y + b.h < a.y - b.h);
}}

// Simple collision resolution: try 8 positions around each dot
const offsets = [[10,-10],[10,10],[-10,-10],[-10,10],[10,-25],[10,25],[-10,-25],[-10,25]];
for (let i = 0; i < labels.length; i++) {{
    for (let j = 0; j < i; j++) {{
        if (overlaps(labels[i], labels[j])) {{
            for (const [ox, oy] of offsets) {{
                const newX = labels[i].cx + ox;
                const newY = labels[i].cy + oy;
                const test = {{...labels[i], x: newX, y: newY}};
                let ok = true;
                for (let k = 0; k < i; k++) {{
                    if (overlaps(test, labels[k])) {{ ok = false; break; }}
                }}
                if (ok) {{ labels[i].x = newX; labels[i].y = newY; break; }}
            }}
        }}
    }}
}}

labels.forEach(l => {{
    // Leader line if label is far from dot
    const dist = Math.sqrt((l.x - l.cx)**2 + (l.y - l.cy)**2);
    if (dist > 15) {{
        svg.append("line")
            .attr("x1", l.cx).attr("y1", l.cy)
            .attr("x2", l.x).attr("y2", l.y)
            .attr("stroke", "#ccc").attr("stroke-width", 0.5);
    }}
    svg.append("text")
        .attr("x", l.x).attr("y", l.y)
        .attr("font-family", "ABC Oracle Edu").attr("font-size", labelSize + "px")
        .attr("font-weight", 500).attr("fill", l.color)
        .text(l.text);
}});

// Source
svg.append("text")
    .attr("x", gridLeft).attr("y", sourceTop)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", "15px")
    .attr("font-weight", 200).attr("fill", "#3D3733")
    .text("{source}");

// Logo
svg.append("image")
    .attr("href", "data:image/png;base64,{logo_b64}")
    .attr("x", gridRight - 130).attr("y", sourceTop - 20)
    .attr("width", 130).attr("opacity", 0.6);

</script></body></html>"""

    path = f"{OUTPUTS}/{filename}"
    with open(path, 'w') as f:
        f.write(html)
    print(f"  Saved: {filename}")


# ── Load data ──────────────────────────────────────────────────────────────
merged = pd.read_csv(f"{DATA}/whr2026_merged_with_pti.csv")
changes = pd.read_csv(f"{DATA}/whr2026_changes.csv")
longterm = pd.read_csv(f"{DATA}/whr2026_longterm.csv")

# Compute recent changes (2018 → 2023-25)
happiness_old = pd.read_csv(f"{DATA}/happiness_raw.csv")
hap_2018 = happiness_old[happiness_old['year'] == 2018][['country', 'cantril_ladder_score']].rename(
    columns={'cantril_ladder_score': 'hap_2018'})
whr2026 = pd.read_csv(f"{DATA}/whr2026_rankings.csv")
whr2026.loc[whr2026['country'] == 'Republic of Korea', 'country'] = 'South Korea'

GHC = "/Users/azizsunderji/Dropbox/Home Economics/GlobalHousingCrisis"
oecd_file = f"{GHC}/OECD.ECO.MPD,DSD_AN_HOUSE_PRICES@DF_HOUSE_PRICES,+DNK+FIN+FRA+DEU+IRL+ITA+JPN+KOR+MEX+NOR+PRT+ESP+SWE+CHE+GBR+AUT+BEL+AUS+CAN+NZL+EA+USA+OECD.Q.HPI_YDH+RHP.IX.csv"
oecd_raw = pd.read_csv(oecd_file)
pti = oecd_raw[oecd_raw['MEASURE'] == 'HPI_YDH'].copy()
pti['year'] = pti['TIME_PERIOD'].str[:4].astype(int)
pti['value'] = pd.to_numeric(pti['OBS_VALUE'], errors='coerce')

iso3_to_whr = {
    'AUS': 'Australia', 'AUT': 'Austria', 'BEL': 'Belgium', 'CAN': 'Canada',
    'CHE': 'Switzerland', 'DEU': 'Germany', 'DNK': 'Denmark', 'ESP': 'Spain',
    'FIN': 'Finland', 'FRA': 'France', 'GBR': 'United Kingdom', 'IRL': 'Ireland',
    'ITA': 'Italy', 'JPN': 'Japan', 'KOR': 'South Korea', 'MEX': 'Mexico',
    'NOR': 'Norway', 'NZL': 'New Zealand', 'PRT': 'Portugal', 'SWE': 'Sweden',
    'USA': 'United States',
}
pti_annual = pti.groupby(['REF_AREA', 'year'])['value'].mean().reset_index()
pti_annual['country'] = pti_annual['REF_AREA'].map(iso3_to_whr)
pti_annual = pti_annual.dropna(subset=['country'])

pti_2018 = pti_annual[pti_annual['year'] == 2018][['country', 'value']].rename(columns={'value': 'pti_2018'})
pti_2023_25 = pti_annual[pti_annual['year'].isin([2023, 2024, 2025])].groupby('country')['value'].mean().reset_index()
pti_2023_25.columns = ['country', 'pti_2023_25']

recent = pti_2018.merge(pti_2023_25, on='country').merge(hap_2018, on='country').merge(
    whr2026[['country', 'happiness_score']], on='country')
recent['pti_change'] = recent['pti_2023_25'] - recent['pti_2018']
recent['hap_change'] = recent['happiness_score'] - recent['hap_2018']
anglophone = {'United States', 'United Kingdom', 'Canada', 'Australia', 'New Zealand', 'Ireland'}
recent['anglophone'] = recent['country'].isin(anglophone)
recent = recent.dropna()
recent.to_csv(f"{DATA}/whr2026_recent_changes.csv", index=False)

r_recent, p_recent = stats.pearsonr(recent['pti_change'], recent['hap_change'])
print(f"Recent (2018→2023-25): r={r_recent:.3f}, p={p_recent:.4f}")

# ── Chart 1: PTI change vs happiness change (long-term) ───────────────────
print("\nChart 1: PTI change vs happiness change")
r1, p1 = stats.pearsonr(changes['pti_change'], changes['happiness_change_2006_2025'])
scatter_chart(
    data=changes.to_dict('records'),
    title="Housing costs and happiness",
    subtitle="Change in price-to-income ratio vs change in happiness score, OECD countries",
    x_label="Change in price-to-income index (2011–13 to 2023–25)",
    y_label="Change in happiness score (2006–10 to 2023–25)",
    corr_text=f"r = {r1:.2f}, p = {p1:.2f}",
    source="Source: OECD Analytical House Prices, World Happiness Report 2026",
    filename="scatter_pti_change_vs_happiness_change.html",
    x_col='pti_change', y_col='happiness_change_2006_2025',
)

# ── Chart 2: PTI level vs happiness level (2023-25) ───────────────────────
print("\nChart 2: PTI level vs happiness level")
r2, p2 = stats.pearsonr(merged['pti_2023_25'].dropna(), merged.loc[merged['pti_2023_25'].notna(), 'happiness_score'])
scatter_chart(
    data=merged.dropna(subset=['pti_2023_25']).to_dict('records'),
    title="Housing costs and happiness today",
    subtitle="OECD price-to-income index vs happiness score, 2023–2025 average",
    x_label="Price-to-income index (2015 = 100)",
    y_label="Happiness score (Cantril ladder, 0–10)",
    corr_text=f"r = {r2:.2f}, not significant",
    source="Source: OECD Analytical House Prices, World Happiness Report 2026",
    filename="scatter_pti_level_vs_happiness_2023.html",
    x_col='pti_2023_25', y_col='happiness_score',
    show_zero_lines=False,
)

# ── Chart 3: Long-term PTI change vs happiness ────────────────────────────
print("\nChart 3: Long-term PTI change vs happiness")
r3, p3 = stats.pearsonr(longterm['pti_change_pct'], longterm['happiness_score'])
scatter_chart(
    data=longterm.to_dict('records'),
    title="Long-term housing costs vs happiness today",
    subtitle="Change in price-to-income index (2005 to 2023–25) vs happiness (2023–25)",
    x_label="Percent change in price-to-income index since 2005",
    y_label="Happiness score (Cantril ladder, 2023–25 avg)",
    corr_text=f"r = +{r3:.2f}, not significant",
    source="Source: OECD Analytical House Prices, World Happiness Report 2026",
    filename="scatter_longterm_pti_vs_happiness.html",
    x_col='pti_change_pct', y_col='happiness_score',
    show_zero_lines=True,
)

# ── Chart 4: Recent PTI change vs happiness change (2018→2023-25) ─────────
print("\nChart 4: Recent changes")
scatter_chart(
    data=recent.to_dict('records'),
    title="The recent picture",
    subtitle="Change in price-to-income index vs change in happiness, 2018 to 2023–2025",
    x_label="Change in price-to-income index (2018 to 2023–25)",
    y_label="Change in happiness score (2018 to 2023–25)",
    corr_text=f"r = {r_recent:.2f}, p = {p_recent:.2f}",
    source="Source: OECD Analytical House Prices, World Happiness Report 2026",
    filename="scatter_recent_pti_vs_happiness_change.html",
    x_col='pti_change', y_col='hap_change',
)

print("\nAll 4 scatter charts rebuilt.")
