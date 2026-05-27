"""
Filter the raw NYT Article Search results down to topically-relevant articles.

Rule: an article is kept if its headline + lead_paragraph + snippet contains
BOTH a city/urban term AND a family/kids/schools/fertility term — AND it
isn't one of the obvious off-topic sections (Style/Arts/Books-fiction).

Also produce a ranking signal:
  match_score = (# of queries that returned it) × engagement-ish proxy
We don't have engagement metrics from NYT, but articles surfaced by many
queries are strong topical matches.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from datetime import datetime

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"

URBAN = [
    r"\bcity\b", r"\bcities\b", r"\burban\b", r"\bdowntown\b",
    r"\bsuburb", r"\bcentral cit", r"\bmetropolitan\b", r"\bmetro\b",
    r"\bborough", r"\bneighborhood",
    r"\bManhattan\b", r"\bBrooklyn\b", r"\bQueens\b", r"\bBronx\b",
    r"\bSan Francisco\b", r"\bSF\b", r"\bSan Jose\b", r"\bOakland\b",
    r"\bSeattle\b", r"\bChicago\b", r"\bBoston\b", r"\bWashington\b",
    r"\bAustin\b", r"\bDenver\b", r"\bPortland\b",
    r"\bNew York\b", r"\bNYC\b", r"\bLos Angeles\b",
    r"\bToronto\b", r"\bLondon\b", r"\bSydney\b",
    r"\bPhiladelphia\b", r"\bAtlanta\b",
]
URBAN_RX = re.compile("|".join(URBAN), re.IGNORECASE)

FAMILY = [
    r"\bkids?\b", r"\bchild(ren)?\b", r"\bfamil(y|ies)\b",
    r"\bparent", r"\bbab(y|ies)\b",
    r"\bschool", r"\benrollment\b",
    r"\bbirth ?rate", r"\bfertilit", r"\bdemograph",
    r"\bunder ?18\b", r"\bteens?\b", r"\btoddler", r"\bdaycare\b", r"\bstroller",
    r"\bchildless\b", r"\bdepopulation\b", r"\bhollow",
    r"\bpre-?k\b", r"\bkindergarten\b", r"\belementary\b",
]
FAMILY_RX = re.compile("|".join(FAMILY), re.IGNORECASE)

# Section blocklist — almost never on-topic for our research question
SECTION_BLOCK = {"Sports", "Style", "Arts", "Travel", "Food", "Movies", "Theater"}


def text_blob(a):
    parts = [
        a.get("headline") or "",
        a.get("snippet") or "",
        a.get("lead_paragraph") or "",
        " ".join(a.get("keywords") or []),
    ]
    return "\n".join(parts)


def relevant(a) -> tuple[bool, str]:
    if a.get("section_name") in SECTION_BLOCK:
        return False, f"section_block:{a.get('section_name')}"
    blob = text_blob(a)
    if not blob.strip():
        return False, "empty"
    has_urban = bool(URBAN_RX.search(blob))
    has_family = bool(FAMILY_RX.search(blob))
    if not (has_urban and has_family):
        return False, "no_match"
    return True, "kept"


def main():
    raw = json.load(open(DATA / "nyt_articles_raw.json"))
    print(f"Raw: {len(raw)} articles")
    kept = []
    drops = {}
    for a in raw:
        ok, r = relevant(a)
        if ok:
            kept.append(a)
        else:
            drops[r] = drops.get(r, 0) + 1
    print(f"Kept: {len(kept)}")
    print(f"Dropped: {sum(drops.values())}")
    for k, v in sorted(drops.items(), key=lambda x: -x[1])[:10]:
        print(f"  {k}: {v}")

    # Score: # of distinct queries that found it (signal of topical density)
    def score(a):
        return len(a.get("found_by", []))

    kept.sort(key=lambda x: (-score(x), x.get("pub_date") or ""), reverse=False)
    # Note: negative score for descending, then pub_date ascending → flip
    kept.sort(key=lambda x: (score(x), x.get("pub_date") or ""), reverse=True)

    with open(DATA / "nyt_articles_filtered.json", "w") as f:
        json.dump(kept, f, indent=2, default=str)

    md = DATA / "nyt_sweep_filtered.md"
    with open(md, "w") as f:
        f.write(f"# NYT Article Search — Filtered to Kids/Families × City\n\n")
        f.write(f"_{len(kept)} on-topic articles from {len(raw)} raw. Sorted by # of distinct queries that returned it (descending), then date._\n\n")
        f.write(f"Filter rule: headline/snippet/lead/keywords must mention BOTH a city/urban term AND a kids/families/schools/fertility term. Sections Sports/Style/Arts/Travel/Food/Movies/Theater dropped.\n\n---\n\n")
        for i, a in enumerate(kept, 1):
            f.write(f"### {i}. {a.get('headline') or '(no headline)'}\n")
            f.write(f"- **Date:** {a.get('pub_date','')}\n")
            f.write(f"- **Section:** {a.get('section_name','')}\n")
            f.write(f"- **Byline:** {a.get('byline','')}\n")
            f.write(f"- **Type:** {a.get('type_of_material','')}\n")
            f.write(f"- **URL:** {a.get('web_url','')}\n")
            f.write(f"- **Match score (# queries):** {score(a)}\n")
            f.write(f"- **Found by:** {', '.join(a.get('found_by', []))}\n")
            snip = (a.get('snippet') or "").strip()
            lp = (a.get('lead_paragraph') or "").strip()
            if snip:
                f.write(f"- **Snippet:** {snip}\n")
            if lp and lp != snip:
                f.write(f"- **Lead:** {lp[:400]}{'…' if len(lp)>400 else ''}\n")
            kws = a.get("keywords") or []
            if kws:
                f.write(f"- **Keywords:** {'; '.join(kws[:10])}\n")
            f.write("\n")
    print(f"Wrote → {md}")

    # Section breakdown of kept
    by_section = {}
    for a in kept:
        by_section[a.get('section_name','(none)')] = by_section.get(a.get('section_name','(none)'), 0) + 1
    print("\nKept by section:")
    for s, n in sorted(by_section.items(), key=lambda x: -x[1])[:15]:
        print(f"  {s}: {n}")

    by_year = {}
    for a in kept:
        y = (a.get("pub_date") or "")[:4]
        if y:
            by_year[y] = by_year.get(y, 0) + 1
    print("\nKept by year:")
    for y, n in sorted(by_year.items()):
        print(f"  {y}: {n}")


if __name__ == "__main__":
    main()
