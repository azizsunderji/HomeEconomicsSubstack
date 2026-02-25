"""Export side-by-side scatter chart as static SVG with population-scaled bubbles, labels on bubbles."""
import json
import math
import numpy as np

font_dir = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
PROJECT = "/Users/azizsunderji/Dropbox/Home Economics/2026_02_23_DCRentDecline"

with open(f"{PROJECT}/data/scatter_side_by_side.json") as f:
    DATA = json.load(f)

W, H = 898, 740
margin = {"top": 40, "right": 30, "bottom": 55, "left": 50}
gap = 60
panelW = (W - margin["left"] - margin["right"] - gap) / 2
panelH = H - margin["top"] - margin["bottom"]

rents = [d["rent"] for d in DATA]
yMin, yMax = min(rents), max(rents)
yPad = (yMax - yMin) * 0.08
yDomMin, yDomMax = yMin - yPad, yMax + yPad

def y_scale(val):
    return panelH - (val - yDomMin) / (yDomMax - yDomMin) * panelH

pops = [d["pop"] for d in DATA]
popMin, popMax = min(pops), max(pops)
rMin, rMax = 3, 18

def r_scale(pop):
    return rMin + (rMax - rMin) * math.sqrt((pop - popMin) / (popMax - popMin))

panels = [
    {"key": "permits", "title": "Multifamily permits per 1K workers",
     "xField": "permits", "xLabel": "Cumulative MF permits per 1K workers",
     "color": "#3D3733", "rLabel": "r = \u20130.51"},
    {"key": "wfh", "title": "Work-from-home share",
     "xField": "wfh", "xLabel": "Average WFH share (%)",
     "color": "#0BB4FF", "rLabel": "r = \u20130.55"},
]

def compute_regression(data, xField):
    xs = [d[xField] for d in data]
    ys = [d["rent"] for d in data]
    xm, ym = np.mean(xs), np.mean(ys)
    num = sum((x - xm) * (y - ym) for x, y in zip(xs, ys))
    den = sum((x - xm) ** 2 for x in xs)
    slope = num / den
    return slope, ym - slope * xm

LABELED = {"D.C.", "Austin", "Salt Lake City", "San Francisco", "Miami", "New York", "Los Angeles", "Chicago", "Denver"}

lines = []
lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')

lines.append('<defs><style type="text/css">')
for weight, name in [(300, "Light"), (400, "Regular"), (500, "Medium"), (700, "Bold")]:
    lines.append(f"@font-face {{ font-family: 'ABC Oracle Edu'; src: url('{font_dir}/ABCOracle-{name}.otf') format('opentype'); font-weight: {weight}; font-style: normal; }}")
lines.append('</style></defs>')

lines.append(f'<rect width="{W}" height="{H}" fill="#F6F7F3"/>')

y_ticks = list(range(10, 70, 10))
DATA_sorted = sorted(DATA, key=lambda d: -d["pop"])

