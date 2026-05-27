"""Build full place FIPS table for central cities of all 172 1950 SMAs.

Inputs:
  data/sma_1950_ranked.csv  (172 rows, columns sma_code, sma_name, central_cities, under18)
  data/central_city_place_fips.csv  (already-mapped top 60 cities)

Output:
  data/central_city_place_fips_all172.csv

Approach:
  1) Keep all rows already present in central_city_place_fips.csv.
  2) For each remaining SMA, parse pipe-separated central cities.
  3) Infer state(s) from the sma_name (e.g., "Wichita, KS SMA" -> KS, or "Springfield-Holyoke, MA-CT SMA" -> [MA,CT]).
  4) Query Census API for all places in each candidate state, then fuzzy-match the city name.
  5) For each match, also resolve the COUNTY FIPS (county subdivision containing the place).
"""

import csv
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = ROOT / "data"
API_KEY = "06048dc3bd32068702b5ef9b49875ec0c5ca56ce"

STATE_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08",
    "CT": "09", "DE": "10", "DC": "11", "FL": "12", "GA": "13", "HI": "15",
    "ID": "16", "IL": "17", "IN": "18", "IA": "19", "KS": "20", "KY": "21",
    "LA": "22", "ME": "23", "MD": "24", "MA": "25", "MI": "26", "MN": "27",
    "MS": "28", "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33",
    "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
    "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46",
    "TN": "47", "TX": "48", "UT": "49", "VT": "50", "VA": "51", "WA": "53",
    "WV": "54", "WI": "55", "WY": "56", "PR": "72",
}


# ---------- helpers ----------

def parse_states_from_sma_name(sma_name: str) -> list:
    """Extract list of state abbreviations from an SMA name.

    Examples:
      "Wichita, KS SMA"            -> ["KS"]
      "Springfield-Holyoke, MA-CT SMA" -> ["MA", "CT"]
      "Honolulu, Territory of Hawaii SMA" -> ["HI"]
    """
    if "Territory of Hawaii" in sma_name:
        return ["HI"]
    # Capture token after comma, before "SMA"
    m = re.match(r"^[^,]+,\s*([A-Za-z\-]+)\s+SMA", sma_name)
    if not m:
        return []
    token = m.group(1)
    # Token might be like "KS" or "MA-CT" or "WV-KY-OH"
    parts = [p.strip().upper() for p in token.split("-")]
    states = [p for p in parts if p in STATE_FIPS]
    return states


# Manual overrides for cases where fuzzy matching is unreliable
# (Spanish characters in Puerto Rico, Rio Piedras now merged into San Juan, etc.)
MANUAL_OVERRIDES = {
    # (sma_code, city_name): (state_fips, place_fips_7digit, county_fips_5digit)
    ("4840", "Mayaguez"): ("72", "7252431", "72097"),  # Mayagüez zona urbana / Mayagüez Municipio
    ("7440", "Rio Piedras"): ("72", "7276770", "72127"),  # merged into San Juan
}


def normalize_name(s: str) -> str:
    """Strip suffixes and normalize for matching."""
    s = s.lower().strip()
    # Strip place type suffixes
    for suf in [
        " city and borough", " municipality", " consolidated government",
        " metropolitan government", " urban county", " metro government",
        " unified government", " (balance)", " (county)", " ccd",
        " city", " town", " village", " borough", " cdp", " place",
    ]:
        if s.endswith(suf):
            s = s[: -len(suf)].strip()
    s = s.replace(".", "").replace(",", "").replace("--", "-").replace("  ", " ").strip()
    return s


def http_get_json(url: str) -> list:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------- Census API loaders (cached on disk) ----------

CACHE_DIR = DATA / "census_place_cache"
CACHE_DIR.mkdir(exist_ok=True)


