"""
Build country-level LLM coverage scores using:
1. LanguageBench results (per-language scores across 34 models, 7 tasks)
2. CLDR language-speaking population data (language-country pairs with speaker counts)

Methodology (same as the AI Language Proficiency Monitor paper):
  country_score = Σ(language_score × speakers_in_country) / total_speakers_in_country

Output: data/country_scores.json
"""
import json
import os
from collections import defaultdict
from language_data.population_data import LANGUAGE_SPEAKING_POPULATION

BASE_DIR = "/Users/azizsunderji/Dropbox/Home Economics/2026_02_10_LLMLanguages"
RESULTS_PATH = os.path.join(BASE_DIR, "data", "results.json")
LANGUAGES_PATH = os.path.join(BASE_DIR, "data", "languages.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "country_scores.json")

# ── Step 1: Compute per-language average score across all models and tasks ─────

with open(RESULTS_PATH) as f:
    results = json.load(f)

with open(LANGUAGES_PATH) as f:
    lang_meta = {l["bcp_47"]: l for l in json.load(f)}

# Average score per language (across all models, tasks, metrics)
lang_scores_raw = defaultdict(list)
for r in results:
    lang_scores_raw[r["bcp_47"]].append(r["score"])

lang_avg_scores = {}
for bcp, scores in lang_scores_raw.items():
    lang_avg_scores[bcp] = sum(scores) / len(scores)

print(f"Language scores computed for {len(lang_avg_scores)} languages")
print(f"  English: {lang_avg_scores.get('en', 'N/A'):.3f}")
print(f"  French:  {lang_avg_scores.get('fr', 'N/A'):.3f}")
print(f"  Swahili: {lang_avg_scores.get('sw', 'N/A'):.3f}")
print(f"  Hindi:   {lang_avg_scores.get('hi', 'N/A'):.3f}")

# ── Step 2: Parse CLDR data into country → [(language, speakers)] ──────────────

country_languages = defaultdict(list)  # ISO2 → [(bcp_47, speakers)]

for key, speakers in LANGUAGE_SPEAKING_POPULATION.items():
    if '-' not in key:
        continue  # Skip entries without country code (e.g., "aa" without territory)
    parts = key.split('-')
    # Format is "lang-COUNTRY" (e.g., "en-US", "kk-KZ")
    # But some have script: "zh-Hant-TW" → country is last part if uppercase 2-letter
    country = parts[-1]
    lang = parts[0]
    # Only take 2-letter uppercase country codes
    if len(country) == 2 and country.isalpha() and country.isupper():
        country_languages[country].append((lang, speakers))

print(f"\nCountry-language mappings for {len(country_languages)} countries")

# ── Step 3: Compute weighted country scores ────────────────────────────────────

country_scores = {}
unmatched_langs = set()

for country, lang_list in country_languages.items():
    total_speakers = sum(s for _, s in lang_list)
    if total_speakers < 1000:
        continue  # Skip tiny populations

    weighted_sum = 0
    matched_speakers = 0
    lang_details = []

    for lang, speakers in sorted(lang_list, key=lambda x: -x[1]):
        score = lang_avg_scores.get(lang)
        if score is not None:
            weighted_sum += score * speakers
            matched_speakers += speakers
            lang_name = lang_meta.get(lang, {}).get("language_name", lang)
            lang_details.append({
                "language": lang,
                "language_name": lang_name,
                "speakers": speakers,
                "pct_of_country": round(speakers / total_speakers * 100, 1),
                "score": round(score, 3),
            })
        else:
            unmatched_langs.add(lang)

    if matched_speakers > 0:
        coverage_pct = matched_speakers / total_speakers * 100
        overall_score = weighted_sum / matched_speakers
        country_scores[country] = {
            "score": round(overall_score, 3),
            "coverage_pct": round(coverage_pct, 1),
            "total_speakers": total_speakers,
            "matched_speakers": matched_speakers,
            "languages": lang_details[:10],  # Top 10 languages
        }

print(f"Country scores computed for {len(country_scores)} countries")
print(f"Unmatched languages (no benchmark score): {len(unmatched_langs)}")

# ── Step 4: Spot checks ───────────────────────────────────────────────────────

print("\n── Spot Checks ──")
for cc, name in [("KZ", "Kazakhstan"), ("IN", "India"), ("NG", "Nigeria"),
                  ("US", "United States"), ("FR", "France"), ("ET", "Ethiopia")]:
    if cc in country_scores:
        cs = country_scores[cc]
        print(f"\n{name} ({cc}): score={cs['score']:.3f}, coverage={cs['coverage_pct']:.1f}%")
        for ld in cs["languages"][:5]:
            print(f"  {ld['language_name']:20s} ({ld['pct_of_country']:5.1f}%) → {ld['score']:.3f}")

# ── Step 5: Save ──────────────────────────────────────────────────────────────

with open(OUTPUT_PATH, 'w') as f:
    json.dump(country_scores, f, indent=2)
print(f"\nSaved to {OUTPUT_PATH}")

# Score distribution
scores = [v["score"] for v in country_scores.values()]
print(f"\nScore distribution:")
print(f"  Min:    {min(scores):.3f}")
print(f"  Max:    {max(scores):.3f}")
print(f"  Median: {sorted(scores)[len(scores)//2]:.3f}")
print(f"  Mean:   {sum(scores)/len(scores):.3f}")
