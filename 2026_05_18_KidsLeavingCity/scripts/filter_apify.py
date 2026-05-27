"""
Filter the raw Apify Twitter results down to topically-relevant tweets.

The raw sweep contains many false positives because the query 'San Francisco
families exodus OR leaving' (etc.) caught sports/celebrity content too. We
keep only tweets that BOTH:
  - reference a city/urban/suburb context, AND
  - reference kids/families/fertility/schools/demographics

And drop tweets that look like sports/celebrity/unrelated.

Outputs a curated engagement-sorted markdown digest.
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
    r"\bborough", r"\bneighborhood", r"\bzon(ed|ing)\b",
    r"\bManhattan\b", r"\bBrooklyn\b", r"\bQueens\b", r"\bBronx\b",
    r"\bSan Francisco\b", r"\bSan Jose\b", r"\bOakland\b", r"\bBerkeley\b",
    r"\bSeattle\b", r"\bChicago\b", r"\bBoston\b", r"\bWashington\b", r"\bD\.?C\.?\b",
    r"\bAustin\b", r"\bDenver\b", r"\bPortland\b", r"\bMinneapolis\b",
    r"\bNew York\b", r"\bNYC\b", r"\bLA\b", r"\bLos Angeles\b",
    r"\bToronto\b", r"\bVancouver\b", r"\bLondon\b", r"\bMontreal\b", r"\bSydney\b",
    r"\bPhiladelphia\b", r"\bAtlanta\b", r"\bDallas\b", r"\bHouston\b",
]
URBAN_RX = re.compile("|".join(URBAN), re.IGNORECASE)

FAMILY = [
    r"\bkids?\b", r"\bchild(ren)?\b", r"\bfamil(y|ies)\b",
    r"\bparent", r"\bmoms?\b", r"\bdads?\b", r"\bbab(y|ies)\b",
    r"\bschool", r"\benrollment\b", r"\bdistrict\b",
    r"\bbirth ?rate", r"\bfertilit", r"\bdemograph",
    r"\bunder ?18\b", r"\bteens?\b", r"\btoddler", r"\bdaycare\b", r"\bstroller",
    r"\bchildless\b", r"\bdepopulation\b", r"\bhollow", r"\bexodus\b",
    r"\bunder-?18\b", r"\bunder-?5\b",
]
FAMILY_RX = re.compile("|".join(FAMILY), re.IGNORECASE)

# Hard exclusions — words/phrases that almost always indicate off-topic content
EXCLUDE = [
    r"\bChelsea\b", r"\bArsenal\b", r"\bLiverpool\b", r"\bNewcastle\b",
    r"\bSunderland\b", r"\bManchester\b", r"\bReal Madrid\b", r"\bBarcelona\b",
    r"\bMourinho\b", r"\bManager\b", r"\bgoalkeeper\b", r"\bstriker\b",
    r"\bManCity\b", r"\bChelsea FC\b", r"\bCFC\b",
    r"\bKanye\b", r"\bKardashian\b", r"\bBianca\b",
    r"\bMariupol\b", r"\bUkraine\b", r"\bPutin\b", r"\bRussia\b", r"\bDonbas\b",
    r"\bGaza\b", r"\bIDF\b", r"\bHamas\b", r"\bPalestin",
    r"\bShameless\b", r"\bFrank Gallagher\b",
    r"\bChipotle\b", r"\b9/11\b", r"\bSeptember 11\b",
    r"\bSyria\b", r"\bAfghanistan\b", r"\brefugee", r"\basylum",
    r"\bgangs?\b", r"\bgroomi", r"\bmurder\b", r"\bshooting\b", r"\barrest",
    r"\bclub\b.*\btransfer\b", r"\btransfer\b.*\bclub\b",
    r"\bMatch ?day\b", r"\bGoal\b.*\bminute\b",
    r"\bcelebrity\b", r"\bMet Gala\b", r"\bGrammy\b", r"\bOscar\b",
    r"\bnest\b.*\bbird\b", r"\bbird\b.*\bnest\b",
]
EXCLUDE_RX = re.compile("|".join(EXCLUDE), re.IGNORECASE)


def relevant(tweet) -> tuple[bool, str]:
    text = (tweet.get("fullText") or tweet.get("text") or "").strip()
    if not text:
        return False, "empty"
    if EXCLUDE_RX.search(text):
        return False, "excluded"
    has_urban = bool(URBAN_RX.search(text))
    has_family = bool(FAMILY_RX.search(text))
    if not (has_urban and has_family):
        return False, "no_match"
    return True, "kept"


def main():
    raw = json.load(open(DATA / "twitter_apify_raw.json"))
    print(f"Raw: {len(raw)} tweets")

    kept = []
    dropped = {"empty": 0, "excluded": 0, "no_match": 0}
    for tw in raw:
        ok, reason = relevant(tw)
        if ok:
            kept.append(tw)
        else:
            dropped[reason] = dropped.get(reason, 0) + 1
    print(f"Kept: {len(kept)}, Dropped: {dropped}")

    def eng(t):
        return (t.get("likeCount", 0) or 0) + (t.get("retweetCount", 0) or 0) + (t.get("replyCount", 0) or 0)
    kept.sort(key=eng, reverse=True)

    # Write filtered JSON
    out_json = DATA / "twitter_apify_filtered.json"
    with open(out_json, "w") as f:
        json.dump(kept, f, indent=2, default=str)
    print(f"Wrote {out_json}")

    # Markdown digest of top-N
    out_md = DATA / "twitter_apify_filtered.md"
    with open(out_md, "w") as f:
        f.write(f"# Twitter Apify Sweep — Filtered to Kids/Families × City\n\n")
        f.write(f"_{len(kept)} on-topic tweets from {len(raw)} raw. Sorted by engagement "
                f"(likes + retweets + replies). Collected {datetime.now().isoformat()} via "
                f"apidojo/twitter-scraper-lite._\n\n")
        f.write(f"Filter rule: tweet must mention BOTH a city/urban term AND a kids/families/fertility/school term, "
                f"and not match the exclusion list (sports, celebrity, war, etc.).\n\n---\n\n")
        for i, t in enumerate(kept, 1):
            author = t.get("author") or {}
            uname = author.get("userName") if isinstance(author, dict) else str(author)
            text = (t.get("fullText") or t.get("text") or "").strip().replace("\n", " ")
            url = t.get("twitterUrl") or t.get("url") or f"https://x.com/{uname}/status/{t.get('id','')}"
            likes = t.get("likeCount", 0) or 0
            rts = t.get("retweetCount", 0) or 0
            replies = t.get("replyCount", 0) or 0
            views = t.get("viewCount", 0) or 0
            created = t.get("createdAt", "")
            found = ", ".join(t.get("_found_in", []))
            f.write(f"### {i}. @{uname} — {likes:,} ♥ / {rts:,} ↻ / {replies:,} 💬 / {views:,} 👁\n")
            f.write(f"- **Date:** {created}\n")
            f.write(f"- **URL:** {url}\n")
            f.write(f"- **Found in:** {found}\n")
            f.write(f"- **Text:** {text[:600]}{'…' if len(text)>600 else ''}\n\n")

    print(f"Wrote {out_md}")

    # Quick stats by found-in bucket
    bucket = {}
    for t in kept:
        for b in t.get("_found_in", []):
            bucket[b] = bucket.get(b, 0) + 1
    print("\nKept by query group:")
    for b, n in sorted(bucket.items(), key=lambda x: -x[1]):
        print(f"  {b}: {n}")


if __name__ == "__main__":
    main()
