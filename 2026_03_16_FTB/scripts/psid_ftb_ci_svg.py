"""Generate standalone SVG for PSID FTB chart (Illustrator-compatible)."""
import json
import base64
import os
import math

# ── Load data ──────────────────────────────────────────────────────────────
with open("/Users/azizsunderji/Dropbox/Home Economics/2026_03_16_FTB/data/psid_ftb_heads_ci.json") as f:
    data = [d for d in json.load(f) if d["year"] >= 1974]

# ── Load logo as base64 ───────────────────────────────────────────────────
logo_path = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/HomeEconomics-Logo-versions/HE-Large-Black.png"
with open(logo_path, "rb") as f:
    logo_b64 = base64.b64encode(f.read()).decode("ascii")

# ── Canvas constants ──────────────────────────────────────────────────────
W, H = 960, 987
buf = 40
gridLeft = buf
gridRight = W - buf
titleY = buf + 32
subtitleY = titleY + 34
chartTop = subtitleY + 75
sourceLineH = 18
sourceBlockH = sourceLineH * 3
sourceTop = H - buf - sourceBlockH
chartBottom = sourceTop - 45 - 40

# Scales
xDomainMin, xDomainMax = 1972, 2025
yDomainMin, yDomainMax = 24, 40
xRangeMin = gridLeft + 50
xRangeMax = gridRight


def sx(year):
    """Scale x: year -> pixel."""
    return xRangeMin + (year - xDomainMin) / (xDomainMax - xDomainMin) * (xRangeMax - xRangeMin)


def sy(val):
    """Scale y: value -> pixel (inverted)."""
    return chartBottom + (val - yDomainMin) / (yDomainMax - yDomainMin) * (chartTop - chartBottom)


# ── Monotone cubic spline (Fritsch-Carlson) ───────────────────────────────
def monotone_cubic_spline(xs, ys, num_points=300):
    """Compute monotone cubic interpolation matching D3's curveMonotoneX."""
    n = len(xs)
    if n < 2:
        return xs, ys

    # Compute slopes of secant lines
    deltas = []
    for i in range(n - 1):
        deltas.append((ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]))

    # Initialize tangent slopes
    m = [0.0] * n
    m[0] = deltas[0]
    m[n - 1] = deltas[n - 2]
    for i in range(1, n - 1):
        if deltas[i - 1] * deltas[i] <= 0:
            m[i] = 0
        else:
            m[i] = (deltas[i - 1] + deltas[i]) / 2

    # Fritsch-Carlson modification for monotonicity
    for i in range(n - 1):
        if abs(deltas[i]) < 1e-12:
            m[i] = 0
            m[i + 1] = 0
        else:
            alpha = m[i] / deltas[i]
            beta = m[i + 1] / deltas[i]
            # Constrain to monotonicity circle
            s = alpha * alpha + beta * beta
            if s > 9:
                tau = 3.0 / math.sqrt(s)
                m[i] = tau * alpha * deltas[i]
                m[i + 1] = tau * beta * deltas[i]

    # Generate interpolated points
    out_x = []
    out_y = []
    for i in range(n - 1):
        x0, x1 = xs[i], xs[i + 1]
        y0, y1 = ys[i], ys[i + 1]
        h = x1 - x0
        pts = max(2, int(num_points * h / (xs[-1] - xs[0])))
        for j in range(pts):
            t = j / pts
            xv = x0 + t * h
            # Hermite basis functions
            t2 = t * t
            t3 = t2 * t
            h00 = 2 * t3 - 3 * t2 + 1
            h10 = t3 - 2 * t2 + t
            h01 = -2 * t3 + 3 * t2
            h11 = t3 - t2
            yv = h00 * y0 + h10 * h * m[i] + h01 * y1 + h11 * h * m[i + 1]
            out_x.append(xv)
            out_y.append(yv)
    # Add last point
    out_x.append(xs[-1])
    out_y.append(ys[-1])
    return out_x, out_y


def points_to_path(pixel_xs, pixel_ys):
    """Convert pixel coordinates to SVG path d string."""
    parts = [f"M{pixel_xs[0]:.2f},{pixel_ys[0]:.2f}"]
    for i in range(1, len(pixel_xs)):
        parts.append(f"L{pixel_xs[i]:.2f},{pixel_ys[i]:.2f}")
    return "".join(parts)


# ── Compute spline paths ──────────────────────────────────────────────────
years = [d["year"] for d in data]
smoothed = [d["smoothed"] for d in data]
ci_lo_smooth = [d["ci_lo_smooth"] for d in data]
ci_hi_smooth = [d["ci_hi_smooth"] for d in data]

# Trend line
sp_x, sp_y = monotone_cubic_spline(years, smoothed, 400)
trend_px = [sx(x) for x in sp_x]
trend_py = [sy(y) for y in sp_y]
trend_d = points_to_path(trend_px, trend_py)

# CI band: area = upper forward + lower reversed
sp_x_lo, sp_y_lo = monotone_cubic_spline(years, ci_lo_smooth, 400)
sp_x_hi, sp_y_hi = monotone_cubic_spline(years, ci_hi_smooth, 400)

ci_upper_px = [sx(x) for x in sp_x_hi]
ci_upper_py = [sy(y) for y in sp_y_hi]
ci_lower_px = [sx(x) for x in sp_x_lo]
ci_lower_py = [sy(y) for y in sp_y_lo]

# Build area path: upper forward, then lower reversed, close
area_parts = [f"M{ci_upper_px[0]:.2f},{ci_upper_py[0]:.2f}"]
for i in range(1, len(ci_upper_px)):
    area_parts.append(f"L{ci_upper_px[i]:.2f},{ci_upper_py[i]:.2f}")
