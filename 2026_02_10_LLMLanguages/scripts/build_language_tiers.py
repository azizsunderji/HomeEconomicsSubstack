"""
Build admin-1 → language → LLM tier mapping.
Output: data/admin1_llm_tiers.json

Three-layer approach:
1. Country-level primary spoken language (with manual overrides for ~40 countries)
2. Admin-1 level overrides for ~15 multilingual countries
3. Language → tier classification using MMLU-ProX scores + family proximity
"""
import os
import json

BASE_DIR = "/Users/azizsunderji/Dropbox/Home Economics/2026_02_10_LLMLanguages"
DATA_DIR = os.path.join(BASE_DIR, "data")
TOPO_PATH = os.path.join(DATA_DIR, "admin1_simplified.topojson")
OUTPUT_PATH = os.path.join(DATA_DIR, "admin1_llm_tiers.json")

# ═══════════════════════════════════════════════════════════════
# MMLU-ProX SCORES (2025) — 29 measured languages
# ═══════════════════════════════════════════════════════════════
MMLU_SCORES = {
    "Italian": 80.9, "German": 80.3, "French": 79.8, "English": 79.4,
    "Spanish": 78.6, "Portuguese": 78.2, "Russian": 76.8, "Dutch": 76.5,
    "Polish": 75.8, "Czech": 75.2, "Romanian": 74.8, "Hungarian": 74.1,
    "Ukrainian": 73.5, "Serbian": 72.9, "Chinese": 77.5, "Japanese": 76.2,
    "Korean": 75.0, "Arabic": 71.8, "Hindi": 70.2, "Bengali": 68.5,
    "Turkish": 67.8, "Vietnamese": 66.5, "Thai": 69.2, "Indonesian": 70.8,
    "Swahili": 55.2, "Telugu": 62.5, "Marathi": 61.8, "Nepali": 58.5,
    "Wolof": 36.9,
}

