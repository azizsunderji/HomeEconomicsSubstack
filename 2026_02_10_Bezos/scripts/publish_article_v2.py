"""Publish rewritten Bezos philanthropy article to Notion — v2."""
import json
import urllib.request

NOTION_TOKEN = "ntn_VG145417769qVFknpVyS6nkTJFW8wXMjAIenddQwA5SgvA"
PAGE_ID = "303008aa-e629-818a-bc16-c9f4d1a5fdf7"
AFTER_BLOCK = "303008aa-e629-809c-854b-eba26b645d51"


def rt(content, bold=False, italic=False, color="default"):
    obj = {"type": "text", "text": {"content": content}}
    annotations = {}
    if bold:
        annotations["bold"] = True
    if italic:
        annotations["italic"] = True
    if color != "default":
        annotations["color"] = color
    if annotations:
        obj["annotations"] = annotations
    return obj


def para(*rich_texts):
    return {"type": "paragraph", "paragraph": {"rich_text": list(rich_texts)}}


children = [
    # --- ABOVE CHART ---
    para(
        rt(
            "Jeff Bezos has given away roughly 2% of his fortune \u2014 less, "
            "as a share of wealth, than Carnegie, Rockefeller, or Mellon "
            "managed more than a century ago.",
            bold=True,
        ),
        rt(
            " The chart below ranks the 17 living billionaires worth "
            "$50 billion or more alongside three Gilded Age industrialists "
            "by lifetime charitable giving as a share of peak wealth. "
            "Bubble size reflects net worth; horizontal lines show estimated "
            "ranges where sources disagree."
        ),
    ),
    # Chart placeholder
    para(rt("[Chart: fifty_b_continuous.html]", italic=True, color="gray")),
    # --- BELOW CHART ---
    # 1. What 2% means at this scale
    para(
        rt(
            "Two percent of $200 billion is $4 billion. That is roughly "
            "what Bezos has given away over his entire lifetime, according "
            "to Forbes. His wealth, invested at the S&P 500\u2019s long-run "
            "average, grows by more than $20 billion a year. His lifetime "
            "giving amounts to about two months of passive appreciation. "
            "He could fund the Washington Post\u2019s reported $100 million "
            "annual losses for the next century and spend less than 5% of "
            "his net worth."
        )
    ),
    # 2. Peers + Gilded Age in one paragraph
    para(
        rt(
            "Only three of the 17 modern billionaires in this cohort have "
            "given more than 5%: Warren Buffett (43%), Bill Gates (34%), "
            "and Michael Bloomberg (18%). The other 14 score a 1 or 2 on "
            "the Forbes philanthropy scale. Carnegie gave roughly 90% of "
            "his inflation-adjusted $310 billion fortune. Rockefeller gave "
            "35% of his $400 billion. Mellon gave 25%. None had a charitable "
            "tax deduction to incentivize them."
        )
    ),
    # 3. The divorce — flat, no moralizing
    para(
        rt(
            "When Bezos and MacKenzie Scott divorced in 2019, she received "
            "a quarter of their Amazon stake. Since then, Scott has donated "
            "$26 billion to roughly 2,000 nonprofits. Bezos has donated "
            "approximately $4 billion over his entire career. Scott\u2019s "
            "net worth has barely declined despite this pace, because Amazon "
            "stock appreciates faster than she can give it away."
        )
    ),
    # 4. Tax picture
    para(
        rt(
            "ProPublica found that Bezos paid zero federal income tax in "
            "2007 and 2011, and that his \u201ctrue tax rate\u201d on $99 "
            "billion in wealth growth was less than 1%. In late 2023, he "
            "moved from Washington to Florida shortly after Washington "
            "upheld a 7% capital gains tax, then sold $16.5 billion in "
            "Amazon stock \u2014 saving an estimated $1 billion in state "
            "taxes, more than his typical annual charitable giving. The "
            "Institute for Policy Studies estimates that for every dollar "
            "a billionaire donates, taxpayers forgo up to 74 cents in "
            "revenue."
        )
    ),
    # 5. Ending — the compounding math
    para(
        rt(
            "The Bezos Earth Fund, his largest philanthropic commitment, "
            "pledged $10 billion in 2020 to be spent down by 2030. At the "
            "halfway point, roughly $2.3 billion has been disbursed. At "
            "his current net worth, the full $10 billion pledge amounts "
            "to less than six months of estimated passive appreciation."
        )
    ),
]

body = {"children": children, "after": AFTER_BLOCK}

req = urllib.request.Request(
    f"https://api.notion.com/v1/blocks/{PAGE_ID}/children",
    data=json.dumps(body).encode("utf-8"),
    headers={
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    },
    method="PATCH",
)

try:
    response = urllib.request.urlopen(req)
    print(f"Success: {response.status}")
    result = json.loads(response.read().decode())
    print(f"Blocks created: {len(result.get('results', []))}")
except urllib.error.HTTPError as e:
    print(f"Error: {e.code}")
    print(e.read().decode())