def places_for_state(state_fips: str) -> list:
    """Return list of dicts with NAME, state, place for all places in a state.

    Uses ACS 2021 5-year (broad coverage of incorporated places + CDPs).
    """
    cache_file = CACHE_DIR / f"places_{state_fips}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())

    url = (
        f"https://api.census.gov/data/2020/dec/dhc?get=NAME"
        f"&for=place:*&in=state:{state_fips}&key={API_KEY}"
    )
    try:
        rows = http_get_json(url)
    except Exception as e:
        # Fallback to 2020 ACS 5-year
        try:
            url2 = (
                f"https://api.census.gov/data/2020/acs/acs5?get=NAME"
                f"&for=place:*&in=state:{state_fips}&key={API_KEY}"
            )
            rows = http_get_json(url2)
        except Exception as e2:
            print(f"  ! Failed to fetch places for state {state_fips}: {e} / {e2}", file=sys.stderr)
            return []
    header = rows[0]
    name_i = header.index("NAME")
    state_i = header.index("state")
    place_i = header.index("place")
    out = []
    for r in rows[1:]:
        full = r[name_i]
        # NAME like "Wichita city, Kansas"; split off ", Kansas"
        city_part = full.split(",", 1)[0]
        out.append({
            "name_full": full,
            "name_city": city_part,
            "state_fips": r[state_i],
            "place_fips": r[place_i],
        })
    cache_file.write_text(json.dumps(out))
    return out


COUSUB_CACHE = CACHE_DIR / "place_county_subdivision.json"


def county_for_place_api(state_fips: str, place_fips: str) -> str:
    """Get 5-digit county FIPS for a place via Census API county-or-part lookup.

    For places spanning multiple counties, returns the one with largest population
    (largest P1_001N total). If population fetch fails, returns the first listed.
    Caches results to disk to avoid refetching.
    """
    cache = {}
    if COUSUB_CACHE.exists():
        try:
            cache = json.loads(COUSUB_CACHE.read_text())
        except Exception:
            cache = {}
    key = f"{state_fips}_{place_fips}"
    if key in cache:
        return cache[key]
    url = (
        f"https://api.census.gov/data/2020/dec/dhc?get=NAME,P1_001N"
        f"&for=county%20(or%20part):*&in=state:{state_fips}%20place:{place_fips}"
        f"&key={API_KEY}"
    )
    try:
        rows = http_get_json(url)
    except Exception as e:
        # Try without population variable
        url2 = (
            f"https://api.census.gov/data/2020/dec/dhc?get=NAME"
            f"&for=county%20(or%20part):*&in=state:{state_fips}%20place:{place_fips}"
            f"&key={API_KEY}"
        )
        try:
            rows = http_get_json(url2)
        except Exception:
            cache[key] = ""
            COUSUB_CACHE.write_text(json.dumps(cache))
            return ""
    header = rows[0]
    if len(rows) < 2:
        cache[key] = ""
        COUSUB_CACHE.write_text(json.dumps(cache))
        return ""
    state_i = header.index("state")
    cnty_i = header.index("county (or part)")
    pop_i = header.index("P1_001N") if "P1_001N" in header else None
    # Pick row with largest population
    best = rows[1]
    best_pop = -1
    for r in rows[1:]:
        try:
            pop = int(r[pop_i]) if pop_i is not None else 0
        except (ValueError, TypeError):
            pop = 0
        if pop > best_pop:
            best_pop = pop
            best = r
    result = best[state_i].zfill(2) + best[cnty_i].zfill(3)
    cache[key] = result
    COUSUB_CACHE.write_text(json.dumps(cache))
    return result


# ---------- matching ----------

def match_city(city_name: str, places: list, mode: str = "exact") -> dict | None:
    """Find best place row for a given city name from a list of state places.

    mode='exact'   : require normalized exact match.
    mode='prefix'  : allow the candidate to start with the target (e.g. 'Greensboro-High Point' -> 'Greensboro').
    mode='loose'   : allow startswith in either direction or substring on word boundary.
    """
    target = normalize_name(city_name)
    if mode == "exact":
        for p in places:
            if normalize_name(p["name_city"]) == target:
                return p
        return None
    if mode == "prefix":
        # Candidate place name should *start with* the target city's first word(s),
        # or vice versa, to allow hyphenated city names.
        best = None
        for p in places:
            cand = normalize_name(p["name_city"])
            if cand.startswith(target) or target.startswith(cand):
                if best is None or abs(len(cand) - len(target)) < abs(len(normalize_name(best["name_city"])) - len(target)):
                    best = p
        return best
    if mode == "loose":
        # Match only on whole-word boundaries (target must be a separate word in cand or vice versa)
        target_words = set(target.split())
        best = None
        for p in places:
            cand = normalize_name(p["name_city"])
            cand_words = set(cand.split())
            if target_words & cand_words:
                if best is None:
                    best = p
        return best
    return None


