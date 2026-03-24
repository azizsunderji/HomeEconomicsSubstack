"""
AHS First-Time Homebuyer: Median and Mean age at purchase, 1985-2023.
"""
import sys
sys.path.insert(0, "/Users/azizsunderji/Dropbox/Home Economics/Scripts")
from templates.d3_base import html_wrapper, COLORS as D3_COLORS

ahs = [
    (1985, 30, 32.4),
    (1987, 31, 35.1),
    (1989, 31, 34.0),
    (1991, 31, 34.5),
    (1993, 32, 35.2),
    (1995, 32, 34.6),
    # 1997, 1999: no actual age variable
    (2001, 31, 33.3),
    (2003, 31, 32.8),
    (2005, 30, 32.5),
    (2007, 30, 32.7),
    (2009, 30, 32.9),
    (2011, 30, 33.1),
    (2013, 30, 33.4),
    (2015, 32, 34.8),
    (2017, 32, 35.7),
    (2019, 32, 35.4),
    (2021, 33, 35.8),
    (2023, 34, 36.6),
]

median_json = ", ".join([f'{{"year":{y},"age":{m}}}' for y, m, _ in ahs])
mean_json = ", ".join([f'{{"year":{y},"age":{round(a,1)}}}' for y, _, a in ahs])

html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<style>
  body {{ margin:0; background: #F6F7F3; font-family: 'ABC Oracle Edu', system-ui, sans-serif; }}
  svg {{ display: block; margin: 0 auto; }}
  .title {{ font-size: 18px; font-weight: 700; fill: #3D3733; }}
  .subtitle {{ font-size: 13px; fill: #3D3733; opacity: 0.8; }}
  .source {{ font-size: 10px; fill: #999; font-style: italic; }}
  .axis text {{ font-size: 11px; fill: #3D3733; }}
  .axis path, .axis line {{ stroke: #ccc; }}
  .grid line {{ stroke: #fff; stroke-width: 1; }}
  .grid path {{ stroke: none; }}
  .label {{ font-size: 11px; font-weight: 600; }}
  .dot {{ stroke: #fff; stroke-width: 1.5; }}
  .annotation {{ font-size: 10px; fill: #999; font-style: italic; }}
  .break-line {{ stroke: #999; stroke-dasharray: 4,3; stroke-width: 1; }}
</style>
<script src="https://d3js.org/d3.v7.min.js"></script>
</head><body>
<script>
const median = [{median_json}];
const mean = [{mean_json}];

const W = 900, H = 550;
const margin = {{top: 70, right: 90, bottom: 60, left: 50}};
const w = W - margin.left - margin.right;
const h = H - margin.top - margin.bottom;

const svg = d3.select("body").append("svg")
  .attr("width", W).attr("height", H)
  .style("background", "#F6F7F3");

const g = svg.append("g")
  .attr("transform", `translate(${{margin.left}},${{margin.top}})`);

// Title
svg.append("text").attr("class","title")
  .attr("x", margin.left).attr("y", 28)
  .text("Median and mean age of first-time homebuyers");
svg.append("text").attr("class","subtitle")
  .attr("x", margin.left).attr("y", 48)
  .text("Age at purchase, recent movers only. AHS biennial, 1985-2023.");

// Scales
const x = d3.scaleLinear()
  .domain([1984, 2025])
  .range([0, w]);

const y = d3.scaleLinear()
  .domain([28, 38])
  .range([h, 0]);

// Grid
g.append("g").attr("class","grid")
  .call(d3.axisLeft(y).tickSize(-w).tickFormat("").ticks(5));

// X axis
g.append("g").attr("class","axis")
  .attr("transform", `translate(0,${{h}})`)
  .call(d3.axisBottom(x).tickFormat(d3.format("d"))
    .tickValues([1985,1990,1995,2000,2005,2010,2015,2020,2025]));

// Y axis
const yAxis = g.append("g").attr("class","axis")
  .call(d3.axisLeft(y).ticks(5).tickSize(0)
    .tickFormat((d,i,nodes) => i === nodes.length-1 ? d + " yrs" : d));
yAxis.select(".domain").remove();

// Break annotation (1997-1999 gap)
const gapX1 = x(1995), gapX2 = x(2001);
g.append("line").attr("class","break-line")
  .attr("x1", gapX1+5).attr("x2", gapX2-5)
  .attr("y1", y(32.5)).attr("y2", y(32.5));
g.append("text").attr("class","annotation")
  .attr("x", (gapX1+gapX2)/2).attr("y", y(32.5) - 8)
  .attr("text-anchor","middle")
  .text("no age data");

// 2015 break annotation
g.append("line")
  .attr("x1", x(2015)).attr("x2", x(2015))
  .attr("y1", y(28)).attr("y2", y(37.5))
  .attr("stroke", "#F4743B").attr("stroke-dasharray", "3,3")
  .attr("stroke-width", 1).attr("opacity", 0.6);
g.append("text").attr("class","annotation")
  .attr("x", x(2015)+4).attr("y", y(37.2))
  .attr("fill", "#F4743B").attr("font-style","italic")
  .text("AHS redesign");

// Lines
const line = d3.line().x(d => x(d.year)).y(d => y(d.age));

// Split at gap
const pre = (arr) => arr.filter(d => d.year <= 1995);
const post = (arr) => arr.filter(d => d.year >= 2001);

// Mean line
[pre(mean), post(mean)].forEach(seg => {{
  g.append("path").datum(seg)
    .attr("d", line)
    .attr("fill","none").attr("stroke","#FEC439")
    .attr("stroke-width", 2.5).attr("stroke-dasharray","6,3");
}});

// Median line
[pre(median), post(median)].forEach(seg => {{
  g.append("path").datum(seg)
    .attr("d", line)
    .attr("fill","none").attr("stroke","#0BB4FF")
    .attr("stroke-width", 2.5);
}});

// Dots
median.forEach(d => {{
  g.append("circle").attr("class","dot")
    .attr("cx", x(d.year)).attr("cy", y(d.age))
    .attr("r", 3.5).attr("fill","#0BB4FF");
}});
mean.forEach(d => {{
  g.append("circle").attr("class","dot")
    .attr("cx", x(d.year)).attr("cy", y(d.age))
    .attr("r", 3.5).attr("fill","#FEC439");
}});

// End labels
const lastMed = median[median.length-1];
const lastMean = mean[mean.length-1];
g.append("text").attr("class","label")
  .attr("x", x(lastMed.year)+8).attr("y", y(lastMed.age)+4)
  .attr("fill","#0BB4FF").text("Median: " + lastMed.age);
g.append("text").attr("class","label")
  .attr("x", x(lastMean.year)+8).attr("y", y(lastMean.age)+4)
  .attr("fill","#FEC439").text("Mean: " + lastMean.age);

// Start labels
const firstMed = median[0];
const firstMean = mean[0];
g.append("text").attr("class","label")
  .attr("x", x(firstMed.year)-8).attr("y", y(firstMed.age)+4)
  .attr("text-anchor","end").attr("fill","#0BB4FF")
  .text(firstMed.age);
g.append("text").attr("class","label")
  .attr("x", x(firstMean.year)-8).attr("y", y(firstMean.age)+4)
  .attr("text-anchor","end").attr("fill","#FEC439")
  .text(firstMean.age);

// Source
svg.append("text").attr("class","source")
  .attr("x", margin.left).attr("y", H - 12)
  .text("Source: American Housing Survey (Census/HUD), 1985-2023. Recent movers (within 2 years), first-time owners, weighted.");
</script>
</body></html>"""

with open("/Users/azizsunderji/Dropbox/Home Economics/2026_03_16_FTB/outputs/ahs_ftb_age.html", "w") as f:
    f.write(html)
print("Saved to outputs/ahs_ftb_age.html")
