"""
Delete previous draft article blocks from Notion page and post a revised
version that more closely follows the author's outline:

Outline points (from the page's bulleted list at the top):
  1. Conventional view (Derek Thompson, Atlantic) + zoning advocates picking it up
  2. NYC as poster child — boroughs losing kids faster than anywhere
  3. When movers are asked WHY — space/amenities, not affordability
  4. CPS voronoi chart
  5. Affordability isn't irrelevant — more important than crime; fungible
  6. But this isn't new — every decade since 1940s
  7. National burden data corroborates
  8. (Fertility is HIGHER in cities — fits in para about cities not being fertility-deficient)
  9. Sun Belt cores grow on external migration, not retention
"""
import json
import requests
import time
from pathlib import Path

NOTION_TOKEN = json.load(open(Path.home() / ".claude.json"))["mcpServers"]["notion"]["env"]["NOTION_TOKEN"]
PAGE_ID = "364008aa-e629-8155-b2b3-edbb4b20ad41"
HDRS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
}

# ── Step 1: fetch all top-level blocks and find ones I created at 17:33 ────────
r = requests.get(
    f"https://api.notion.com/v1/blocks/{PAGE_ID}/children?page_size=100",
    headers=HDRS, timeout=30,
)
r.raise_for_status()
all_blocks = r.json().get("results", [])
print(f"Total top-level blocks on page: {len(all_blocks)}")

# My previous post was on 2026-05-19 around 17:33 UTC. Delete anything created
# on this date that's a draft-article block I added.
to_delete = []
in_draft_section = False
for b in all_blocks:
    ct = b.get("created_time", "")
    if ct.startswith("2026-05-19T17:33") or ct.startswith("2026-05-19T17:34") or ct.startswith("2026-05-19T17:35"):
        to_delete.append(b["id"])

print(f"Found {len(to_delete)} blocks to delete (previous draft).")

for bid in to_delete:
    rr = requests.delete(
        f"https://api.notion.com/v1/blocks/{bid}",
        headers={**HDRS, "Content-Type": "application/json"},
        timeout=30,
    )
    print(f"  delete {bid}: HTTP {rr.status_code}")
    time.sleep(0.1)

# ── Step 2: post revised article ──────────────────────────────────────────────
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
    return {"type": "table_row", "table_row": {"cells": [[text(c, bold=bold)] for c in cells]}}


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

DOE_TABLE = {
    "type": "table",
    "table": {
        "table_width": 2,
        "has_column_header": True,
        "has_row_header": False,
        "children": (
            [table_row(DOE_TABLE_ROWS[0], bold=True)]
            + [table_row(r) for r in DOE_TABLE_ROWS[1:]]
        ),
    },
}


P1_BOLD = ('The view that American cities are being hollowed out of children—spread most '
           'influentially by Derek Thompson\'s 2019 Atlantic essay "The Future of the City '
           'Is Childless," and adopted by zoning-reform advocates as a foundational argument '
           'against urban zoning restrictions—has been particularly attached to New York. '
           'Of all counties in the country, NYC\'s five boroughs have been losing children '
           'fastest: Manhattan -73,000 to net out-migration between 2011 and 2024 (a 31% '
           'drop from its baseline, the steepest of any large county), Brooklyn -114,000, '
           'Queens -55,000.')

P2 = ('When the families themselves are asked why they moved, "cheaper housing" comes in fifth. '
      'The chart below shows reasons NY families with kids gave for moving out of state, '
      'from the Census Bureau\'s Current Population Survey, pooled 1999-2025 (n=1,291). '
      'Cells are sized by share of moves; categories share a color.')

CHART1 = ("[Chart: outputs/whymove_voronoi.html — NY families with kids: stated reasons for "
          "leaving the state, CPS ASEC pooled 1999-2025.]")

P3 = ('A new job is the most-cited reason (27%), followed by family circumstances (13%), '
      '"new or better housing" (10%), wanting to own (7%), better neighborhood or less crime '
      '(6%), and cheaper housing (5%). The upgrade motives in the housing cluster beat the '
      'cost-flight motive about two-to-one. A 2024-25 NYC Department of Education survey of '
      '1,604 families that left the city\'s public schools reaches the same ordering.')

