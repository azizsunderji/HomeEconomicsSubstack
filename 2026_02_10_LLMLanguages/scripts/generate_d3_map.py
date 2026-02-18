"""
Generate D3.js interactive world choropleth of LLM language coverage.
Uses admin1-level TopoJSON with tier + score properties.
Output: outputs/llm_language_map.html
"""
import os
import json

BASE_DIR = "/Users/azizsunderji/Dropbox/Home Economics/2026_02_10_LLMLanguages"
TOPO_PATH = os.path.join(BASE_DIR, "data", "admin1_with_tiers.topojson")
OUTPUT_HTML = os.path.join(BASE_DIR, "outputs", "llm_language_map.html")

# Load TopoJSON
with open(TOPO_PATH) as f:
    topo_data = json.load(f)

# Get the object name
obj_name = list(topo_data["objects"].keys())[0]
topo_json_str = json.dumps(topo_data)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Which Countries Are Left Behind by AI?</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>

        @font-face {{
            font-family: 'ABC Oracle Edu';
            src: url('/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop/ABCOracle-Light.otf') format('opentype');
            font-weight: 300;
            font-style: normal;
        }}
        @font-face {{
            font-family: 'ABC Oracle Edu';
            src: url('/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop/ABCOracle-Regular.otf') format('opentype');
            font-weight: 400;
            font-style: normal;
        }}
        @font-face {{
            font-family: 'ABC Oracle Edu';
            src: url('/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop/ABCOracle-Medium.otf') format('opentype');
            font-weight: 500;
            font-style: normal;
        }}
        @font-face {{
            font-family: 'ABC Oracle Edu';
            src: url('/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop/ABCOracle-Bold.otf') format('opentype');
            font-weight: 700;
            font-style: normal;
        }}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    font-family: 'ABC Oracle Edu', system-ui, sans-serif;
    background: #F6F7F3;
    display: flex;
    justify-content: center;
    padding: 20px;
}}

.chart-container {{
    width: 900px;
    background: #F6F7F3;
}}

.chart-title {{
    font-size: 23px;
    font-weight: 500;
    color: #3D3733;
    margin-bottom: 4px;
    line-height: 1.2;
}}

.chart-subtitle {{
    font-size: 16px;
    font-weight: 300;
    color: #3D3733;
    opacity: 0.7;
    margin-bottom: 16px;
    line-height: 1.3;
}}

.chart-source {{
    font-size: 11px;
    font-weight: 300;
    color: #999;
    font-style: italic;
    margin-top: 8px;
}}

.tooltip {{
    position: absolute;
    background: white;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 8px 12px;
    font-size: 13px;
    font-family: 'ABC Oracle Edu', system-ui, sans-serif;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.15s ease;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    color: #3D3733;
}}

.tooltip-title {{
    font-weight: 500;
    margin-bottom: 2px;
}}

.tooltip-subtitle {{
    font-weight: 300;
    opacity: 0.6;
    font-size: 12px;
    margin-bottom: 4px;
}}

.tooltip-tier {{
    display: inline-block;
    padding: 1px 8px;
    border-radius: 3px;
    color: white;
    font-size: 11px;
    font-weight: 500;
    margin-top: 2px;
}}

#map-container {{
    width: 900px;
    height: 520px;
    position: relative;
}}

#map {{
    width: 100%;
    height: 100%;
}}

.admin1 {{
    stroke: #fff;
    stroke-width: 0.3px;
    cursor: pointer;
    transition: opacity 0.1s;
}}

.admin1:hover {{
    opacity: 0.8;
    stroke-width: 1px;
    stroke: #3D3733;
}}

.country-border {{
    fill: none;
    stroke: #fff;
    stroke-width: 0.8px;
    pointer-events: none;
}}

.sphere {{
    fill: none;
    stroke: #3D3733;
    stroke-width: 0.5px;
}}

.graticule {{
    fill: none;
    stroke: #ddd;
    stroke-width: 0.3px;
}}

#legend {{
    display: flex;
    gap: 24px;
    justify-content: center;
    margin-top: 12px;
    font-size: 13px;
    color: #3D3733;
}}

.legend-item {{
    display: flex;
    align-items: center;
    gap: 6px;
}}

.legend-swatch {{
    width: 16px;
    height: 16px;
    border-radius: 3px;
}}