# ═══════════════════════════════════════════════════════════════
# TIER CLASSIFICATION — language → tier
# Tier 1: MMLU ≥ 75% or closely related to scored lang ≥ 75%
# Tier 2: MMLU 55-74.9% or related to a lang in that range
# Tier 3: MMLU < 55%, unmeasured with no close high-resource relative
# ═══════════════════════════════════════════════════════════════
LANGUAGE_TIERS = {
    # Tier 1 — well served (MMLU-ProX ≥ 75% or closely related)
    "English": 1, "French": 1, "German": 1, "Spanish": 1, "Portuguese": 1,
    "Italian": 1, "Russian": 1, "Chinese": 1, "Mandarin": 1, "Japanese": 1,
    "Korean": 1, "Dutch": 1, "Polish": 1, "Czech": 1,
    # Closely related to scored ≥75% languages
    "Swedish": 1, "Danish": 1, "Norwegian": 1,  # ← Germanic, close to German/Dutch
    "Afrikaans": 1,  # ← daughter of Dutch (76.5%)
    "Slovak": 1,  # ← very close to Czech (75.2%)
    "Catalan": 1,  # ← very close to Spanish (78.6%)
    "Galician": 1,  # ← sister of Portuguese (78.2%)
    "Cantonese": 1,  # ← variety of Chinese (77.5%)

    # Tier 2 — partially served (MMLU-ProX 55-74.9% or related)
    "Arabic": 2, "Hindi": 2, "Indonesian": 2, "Malay": 2, "Thai": 2,
    "Romanian": 2, "Hungarian": 2, "Ukrainian": 2, "Serbian": 2,
    "Bengali": 2, "Telugu": 2, "Marathi": 2, "Nepali": 2, "Urdu": 2,
    "Croatian": 2, "Bosnian": 2, "Slovenian": 2,  # ← Serbian is 72.9% (Tier 2)
    "Bulgarian": 2, "Lithuanian": 2, "Latvian": 2, "Estonian": 2,
    "Finnish": 2, "Icelandic": 2, "Macedonian": 2,
    "Vietnamese": 2, "Swahili": 2, "Turkish": 2, "Farsi": 2, "Persian": 2,
    "Tamil": 2, "Kannada": 2, "Malayalam": 2, "Gujarati": 2, "Punjabi": 2,
    "Tagalog": 2, "Filipino": 2, "Greek": 2, "Hebrew": 2, "Georgian": 2,
    "Armenian": 2, "Kazakh": 2, "Uzbek": 2, "Azerbaijani": 2, "Burmese": 2,
    "Khmer": 2, "Lao": 2, "Sinhala": 2, "Amharic": 2, "Mongolian": 2,
    "Albanian": 2, "Malagasy": 2, "Somali": 2, "Javanese": 2,
    "Sundanese": 2, "Assamese": 2, "Odia": 2,
    "Belarusian": 2, "Maltese": 2, "Welsh": 2, "Irish": 2,
    "Kyrgyz": 2, "Tajik": 2, "Turkmen": 2,

    # Tier 3 — poorly served
    "Hausa": 3, "Yoruba": 3, "Igbo": 3, "Wolof": 3, "Zulu": 3, "Xhosa": 3,
    "Oromo": 3, "Tigrinya": 3, "Shona": 3, "Kinyarwanda": 3, "Kirundi": 3,
    "Lingala": 3, "Chichewa": 3, "Tswana": 3, "Fula": 3, "Twi": 3,
    "Pashto": 3, "Balochi": 3, "Dzongkha": 3, "Basque": 3, "Tibetan": 3,
    "Uyghur": 3, "Chechen": 3, "Avar": 3, "Tatar": 3, "Sindhi": 3,
    "Kikongo": 3, "Tshiluba": 3, "Sotho": 3, "Tsonga": 3, "Venda": 3,
    "Ndebele": 3, "Swazi": 3, "Bemba": 3, "Lozi": 3, "Tonga": 3,
    "Chewa": 3, "Sena": 3, "Makhuwa": 3, "Sukuma": 3, "Ganda": 3,
    "Luo": 3, "Kalenjin": 3, "Kamba": 3, "Meru": 3, "Maasai": 3,
    "Dinka": 3, "Nuer": 3, "Bari": 3, "Acholi": 3, "Teso": 3,
    "Karen": 3, "Shan": 3, "Chin": 3, "Kachin": 3, "Rakhine": 3, "Mon": 3,
    "Naga": 3, "Meitei": 3, "Mizo": 3, "Khasi": 3, "Nishi": 3,
    "Hmong": 3, "Tetum": 3, "Tok Pisin": 3, "Fijian": 3, "Samoan": 3,
    "Tongan": 3, "Marshallese": 3, "Chamorro": 3, "Palauan": 3,
    "Chuukese": 3, "Bislama": 3, "Hiri Motu": 3,
    "Guarani": 3, "Quechua": 3, "Aymara": 3, "Nahuatl": 3, "Mayan": 3,
    "Divehi": 3, "Dari": 3,
    "Bambara": 3, "Soninke": 3, "Mandinka": 3, "Jola": 3, "Serer": 3,
    "Ewe": 3, "Fon": 3, "Mossi": 3, "Dioula": 3, "Bété": 3,
    "Kabyle": 3, "Berber": 3, "Tamazight": 3, "Hassaniya": 3,
    "Comorian": 3, "Swati": 3,
    "Tigre": 3, "Afar": 3, "Sidamo": 3, "Hadiyya": 3, "Gurage": 3,
    "Nuer": 3, "Fur": 3, "Zaghawa": 3, "Masalit": 3,
    "Sango": 3, "Mbochi": 3, "Teke": 3,
    "Haitian Creole": 3, "Kurdish": 3, "Konkani": 3, "Kanuri": 3,
    "Tiv": 3, "Bashkir": 3, "Chuvash": 3, "Harari": 3,
    "Zhuang": 3, "Cebuano": 3, "Valencian": 3,
    "Umbundu": 3, "Kimbundu": 3, "Oshiwambo": 3, "Fang": 3,
    "Krio": 3, "Kpelle": 3, "Kriol": 3, "Cape Verdean Creole": 3,
    "Mauritian Creole": 3, "Seychellois Creole": 3,
}