for i in range(len(ci_lower_px) - 1, -1, -1):
    area_parts.append(f"L{ci_lower_px[i]:.2f},{ci_lower_py[i]:.2f}")
area_parts.append("Z")
ci_d = "".join(area_parts)

# ── X-axis config ─────────────────────────────────────────────────────────
x_ticks = [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020]
x_labels = ["1975", "\u201880", "\u201885", "\u201890", "\u201895", "2000", "\u201805", "\u201810", "\u201815", "\u201820"]
y_ticks = [24, 26, 28, 30, 32, 34, 36, 38, 40]

# ── Build SVG ─────────────────────────────────────────────────────────────
lines = []
lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')

# Background
lines.append(f'  <rect width="{W}" height="{H}" fill="#F6F7F3"/>')

# Title
lines.append(f'  <g id="title">')
lines.append(f'    <text x="{gridLeft}" y="{titleY}" font-family="ABC Oracle Edu" font-size="32" font-weight="500" fill="#3D3733">Median age at first homeownership</text>')
lines.append(f'  </g>')

# Subtitle
lines.append(f'  <g id="subtitle">')
lines.append(f'    <text x="{gridLeft}" y="{subtitleY}" font-family="ABC Oracle Edu" font-size="23" font-weight="400" fill="#7F7570">PSID, household heads, rent-to-own transitions (weighted)</text>')
lines.append(f'  </g>')

# Grid lines
lines.append(f'  <g id="grid-lines">')
for v in y_ticks:
    yp = sy(v)
    lines.append(f'    <line x1="{gridLeft}" x2="{gridRight}" y1="{yp:.2f}" y2="{yp:.2f}" stroke="#e1e2e3" stroke-width="1" fill="none"/>')
lines.append(f'  </g>')

# Y-axis labels
lines.append(f'  <g id="y-axis-labels">')
for i, v in enumerate(y_ticks):
    yp = sy(v)
    label = f"{v} yrs" if i == len(y_ticks) - 1 else str(v)
    lines.append(f'    <text x="{gridLeft}" y="{yp:.2f}" dy="-0.35em" font-family="ABC Oracle Edu" font-size="22" font-weight="300" fill="#333" text-anchor="start">{label}</text>')
lines.append(f'  </g>')

# CI band
lines.append(f'  <g id="ci-band">')
lines.append(f'    <path d="{ci_d}" fill="#0BB4FF" fill-opacity="0.15" stroke="none"/>')
lines.append(f'  </g>')

# Trend line
lines.append(f'  <g id="data-series">')
lines.append(f'    <path d="{trend_d}" fill="none" stroke="#3D3733" stroke-width="2.5"/>')
lines.append(f'  </g>')

# X-axis ticks
lines.append(f'  <g id="x-axis-ticks">')
for v in x_ticks:
    xp = sx(v)
    lines.append(f'    <line x1="{xp:.2f}" x2="{xp:.2f}" y1="{chartBottom:.2f}" y2="{chartBottom + 12:.2f}" stroke="#3D3733" stroke-width="0.5" fill="none"/>')
lines.append(f'  </g>')

# X-axis labels
lines.append(f'  <g id="x-axis-labels">')
for i, v in enumerate(x_ticks):
    xp = sx(v)
    lines.append(f'    <text x="{xp:.2f}" y="{chartBottom + 12:.2f}" dy="1.5em" font-family="ABC Oracle Edu" font-size="22" font-weight="300" fill="#333" text-anchor="middle">{x_labels[i]}</text>')
lines.append(f'  </g>')

# Source note
lines.append(f'  <g id="source">')
lines.append(f'    <text x="{gridLeft}" y="{sourceTop}" font-family="ABC Oracle Edu" font-size="15" font-weight="200" fill="#3D3733">')
lines.append(f'      <tspan x="{gridLeft}" dy="0">Source: Panel Study of Income Dynamics, 1968\u20132023.</tspan>')
lines.append(f'      <tspan x="{gridLeft}" dy="{sourceLineH}">Weighted median age at first rent-to-own transition for household heads.</tspan>')
lines.append(f'      <tspan x="{gridLeft}" dy="{sourceLineH}">Latino supplement excluded. Line is 5-survey rolling average. 90% bootstrap CI shown.</tspan>')
lines.append(f'    </text>')
lines.append(f'  </g>')

# Logo
logo_w = 130
# Get actual aspect ratio
from PIL import Image
img = Image.open(logo_path)
logo_aspect = img.height / img.width
logo_h = logo_w * logo_aspect
logo_x = gridRight - logo_w
# Bottom-align with source text block bottom
source_bottom = sourceTop + sourceBlockH
logo_y = source_bottom - logo_h

lines.append(f'  <g id="logo">')
lines.append(f'    <image xlink:href="data:image/png;base64,{logo_b64}" x="{logo_x:.2f}" y="{logo_y:.2f}" width="{logo_w}" height="{logo_h:.2f}" opacity="0.6"/>')
lines.append(f'  </g>')

lines.append('</svg>')

svg_content = "\n".join(lines)

# ── Write SVG ─────────────────────────────────────────────────────────────
svg_path = "/Users/azizsunderji/Dropbox/Home Economics/2026_03_16_FTB/outputs/psid_ftb_ci.svg"
with open(svg_path, "w") as f:
    f.write(svg_content)

print(f"SVG written to {svg_path}")
print(f"Data points: {len(data)}, Spline points: {len(sp_x)}")

# Open in Illustrator
os.system(f'open -a "Adobe Illustrator" "{svg_path}"')