</style>
</head>
<body>
<div class="chart-container">
    <div class="chart-title">Which Countries Are Left Behind by AI?</div>
    <div class="chart-subtitle">LLM language performance by sub-national region, based on LanguageBench scores across 34 models</div>
    <div id="map-container">
        <svg id="map"></svg>
    </div>
    <div id="legend"></div>
    <div class="chart-source">Sources: LanguageBench (fair-forward, 2025), Unicode CLDR, Natural Earth</div>
</div>
<div class="tooltip" id="tooltip"></div>

<script src="https://cdn.jsdelivr.net/npm/topojson-client@3"></script>

<script>

const topoData = {topo_json_str};
const objName = "{obj_name}";

const tierColors = {{
    1: "#0BB4FF",
    2: "#FEC439",
    3: "#F4743B"
}};

const tierLabels = {{
    1: "Well served",
    2: "Partially served",
    3: "Poorly served"
}};

const width = 900;
const height = 520;

const svg = d3.select("#map")
    .attr("viewBox", [0, 0, width, height]);

// Equal Earth projection
const projection = d3.geoEqualEarth()
    .fitSize([width, height], {{type: "Sphere"}})
    .translate([width / 2, height / 2 + 20]);

const path = d3.geoPath(projection);

// Background
svg.append("rect")
    .attr("width", width)
    .attr("height", height)
    .attr("fill", "#F6F7F3");

// Graticule
const graticule = d3.geoGraticule().step([30, 30]);
svg.append("path")
    .datum(graticule)
    .attr("class", "graticule")
    .attr("d", path);

// Admin-1 regions
const admin1 = topojson.feature(topoData, topoData.objects[objName]);

svg.selectAll(".admin1")
    .data(admin1.features)
    .enter()
    .append("path")
    .attr("class", "admin1")
    .attr("d", path)
    .attr("fill", d => {{
        const tier = d.properties.tier || null;
        if (tier === null) return "#E0E0E0";
        return tierColors[tier] || "#E0E0E0";
    }})
    .on("mouseover", function(event, d) {{
        const props = d.properties;
        const tier = props.tier;
        const score = props.score;
        const scoreStr = score ? (score * 100).toFixed(0) + "/100" : "Not measured";
        const lang = props.language || "Unknown";

        const tooltip = d3.select("#tooltip");
        let html = `
            <div class="tooltip-title">${{props.name}}</div>
            <div class="tooltip-subtitle">${{props.admin || props.iso_a2 || ""}}</div>
            <div>Language: ${{lang}}</div>
            <div>Score: ${{scoreStr}}</div>
        `;
        if (tier) {{
            html += `<div class="tooltip-tier" style="background:${{tierColors[tier]}}">${{tierLabels[tier]}}</div>`;
        }}
        tooltip.html(html)
            .style("opacity", 1)
            .style("left", (event.pageX + 12) + "px")
            .style("top", (event.pageY - 28) + "px");
    }})
    .on("mousemove", function(event) {{
        d3.select("#tooltip")
            .style("left", (event.pageX + 12) + "px")
            .style("top", (event.pageY - 28) + "px");
    }})
    .on("mouseout", function() {{
        d3.select("#tooltip").style("opacity", 0);
    }});

// Country borders (thicker mesh)
const countryMesh = topojson.mesh(topoData, topoData.objects[objName],
    (a, b) => a.properties.iso_a2 !== b.properties.iso_a2);
svg.append("path")
    .datum(countryMesh)
    .attr("class", "country-border")
    .attr("d", path);

// Legend
const legendContainer = d3.select("#legend");
[1, 2, 3].forEach(tier => {{
    const item = legendContainer.append("div").attr("class", "legend-item");
    item.append("div").attr("class", "legend-swatch")
        .style("background", tierColors[tier]);
    item.append("span").text(tierLabels[tier]);
}});
// No data legend
const noDataItem = legendContainer.append("div").attr("class", "legend-item");
noDataItem.append("div").attr("class", "legend-swatch")
    .style("background", "#E0E0E0");
noDataItem.append("span").text("No data");

</script>
</body>
</html>"""

with open(OUTPUT_HTML, 'w') as f:
    f.write(html)

size_mb = os.path.getsize(OUTPUT_HTML) / 1e6
print(f"Saved {OUTPUT_HTML} ({size_mb:.1f} MB)")
