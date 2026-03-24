"""
Two charts comparing MS-2 method vs naive cross-sectional method.
3 series each: Ownership (PSID), Marriage, Headship.
"""
import json, base64, os

# ── Data ──
psid = [
    (1974,27),(1975,29),(1976,28),(1977,28),(1978,28),(1979,28),(1980,28),(1981,28),
    (1982,29),(1983,28),(1984,30),(1985,29),(1986,29),(1987,31),(1988,31),(1989,30),
    (1991,32),(1992,33),(1993,32),(1994,35),(1995,33),(1996,33),(1997,32),(1999,33),
    (2001,33),(2003,33),(2005,32),(2007,33),(2009,32),(2011,31),(2013,32),(2015,32),
    (2017,34),(2019,34),(2021,35),(2023,34),
]

# Published Census MS-2
marriage_census = [
    (1974,22.9),(1975,22.7),(1976,23.0),(1977,23.1),(1978,23.4),(1979,23.6),
    (1980,23.4),(1981,23.8),(1982,24.0),(1983,24.2),(1984,24.5),(1985,24.4),
    (1986,25.0),(1987,25.2),(1988,25.2),(1989,25.5),(1990,25.0),(1991,25.3),
    (1992,25.5),(1993,25.5),(1994,25.5),(1995,25.7),(1996,25.8),(1997,26.0),
    (1998,26.1),(1999,26.3),(2000,26.0),(2001,26.0),(2002,26.1),(2003,26.3),
    (2004,26.4),(2005,26.2),(2006,26.6),(2007,26.8),(2008,27.0),(2009,27.4),
    (2010,27.1),(2011,27.6),(2012,27.6),(2013,27.8),(2014,28.0),(2015,28.1),
    (2016,28.5),(2017,28.5),(2018,28.8),(2019,28.9),(2020,29.3),(2021,29.5),
    (2022,29.1),(2023,29.3),(2024,29.4),(2025,29.6),
]

# Load computed results
with open('/Users/azizsunderji/Dropbox/Home Economics/2026_03_16_FTB/data/ms2_method_proper.json') as f:
    computed = json.load(f)

# MS-2 method versions (from our proper computation)
marriage_ms2 = [(r['year'], r['age']) for r in computed['marriage_ms2_method']]
headship_ms2 = [(r['year'], r['age']) for r in computed['headship_ms2_method']]

# Naive versions
marriage_naive = [(r['year'], r['age']) for r in computed['marriage_naive']]
headship_naive = [(r['year'], r['age']) for r in computed['headship_naive']]

def to_js(data):
    return "[" + ",".join(f'{{"year":{y},"age":{a}}}' for y,a in data) + "]"

LOGO = '/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/HomeEconomics-Logo-versions/HE-Large-Black.png'
with open(LOGO, 'rb') as f:
    logo_b64 = base64.b64encode(f.read()).decode()

BLUE = "#0077CC"
RED = "#F4743B"
RED_DARK = "#C4301C"
GREEN = "#67A275"

