"""
Merge the WebSearch (credibility-curated) and Apify (engagement-ranked) Twitter
sweeps into a single ranked top-30 list.

Logic:
  1. Extract URLs + authors + agent annotation from twitter_sweep_raw.md.
     These are "curated" — the WebSearch agent already filtered for credibility/
     authoritative voices.
  2. Read the Apify filtered set (twitter_apify_filtered.json) which has full
     engagement metrics.
  3. Dedupe by tweet status_id (URL last numeric segment), since URLs vary
     between x.com/twitter.com.
  4. Score each tweet:
        engagement = log10((likes + retweets + replies + views/100) + 1)
        credibility_bonus = 3.0 if author was surfaced by the WebSearch agent
        bonus_in_both = 1.5 if found in BOTH sources (strong topical signal)
        score = engagement + credibility_bonus + bonus_in_both
     For WebSearch-only tweets (no engagement data), use a synthetic engagement
     of 1.0 so credibility carries them.
  5. Output top-30 markdown with: rank, author, engagement, source flag, why
     it ranked here, the tweet text, and URL.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from datetime import datetime

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"

WEBSEARCH_MD = DATA / "twitter_sweep_raw.md"
APIFY_JSON = DATA / "twitter_apify_filtered.json"
APIFY_RAW_JSON = DATA / "twitter_apify_raw.json"   # fall back for items the filter dropped but were curated
OUT_MD = DATA / "twitter_top30.md"
OUT_JSON = DATA / "twitter_top30.json"


STATUS_ID_RX = re.compile(r"status/(\d+)")
WEBSEARCH_ENTRY_RX = re.compile(
    r"^\s*\d+\.\s+\*\*([^*]+?)\*\*\s+—\s+(https?://\S+?)\s+—\s+@?(\S+?)\s+—\s+(.+?)(?=\n\d+\.|\n###|\Z)",
    re.DOTALL | re.MULTILINE,
)


def extract_status_id(url: str) -> str | None:
    m = STATUS_ID_RX.search(url)
    return m.group(1) if m else None


def parse_websearch(md_path: Path) -> list[dict]:
    """Parse the agent's markdown report. Each entry block starts with a numbered list item."""
    text = md_path.read_text()
    entries = []
    # Each numbered entry looks like:
    # 1. **Author Name** — https://x.com/handle/status/123 — @handle — "snippet" — **Single tweet.** **Stance: ...**
    # Use regex per line that begins with `^\d+\. \*\*`
    blocks = re.split(r"\n(?=\d+\.\s+\*\*)", text)
    for b in blocks:
        m = re.match(r"\s*(\d+)\.\s+\*\*([^*]+)\*\*\s*—\s*(https?://\S+?)\s*—\s*@?(\S+?)\s*—\s*(.+)", b, re.DOTALL)
        if not m:
            continue
        rank_in_agent, author_name, url, handle, body = m.groups()
        # Clean body (strip trailing newlines, normalize spaces)
        body = re.sub(r"\s+", " ", body).strip()
        # Strip trailing markdown after the first '—' chains: keep up to ~600 chars
        sid = extract_status_id(url)
        entries.append({
            "agent_rank": int(rank_in_agent),
            "author_name": author_name.strip(),
            "handle": handle.strip().rstrip(",.;:"),
            "url": url.rstrip(".,;)\"'"),
            "status_id": sid,
            "annotation": body[:800],
        })
    return entries


def normalize_handle(h: str) -> str:
    return (h or "").lower().lstrip("@")