DOE_CAPTION = ("Source: NYC Department of Education, April 2025 Enrollment Survey. "
               "Multi-select question; shares do not sum to 100%. n=1,604.")

P4 = ('This doesn\'t make housing costs irrelevant. The combined housing-related cluster '
      '("new or better housing" + "wanted to own" + "cheaper housing") is 22% of moves—roughly '
      'three times the share citing crime. And the categories are fungible: when a family says '
      'it left for more space, that often means it couldn\'t afford that space in the city. '
      'The trigger is usually having a baby. 60% of NYC families that move to the suburbs have '
      'just one child, and 45% have an oldest kid aged 1-3. The move concentrates at pre-K, '
      'not at kindergarten.')

P5 = ('But the bigger challenge for the housing-crisis story is that this flow isn\'t new. '
      'NYC\'s five boroughs have had net out-migration of children in every decade since the 1940s. '
      'The 1950s, when the postwar suburbs were still being built, saw NYC lose 323,000 kids '
      'to migration—the biggest decadal exodus in the city\'s history. The 1970s lost another '
      '286,000 on top of a baby bust (the only decade where both forces pulled in the same '
      'direction). The 2010s number, 152,000, is on the small end.')

CHART2 = ("[Chart: outputs/nyc_decadal_decomposition_combined.html — NYC 5-borough under-18 "
          "by decade, 1940-2020. Natural change (births minus aging-out) in green, net migration "
          "in blue. Net Δ marker in black.]")

P6 = ('Cities are not, despite the framing, fertility-deficient. NYC\'s five boroughs '
      'out-produced their aging-out cohort over 2011-2024: more babies were born to residents '
      'than under-18s aged into adulthood. The cross-sectional data doesn\'t support an '
      'affordability mechanism either. Across 316 counties where I can compare 2011-2023 changes '
      'in housing burden to changes in under-18 population, the relationship is essentially flat '
      '(R² of 0.07). The most-burdened cities (Bronx 55%, Brooklyn 46%, LA 47%) actually saw '
      'burden decline as the most-burdened residents left. The Sun Belt suburbs that gained '
      'kids fastest—Johnson County TX (+10pp), Brazoria (+5pp), Denton (+3pp)—saw burden rise. '
      'Burden growth and kid growth move together.')

P7 = ('The Sun Belt urban cores that grew aren\'t retaining their own families either. '
      'Maricopa County (Phoenix) drew 80% of its in-migrants from outside Arizona and only '
      '8% from the local Phoenix suburbs. Mecklenburg (Charlotte) drew 60% out-of-state and '
      '25% local. Travis (Austin) was 46% versus 25%. The cores grow because external '
      'migration is large enough to drown out a still-substantial core-to-suburb flow, '
      'not because they\'ve solved the housing-and-family problem. The flow from city to suburb '
      'survived the postwar boom, the 1970s fiscal crisis, the 1990s rebound, and the 2010s '
      'YIMBY revival. Treating it as a housing-policy emergency makes for both bad policy and '
      'weak history.')


blocks = [
    {"type": "divider", "divider": {}},
    heading(2, "Draft Article"),
    heading(3, "Why Are Families Leaving New York City?"),
    {
        "type": "paragraph",
        "paragraph": {"rich_text": [text(P1_BOLD, bold=True)]},
    },
    para(P2),
    callout(CHART1),
    para(P3),
    DOE_TABLE,
    para(DOE_CAPTION, italic=True),
    para(P4),
    para(P5),
    callout(CHART2),
    para(P6),
    para(P7),
]

resp = requests.patch(
    f"https://api.notion.com/v1/blocks/{PAGE_ID}/children",
    headers={**HDRS, "Content-Type": "application/json"},
    data=json.dumps({"children": blocks}),
    timeout=60,
)
print(f"\nPOST result: HTTP {resp.status_code}")
print(resp.text[:600])