def make_chart(title, subtitle, marriage_data, headship_data, source_note, marriage_label, chart_id):
    return f"""
function drawChart_{chart_id}(containerId) {{
  const psid = {to_js(psid)};
  const marriage = {to_js(marriage_data)};
  const marriage_census = {to_js(marriage_census)};
  const headship = {to_js(headship_data)};

  const W = 960, H = 850;
  const pad = 30;
  const titleY = 40 + 32;
  const subtitleY = titleY + 34;
  const gapSubtitleToChart = 65;
  const chartTop = subtitleY + gapSubtitleToChart;
  const sourceFont = 15;
  const sourceLineH = sourceFont + 3;
  const sourceBlockH = 2 * sourceLineH;
  const gapXaxisToSource = 45;
  const gapSourceToBottom = 40;
  const sourceTop = H - gapSourceToBottom - sourceBlockH;
  const xAxisLabelsBottom = sourceTop - gapXaxisToSource;
  const xAxisLabelsH = 50;
  const chartBottom = xAxisLabelsBottom - xAxisLabelsH;
  const chartH = chartBottom - chartTop;
  const mLeft = 95, mRight = 40;
  const chartLeft = mLeft;
  const chartW = W - mLeft - mRight;
  const gridExtendLeft = 55;
  const gridLeftEdge = chartLeft - gridExtendLeft;

  const svg = d3.select("#"+containerId).append("svg").attr("width",W).attr("height",H)
    .attr("font-family","ABC Oracle Edu").style("display","block");
  svg.append("rect").attr("width",W).attr("height",H).attr("fill","#F6F7F3");
  const tx = chartLeft, ty = chartTop;

  // Title
  svg.append("text").attr("x",gridLeftEdge).attr("y",titleY)
    .attr("font-size","32px").attr("font-weight","500").attr("fill","#3D3733")
    .text("{title}");
  svg.append("text").attr("x",gridLeftEdge).attr("y",subtitleY)
    .attr("font-size","23px").attr("font-weight","400").attr("fill","#7F7570")
    .text("{subtitle}");

  const w = chartW, h = chartH;
  const gGrid = svg.append("g").attr("transform",`translate(${{tx}},${{ty}})`);
  const gSeries = svg.append("g").attr("transform",`translate(${{tx}},${{ty}})`);
  const gLabels = svg.append("g").attr("transform",`translate(${{tx}},${{ty}})`);

  const x = d3.scaleLinear().domain([1972,2027]).range([0,w]);
  const y = d3.scaleLinear().domain([20,40]).range([h,0]);

  // Grid
  gGrid.append("g").attr("transform",`translate(-${{gridExtendLeft}},0)`)
    .call(d3.axisLeft(y).tickSize(-(w+gridExtendLeft)).tickFormat("").tickValues([20,25,30,35,40]));
  gGrid.selectAll("line").attr("stroke","#e1e2e3").attr("stroke-width",1);
  gGrid.selectAll("path").attr("stroke","none");

  // X axis
  const xTickVals = [1975,1985,1995,2005,2015,2025];
  const xFmt = d => (d===1975||d===2005) ? String(d) : "\\u2019"+String(d).slice(2);
  xTickVals.forEach(v => {{
    svg.append("line").attr("x1",tx+x(v)).attr("x2",tx+x(v))
      .attr("y1",ty+h).attr("y2",ty+h+12).attr("stroke","#3D3733").attr("stroke-width",0.5);
    svg.append("text").attr("x",tx+x(v)).attr("y",ty+h+12).attr("dy","1.5em")
      .attr("text-anchor","middle").attr("font-size","22px").attr("fill","#333")
      .attr("font-weight","300").attr("font-family","ABC Oracle Edu").text(xFmt(v));
  }});

  // Y axis
  [20,25,30,35,40].forEach((v,i,arr) => {{
    svg.append("text").attr("x",tx-gridExtendLeft).attr("y",ty+y(v))
      .attr("dy","-0.35em").attr("text-anchor","start")
      .attr("font-size","22px").attr("fill","#333").attr("font-weight","300")
      .attr("font-family","ABC Oracle Edu")
      .text(i===arr.length-1 ? v+" yrs" : v);
  }});

  const line = d3.line().x(d=>x(d.year)).y(d=>y(d.age));

  function drawLine(data, color, width) {{
    gSeries.append("path").datum(data).attr("d",line)
      .attr("fill","none").attr("stroke",color).attr("stroke-width",width)
      .style("mix-blend-mode","multiply");
  }}

  // Draw Census MS-2 as thin dashed reference on both charts
  gSeries.append("path").datum(marriage_census).attr("d",line)
    .attr("fill","none").attr("stroke","{RED_DARK}").attr("stroke-width",1.5)
    .attr("stroke-dasharray","6,4").style("mix-blend-mode","multiply");

  drawLine(marriage, "{RED}", 2.5);
  drawLine(headship, "{GREEN}", 2.5);
  drawLine(psid, "{BLUE}", 2.5);

  // Labels
  const labelData = [
    {{data:psid, color:"{BLUE}", label:"Ownership (PSID)", year:2019, yOff:-18}},
    {{data:marriage, color:"{RED}", label:"{marriage_label}", year:2000, yOff:16}},
    {{data:marriage_census, color:"{RED_DARK}", label:"Marriage (Census MS-2)", year:2015, yOff:16}},
    {{data:headship, color:"{GREEN}", label:"Headship (CPS)", year:2008, yOff:-16}},
  ];
  labelData.forEach(lb => {{
    const pt = lb.data.find(d=>d.year===lb.year);
    if (!pt) return;
    const lx = x(pt.year)+10, ly = y(pt.age)+lb.yOff;
    gLabels.append("text").attr("x",lx).attr("y",ly)
      .attr("font-size","16px").attr("font-weight","500").attr("fill",lb.color)
      .attr("stroke","#F6F7F3").attr("stroke-width",5).attr("stroke-linejoin","round")
      .attr("paint-order","stroke").attr("font-family","ABC Oracle Edu").text(lb.label);
  }});

  // Source
  const srcG = svg.append("text").attr("x",gridLeftEdge).attr("y",sourceTop+sourceFont)
    .attr("font-size",sourceFont+"px").attr("font-weight","200").attr("fill","#3D3733");
  srcG.append("tspan").attr("x",gridLeftEdge).attr("dy",0)
    .text("{source_note}");

  // Logo
  const logoW=130, logoH=42;
  const logoX = chartLeft+w-logoW;
  const logoY = sourceTop+sourceFont+sourceLineH-logoH;
  svg.append("image").attr("x",logoX).attr("y",logoY).attr("width",logoW).attr("height",logoH)
    .attr("opacity",0.6).each(function() {{
      this.setAttributeNS("http://www.w3.org/1999/xlink","xlink:href",
        "data:image/png;base64,{logo_b64}");
    }});
}}
"""

dash = "\u2013"
chart_ms2_js = make_chart(
    "Life milestones: MS-2 method",
    "Adjusted for permanently-never share (Census Bureau methodology)",
    marriage_ms2, headship_ms2,
    f"Sources: PSID 1974{dash}2023 (rent-to-own transitions). CPS ASEC (marriage, headship via MS-2 method). Census MS-2 (dashed).",
    "Marriage (CPS, MS-2 method)",
    "ms2"
)
chart_naive_js = make_chart(
    "Life milestones: naive cross-sectional method",
    "Raw age where 50% of population has experienced each milestone",
    marriage_naive, headship_naive,
    f"Sources: PSID 1974{dash}2023 (rent-to-own transitions). CPS ASEC (marriage, headship via 50% crossing).",
    "Marriage (CPS, naive)",
    "naive"
)

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
  .chart-container {{ margin-bottom: 40px; }}
</style>
<script src="https://d3js.org/d3.v7.min.js"></script>
</head><body>
<div id="chart_ms2" class="chart-container"></div>
<div id="chart_naive" class="chart-container"></div>
<script>
{chart_ms2_js}
{chart_naive_js}
drawChart_ms2("chart_ms2");
drawChart_naive("chart_naive");
</script>
</body></html>"""

out = "/Users/azizsunderji/Dropbox/Home Economics/2026_03_16_FTB/outputs/ftb_ms2_vs_naive.html"
with open(out, "w") as f:
    f.write(html)
print(f"Saved to {out}")
os.system(f'open "{out}"')