# ═══════════════════════════════════════════════════════════════
# COUNTRY → PRIMARY LANGUAGE (manual curated list)
# For the ~190 countries, what language do most people speak day-to-day?
# ═══════════════════════════════════════════════════════════════
COUNTRY_LANGUAGE = {
    # Americas
    "US": "English", "CA": "English", "MX": "Spanish", "GT": "Spanish",
    "BZ": "English", "HN": "Spanish", "SV": "Spanish", "NI": "Spanish",
    "CR": "Spanish", "PA": "Spanish", "CU": "Spanish", "JM": "English",
    "HT": "Haitian Creole", "DO": "Spanish", "PR": "Spanish", "TT": "English",
    "BS": "English", "BB": "English", "GD": "English", "AG": "English",
    "DM": "English", "LC": "English", "VC": "English", "KN": "English",
    "CO": "Spanish", "VE": "Spanish", "GY": "English", "SR": "Dutch",
    "EC": "Spanish", "PE": "Spanish", "BO": "Spanish", "PY": "Spanish",
    "UY": "Spanish", "AR": "Spanish", "CL": "Spanish", "BR": "Portuguese",

    # Europe
    "GB": "English", "IE": "English", "FR": "French", "DE": "German",
    "AT": "German", "CH": "German", "NL": "Dutch", "BE": "Dutch",
    "LU": "French", "IT": "Italian", "ES": "Spanish", "PT": "Portuguese",
    "GR": "Greek", "CY": "Greek", "MT": "Maltese",
    "PL": "Polish", "CZ": "Czech", "SK": "Slovak", "HU": "Hungarian",
    "RO": "Romanian", "BG": "Bulgarian", "HR": "Croatian", "SI": "Slovenian",
    "BA": "Bosnian", "RS": "Serbian", "ME": "Serbian", "MK": "Macedonian",
    "AL": "Albanian", "XK": "Albanian",
    "DK": "Danish", "SE": "Swedish", "NO": "Norwegian", "FI": "Finnish",
    "IS": "Icelandic", "EE": "Estonian", "LV": "Latvian", "LT": "Lithuanian",
    "UA": "Ukrainian", "BY": "Russian", "MD": "Romanian",
    "RU": "Russian",

    # Middle East & Central Asia
    "TR": "Turkish", "IR": "Farsi", "IQ": "Arabic", "SY": "Arabic",
    "JO": "Arabic", "LB": "Arabic", "IL": "Hebrew", "PS": "Arabic",
    "SA": "Arabic", "YE": "Arabic", "OM": "Arabic", "AE": "Arabic",
    "QA": "Arabic", "BH": "Arabic", "KW": "Arabic",
    "GE": "Georgian", "AM": "Armenian", "AZ": "Azerbaijani",
    "KZ": "Kazakh", "UZ": "Uzbek", "TM": "Turkmen", "KG": "Kyrgyz",
    "TJ": "Tajik", "AF": "Dari",

    # South Asia
    "IN": "Hindi", "PK": "Urdu", "BD": "Bengali", "LK": "Sinhala",
    "NP": "Nepali", "BT": "Dzongkha", "MV": "Divehi",

    # East Asia
    "CN": "Mandarin", "TW": "Mandarin", "JP": "Japanese", "KR": "Korean",
    "KP": "Korean", "MN": "Mongolian",

    # Southeast Asia
    "VN": "Vietnamese", "TH": "Thai", "MM": "Burmese", "LA": "Lao",
    "KH": "Khmer", "MY": "Malay", "SG": "English", "ID": "Indonesian",
    "PH": "Filipino", "BN": "Malay", "TL": "Tetum",

    # Africa — North
    "MA": "Arabic", "DZ": "Arabic", "TN": "Arabic", "LY": "Arabic",
    "EG": "Arabic", "SD": "Arabic", "SS": "Dinka", "MR": "Arabic",

    # Africa — West
    "SN": "Wolof", "GM": "Mandinka", "GW": "Kriol", "GN": "Fula",
    "SL": "Krio", "LR": "Kpelle", "CI": "Dioula", "ML": "Bambara",
    "BF": "Mossi", "GH": "Twi", "TG": "Ewe", "BJ": "Fon",
    "NE": "Hausa", "NG": "English", "CV": "Cape Verdean Creole",

    # Africa — Central
    "CM": "French", "CF": "Sango", "TD": "Arabic", "CG": "Lingala",
    "CD": "Lingala", "GQ": "Fang", "GA": "Fang", "ST": "Portuguese",

    # Africa — East
    "ET": "Amharic", "ER": "Tigrinya", "DJ": "Somali", "SO": "Somali",
    "KE": "Swahili", "UG": "Ganda", "RW": "Kinyarwanda",
    "BI": "Kirundi", "TZ": "Swahili", "MZ": "Makhuwa",
    "MW": "Chichewa", "ZM": "Bemba", "ZW": "Shona",
    "MG": "Malagasy", "KM": "Comorian", "MU": "Mauritian Creole", "SC": "Seychellois Creole",

    # Africa — Southern
    "ZA": "Zulu", "NA": "Oshiwambo", "BW": "Tswana", "SZ": "Swazi",
    "LS": "Sotho", "AO": "Umbundu",

    # Oceania
    "AU": "English", "NZ": "English", "PG": "Tok Pisin", "FJ": "Fijian",
    "SB": "English", "VU": "Bislama", "WS": "Samoan", "TO": "Tongan",
    "MH": "Marshallese", "FM": "Chuukese", "PW": "Palauan",
    "KI": "English", "NR": "English", "TV": "English",
    "NC": "French", "PF": "French", "GU": "English",

    # Small territories & dependencies
    "HK": "Cantonese", "MO": "Cantonese",
    "AI": "English", "BM": "English", "TC": "English", "MS": "English",
    "VI": "English", "VG": "English", "KY": "English", "GI": "English",
    "JE": "English", "GG": "English", "IM": "English", "FK": "English",
    "SH": "English", "NF": "English", "PN": "English", "CK": "English",
    "NU": "English", "TK": "English", "AS": "Samoan",
    "LI": "German", "AD": "Catalan", "MC": "French", "SM": "Italian",
    "VA": "Italian", "AX": "Swedish", "FO": "Danish", "GL": "Danish",
    "PM": "French", "WF": "French", "BL": "French", "MF": "French",
    "GS": "English", "IO": "English", "HM": "English",
    "CW": "Dutch", "SX": "Dutch", "AW": "Dutch",
    "EH": "Arabic", "AQ": "English", "TF": "French",
    "MP": "English", "UM": "English",
}

