"""
Build admin-1 → language → LLM score mapping using LanguageBench data.
Uses comprehensive admin1 language map from Ethnologue/Glottolog knowledge.

Output: data/admin1_scores.json + data/admin1_with_tiers.topojson
"""
import os
import json
from collections import defaultdict

BASE_DIR = "/Users/azizsunderji/Dropbox/Home Economics/2026_02_10_LLMLanguages"
DATA_DIR = os.path.join(BASE_DIR, "data")
LIVE_SCORES_PATH = os.path.join(DATA_DIR, "language_table_live.json")
TOPO_PATH = os.path.join(DATA_DIR, "admin1_simplified.topojson")
COUNTRY_SCORES_PATH = os.path.join(DATA_DIR, "country_scores.json")
OUTPUT_PATH = os.path.join(DATA_DIR, "admin1_scores.json")

# Tier cutoffs (on live API "average" scores, which are pre-computed by the researchers)
# These scores range from ~0.25 to ~0.75 and already reflect proper normalization.
TIER1_CUTOFF = 0.65  # Well served (≥65%)
TIER2_CUTOFF = 0.50  # Partially served; below = poorly served

# ── Step 1: Load language scores from LanguageBench live API ─────────────────
# Uses pre-computed averages from the researchers' API, which reflect their
# full methodology (36 models, proper normalization across tasks).

with open(LIVE_SCORES_PATH) as f:
    lang_table = json.load(f)

# Build BCP-47 → score mapping from live API data
bcp_scores = {}
lang_meta_list = []
for entry in lang_table:
    bcp = entry["bcp_47"]
    avg = entry.get("average")
    if avg is not None:
        bcp_scores[bcp] = avg
    lang_meta_list.append(entry)

# Build name → bcp mapping
bcp_by_name = {}
for l in lang_meta_list:
    bcp_by_name[l["language_name"].lower()] = l["bcp_47"]

