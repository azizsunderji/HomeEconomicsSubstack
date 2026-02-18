"""Publish the Bezos philanthropy article to Notion."""
import json
import urllib.request

NOTION_TOKEN = "ntn_VG145417769qVFknpVyS6nkTJFW8wXMjAIenddQwA5SgvA"
PAGE_ID = "303008aa-e629-818a-bc16-c9f4d1a5fdf7"
AFTER_BLOCK = "303008aa-e629-809c-854b-eba26b645d51"  # last editorial bullet


def rt(content, bold=False, italic=False, color="default"):
    """Build a rich_text element."""
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
            "Jeff Bezos has donated roughly 2% of his wealth to charity, "
            "less than Andrew Carnegie, John D. Rockefeller, or Andrew Mellon "
            "parted with more than a century ago.",
            bold=True,
        ),
        rt(
            " The recent evisceration of the Washington Post has invited fresh "
            "scrutiny of Bezos, but the numbers cast a less personal and more "
            "historical light. The chart below ranks the 17 living billionaires "
            "worth $50 billion or more alongside three Gilded Age industrialists "
            "by lifetime charitable giving as a share of peak wealth. Bubble size "
            "reflects net worth; horizontal lines show estimated ranges where "
            "sources disagree."
        ),
    ),
    # Chart placeholder
    para(rt("[Chart: fifty_b_continuous.html]", italic=True, color="gray")),
    # --- BELOW CHART ---
    # 1. WP + Blue Origin
    para(
        rt(
            "The Washington Post reportedly loses around $100 million a year. "
            "Bezos could fund those losses for the next hundred years and spend "
            "less than 5% of his net worth. In 2017, he told an interviewer he "
            "was selling $1 billion a year in Amazon stock to fund Blue Origin, "
            "his private space venture. His lifetime charitable giving, by "
            "contrast, totals $3.3 to $4.1 billion."
        )
    ),
    # 2. Peers
    para(
        rt(
            "Forbes gives Bezos a philanthropy score of 2 on a 5-point scale, "
            "meaning he has donated between 1% and 5% of his wealth. Warren "
            "Buffett scores 5, having given 43% ($62 billion); Bill Gates also "
            "scores 5 at 34% ($48 billion); Michael Bloomberg scores 4, at 18% "
            "($21 billion). Only these three, of the 17 modern billionaires "
            "worth $50 billion or more, score above a 2."
        )
    ),
    # 3. MacKenzie Scott
    para(
        rt(
            "The most pointed comparison is within Bezos\u2019s own family. "
            "MacKenzie Scott received a quarter of the Amazon fortune in their "
            "2019 divorce, signed the Giving Pledge the same year, and has since "
            "donated $26 billion to roughly 2,000 nonprofits with no strings "
            "attached. She gives more in a typical year than Bezos has donated "
            "in his lifetime. They built their wealth from the same company."
        )
    ),
    # 4. Gilded Age
    para(
        rt(
            "Carnegie gave away roughly 90% of his fortune, Rockefeller 35%, "
            "Mellon 25%. The modern $50 billion club is also overwhelmingly "
            "self-made (among billionaires broadly, more are now minted through "
            "inheritance than entrepreneurship, but not in this cohort). The "
            "Gilded Age tycoons faced no tax incentive to give, and their labor "
            "practices were at least as brutal: Carnegie crushed the Homestead "
            "Strike, Rockefeller presided over the Ludlow Massacre."
        )
    ),
    # 5. Broader pattern
    para(
        rt(
            "Bezos is a poster child, but stinginess is the norm among the "
            "ultra-wealthy. Three quarters of all scored billionaires in the "
            "Forbes database rate a 1 or 2, meaning they have given away less "
            "than 5%. The Giving Pledge, launched by Gates and Buffett in 2010, "
            "has not changed this: the original signatories who remain "
            "billionaires are 283% wealthier than when they signed, and only "
            "one living couple has fulfilled the commitment."
        )
    ),
    # 6a. Tax subsidy
    para(
        rt(
            "What giving does occur is heavily subsidized. For every dollar a "
            "billionaire donates, taxpayers contribute up to 74 cents in forgone "
            "revenue, according to the Institute for Policy Studies. In 2022, "
            "41% of individual charitable giving flowed to donor-advised funds "
            "and private foundations, vehicles with no legal obligation to ever "
            "distribute."
        )
    ),
    # 6b. Tax avoidance
    para(
        rt(
            "ProPublica found that Bezos paid zero federal income tax in 2007 "
            'and 2011, with a "true tax rate" of less than 1% on $99 billion '
            "in wealth growth. In late 2023, he moved from Washington state to "
            "Florida, shortly after Washington upheld a 7% capital gains tax. "
            "He then sold $16.5 billion in Amazon stock. The estimated tax "
            "savings: roughly $1 billion, more than his typical annual giving."
        )
    ),
    # 7. Singer ending
    para(
        rt(
            "Peter Singer, the Princeton utilitarian philosopher who helped "
            "launch the effective altruism movement, has argued that declining "
            "to save a drowning child to keep your clothes dry is morally "
            "equivalent to declining to give when the cost is trivial relative "
            "to your resources. Bezos could give away 99% of his fortune and "
            "retain $2 billion. He has given away 2%."
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
