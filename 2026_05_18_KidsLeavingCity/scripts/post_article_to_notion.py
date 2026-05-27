"""
Post the draft article to the project Notion page as a new section.
Includes the NYC DOE survey as a featured table.
"""
import json
import requests
from pathlib import Path

NOTION_TOKEN = json.load(open(Path.home() / ".claude.json"))["mcpServers"]["notion"]["env"]["NOTION_TOKEN"]
PAGE_ID = "364008aa-e629-8155-b2b3-edbb4b20ad41"
HDRS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# ── Article paragraphs ────────────────────────────────────────────────────────

P1_BOLD = ("NYC's five boroughs lost nearly 300,000 children to net out-migration between 2011 and 2024"
           "—Manhattan -73,000, Brooklyn -114,000, Queens -55,000. "
           "The conventional explanation is unaffordable housing. "
           "But when the families themselves are asked, \"cheaper housing\" comes in fifth.")

CHART1_NOTE = ("[Chart: outputs/whymove_voronoi.html — Reasons NYC-area families with kids gave for moving "
               "out of state. Census Bureau Current Population Survey ASEC, pooled 1999-2025, n=1,291. "
               "Cells sized by share of moves; categories share a color.]")

P2 = ('A new job is the most-cited reason (27%), followed by family circumstances (13%), '
      '"new or better housing" (10%), wanting to own (7%), better neighborhood or less crime (6%), '
      'and cheaper housing (5%). The upgrade motives in the housing cluster beat the cost-flight motive '
      'roughly two-to-one.')

P3_TABLE_INTRO = ("A 2024-25 NYC Department of Education survey of 1,604 families that left the city's "
                  "public schools points the same way. Cheaper housing was a real factor, but not the "
                  "dominant one.")

# NYC DOE Enrollment Survey, April 2025 (n=1,604 families that left NYC public schools)
DOE_TABLE_ROWS = [
    ("Reason cited for leaving NYC", "Share"),
    ("Better environment to raise kids", "64%"),
    ("Concerns about schools", "50%"),
    ("More housing space", "50%"),
    ("Concerns about crime", "42%"),
    ("Cheaper housing options", "36%"),
    ("Closeness to family", "21%"),
    ("A new job opportunity", "19%"),
    ("Pandemic-related concerns", "6%"),
]
DOE_TABLE_CAPTION = ("Source: NYC Department of Education, April 2025 Enrollment Survey. "
                     "Multi-select question; shares sum to >100%. n=1,604 families that left NYC public schools.")

P4 = ('The classic move trigger is having a baby. Sixty percent of NYC families that move to the suburbs '
      'have just one child, and 45% have an oldest kid aged 1-3. The move concentrates at pre-K, not at '
      'kindergarten. Affordability is rarely irrelevant—the choice between an 800-square-foot Brooklyn '
      'apartment and a 2,400-square-foot Bergen County colonial is partly a price-per-square-foot '
      'decision. But families describe their reasoning as space-and-amenities first, cost second.')

P5 = ("This migration is also very old. NYC's five boroughs have had net out-migration of children in "
      "every decade since the 1940s. The 1950s, when the suburbs were still being built, saw NYC lose "
      "323,000 kids to migration—the biggest decadal exodus in the city's history. The 1970s lost "
      "another 286,000 on top of a baby bust (the only decade where both forces pulled in the same "
      "direction). The 2010s number, 152,000, is on the small end.")

CHART2_NOTE = ("[Chart: outputs/nyc_decadal_decomposition.html — NYC 5-borough under-18 population by "
               "decade, 1940-2020. Births (green) minus aging-out (red) plus net migration (blue) sums "
               "to the net Δ marker. Sources: NHGIS decennial census age tables + NYC DOH Summary of "
               "Vital Statistics.]")

P6 = ("If the housing-crisis frame is right, it has to explain a flow that has been continuous since "
      "World War II. The cross-sectional data makes that hard. Across 316 counties where I can compare "
      "2011-2023 changes in housing burden to changes in under-18 population, the relationship is "
      "essentially flat (R² of 0.07). The most-burdened cities (Bronx 55%, Brooklyn 46%, LA 47%) "
      "actually saw burden decline over the period as the most-burdened residents left. The Sun Belt "
      "suburbs that gained kids fastest—Johnson County TX (+10pp), Brazoria (+5pp), Denton (+3pp)—saw "
      "the biggest burden increases. Burden and kid growth move together, not opposite.")

P7 = ("The Sun Belt urban cores that grew aren't retaining their own families either. Maricopa County "
      "(Phoenix) drew 80% of its in-migrants from outside Arizona and only 8% from the local Phoenix "
      "suburbs. Mecklenburg (Charlotte) drew 60% out-of-state and 25% local. Travis (Austin) was 46% "
      "versus 25%. The cores grow because external migration is large enough to drown out a "
      "still-substantial core-to-suburb flow, not because they've solved the housing-and-family "
      "problem. The flow from city to suburb survived the postwar boom, the 1970s fiscal crisis, the "
      "1990s rebound, and the 2010s YIMBY revival. Treating it as a housing-policy emergency makes "
      "for both bad policy and weak history.")


# ── Block builders ────────────────────────────────────────────────────────────

def text(content, bold=False, italic=False, color="default"):
    return {
        "type": "text",
        "text": {"content": content},
        "annotations": {"bold": bold, "italic": italic, "color": color},
    }


def para(s, bold=False, italic=False):
    return {"type": "paragraph", "paragraph": {"rich_text": [text(s, bold=bold, italic=italic)]}}


def heading(level, s):
    key = f"heading_{level}"
    return {"type": key, key: {"rich_text": [text(s)]}}


def callout(s, emoji="📊"):
    return {
        "type": "callout",
        "callout": {
            "rich_text": [text(s, italic=True, color="gray")],
            "icon": {"type": "emoji", "emoji": emoji},
            "color": "gray_background",
        },
    }


def table_row(cells, bold=False):
    return {
        "type": "table_row",
        "table_row": {"cells": [[text(c, bold=bold)] for c in cells]},
    }


def doe_table():
    rows = [table_row(DOE_TABLE_ROWS[0], bold=True)]
    for r in DOE_TABLE_ROWS[1:]:
        rows.append(table_row(r))
    return {
        "type": "table",
        "table": {
            "table_width": 2,
            "has_column_header": True,
            "has_row_header": False,
            "children": rows,
        },
    }


blocks = [
    {"type": "divider", "divider": {}},
    heading(2, "Draft Article"),
    heading(3, "Why Are Families Leaving New York City?"),
    {
        "type": "paragraph",
        "paragraph": {"rich_text": [text(P1_BOLD, bold=True)]},
    },
    callout(CHART1_NOTE),
    para(P2),
    para(P3_TABLE_INTRO),
    doe_table(),
    para(DOE_TABLE_CAPTION, italic=True),
    para(P4),
    para(P5),
    callout(CHART2_NOTE),
    para(P6),
    para(P7),
]

resp = requests.patch(
    f"https://api.notion.com/v1/blocks/{PAGE_ID}/children",
    headers=HDRS,
    data=json.dumps({"children": blocks}),
    timeout=60,
)
print(f"HTTP {resp.status_code}")
print(resp.text[:1500])