# ═══════════════════════════════════════════════════════════════
# ADMIN-1 OVERRIDES — multilingual countries (~300 regions)
# Key: iso_3166_2 code or partial name match
# ═══════════════════════════════════════════════════════════════

# India: state → language
INDIA_OVERRIDES = {
    # Hindi belt (Tier 1 via Hindi)
    "IN-UP": "Hindi", "IN-MP": "Hindi", "IN-RJ": "Hindi", "IN-BR": "Hindi",
    "IN-JH": "Hindi", "IN-CT": "Hindi", "IN-HR": "Hindi", "IN-HP": "Hindi",
    "IN-UT": "Hindi", "IN-DL": "Hindi",
    # Dravidian south (Tier 2)
    "IN-TN": "Tamil", "IN-KA": "Kannada", "IN-KL": "Malayalam",
    "IN-AP": "Telugu", "IN-TG": "Telugu",
    # East
    "IN-WB": "Bengali", "IN-OR": "Odia", "IN-AS": "Assamese",
    # West
    "IN-GJ": "Gujarati", "IN-MH": "Marathi", "IN-GA": "Konkani",
    # Punjab
    "IN-PB": "Punjabi",
    # Northeast (NE Indian languages — Tier 3 for most)
    "IN-NL": "Naga", "IN-MN": "Meitei", "IN-MZ": "Mizo",
    "IN-TR": "Bengali", "IN-ML": "Khasi", "IN-AR": "Nishi",
    "IN-SK": "Nepali",
    # Union territories
    "IN-JK": "Urdu", "IN-LA": "Tibetan", "IN-CH": "Hindi",
    "IN-PY": "Tamil", "IN-AN": "Hindi", "IN-DH": "Gujarati",
    "IN-LD": "Malayalam",
}