def main():
    websearch = parse_websearch(WEBSEARCH_MD)
    print(f"Parsed {len(websearch)} entries from WebSearch sweep")

    # Apify filtered = the on-topic set; also load full raw for any websearch
    # tweet that was filtered out (we still want to keep its engagement metrics
    # if we have them).
    apify_filtered = json.load(open(APIFY_JSON))
    apify_raw = json.load(open(APIFY_RAW_JSON))

    # Build lookup by status_id (Apify)
    apify_by_sid = {}
    for t in apify_raw:
        sid = t.get("id") or t.get("tweet_id")
        if sid:
            apify_by_sid[str(sid)] = t
    print(f"Apify lookup built: {len(apify_by_sid)} tweets")

    apify_in_filtered_sids = set()
    for t in apify_filtered:
        sid = t.get("id") or t.get("tweet_id")
        if sid:
            apify_in_filtered_sids.add(str(sid))

    # "Curated authors" = authors that appear in the WebSearch report.
    # These get the credibility bonus.
    curated_authors = {normalize_handle(e["handle"]) for e in websearch}
    print(f"Curated authors: {len(curated_authors)}")

    # Build combined records, keyed by status_id (fallback to url)
    records: dict[str, dict] = {}

    def rec_key(sid, url):
        return sid or url

    # Seed with WebSearch entries
    for e in websearch:
        sid = e["status_id"]
        key = rec_key(sid, e["url"])
        # If the same tweet is in Apify, attach engagement metrics
        ap = apify_by_sid.get(sid) if sid else None
        likes = (ap or {}).get("likeCount", 0) or 0
        rts = (ap or {}).get("retweetCount", 0) or 0
        reps = (ap or {}).get("replyCount", 0) or 0
        views = (ap or {}).get("viewCount", 0) or 0
        quotes = (ap or {}).get("quoteCount", 0) or 0
        text = ""
        if ap:
            text = (ap.get("fullText") or ap.get("text") or "").strip()
        created = (ap or {}).get("createdAt", "")
        records[key] = {
            "status_id": sid,
            "url": e["url"],
            "handle": e["handle"],
            "author_name": e["author_name"],
            "in_websearch": True,
            "agent_rank": e["agent_rank"],
            "in_apify_filtered": sid in apify_in_filtered_sids,
            "in_apify_raw": sid in apify_by_sid,
            "websearch_annotation": e["annotation"],
            "text": text,
            "likes": likes, "retweets": rts, "replies": reps, "quotes": quotes, "views": views,
            "created_at": created,
        }

    # Add Apify-filtered (engagement-on-topic) tweets that we haven't already captured
    for t in apify_filtered:
        sid = str(t.get("id") or t.get("tweet_id") or "")
        if not sid:
            continue
        if sid in records or any(r.get("status_id") == sid for r in records.values()):
            continue
        author = t.get("author") or {}
        handle = author.get("userName") if isinstance(author, dict) else str(author)
        records[sid] = {
            "status_id": sid,
            "url": t.get("twitterUrl") or t.get("url") or f"https://x.com/{handle}/status/{sid}",
            "handle": handle,
            "author_name": (author.get("name") if isinstance(author, dict) else "") or handle,
            "in_websearch": False,
            "in_apify_filtered": True,
            "in_apify_raw": True,
            "websearch_annotation": "",
            "text": (t.get("fullText") or t.get("text") or "").strip(),
            "likes": t.get("likeCount", 0) or 0,
            "retweets": t.get("retweetCount", 0) or 0,
            "replies": t.get("replyCount", 0) or 0,
            "quotes": t.get("quoteCount", 0) or 0,
            "views": t.get("viewCount", 0) or 0,
            "created_at": t.get("createdAt", ""),
        }

    # Score
    for r in records.values():
        eng_raw = r["likes"] + r["retweets"] + r["replies"] + r["views"] / 100
        engagement = math.log10(max(eng_raw, 1.0) + 1)  # ~0 to ~5
        credibility = 2.5 if normalize_handle(r["handle"]) in curated_authors else 0.0
        both_bonus = 1.5 if r["in_websearch"] and r["in_apify_filtered"] else 0.0
        # WebSearch-only without engagement data — give a floor so credible voices
        # not surfaced by Apify still make the top list
        websearch_only_floor = 2.5 if (r["in_websearch"] and not r["in_apify_raw"]) else 0.0
        r["score"] = engagement + credibility + both_bonus + websearch_only_floor
        r["engagement_component"] = round(engagement, 2)
        r["credibility_component"] = credibility
        r["both_bonus"] = both_bonus
        r["websearch_only_floor"] = websearch_only_floor

    # Sort by score desc, then by agent_rank asc (lower agent_rank = curator
    # judged more important), then by engagement desc as final tiebreaker.
    ranked = sorted(
        records.values(),
        key=lambda x: (
            -x["score"],
            x.get("agent_rank", 999),
            -(x["likes"] + x["retweets"] + x["replies"]),
        ),
    )

    # Per-author cap so the top-30 represents the breadth of voices, not just
    # the two most-frequently-tweeting credible accounts.
    MAX_PER_AUTHOR = 2
    seen_author_count: dict[str, int] = {}
    top30 = []
    for r in ranked:
        h = normalize_handle(r["handle"])
        if seen_author_count.get(h, 0) >= MAX_PER_AUTHOR:
            continue
        top30.append(r)
        seen_author_count[h] = seen_author_count.get(h, 0) + 1
        if len(top30) >= 30:
            break

    # Save JSON
    with open(OUT_JSON, "w") as f:
        json.dump(top30, f, indent=2, default=str)

    # Markdown digest
    with open(OUT_MD, "w") as f:
        f.write(f"# Top 30 Tweets — Kids/Families Leaving Cities\n\n")
        f.write(f"_Merged from the WebSearch (credibility-curated) and Apify (engagement) sweeps. "
                f"Generated {datetime.now().isoformat(timespec='seconds')}._\n\n")
        f.write("**Scoring** = `log10(likes + retweets + replies + views/100 + 1)` "
                "+ `3.0` if author was surfaced by the WebSearch curator "
                "+ `1.5` bonus if the tweet appears in *both* sweeps "
                "+ `1.0` floor for credible WebSearch-only entries.\n\n")
        f.write("| Rank | Author | Engagement | Sources | Score |\n")
        f.write("|------|--------|------------|---------|-------|\n")
        for i, r in enumerate(top30, 1):
            eng_str = f"{r['likes']:,}♥ / {r['retweets']:,}↻ / {r['replies']:,}💬 / {r['views']:,}👁" if r["in_apify_raw"] else "—"
            sources = []
            if r["in_websearch"]: sources.append("WebSearch")
            if r["in_apify_filtered"]: sources.append("Apify")
            if r["in_websearch"] and r["in_apify_raw"] and not r["in_apify_filtered"]:
                sources.append("Apify-raw")
            handle = r["handle"]
            f.write(f"| {i} | @{handle} | {eng_str} | {' + '.join(sources)} | {r['score']:.2f} |\n")
        f.write("\n---\n\n")

        for i, r in enumerate(top30, 1):
            f.write(f"## {i}. @{r['handle']} — score {r['score']:.2f}\n")
            f.write(f"- **Engagement:** {r['likes']:,} likes / {r['retweets']:,} RT / {r['replies']:,} replies / {r['views']:,} views\n")
            f.write(f"- **Date:** {r['created_at']}\n")
            f.write(f"- **URL:** {r['url']}\n")
            sources = []
            if r["in_websearch"]: sources.append("WebSearch")
            if r["in_apify_filtered"]: sources.append("Apify-filtered")
            elif r["in_apify_raw"]: sources.append("Apify-raw")
            f.write(f"- **Found in:** {', '.join(sources)}\n")
            f.write(f"- **Score breakdown:** engagement={r['engagement_component']}, "
                    f"credibility={r['credibility_component']}, both-bonus={r['both_bonus']}, "
                    f"websearch-floor={r['websearch_only_floor']}\n")
            if r["text"]:
                text = r["text"].replace("\n", " ")
                f.write(f"- **Text:** {text[:700]}{'…' if len(text) > 700 else ''}\n")
            if r["websearch_annotation"]:
                f.write(f"- **Agent annotation:** {r['websearch_annotation'][:500]}\n")
            f.write("\n")

    print(f"\nWrote → {OUT_MD}")
    print(f"Wrote → {OUT_JSON}")
    print(f"\nTotal merged tweets: {len(records)}")
    print(f"In WebSearch only: {sum(1 for r in records.values() if r['in_websearch'] and not r['in_apify_raw'])}")
    print(f"In Apify only:     {sum(1 for r in records.values() if not r['in_websearch'])}")
    print(f"In both:           {sum(1 for r in records.values() if r['in_websearch'] and r['in_apify_raw'])}")


if __name__ == "__main__":
    main()
