"""
FTB long-run chart — production version matching Illustrator style reference.
3 series: Ownership (PSID), Marriage (CPS MS-2 method), Headship (CPS MS-2 method).
"""
import json, base64

# ── Data ──
psid = [
    (1974,27),(1975,29),(1976,28),(1977,28),(1978,28),(1979,28),(1980,28),(1981,28),
    (1982,29),(1983,28),(1984,30),(1985,29),(1986,29),(1987,31),(1988,31),(1989,30),
    (1991,32),(1992,33),(1993,32),(1994,35),(1995,33),(1996,33),(1997,32),(1999,33),
    (2001,33),(2003,33),(2005,32),(2007,33),(2009,32),(2011,31),(2013,32),(2015,32),
    (2017,34),(2019,34),(2021,35),(2023,34),
]
# Marriage: CPS MS-2 method 1976-2007, ACS direct measure 2008-2023
marriage = [
    (1976,21.9),(1977,22.2),(1978,22.3),(1979,22.5),(1980,22.7),(1981,22.9),(1982,23.2),
    (1983,23.3),(1984,23.5),(1985,23.8),(1986,23.6),(1987,24.1),(1988,24.0),(1989,24.6),
    (1990,24.6),(1991,24.7),(1992,25.0),(1993,25.0),(1994,25.1),(1995,24.9),(1996,25.5),
    (1997,25.6),(1998,25.7),(1999,25.5),(2000,25.6),(2001,25.5),(2002,25.6),(2003,25.8),
    (2004,25.7),(2005,25.6),(2006,26.0),(2007,25.9),
    (2008,25.8),(2009,25.8),(2010,26.1),(2011,26.2),(2012,26.4),(2013,26.7),(2014,27.1),
    (2015,27.3),(2016,27.3),(2017,27.4),(2018,27.4),(2019,27.5),(2020,27.4),(2021,27.6),
    (2022,27.8),(2023,28.1),
]
headship = [
    (1976,21.3),(1977,21.5),(1978,21.5),(1979,21.6),(1980,21.6),(1981,21.8),(1982,22.0),
    (1983,22.5),(1984,22.6),(1985,22.6),(1986,22.5),(1987,22.7),(1988,22.7),(1989,22.6),
    (1990,22.7),(1991,22.9),(1992,22.9),(1993,23.1),(1994,23.2),(1995,23.1),(1996,22.9),
    (1997,23.2),(1998,23.0),(1999,23.0),(2000,23.0),(2001,22.6),(2002,22.7),(2003,22.9),
    (2004,23.1),(2005,23.0),(2006,22.9),(2007,23.2),(2008,23.2),(2009,23.5),(2010,23.7),
    (2011,23.8),(2012,23.7),(2013,24.2),(2014,24.1),(2015,24.2),(2016,24.1),(2017,23.8),
    (2018,24.2),(2019,23.8),(2020,24.4),(2021,24.7),(2022,23.9),(2023,23.9),(2024,24.0),(2025,24.1),
]

def to_js(data):
    return "[" + ",".join(f'{{"year":{y},"age":{a}}}' for y,a in data) + "]"

LOGO = '/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/HomeEconomics-Logo-versions/HE-Large-Black.png'
with open(LOGO, 'rb') as f:
    logo_b64 = base64.b64encode(f.read()).decode()