for pi, panel in enumerate(panels):
    x0 = margin["left"] + pi * (panelW + gap)

    xs = [d[panel["xField"]] for d in DATA]
    xMin_data, xMax_data = min(xs), max(xs)
    xPad_data = (xMax_data - xMin_data) * 0.08
    xDomMin = max(0, xMin_data - xPad_data)
    xDomMax = xMax_data + xPad_data

    def x_scale(val, _xDomMin=xDomMin, _xDomMax=xDomMax):
        return (val - _xDomMin) / (_xDomMax - _xDomMin) * panelW

    # Gridlines
    for t in y_ticks:
        yy = y_scale(t)
        lines.append(f'<line x1="{x0}" y1="{margin["top"] + yy:.1f}" x2="{x0 + panelW}" y2="{margin["top"] + yy:.1f}" stroke="#D8DAD1" stroke-width="0.5"/>')

    # Regression line
    slope, intercept = compute_regression(DATA, panel["xField"])
    lines.append(f'<line x1="{x0 + x_scale(xDomMin):.1f}" y1="{margin["top"] + y_scale(intercept + slope * xDomMin):.1f}" '
                 f'x2="{x0 + x_scale(xDomMax):.1f}" y2="{margin["top"] + y_scale(intercept + slope * xDomMax):.1f}" '
                 f'stroke="{panel["color"]}" stroke-width="1.5" opacity="0.4" stroke-dasharray="6,3"/>')

    # Bubbles (big ones first)
    for d in DATA_sorted:
        cx = x0 + x_scale(d[panel["xField"]])
        cy = margin["top"] + y_scale(d["rent"])
        r = r_scale(d["pop"])
        is_labeled = d["short_name"] in LABELED

        if d["is_dc"]:
            lines.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="#F4743B" stroke="#3D3733" stroke-width="1.2"/>')
        elif is_labeled:
            lines.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{panel["color"]}" stroke="#3D3733" stroke-width="1"/>')
        else:
            lines.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{panel["color"]}" stroke="{panel["color"]}" stroke-width="0.5"/>')

    # Labels centered on bubbles
    for d in DATA:
        sn = d["short_name"]
        if sn not in LABELED:
            continue

        cx = x0 + x_scale(d[panel["xField"]])
        cy = margin["top"] + y_scale(d["rent"])
        r = r_scale(d["pop"])

        display_name = "D.C." if d["is_dc"] else sn
        fill = "#F4743B" if d["is_dc"] else "#3D3733"
        weight = 500

        # Place label just above the bubble
        ly = cy - r - 4

        lines.append(f'<text x="{cx:.1f}" y="{ly:.1f}" text-anchor="middle" '
                     f'font-family="ABC Oracle Edu, system-ui, sans-serif" font-size="9" font-weight="{weight}" fill="{fill}">'
                     f'{display_name}</text>')

    # Panel title
    lines.append(f'<text x="{x0 + panelW/2:.1f}" y="{margin["top"] - 12:.1f}" text-anchor="middle" '
                 f'font-family="ABC Oracle Edu, system-ui, sans-serif" font-size="14" font-weight="500" fill="#3D3733">'
                 f'{panel["title"]}</text>')

    # Correlation label
    lines.append(f'<text x="{x0 + panelW - 5:.1f}" y="{margin["top"] + 20:.1f}" text-anchor="end" '
                 f'font-family="ABC Oracle Edu, system-ui, sans-serif" font-size="12" font-weight="400" '
                 f'fill="{panel["color"]}" opacity="0.7">{panel["rLabel"]}</text>')

    # X axis
    x_ticks_vals = [0, 20, 40, 60, 80] if panel["key"] == "permits" else [8, 12, 16, 20, 24]
    for t in x_ticks_vals:
        if t < xDomMin or t > xDomMax:
            continue
        tx = x0 + x_scale(t)
        ty = margin["top"] + panelH
        lines.append(f'<line x1="{tx:.1f}" y1="{ty:.1f}" x2="{tx:.1f}" y2="{ty + 4:.1f}" stroke="#ccc" stroke-width="1"/>')
        lines.append(f'<text x="{tx:.1f}" y="{ty + 16:.1f}" text-anchor="middle" '
                     f'font-family="ABC Oracle Edu, system-ui, sans-serif" font-size="11" fill="#3D3733">{t}</text>')

    lines.append(f'<line x1="{x0}" y1="{margin["top"] + panelH}" x2="{x0 + panelW}" y2="{margin["top"] + panelH}" stroke="#ccc" stroke-width="1"/>')
    lines.append(f'<text x="{x0 + panelW/2:.1f}" y="{margin["top"] + panelH + 40:.1f}" text-anchor="middle" '
                 f'font-family="ABC Oracle Edu, system-ui, sans-serif" font-size="11" fill="#3D3733" opacity="0.6">'
                 f'{panel["xLabel"]}</text>')

    # Y axis
    if pi == 0:
        for t in y_ticks:
            yy = margin["top"] + y_scale(t)
            label = f"{t}%" if t == y_ticks[-1] else str(t)
            lines.append(f'<text x="{x0 - 8:.1f}" y="{yy + 4:.1f}" text-anchor="end" '
                         f'font-family="ABC Oracle Edu, system-ui, sans-serif" font-size="11" fill="#3D3733">{label}</text>')
        mid_y = margin["top"] + panelH / 2
        lines.append(f'<text transform="translate({x0 - 38},{mid_y}) rotate(-90)" text-anchor="middle" '
                     f'font-family="ABC Oracle Edu, system-ui, sans-serif" font-size="11" fill="#3D3733" opacity="0.6">'
                     f'Cumulative rent growth (%)</text>')
    else:
        for t in y_ticks:
            yy = margin["top"] + y_scale(t)
            label = f"{t}%" if t == y_ticks[-1] else str(t)
            lines.append(f'<text x="{x0 - 8:.1f}" y="{yy + 4:.1f}" text-anchor="end" '
                         f'font-family="ABC Oracle Edu, system-ui, sans-serif" font-size="11" fill="#3D3733" opacity="0.4">{label}</text>')

lines.append(f'<text x="{margin["left"]}" y="{H - 5}" font-family="ABC Oracle Edu, system-ui, sans-serif" '
             f'font-size="11" font-weight="300" fill="#999" font-style="italic">'
             f'Source: Zillow ZORI, Census BPS, ACS 1-Year WFH estimates. Bubble size = employed population.</text>')

lines.append('</svg>')

svg_content = '\n'.join(lines)
out_path = f"{PROJECT}/outputs/14_side_by_side_scatter.svg"
with open(out_path, 'w') as f:
    f.write(svg_content)

print(f"SVG saved to {out_path}")
print(f"Size: {len(svg_content):,} bytes")