# Nigeria: state → language
NIGERIA_OVERRIDES = {
    # Hausa north
    "NG-KN": "Hausa", "NG-KT": "Hausa", "NG-SO": "Hausa", "NG-ZA": "Hausa",
    "NG-JI": "Hausa", "NG-BO": "Kanuri", "NG-YO": "Hausa", "NG-BA": "Hausa",
    "NG-GO": "Hausa", "NG-KE": "Hausa", "NG-KD": "Hausa", "NG-NI": "Hausa",
    "NG-AD": "Hausa", "NG-FC": "Hausa", "NG-NA": "Hausa", "NG-TA": "Hausa",
    "NG-KW": "Hausa", "NG-PL": "Hausa", "NG-BE": "Tiv",
    "NG-KO": "Yoruba",  # Kogi — Middle Belt, Yoruba plurality
    # Yoruba southwest
    "NG-OY": "Yoruba", "NG-OG": "Yoruba", "NG-ON": "Yoruba", "NG-OS": "Yoruba",
    "NG-EK": "Yoruba", "NG-LA": "Yoruba",
    # Igbo southeast
    "NG-AN": "Igbo", "NG-EN": "Igbo", "NG-EB": "Igbo", "NG-IM": "Igbo",
    "NG-AB": "Igbo",
    # Niger Delta / Middle Belt — English/Pidgin default
    "NG-RI": "English", "NG-BY": "English", "NG-CR": "English",
    "NG-AK": "English", "NG-ED": "English", "NG-DE": "English",
}

# Ethiopia: region → language
ETHIOPIA_OVERRIDES = {
    "ET-OR": "Oromo", "ET-AM": "Amharic", "ET-TI": "Tigrinya",
    "ET-SO": "Somali", "ET-AF": "Afar", "ET-SN": "Sidamo",
    "ET-GA": "Oromo", "ET-HA": "Harari", "ET-BE": "Amharic",
    "ET-AA": "Amharic", "ET-DD": "Amharic",
}

# Pakistan: province → language
PAKISTAN_OVERRIDES = {
    "PK-PB": "Punjabi", "PK-SD": "Sindhi", "PK-KP": "Pashto",
    "PK-BA": "Balochi", "PK-IS": "Urdu", "PK-GB": "Urdu",
    "PK-JK": "Urdu", "PK-TA": "Pashto",
}

# China: province → language
CHINA_OVERRIDES = {
    "CN-GD": "Cantonese", "CN-XZ": "Tibetan", "CN-XJ": "Uyghur",
    "CN-NM": "Mongolian", "CN-HK": "Cantonese", "CN-MO": "Cantonese",
    # Taiwan handled by country code TW
}

# South Africa: province → language
SOUTH_AFRICA_OVERRIDES = {
    "ZA-NL": "Zulu", "ZA-EC": "Xhosa", "ZA-WC": "Afrikaans",
    "ZA-NC": "Afrikaans", "ZA-GT": "Zulu", "ZA-FS": "Sotho",
    "ZA-NW": "Tswana", "ZA-LP": "Sotho", "ZA-MP": "Swazi",
}

# Indonesia: province → language
INDONESIA_OVERRIDES = {
    "ID-JT": "Javanese", "ID-JI": "Javanese", "ID-YO": "Javanese",
    "ID-JB": "Sundanese", "ID-BT": "Sundanese",
    # Rest inherit Indonesian (Tier 1)
}

# Russia: subject → language
RUSSIA_OVERRIDES = {
    "RU-CE": "Chechen", "RU-DA": "Avar", "RU-IN": "Chechen",
    "RU-TA": "Tatar", "RU-BA": "Bashkir", "RU-CU": "Chuvash",
    # Rest inherit Russian (Tier 1)
}

# Spain
SPAIN_OVERRIDES = {
    # Catalan provinces (Catalonia + Balearics)
    "ES-B": "Catalan", "ES-GI": "Catalan", "ES-L": "Catalan", "ES-T": "Catalan",
    "ES-PM": "Catalan",
    # Basque provinces
    "ES-BI": "Basque", "ES-SS": "Basque", "ES-VI": "Basque",
    # Galician provinces
    "ES-C": "Galician", "ES-LU": "Galician", "ES-OR": "Galician", "ES-PO": "Galician",
}