html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<style>
  @font-face {{ font-family:'ABC Oracle Edu'; src:url('/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop/ABCOracle-Thin.otf'); font-weight:200; }}
  @font-face {{ font-family:'ABC Oracle Edu'; src:url('/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop/ABCOracle-Light.otf'); font-weight:300; }}
  @font-face {{ font-family:'ABC Oracle Edu'; src:url('/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop/ABCOracle-Book.otf'); font-weight:350; }}
  @font-face {{ font-family:'ABC Oracle Edu'; src:url('/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop/ABCOracle-Regular.otf'); font-weight:400; }}
  @font-face {{ font-family:'ABC Oracle Edu'; src:url('/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop/ABCOracle-Medium.otf'); font-weight:500; }}
  @font-face {{ font-family:'ABC Oracle Edu'; src:url('/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop/ABCOracle-Bold.otf'); font-weight:700; }}
  body {{ margin:20px; background:#fff; font-family:'ABC Oracle Edu',system-ui,sans-serif; }}
  .grid line {{ stroke:#e1e2e3; stroke-width:1; }}
  .grid path {{ stroke:none; }}
  .axis text {{ font-size:22px; fill:#333; font-weight:300; }}
  .axis line {{ stroke:#3D3733; stroke-width:0.5; }}
</style>
<script src="https://d3js.org/d3.v7.min.js"></script>
</head><body>
<script>
const psid = {to_js(psid)};
const marriage_data = {to_js(marriage)};
const headship_data = {to_js(headship)};

const W = 960, H = 987;

// ── Layout: explicit vertical anchors with guaranteed gaps ──
const pad = 30;                    // canvas edge padding
const titleY = 40 + 32;            // 40px top buffer + ascent
const subtitleY = titleY + 34;     // subtitle baseline (34pt leading)
const gapSubtitleToChart = 75;     // guaranteed gap below subtitle
const chartTop = subtitleY + gapSubtitleToChart;

// Source: 15px Thin, max width = chart width minus logo space
const sourceFont = 15;
const sourceLines = 3;             // max lines
const sourceLineH = sourceFont + 3;
const sourceBlockH = sourceLines * sourceLineH;
const gapXaxisToSource = 45;       // guaranteed gap below x-axis labels
const gapSourceToBottom = 40;       // equal to side buffers

// Work backwards from bottom for chart area
const sourceTop = H - gapSourceToBottom - sourceBlockH;
const xAxisLabelsBottom = sourceTop - gapXaxisToSource;
const xAxisLabelsH = 50;           // x-axis ticks + labels height
const chartBottom = xAxisLabelsBottom - xAxisLabelsH;
const chartH = chartBottom - chartTop;

const mLeft = 95, mRight = 40;
const chartLeft = mLeft;
const chartW = W - mLeft - mRight;

const svg = d3.select("body").append("svg").attr("width",W).attr("height",H)
  .attr("font-family","ABC Oracle Edu")
  .style("display","block");
// Background rect (inline, not CSS — survives Illustrator import)
svg.append("rect").attr("width",W).attr("height",H).attr("fill","#F6F7F3");
// Chart offset — applied to each group individually, NOT via a shared parent <g>
const tx = chartLeft, ty = chartTop;

// ── Title group ──
const gTitle = svg.append("g").attr("id","title");
// Grid extends left by this much to put labels above gridlines
const gridExtendLeft = 55;
// All text left-aligns with grid left edge
const gridLeftEdge = chartLeft - gridExtendLeft;
gTitle.append("text")
  .attr("x", gridLeftEdge).attr("y", titleY)
  .attr("font-size","32px").attr("font-weight","500").attr("fill","#3D3733")
  .text("Median age of first-time homebuyers, 1974\u20132025");

// ── Subtitle group ──
const gSubtitle = svg.append("g").attr("id","subtitle");
gSubtitle.append("text")
  .attr("x", gridLeftEdge).attr("y", subtitleY)
  .attr("font-size","23px").attr("font-weight","400").attr("fill","#7F7570")
  .text("FTB age rose with marriage age through the early 1990s, then decoupled");

const w = chartW, h = chartH;

// ── Each group is a direct child of SVG with its own transform ──
const gGrid = svg.append("g").attr("id","grid-lines").attr("transform",`translate(${{tx}},${{ty}})`);
const gSeries = svg.append("g").attr("id","data-series").attr("transform",`translate(${{tx}},${{ty}})`);
const gXTicks = svg.append("g").attr("id","x-axis-ticks").attr("transform",`translate(${{tx}},${{ty}})`);
const gXLabels = svg.append("g").attr("id","x-axis-labels").attr("transform",`translate(${{tx}},${{ty}})`);
const gYLabels = svg.append("g").attr("id","y-axis-labels").attr("transform",`translate(${{tx}},${{ty}})`);
// (label halos now combined into label elements via paint-order)
const gLabels = svg.append("g").attr("id","series-labels").attr("transform",`translate(${{tx}},${{ty}})`);

// ── Scales ──
const x = d3.scaleLinear().domain([1972,2027]).range([0,w]);
const y = d3.scaleLinear().domain([20,40]).range([h,0]);

// ── Grid lines ──
gGrid.append("g")
  .attr("transform",`translate(-${{gridExtendLeft}},0)`)
  .call(d3.axisLeft(y).tickSize(-(w + gridExtendLeft)).tickFormat("").tickValues([20,25,30,35,40]));
gGrid.selectAll("line").attr("stroke","#e1e2e3").attr("stroke-width",1);
gGrid.selectAll("path").attr("stroke","none");

// ── X Axis: ticks and labels in SEPARATE groups ──
const xTickVals = [1975,1985,1995,2005,2015,2025];
const xFmt = d => (d===1975||d===2005) ? String(d) : "\u2019"+String(d).slice(2);
// Tick marks only
xTickVals.forEach(v => {{
  gXTicks.append("line")
    .attr("x1",x(v)).attr("x2",x(v))
    .attr("y1",h).attr("y2",h+12)
    .attr("stroke","#3D3733").attr("stroke-width",0.5);
}});
// Labels only
xTickVals.forEach(v => {{
  gXLabels.append("text")
    .attr("x",x(v)).attr("y",h+12)
    .attr("dy","1.5em").attr("text-anchor","middle")
    .attr("font-size","22px").attr("fill","#333").attr("font-weight","300")
    .attr("font-family","ABC Oracle Edu")
    .text(xFmt(v));
}});

// ── Y Axis: labels only (no ticks, no spine), in own group ──
const yTickVals = [20,25,30,35,40];
yTickVals.forEach((v,i) => {{
  gYLabels.append("text")
    .attr("x", -gridExtendLeft)
    .attr("y", y(v))
    .attr("dy","-0.35em")
    .attr("text-anchor","start")
    .attr("font-size","22px").attr("fill","#333").attr("font-weight","300")
    .attr("font-family","ABC Oracle Edu")
    .text(i === yTickVals.length-1 ? v + " yrs" : v);
}});

// ── Colors ──
const BLUE="#0BB4FF", RED="#F4743B", GREEN="#67A275";

const line = d3.line().x(d=>x(d.year)).y(d=>y(d.age));

function drawLine(data, color, width) {{
  gSeries.append("path").datum(data).attr("d",line)
    .attr("fill","none").attr("stroke",color)
    .attr("stroke-width",width)
    .style("mix-blend-mode","multiply");
}}

drawLine(psid, BLUE, 2.5);
drawLine(marriage_data, RED, 2.5);
drawLine(headship_data, GREEN, 2.5);

// Dot at marriage data source switch (2008)
const switchPt = marriage_data.find(d=>d.year===2008);
if (switchPt) {{
  gSeries.append("circle")
    .attr("cx",x(switchPt.year)).attr("cy",y(switchPt.age))
    .attr("r",4).attr("fill",RED).attr("stroke","#F6F7F3").attr("stroke-width",2);
}}

// ── Inline labels ──
const labelData = [
  {{data:psid, color:BLUE, line1:"Ownership", line2:"(PSID)", year:2019, yOff:-18}},
  {{data:marriage_data, color:RED, line1:"Marriage", line2:"(CPS)", year:2008, yOff:16}},
  {{data:headship_data, color:GREEN, line1:"Headship", line2:"(CPS)", year:2000, yOff:-16}},
];

labelData.forEach(lb => {{
  const pt = lb.data.find(d=>d.year===lb.year);
  if (!pt) return;
  const lx = x(pt.year)+10, ly = y(pt.age)+lb.yOff;

  // Two-line label with halo via paint-order (works in browser; stripped for AI export)
  gLabels.append("text")
    .attr("x",lx).attr("y",ly)
    .attr("font-size","16px").attr("font-weight","500")
    .attr("fill",lb.color)
    .attr("stroke","#F6F7F3").attr("stroke-width",5)
    .attr("stroke-linejoin","round")
    .attr("paint-order","stroke")
    .attr("font-family","ABC Oracle Edu")
    .text(lb.line1 + " " + lb.line2);
}});

// ── Source group ──
const gSource = svg.append("g").attr("id","source");
const srcLeftEdge = chartLeft - gridExtendLeft;
const srcG = gSource.append("text")
  .attr("x",srcLeftEdge).attr("y",sourceTop + sourceFont)
  .attr("font-size",sourceFont+"px").attr("font-weight","200").attr("fill","#3D3733");
srcG.append("tspan").attr("x",srcLeftEdge).attr("dy",0)
  .text("Sources: PSID 1974\u20132023 (rent-to-own transitions); CPS ASEC 1976\u20132025 (headship, MS-2 method);");
srcG.append("tspan").attr("x",srcLeftEdge).attr("dy",sourceLineH)
  .text("Marriage: CPS MS-2 method 1976\u20132007, ACS direct (YRMARR) 2008\u20132023. All medians.");

// Source bottom = sourceTop + sourceFont + sourceLineH (2 lines)
const sourceBottom = sourceTop + sourceFont + sourceLineH;

// ── Logo: embedded PNG via xlink:href for Illustrator compatibility ──
const gLogo = svg.append("g").attr("id","logo");
const logoW = 130, logoH = 42;
const gridRightEdge = chartLeft + w;
const logoX = gridRightEdge - logoW;
const logoY = sourceBottom - logoH;
gLogo.append("image")
  .attr("x",logoX).attr("y",logoY).attr("width",logoW).attr("height",logoH)
  .attr("opacity",0.6)
  .each(function() {{
    // Use xlink:href for Illustrator compatibility
    this.setAttributeNS("http://www.w3.org/1999/xlink", "xlink:href",
      "data:image/png;base64,{logo_b64}");
  }});
// ── SVG Export button ──
const exportBtn = document.createElement("button");
exportBtn.textContent = "Export SVG";
exportBtn.style.cssText = "position:fixed;top:10px;right:10px;padding:8px 16px;background:#3D3733;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:13px;z-index:100;";
exportBtn.onclick = () => {{
  const svgEl = document.querySelector("svg");
  // Strip paint-order halos from labels (Illustrator can't render them)
  svgEl.querySelectorAll("#series-labels text").forEach(t => {{
    t.removeAttribute("stroke");
    t.removeAttribute("stroke-width");
    t.removeAttribute("stroke-linejoin");
    t.removeAttribute("paint-order");
  }});
  // Force ALL computed styles as inline attributes for Illustrator compatibility
  svgEl.querySelectorAll("text").forEach(t => {{
    const cs = getComputedStyle(t);
    t.setAttribute("font-family", "ABC Oracle Edu");
    if (!t.getAttribute("font-size")) t.setAttribute("font-size", cs.fontSize);
    if (!t.getAttribute("fill")) t.setAttribute("fill", cs.fill || "#3D3733");
    if (!t.getAttribute("font-weight")) t.setAttribute("font-weight", cs.fontWeight);
  }});
  svgEl.querySelectorAll("line").forEach(l => {{
    const cs = getComputedStyle(l);
    if (!l.getAttribute("stroke") || l.getAttribute("stroke") === "none") {{
      l.setAttribute("stroke", cs.stroke || "#e1e2e3");
    }}
    if (!l.getAttribute("stroke-width")) l.setAttribute("stroke-width", cs.strokeWidth || "1");
  }});
  svgEl.setAttribute("font-family", "ABC Oracle Edu");
  svgEl.setAttribute("xmlns:xlink", "http://www.w3.org/1999/xlink");
  const serializer = new XMLSerializer();
  let svgStr = serializer.serializeToString(svgEl);
  svgStr = '<?xml version="1.0" encoding="UTF-8"?>\\n' + svgStr;
  const blob = new Blob([svgStr], {{type:"image/svg+xml"}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "ftb_longrun.svg";
  a.click();
  URL.revokeObjectURL(url);
}};
document.body.prepend(exportBtn);
</script>
</body></html>"""

with open("/Users/azizsunderji/Dropbox/Home Economics/2026_03_16_FTB/outputs/ftb_longrun.html", "w") as f:
    f.write(html)
print("Saved to outputs/ftb_longrun.html")

# ── Also generate standalone SVG for Illustrator ──
# Use a headless approach: render the HTML, extract SVG, clean for Illustrator
import subprocess, tempfile, os

# We'll use a small Node.js script with jsdom to render D3 server-side
# But simpler: just extract the SVG structure we know and build it directly

svg_out = '/Users/azizsunderji/Dropbox/Home Economics/2026_03_16_FTB/outputs/ftb_longrun.svg'

# Build SVG string directly from our data (same logic as the HTML but static)
def build_svg():
    import io
    s = io.StringIO()
    W, H = 960, 987
    pad = 30
    titleY = 40 + 32
    subtitleY = titleY + 34
    gapSubtitleToChart = 75
    chartTop = subtitleY + gapSubtitleToChart
    sourceFont = 15
    sourceLineH = sourceFont + 3
    sourceBlockH = 3 * sourceLineH
    gapXaxisToSource = 45
    gapSourceToBottom = 40
    sourceTop = H - gapSourceToBottom - sourceBlockH
    xAxisLabelsBottom = sourceTop - gapXaxisToSource
    xAxisLabelsH = 50
    chartBottom = xAxisLabelsBottom - xAxisLabelsH
    chartH = chartBottom - chartTop
    mLeft, mRight = 95, 40
    chartLeft = mLeft
    chartW = W - mLeft - mRight
    gridExtendLeft = 55
    gridLeftEdge = chartLeft - gridExtendLeft
    gridRightEdge = chartLeft + chartW

    # Scales
    def sx(year): return (year - 1972) / (2027 - 1972) * chartW
    def sy(age): return (40 - age) / (40 - 20) * chartH

    s.write(f'<?xml version="1.0" encoding="UTF-8"?>\n')
    s.write(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" ')
    s.write(f'width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="ABC Oracle Edu">\n')

    # Background
    s.write(f'<rect width="{W}" height="{H}" fill="#F6F7F3"/>\n')

    # Title
    s.write(f'<g id="title"><text x="{gridLeftEdge}" y="{titleY}" font-size="32" font-weight="500" fill="#3D3733">')
    s.write(f'Median age of first-time homebuyers, 1974\u20132025</text></g>\n')

    # Subtitle
    s.write(f'<g id="subtitle"><text x="{gridLeftEdge}" y="{subtitleY}" font-size="23" font-weight="400" fill="#7F7570">')
    s.write(f'FTB age rose with marriage age through the early 1990s, then decoupled</text></g>\n')

    tx, ty = chartLeft, chartTop

    # Grid lines
    s.write(f'<g id="grid-lines">\n')
    for v in [20, 25, 30, 35, 40]:
        yy = ty + sy(v)
        s.write(f'  <line x1="{gridLeftEdge}" y1="{yy}" x2="{gridRightEdge}" y2="{yy}" stroke="#e1e2e3" stroke-width="1"/>\n')
    s.write(f'</g>\n')

    # Data series
    all_series = [
        ('psid', psid, '#0BB4FF'),
        ('marriage', marriage, '#F4743B'),
        ('headship', headship, '#67A275'),
    ]

    s.write(f'<g id="data-series">\n')
    for name, data, color in all_series:
        pts = ' '.join(f'{tx+sx(y)},{ty+sy(a)}' for y,a in data)
        s.write(f'  <polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.5" style="mix-blend-mode:multiply"/>\n')
    # Dot at marriage data source switch (2008)
    switch_age = dict(marriage).get(2008)
    if switch_age:
        cx = tx + sx(2008)
        cy = ty + sy(switch_age)
        s.write(f'  <circle cx="{cx}" cy="{cy}" r="4" fill="#F4743B" stroke="#F6F7F3" stroke-width="2"/>\n')
    s.write(f'</g>\n')

    # X axis ticks
    xTickVals = [1975, 1985, 1995, 2005, 2015, 2025]
    s.write(f'<g id="x-axis-ticks">\n')
    for v in xTickVals:
        xx = tx + sx(v)
        s.write(f'  <line x1="{xx}" y1="{ty+chartH}" x2="{xx}" y2="{ty+chartH+12}" stroke="#3D3733" stroke-width="0.5"/>\n')
    s.write(f'</g>\n')

    # X axis labels
    s.write(f'<g id="x-axis-labels">\n')
    for v in xTickVals:
        xx = tx + sx(v)
        label = str(v) if v in (1975, 2005) else "\u2019" + str(v)[2:]
        s.write(f'  <text x="{xx}" y="{ty+chartH+38}" text-anchor="middle" font-size="22" font-weight="300" fill="#333">{label}</text>\n')
    s.write(f'</g>\n')

    # Y axis labels
    s.write(f'<g id="y-axis-labels">\n')
    for i, v in enumerate([20, 25, 30, 35, 40]):
        yy = ty + sy(v)
        label = f'{v} yrs' if v == 40 else str(v)
        s.write(f'  <text x="{gridLeftEdge}" y="{yy - 5}" font-size="22" font-weight="300" fill="#333">{label}</text>\n')
    s.write(f'</g>\n')

    # Series labels
    label_data = [
        (psid, '#0BB4FF', 'Ownership (PSID)', 2019, -18),
        (marriage, '#F4743B', 'Marriage (CPS)', 2008, 16),
        (headship, '#67A275', 'Headship (CPS)', 2000, -16),
    ]
    # Labels: each halo+text pair is its own top-level <g> (not nested in a shared parent)
    for data, color, label, year, yoff in label_data:
        pt = next((a for y,a in data if y == year), None)
        if pt is None: continue
        lx = tx + sx(year) + 10
        ly = ty + sy(pt) + yoff
        safe_id = label.lower().replace(' ','-').replace('(','').replace(')','')
        s.write(f'<g id="label-{safe_id}">\n')
        s.write(f'  <text x="{lx}" y="{ly}" font-size="16" font-weight="500" fill="#F6F7F3" stroke="#F6F7F3" stroke-width="5" stroke-linejoin="round" font-family="ABC Oracle Edu">{label}</text>\n')
        s.write(f'  <text x="{lx}" y="{ly}" font-size="16" font-weight="500" fill="{color}" font-family="ABC Oracle Edu">{label}</text>\n')
        s.write(f'</g>\n')

    # Source
    sourceBottom = sourceTop + sourceFont + sourceLineH
    s.write(f'<g id="source">\n')
    s.write(f'  <text x="{gridLeftEdge}" y="{sourceTop + sourceFont}" font-size="{sourceFont}" font-weight="200" fill="#3D3733">')
    s.write(f'<tspan x="{gridLeftEdge}" dy="0">Sources: PSID 1974\u20132023 (rent-to-own transitions); CPS ASEC 1976\u20132025 (headship, MS-2 method);</tspan>')
    s.write(f'<tspan x="{gridLeftEdge}" dy="{sourceLineH}">Marriage: CPS MS-2 method 1976\u20132007, ACS direct (YRMARR) 2008\u20132023. All medians.</tspan>')
    s.write(f'</text>\n')
    s.write(f'</g>\n')

    # Logo
    logoW, logoH = 130, 42
    logoX = gridRightEdge - logoW
    logoY = sourceBottom - logoH
    s.write(f'<g id="logo">\n')
    s.write(f'  <image x="{logoX}" y="{logoY}" width="{logoW}" height="{logoH}" opacity="0.6" ')
    s.write(f'xlink:href="data:image/png;base64,{logo_b64}"/>\n')
    s.write(f'</g>\n')

    s.write(f'</svg>')
    return s.getvalue()

svg_content = build_svg()
with open(svg_out, 'w') as f:
    f.write(svg_content)
print(f"Saved SVG to {svg_out}")

# Open in Illustrator
os.system(f'open -a "Adobe Illustrator" "{svg_out}"')