# ---------- main ----------

def main():
    sma_rows = list(csv.DictReader(open(DATA / "sma_1950_ranked.csv")))
    existing = list(csv.DictReader(open(DATA / "central_city_place_fips.csv")))
    existing_sma_codes = {r["sma_code"] for r in existing}
    print(f"SMAs total: {len(sma_rows)}; already-mapped SMA codes: {len(existing_sma_codes)}")

    # Pre-cache places per state for all unique states we will need.
    needed_states = set()
    todo = []
    for row in sma_rows:
        if row["sma_code"] in existing_sma_codes:
            continue
        states = parse_states_from_sma_name(row["sma_name"])
        if not states:
            print(f"  ! No state parsed from '{row['sma_name']}'")
            continue
        for s in states:
            needed_states.add(s)
        cities = row["central_cities"].split("|")
        todo.append((row, states, cities))

    print(f"To-do SMAs: {len(todo)}; states to fetch: {len(needed_states)}")

    # Fetch places per state
    state_places: dict[str, list] = {}
    for st in sorted(needed_states):
        fips = STATE_FIPS.get(st)
        if not fips:
            print(f"  ! Unknown state abbr: {st}")
            continue
        places = places_for_state(fips)
        state_places[st] = places
        print(f"  {st} ({fips}): {len(places)} places")

    # place->county will be looked up on demand via Census API (cached)
    print(f"place-county lookups will use Census API (cached at {COUSUB_CACHE})")

    # Output rows: start with existing
    out_rows = list(existing)
    unmatched = []

    for row, states, cities in todo:
        for city in cities:
            city = city.strip()
            # Skip non-city descriptors like "Northeastern NJ" (only present in row 5600 already mapped).
            if not city:
                continue
            # Manual override check first
            override = MANUAL_OVERRIDES.get((row["sma_code"], city))
            if override:
                out_rows.append({
                    "sma_code": row["sma_code"],
                    "sma_name": row["sma_name"],
                    "central_city": city,
                    "state_fips": override[0],
                    "place_fips": override[1],
                    "county_fips_central": override[2],
                })
                continue

            # Try each candidate state, exact-match first across all states, then prefix, then loose.
            chosen = None
            chosen_state = None
            for mode in ("exact", "prefix", "loose"):
                for st in states:
                    places = state_places.get(st, [])
                    m = match_city(city, places, mode=mode)
                    if m:
                        chosen = m
                        chosen_state = st
                        break
                if chosen:
                    break
            if not chosen:
                unmatched.append((row["sma_code"], row["sma_name"], city, states))
                continue
            cnty = county_for_place_api(chosen["state_fips"], chosen["place_fips"])
            out_rows.append({
                "sma_code": row["sma_code"],
                "sma_name": row["sma_name"],
                "central_city": city,
                "state_fips": chosen["state_fips"],
                "place_fips": chosen["state_fips"] + chosen["place_fips"],
                "county_fips_central": cnty,
            })

    # Write out CSV
    out_path = DATA / "central_city_place_fips_all172.csv"
    fields = ["sma_code", "sma_name", "central_city", "state_fips", "place_fips", "county_fips_central"]
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in out_rows:
            w.writerow({k: r.get(k, "") for k in fields})
    print(f"\nWrote {out_path} with {len(out_rows)} rows.")
    print(f"Unmatched cities: {len(unmatched)}")
    for u in unmatched:
        print(f"  ! SMA {u[0]} '{u[1]}': city '{u[2]}' in states {u[3]}")


if __name__ == "__main__":
    main()