# Language name → BCP-47 code mapping
NAME_TO_BCP = {
    "English": "en", "French": "fr", "German": "de", "Spanish": "es",
    "Portuguese": "pt", "Italian": "it", "Russian": "ru", "Chinese": "zh",
    "Mandarin": "zh", "Japanese": "ja", "Korean": "ko", "Dutch": "nl",
    "Polish": "pl", "Czech": "cs", "Arabic": "ar", "Hindi": "hi",
    "Bengali": "bn", "Turkish": "tr", "Vietnamese": "vi", "Thai": "th",
    "Indonesian": "id", "Malay": "ms", "Romanian": "ro", "Hungarian": "hu",
    "Ukrainian": "uk", "Serbian": "sr", "Croatian": "hr", "Bosnian": "bs",
    "Slovenian": "sl", "Bulgarian": "bg", "Greek": "el", "Hebrew": "he",
    "Georgian": "ka", "Armenian": "hy", "Azerbaijani": "az", "Kazakh": "kk",
    "Uzbek": "uz", "Turkmen": "tk", "Kyrgyz": "ky", "Tajik": "tg",
    "Farsi": "fa", "Persian": "fa", "Urdu": "ur", "Nepali": "ne",
    "Sinhala": "si", "Tamil": "ta", "Kannada": "kn", "Malayalam": "ml",
    "Telugu": "te", "Marathi": "mr", "Gujarati": "gu", "Punjabi": "pa",
    "Odia": "or", "Assamese": "as", "Burmese": "my", "Khmer": "km",
    "Lao": "lo", "Tagalog": "tl", "Filipino": "fil", "Mongolian": "mn",
    "Albanian": "sq", "Macedonian": "mk", "Latvian": "lv", "Lithuanian": "lt",
    "Estonian": "et", "Finnish": "fi", "Swedish": "sv", "Danish": "da",
    "Norwegian": "nb", "Icelandic": "is", "Maltese": "mt", "Welsh": "cy",
    "Irish": "ga", "Catalan": "ca", "Galician": "gl", "Basque": "eu",
    "Slovak": "sk", "Belarusian": "be", "Afrikaans": "af",
    "Swahili": "sw", "Amharic": "am", "Somali": "so", "Hausa": "ha",
    "Yoruba": "yo", "Igbo": "ig", "Zulu": "zu", "Xhosa": "xh",
    "Oromo": "om", "Tigrinya": "ti", "Shona": "sn", "Kinyarwanda": "rw",
    "Malagasy": "mg", "Wolof": "wo", "Lingala": "ln", "Cantonese": "yue",
    "Tibetan": "bo", "Uyghur": "ug", "Pashto": "ps",
    "Javanese": "jv", "Sundanese": "su", "Cebuano": "ceb",
    "Tatar": "tt", "Bashkir": "ba", "Chechen": "ce", "Chuvash": "cv",
    "Kurdish": "ku", "Divehi": "dv", "Quechua": "qu",
    "Haitian Creole": "ht", "Dari": "fa",
    "Fula": "ff", "Bambara": "bm", "Ewe": "ee", "Fon": "fon",
    "Twi": "tw", "Mossi": "mos", "Dioula": "dyu",
    "Tswana": "tn", "Sotho": "st", "Swazi": "ss",
    "Bemba": "bem", "Chichewa": "ny", "Kikongo": "kg",
    "Tshiluba": "lu", "Ganda": "lg", "Kirundi": "rn",
    "Dinka": "din", "Sango": "sg", "Tetum": "tet",
    "Tok Pisin": "tpi", "Bislama": "bi", "Samoan": "sm",
    "Fijian": "fj", "Tongan": "to", "Guarani": "gn",
    "Aymara": "ay", "Maithili": "mai",
    "Berber": "ber", "Tamazight": "zgh", "Avar": "av",
    "Hmong": "hmn", "Naga": "nag", "Meitei": "mni",
    "Mizo": "lus", "Khasi": "kha", "Nishi": "njz",
    "Konkani": "kok", "Sindhi": "sd",
    "Oshiwambo": "kj", "Umbundu": "umb",
    "Mandinka": "mnk", "Krio": "kri",
    "Cape Verdean Creole": "kea", "Mauritian Creole": "mfe",
    "Seychellois Creole": "crs", "Comorian": "zdj",
    "Afar": "aa", "Valencian": "ca",
    # Additional mappings for languages now in live API
    "Acehnese": "ace", "Balinese": "ban", "Minangkabau": "min",
    "Ilocano": "ilo", "Pangasinan": "pag", "Shan": "shn",
    "Northern Sotho": "nso", "Achinese": "ace",
    "Konkani": "gom",  # Goan Konkani in API
}

def get_lang_score(language_name):
    """Get LanguageBench score for a language by its common name.
    Returns None if language is not in LanguageBench at all (→ Tier 3).
    Returns the score even if 0.0 — zero-scored languages ARE poorly served."""
    bcp = NAME_TO_BCP.get(language_name)
    if bcp and bcp in bcp_scores:
        return round(bcp_scores[bcp], 3)
    # Try fuzzy match in LanguageBench metadata
    for meta in lang_meta_list:
        if meta.get("language_name", "").lower() == language_name.lower():
            if meta["bcp_47"] in bcp_scores:
                return round(bcp_scores[meta["bcp_47"]], 3)
    return None

print(f"Language scores computed for {len(bcp_scores)} languages")

# ── Step 2: Import comprehensive language map ────────────────────────────────

from admin1_language_map import ADMIN1_LANGUAGES, COUNTRY_LANGUAGE, get_language_for_region

print(f"Admin1 language overrides: {len(ADMIN1_LANGUAGES)}")
print(f"Country-level defaults: {len(COUNTRY_LANGUAGE)}")

# ── Step 3: Load TopoJSON and country scores, build mapping ──────────────────

with open(COUNTRY_SCORES_PATH) as f:
    country_scores = json.load(f)

print(f"Loading TopoJSON...")
with open(TOPO_PATH) as f:
    topo = json.load(f)

obj_name = list(topo["objects"].keys())[0]
geometries = topo["objects"][obj_name]["geometries"]
print(f"  {len(geometries)} admin-1 regions")

result = {}
stats = {"admin1_override": 0, "country_lang": 0,
         "not_in_languagebench": 0, "zero_score": 0, "no_language": 0}