# Belgium
BELGIUM_OVERRIDES = {
    # Flemish provinces → Dutch
    "BE-VAN": "Dutch", "BE-VBR": "Dutch", "BE-VLI": "Dutch",
    "BE-VOV": "Dutch", "BE-VWV": "Dutch",
    # Walloon provinces → French
    "BE-WBR": "French", "BE-WHT": "French", "BE-WLG": "French",
    "BE-WLX": "French", "BE-WNA": "French",
    # Brussels
    "BE-BRU": "French",
}

# Canada
CANADA_OVERRIDES = {
    "CA-QC": "French",
}

# DRC: province → language
DRC_OVERRIDES = {
    "CD-KN": "Lingala", "CD-EQ": "Lingala", "CD-MO": "Lingala",
    "CD-TU": "Lingala", "CD-SU": "Lingala", "CD-NU": "Lingala",
    "CD-NK": "Swahili", "CD-SK": "Swahili", "CD-MA": "Swahili",
    "CD-HK": "Swahili", "CD-IT": "Swahili", "CD-TA": "Swahili",
    "CD-BC": "Kikongo", "CD-KG": "Kikongo", "CD-KW": "Kikongo",
    "CD-KE": "Tshiluba", "CD-KA": "Tshiluba", "CD-LO": "Tshiluba",
    "CD-SA": "Tshiluba", "CD-LU": "Swahili", "CD-HU": "Swahili",
}

# Myanmar
MYANMAR_OVERRIDES = {
    "MM-11": "Kachin", "MM-12": "Karen", "MM-13": "Karen",
    "MM-14": "Chin", "MM-16": "Rakhine", "MM-17": "Shan",
    "MM-15": "Burmese",  # Mon state — Mon language close to Burmese
}

# Cameroon
CAMEROON_OVERRIDES = {
    "CM-NW": "English", "CM-SW": "English",
    # Rest inherit French
}

# Switzerland: canton → language
SWITZERLAND_OVERRIDES = {
    # French cantons
    "CH-GE": "French", "CH-VD": "French", "CH-NE": "French", "CH-JU": "French",
    # Bilingual cantons — French dominant
    "CH-FR": "French", "CH-VS": "French",
    # Italian canton
    "CH-TI": "Italian",
    # Bilingual — German/Romansh
    "CH-GR": "German",
    # Rest inherit German (country default)
}

# Iraq: Kurdistan region → Kurdish
IRAQ_OVERRIDES = {
    "IQ-AR": "Kurdish", "IQ-DA": "Kurdish", "IQ-SU": "Kurdish",
    "IQ-TS": "Kurdish",  # Kirkuk — contested, significant Kurdish pop
}

# Iran: regional language overrides
IRAN_OVERRIDES = {
    # Azerbaijani Turkish northwest
    "IR-01": "Azerbaijani", "IR-02": "Azerbaijani", "IR-03": "Azerbaijani",
    "IR-11": "Azerbaijani",  # Zanjan
    # Kurdish west
    "IR-16": "Kurdish", "IR-17": "Kurdish", "IR-05": "Kurdish",
    # Arabic southwest
    "IR-10": "Arabic",  # Khuzestan
    # Balochi southeast
    "IR-13": "Balochi",
    # Rest inherit Farsi
}

# Sri Lanka: Tamil-speaking Northern and Eastern provinces
SRI_LANKA_OVERRIDES = {
    "LK-41": "Tamil", "LK-42": "Tamil", "LK-43": "Tamil",
    "LK-44": "Tamil", "LK-45": "Tamil",  # Northern Province districts
    "LK-51": "Tamil", "LK-52": "Tamil", "LK-53": "Tamil",  # Eastern Province
}

# Spain: add Valencia (Valencian/Catalan)
SPAIN_VALENCIA = {
    "ES-V": "Catalan", "ES-A": "Catalan", "ES-CS": "Catalan",
}

