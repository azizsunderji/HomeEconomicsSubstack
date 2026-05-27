"""
NYT Article Search sweep for the 'kids/families leaving cities' narrative.

Article Search API:
  - Rate limit: 5 requests / minute, 500 / day
  - 10 results per page, max page=100 (so max 1000 results per query)
  - Docs: https://developer.nytimes.com/docs/articlesearch-product/1/overview

Strategy:
  - Run a curated set of queries, paginate up to N pages each
  - Dedupe by web_url
  - Save consolidated JSON + a readable markdown digest
"""
import json
import time
import os
from pathlib import Path
from urllib.parse import urlencode
import urllib.request
import urllib.error

API_KEY = "6uRj5uQIe6ATvVnvAKZUOceeovR4AmrPHN0qzRIM3z5JA4Xw"
ENDPOINT = "https://api.nytimes.com/svc/search/v2/articlesearch.json"

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
DATA.mkdir(exist_ok=True)

# Queries — each is a (label, q-string, optional fq) tuple.
# fq filters to news/opinion sections where the narrative shows up.
QUERIES = [
    ("families_leaving_cities", '"families leaving cities"', None),
    ("families_fleeing_cities", '"families fleeing"', None),
    ("urban_exodus_families", '"urban exodus" families', None),
    ("childless_cities", '"childless" cities', None),
    ("kids_disappearing_cities", '"fewer children" cities', None),
    ("school_enrollment_decline_city", '"school enrollment" decline city', None),
    ("housing_costs_families_leave", 'housing costs families leaving city', None),
    ("stroller_index", '"stroller"', None),  # very narrow; check signal
    ("manhattan_families_leave", 'Manhattan families leaving housing', None),
    ("san_francisco_kids_leaving", 'San Francisco children families leaving', None),
    ("brooklyn_families_leave", 'Brooklyn families leaving children', None),
    ("city_suburb_families", 'families moving suburbs city', None),
    ("housing_crisis_children", '"housing crisis" children city', None),
    ("nyc_school_enrollment", 'New York City school enrollment decline', None),
    ("sf_school_enrollment", 'San Francisco school enrollment decline', None),
    ("priced_out_families", '"priced out" families city', None),
    ("birth_rate_cities", 'birth rate cities decline', None),
    ("family_unfriendly_cities", '"family unfriendly" cities', None),
    ("dual_career_families_cities", 'dual income families leaving cities', None),
]

MAX_PAGES_PER_QUERY = 5   # 50 results per query max
SLEEP_BETWEEN_REQ = 13.0  # 5 req/min cap → 12s; pad to 13s


def fetch_page(q, page, fq=None):
    params = {"q": q, "page": page, "sort": "relevance", "api-key": API_KEY}
    if fq:
        params["fq"] = fq
    url = f"{ENDPOINT}?{urlencode(params)}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def run_query(label, q, fq):
    print(f"\n=== {label}: {q!r} ===")
    docs = []
    for page in range(MAX_PAGES_PER_QUERY):
        try:
            data = fetch_page(q, page, fq)
        except urllib.error.HTTPError as e:
            print(f"  HTTPError page={page}: {e}")
            if e.code == 429:
                print("  rate-limited, sleeping 60s and retrying")
                time.sleep(60)
                try:
                    data = fetch_page(q, page, fq)
                except Exception as e2:
                    print(f"  retry failed: {e2}")
                    break
            else:
                break
        except Exception as e:
            print(f"  error page={page}: {e}")
            break

        hits = (data.get("response") or {}).get("docs") or []
        meta = (data.get("response") or {}).get("meta") or {}
        total = meta.get("hits", 0)
        print(f"  page={page}: {len(hits)} hits (total available: {total})")
        for h in hits:
            docs.append({
                "query_label": label,
                "headline": h.get("headline", {}).get("main"),
                "snippet": h.get("snippet") or h.get("abstract"),
                "lead_paragraph": h.get("lead_paragraph"),
                "web_url": h.get("web_url"),
                "pub_date": h.get("pub_date"),
                "section_name": h.get("section_name"),
                "byline": (h.get("byline") or {}).get("original"),
                "word_count": h.get("word_count"),
                "keywords": [k.get("value") for k in h.get("keywords", []) if k.get("value")],
                "type_of_material": h.get("type_of_material"),
            })
        if len(hits) < 10:
            break
        time.sleep(SLEEP_BETWEEN_REQ)
    return docs


def main():
    all_docs = []
    for label, q, fq in QUERIES:
        docs = run_query(label, q, fq)
        all_docs.extend(docs)
        time.sleep(SLEEP_BETWEEN_REQ)

    # Dedupe by web_url, keep first query_label
    seen = {}
    for d in all_docs:
        url = d.get("web_url")
        if not url:
            continue
        if url not in seen:
            seen[url] = d
            seen[url]["found_by"] = [d["query_label"]]
        else:
            if d["query_label"] not in seen[url]["found_by"]:
                seen[url]["found_by"].append(d["query_label"])
    unique = list(seen.values())
    unique.sort(key=lambda x: (x.get("pub_date") or ""), reverse=True)

    out_json = DATA / "nyt_articles_raw.json"
    with open(out_json, "w") as f:
        json.dump(unique, f, indent=2)
    print(f"\nWrote {len(unique)} unique articles → {out_json}")

    # Markdown digest
    out_md = DATA / "nyt_sweep.md"
    with open(out_md, "w") as f:
        f.write("# NYT Article Search Sweep — Kids/Families Leaving Cities\n\n")
        f.write(f"_{len(unique)} unique articles across {len(QUERIES)} queries. "
                f"Sorted by pub_date (newest first)._\n\n")
        for d in unique:
            f.write(f"### {d.get('headline') or '(no headline)'}\n")
            f.write(f"- **Date:** {d.get('pub_date','')}  \n")
            f.write(f"- **Section:** {d.get('section_name','')}  \n")
            f.write(f"- **Byline:** {d.get('byline','')}  \n")
            f.write(f"- **Type:** {d.get('type_of_material','')}  \n")
            f.write(f"- **URL:** {d.get('web_url','')}  \n")
            f.write(f"- **Word count:** {d.get('word_count','')}  \n")
            f.write(f"- **Found by:** {', '.join(d.get('found_by', []))}  \n")
            snip = (d.get("snippet") or "").strip()
            if snip:
                f.write(f"- **Snippet:** {snip}\n")
            lp = (d.get("lead_paragraph") or "").strip()
            if lp and lp != snip:
                f.write(f"- **Lead:** {lp}\n")
            kws = d.get("keywords") or []
            if kws:
                f.write(f"- **Keywords:** {'; '.join(kws[:12])}\n")
            f.write("\n")
    print(f"Wrote digest → {out_md}")

    # Summary stats
    by_section = {}
    for d in unique:
        by_section[d.get("section_name") or "(none)"] = by_section.get(d.get("section_name") or "(none)", 0) + 1
    print("\nTop sections:")
    for s, n in sorted(by_section.items(), key=lambda x: -x[1])[:10]:
        print(f"  {s}: {n}")

    by_year = {}
    for d in unique:
        y = (d.get("pub_date") or "")[:4]
        if y:
            by_year[y] = by_year.get(y, 0) + 1
    print("\nBy year (top 10):")
    for y, n in sorted(by_year.items(), key=lambda x: -x[1])[:10]:
        print(f"  {y}: {n}")


if __name__ == "__main__":
    main()