for geom in geometries:
    props = geom.get("properties", {})
    iso2 = props.get("iso_a2", "")
    name = props.get("name", "Unknown")
    admin = props.get("admin", "")
    iso_code = props.get("iso_3166_2", "")

    # Get language from comprehensive map
    language = get_language_for_region(iso_code, iso2, name)
    score = None

    if language:
        score = get_lang_score(language)
        if iso_code in ADMIN1_LANGUAGES:
            stats["admin1_override"] += 1
        else:
            stats["country_lang"] += 1

    # If language exists but has no LanguageBench score,
    # that IS the data point: this language is poorly served by LLMs.
    # Do NOT fall back to country score — that hides the problem.
    if language and score is None:
        tier = 3  # Poorly served — not even benchmarked
        score = 0.0
        stats["not_in_languagebench"] += 1
    elif score is not None:
        if score >= TIER1_CUTOFF:
            tier = 1
        elif score >= TIER2_CUTOFF:
            tier = 2
        else:
            tier = 3
    elif language is None:
        tier = None  # No language data at all → grey
        stats["no_language"] += 1
    else:
        tier = 3
        stats["zero_score"] += 1

    key = iso_code if iso_code else f"{iso2}-{name}"
    result[key] = {
        "name": name,
        "country": admin if admin else iso2,
        "language": language or "Unknown",
        "score": score,
        "tier": tier,
    }

with open(OUTPUT_PATH, "w") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f"\nSaved {len(result)} region mappings to {OUTPUT_PATH}")
print(f"\n=== STATS ===")
print(f"  Admin-1 overrides:       {stats['admin1_override']}")
print(f"  Country language:        {stats['country_lang']}")
print(f"  Not in LanguageBench:    {stats['not_in_languagebench']} (→ Tier 3)")
print(f"  Zero score:              {stats['zero_score']} (→ Tier 3)")
print(f"  No language data:        {stats['no_language']} (→ grey)")

# Tier distribution
tiers = [v["tier"] for v in result.values() if v["tier"] is not None]
for t in [1, 2, 3]:
    count = tiers.count(t)
    print(f"  Tier {t}: {count} ({count/len(result)*100:.0f}%)")
no_tier = sum(1 for v in result.values() if v["tier"] is None)
print(f"  No tier: {no_tier}")

# Countries with internal variation
from collections import defaultdict as dd
country_tiers = dd(set)
for k, v in result.items():
    if v["tier"]:
        country_tiers[v["country"]].add(v["tier"])
multi = {c: t for c, t in country_tiers.items() if len(t) > 1}
print(f"\nCountries with internal tier variation: {len(multi)}")
for c in sorted(multi):
    print(f"  {c}: tiers {sorted(multi[c])}")

# Score distribution
scores_list = [v["score"] for v in result.values() if v["score"] is not None and v["score"] > 0]
print(f"\nScore distribution ({len(scores_list)} regions with real scores):")
print(f"  Min:    {min(scores_list):.3f}")
print(f"  Max:    {max(scores_list):.3f}")
print(f"  Median: {sorted(scores_list)[len(scores_list)//2]:.3f}")

# ── Step 4: Inject tier + score into TopoJSON properties ─────────────────────

print(f"\nInjecting tiers into TopoJSON...")
for geom in geometries:
    props = geom.get("properties", {})
    iso_code = props.get("iso_3166_2", "")
    name = props.get("name", "Unknown")
    iso2 = props.get("iso_a2", "")
    key = iso_code if iso_code else f"{iso2}-{name}"

    if key in result:
        props["score"] = result[key]["score"]
        props["tier"] = result[key]["tier"]
        props["language"] = result[key]["language"]
    else:
        props["score"] = None
        props["tier"] = None
        props["language"] = "Unknown"

TOPO_OUTPUT = os.path.join(DATA_DIR, "admin1_with_tiers.topojson")
with open(TOPO_OUTPUT, "w") as f:
    json.dump(topo, f, ensure_ascii=False)

topo_size = os.path.getsize(TOPO_OUTPUT) / 1e6
print(f"Saved {TOPO_OUTPUT} ({topo_size:.1f} MB)")