# Merge all overrides
ALL_ADMIN1_OVERRIDES = {}
for d in [INDIA_OVERRIDES, NIGERIA_OVERRIDES, ETHIOPIA_OVERRIDES,
          PAKISTAN_OVERRIDES, CHINA_OVERRIDES, SOUTH_AFRICA_OVERRIDES,
          INDONESIA_OVERRIDES, RUSSIA_OVERRIDES, SPAIN_OVERRIDES,
          SPAIN_VALENCIA, BELGIUM_OVERRIDES, CANADA_OVERRIDES, DRC_OVERRIDES,
          MYANMAR_OVERRIDES, CAMEROON_OVERRIDES, SWITZERLAND_OVERRIDES,
          IRAQ_OVERRIDES, IRAN_OVERRIDES, SRI_LANKA_OVERRIDES]:
    ALL_ADMIN1_OVERRIDES.update(d)

print(f"Total admin-1 language overrides: {len(ALL_ADMIN1_OVERRIDES)}")

# ═══════════════════════════════════════════════════════════════
# LOAD TOPOJSON AND BUILD MAPPING
# ═══════════════════════════════════════════════════════════════

print(f"\nLoading TopoJSON from {TOPO_PATH}...")
with open(TOPO_PATH) as f:
    topo = json.load(f)

# Extract the object collection name (first key in 'objects')
obj_name = list(topo["objects"].keys())[0]
geometries = topo["objects"][obj_name]["geometries"]
print(f"  Found {len(geometries)} geometries in collection '{obj_name}'")

# Build the output mapping
result = {}
stats = {"override": 0, "country_default": 0, "missing_country": 0, "missing_language": 0}
tier_counts = {1: 0, 2: 0, 3: 0, "unknown": 0}

for geom in geometries:
    props = geom.get("properties", {})
    iso2 = props.get("iso_a2", "")
    name = props.get("name", "Unknown")
    admin = props.get("admin", "")
    iso_code = props.get("iso_3166_2", "")

    # Determine language
    language = None
    source = None

    # Layer 1: Check admin-1 override
    if iso_code and iso_code in ALL_ADMIN1_OVERRIDES:
        language = ALL_ADMIN1_OVERRIDES[iso_code]
        source = "admin1_override"
        stats["override"] += 1
    # Layer 2: Country-level default
    elif iso2 and iso2 in COUNTRY_LANGUAGE:
        language = COUNTRY_LANGUAGE[iso2]
        source = "country_default"
        stats["country_default"] += 1
    else:
        language = "Unknown"
        source = "missing"
        stats["missing_country"] += 1

    # Determine tier
    if language in LANGUAGE_TIERS:
        tier = LANGUAGE_TIERS[language]
    elif language == "Unknown":
        tier = 3  # Assume poorly served if we can't identify
    else:
        tier = 3  # Unmapped language → assume poorly served
        stats["missing_language"] += 1

    tier_counts[tier] = tier_counts.get(tier, 0) + 1

    # Get MMLU score if available
    score = MMLU_SCORES.get(language, None)

    # Use iso_3166_2 as key, fallback to constructed key
    key = iso_code if iso_code else f"{iso2}-{name}"

    result[key] = {
        "name": name,
        "country": admin if admin else iso2,
        "language": language,
        "tier": tier,
        "score": score,
    }

# Save output
with open(OUTPUT_PATH, "w") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f"\nSaved {len(result)} region mappings to {OUTPUT_PATH}")
print(f"\n=== STATS ===")
print(f"  Admin-1 overrides applied: {stats['override']}")
print(f"  Country defaults used:     {stats['country_default']}")
print(f"  Missing country code:      {stats['missing_country']}")
print(f"  Unmapped languages:        {stats['missing_language']}")
print(f"\n=== TIER DISTRIBUTION ===")
print(f"  Tier 1 (Well served):      {tier_counts.get(1, 0)}")
print(f"  Tier 2 (Partially served): {tier_counts.get(2, 0)}")
print(f"  Tier 3 (Poorly served):    {tier_counts.get(3, 0)}")
print(f"  Unknown:                   {tier_counts.get('unknown', 0)}")

# Print all overrides for transparency
print(f"\n=== ADMIN-1 OVERRIDES LOG ===")
for key in sorted(ALL_ADMIN1_OVERRIDES.keys()):
    lang = ALL_ADMIN1_OVERRIDES[key]
    tier = LANGUAGE_TIERS.get(lang, 3)
    print(f"  {key}: {lang} → Tier {tier}")
