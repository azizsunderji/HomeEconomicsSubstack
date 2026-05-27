"""
Apify Twitter scraper for the 'kids/families leaving cities' narrative.

Uses apidojo/twitter-scraper-lite (same actor as ~/Dropbox/Home Economics/Explorations/pulse).
Reads APIFY_API_KEY from env. Filter='Top' = engagement-sorted.

Query strategy:
  - Each search term uses Twitter advanced-search operators (min_faves: forces engagement)
  - Three thematic groups: pro-narrative anchors, YIMBY framing, density/pronatalist framing,
    school-enrollment angle, suburb/move angle.
  - Each run gets a small batch of related queries with maxItems split across them.

Cost: each Apify actor run has ~$0.16 fixed overhead. ~10 runs = ~$1.60.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path

import httpx

API_KEY = os.environ.get("APIFY_API_KEY", "")
assert API_KEY, "APIFY_API_KEY env var not set"

APIFY_BASE = "https://api.apify.com/v2"
ACTOR_ID = "apidojo~twitter-scraper-lite"

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
DATA.mkdir(exist_ok=True)

# Each entry is a (label, [search-terms], max_items_per_run) tuple.
# Using min_faves: to force engagement. Top-filter further re-sorts by engagement.
RUNS = [
    ("narrative_anchors", [
        '"families leaving cities" min_faves:25',
        '"families fleeing" cities min_faves:25',
        '"urban exodus" families min_faves:25',
        '"childless city" min_faves:25',
        '"childless cities" min_faves:25',
        '"future of the city is childless" min_faves:5',
    ], 200),

    ("kids_leaving_phrases", [
        '"kids are leaving" city min_faves:25',
        '"no kids" Manhattan OR "San Francisco" OR Brooklyn min_faves:25',
        '"families with kids" leaving city min_faves:25',
        '"hollowing out" cities children OR families min_faves:25',
        '"fewer children" cities min_faves:25',
    ], 200),

    ("yimby_supply", [
        '"family-sized" housing cities min_faves:25',
        '"missing middle" housing families min_faves:25',
        'YIMBY families cities housing min_faves:50',
        '"three bedroom" apartments cities min_faves:25',
        'Yglesias families cities housing min_faves:25',
    ], 200),

    ("density_pronatalist", [
        '"high-rise" fertility min_faves:25',
        'density fertility cities min_faves:25',
        '"birth rate" cities decline min_faves:50',
        '"apartments" fertility OR babies min_faves:25',
        'sprawl families cities OR fertility min_faves:25',
    ], 200),

    ("school_enrollment", [
        '"school enrollment" decline city min_faves:25',
        'SFUSD enrollment decline min_faves:25',
        '"NYC schools" enrollment decline min_faves:25',
        'Seattle schools enrollment families min_faves:25',
        'Chicago schools closing enrollment min_faves:25',
        'DC schools enrollment families min_faves:25',
    ], 200),

    ("suburb_moves", [
        '"moving to the suburbs" families min_faves:25',
        '"leaving the city" suburbs kids min_faves:25',
        '"central city" families suburbs min_faves:25',
        'remote work families suburbs min_faves:50',
    ], 200),

    ("specific_cities", [
        'San Francisco families exodus OR leaving min_faves:50',
        'Manhattan families exodus OR leaving kids min_faves:50',
        'New York City families leaving min_faves:50',
        'Brooklyn families leaving kids min_faves:50',
        'Seattle families leaving children min_faves:25',
    ], 200),

    ("commentators", [
        'from:mattyglesias families cities OR kids OR housing min_faves:25',
        'from:dkthomp childless OR families OR cities min_faves:25',
        'from:jerusalemd cities OR families OR housing min_faves:25',
        'from:lymanstoneky cities OR fertility OR housing min_faves:25',
        'from:cremieuxrecueil cities OR fertility OR housing min_faves:25',
        'from:noahpinion cities OR families OR housing min_faves:25',
        'from:ezraklein cities OR families OR housing min_faves:25',
        'from:morebirths cities OR housing min_faves:25',
    ], 250),

    ("data_charts", [
        '"American Community Survey" children cities min_faves:25',
        '"census" families cities decline min_faves:25',
        '"stroller index" min_faves:5',
        '"under 18" cities decline min_faves:25',
    ], 150),
]


def run_actor(search_terms: list[str], max_items: int = 200, retries: int = 1) -> tuple[list[dict], float]:
    """Run the Apify actor with a batch of search terms. Returns (results, cost_usd)."""
    url = f"{APIFY_BASE}/acts/{ACTOR_ID}/runs?waitForFinish=300"
    payload = {
        "searchTerms": search_terms,
        "maxItems": max_items,
        "filter": "Top",
    }
    headers = {"Authorization": f"Bearer {API_KEY}"}

    for attempt in range(retries + 1):
        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=330)
            resp.raise_for_status()
            run_data = resp.json().get("data", {})
            run_id = run_data.get("id")
            status = run_data.get("status")
            if status != "SUCCEEDED":
                for _ in range(60):
                    sr = httpx.get(f"{APIFY_BASE}/actor-runs/{run_id}", headers=headers, timeout=15)
                    status = sr.json().get("data", {}).get("status")
                    if status == "SUCCEEDED":
                        run_data = sr.json().get("data", {})
                        break
                    elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
                        print(f"  run ended {status}")
                        return [], 0.0
                    time.sleep(5)

            cost = run_data.get("usageTotalUsd", 0) or 0
            dataset_id = run_data.get("defaultDatasetId")
            if not dataset_id:
                return [], cost

            rr = httpx.get(
                f"{APIFY_BASE}/datasets/{dataset_id}/items",
                headers=headers, timeout=60,
            )
            rr.raise_for_status()
            items = rr.json()
            items = [r for r in items if not r.get("noResults")]
            return items, cost
        except Exception as e:
            print(f"  attempt {attempt} error: {e}")
            if attempt < retries:
                time.sleep(10)
            else:
                return [], 0.0
    return [], 0.0


def main():
    all_tweets = {}
    by_run = {}
    total_cost = 0.0
    log = []

    for label, terms, max_items in RUNS:
        print(f"\n=== {label} ({len(terms)} terms, maxItems={max_items}) ===")
        for t in terms:
            print(f"  • {t}")
        t0 = time.time()
        tweets, cost = run_actor(terms, max_items=max_items)
        elapsed = time.time() - t0
        total_cost += cost
        print(f"  → {len(tweets)} tweets, ${cost:.3f}, {elapsed:.0f}s")

        seen_new = 0
        for tw in tweets:
            tid = tw.get("id") or tw.get("tweet_id")
            if not tid:
                continue
            if tid not in all_tweets:
                tw["_found_in"] = [label]
                all_tweets[tid] = tw
                seen_new += 1
            else:
                if label not in all_tweets[tid]["_found_in"]:
                    all_tweets[tid]["_found_in"].append(label)
        by_run[label] = {"raw_count": len(tweets), "new": seen_new, "cost_usd": cost, "queries": terms}
        log.append({"label": label, "raw": len(tweets), "new": seen_new, "cost_usd": cost, "elapsed_s": elapsed})

    # Save raw
    raw_path = DATA / "twitter_apify_raw.json"
    with open(raw_path, "w") as f:
        json.dump(list(all_tweets.values()), f, indent=2, default=str)
    print(f"\nWrote {len(all_tweets)} unique tweets → {raw_path}")
    print(f"Total Apify cost: ${total_cost:.2f}")

    # Save run summary
    with open(DATA / "twitter_apify_runlog.json", "w") as f:
        json.dump({"total_cost_usd": total_cost, "runs": log, "by_run": by_run}, f, indent=2)

    # Build a markdown digest sorted by engagement
    items = list(all_tweets.values())
    def eng(t):
        return (t.get("likeCount", 0) or 0) + (t.get("retweetCount", 0) or 0) + (t.get("replyCount", 0) or 0)
    items.sort(key=eng, reverse=True)

    md_path = DATA / "twitter_apify_top.md"
    with open(md_path, "w") as f:
        f.write(f"# Twitter Apify Sweep — Kids/Families Leaving Cities\n\n")
        f.write(f"_{len(items)} unique tweets, sorted by total engagement (likes + retweets + replies). "
                f"Collected {datetime.now().isoformat()} via apidojo/twitter-scraper-lite._\n\n")
        for i, t in enumerate(items, 1):
            author = (t.get("author") or {})
            uname = author.get("userName") if isinstance(author, dict) else str(author)
            text = (t.get("fullText") or t.get("text") or "").strip().replace("\n", " ")
            url = t.get("twitterUrl") or t.get("url") or f"https://x.com/{uname}/status/{t.get('id','')}"
            likes = t.get("likeCount", 0) or 0
            rts = t.get("retweetCount", 0) or 0
            replies = t.get("replyCount", 0) or 0
            quotes = t.get("quoteCount", 0) or 0
            views = t.get("viewCount", 0) or 0
            created = t.get("createdAt", "")
            found = ", ".join(t.get("_found_in", []))
            f.write(f"### {i}. @{uname} — {likes:,} ♥ / {rts:,} ↻ / {replies:,} 💬 / {views:,} 👁\n")
            f.write(f"- **Date:** {created}\n")
            f.write(f"- **URL:** {url}\n")
            f.write(f"- **Found in:** {found}\n")
            f.write(f"- **Text:** {text[:600]}{'…' if len(text)>600 else ''}\n\n")

    print(f"Wrote digest → {md_path}")


if __name__ == "__main__":
    main()
