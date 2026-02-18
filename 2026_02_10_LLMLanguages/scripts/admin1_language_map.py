"""
Comprehensive admin1 → primary spoken language mapping.
Built from Ethnologue, Glottolog, and linguistic survey data.

For each admin1 region, assigns the dominant/primary spoken language
(NOT the official language, NOT the national lingua franca — the language
most people actually speak at home).

If a regional language isn't in the 91-language LanguageBench set,
that's the point: those regions ARE poorly served by LLMs.
"""

# ── Country-level default languages ──────────────────────────────────────────
# Used when no admin1 override exists. This is the primary HOME language.

COUNTRY_LANGUAGE = {
    # Americas
    "US": "English", "CA": "English", "MX": "Spanish", "GT": "Spanish",
    "BZ": "English", "HN": "Spanish", "SV": "Spanish", "NI": "Spanish",
    "CR": "Spanish", "PA": "Spanish", "CU": "Spanish", "JM": "English",
    "HT": "Haitian Creole", "DO": "Spanish", "PR": "Spanish", "TT": "English",
    "BS": "English", "BB": "English", "GD": "English", "AG": "English",
    "DM": "English", "LC": "English", "VC": "English", "KN": "English",
    "CO": "Spanish", "VE": "Spanish", "GY": "English", "SR": "Dutch",
    "EC": "Spanish", "PE": "Spanish", "BO": "Spanish", "PY": "Guarani",
    "UY": "Spanish", "AR": "Spanish", "CL": "Spanish", "BR": "Portuguese",

    # Western Europe
    "GB": "English", "IE": "English", "FR": "French", "DE": "German",
    "AT": "German", "NL": "Dutch", "LU": "French", "IT": "Italian",
    "ES": "Spanish", "PT": "Portuguese", "GR": "Greek", "CY": "Greek",
    "MT": "Maltese", "AD": "Catalan", "MC": "French", "SM": "Italian",
    "VA": "Italian", "LI": "German",

    # Northern Europe
    "DK": "Danish", "SE": "Swedish", "NO": "Norwegian", "FI": "Finnish",
    "IS": "Icelandic", "FO": "Faroese", "GL": "Greenlandic", "AX": "Swedish",

    # Central/Eastern Europe
    "PL": "Polish", "CZ": "Czech", "SK": "Slovak", "HU": "Hungarian",
    "RO": "Romanian", "BG": "Bulgarian", "HR": "Croatian", "SI": "Slovenian",
    "BA": "Bosnian", "RS": "Serbian", "ME": "Serbian", "MK": "Macedonian",
    "AL": "Albanian", "XK": "Albanian",

    # Baltic
    "EE": "Estonian", "LV": "Latvian", "LT": "Lithuanian",

    # Eastern Europe / Caucasus
    "UA": "Ukrainian", "BY": "Belarusian", "MD": "Romanian",
    "GE": "Georgian", "AM": "Armenian", "AZ": "Azerbaijani",

    # Russia (default)
    "RU": "Russian",

    # Turkey / Middle East
    "TR": "Turkish", "IR": "Farsi", "IQ": "Arabic", "SY": "Arabic",
    "JO": "Arabic", "LB": "Arabic", "IL": "Hebrew", "PS": "Arabic",
    "SA": "Arabic", "YE": "Arabic", "OM": "Arabic", "AE": "Arabic",
    "QA": "Arabic", "BH": "Arabic", "KW": "Arabic",

    # Central Asia
    "KZ": "Kazakh", "UZ": "Uzbek", "TM": "Turkmen", "KG": "Kyrgyz",
    "TJ": "Tajik", "AF": "Dari",

    # South Asia
    "IN": "Hindi", "PK": "Urdu", "BD": "Bengali", "LK": "Sinhala",
    "NP": "Nepali", "BT": "Dzongkha", "MV": "Divehi",

    # East Asia
    "CN": "Chinese", "TW": "Chinese", "JP": "Japanese", "KR": "Korean",
    "KP": "Korean", "MN": "Mongolian", "HK": "Cantonese", "MO": "Cantonese",

    # Southeast Asia
    "VN": "Vietnamese", "TH": "Thai", "MM": "Burmese", "LA": "Lao",
    "KH": "Khmer", "MY": "Malay", "SG": "English", "ID": "Indonesian",
    "PH": "Filipino", "BN": "Malay", "TL": "Tetum",

    # North Africa
    "MA": "Arabic", "DZ": "Arabic", "TN": "Arabic", "LY": "Arabic",
    "EG": "Arabic", "SD": "Arabic", "MR": "Arabic", "EH": "Arabic",

    # West Africa
    "SN": "Wolof", "GM": "Mandinka", "GW": "Portuguese Creole", "GN": "Fula",
    "SL": "Krio", "LR": "English", "CI": "Dioula", "ML": "Bambara",
    "BF": "Mossi", "GH": "Twi", "TG": "Ewe", "BJ": "Fon",
    "NE": "Hausa", "NG": "Hausa", "CV": "Cape Verdean Creole",

    # Central Africa
    "CM": "French", "CF": "Sango", "TD": "Arabic", "CG": "Lingala",
    "CD": "Lingala", "GQ": "Fang", "GA": "Fang", "ST": "Portuguese",

    # East Africa
    "ET": "Amharic", "ER": "Tigrinya", "DJ": "Somali", "SO": "Somali",
    "KE": "Swahili", "UG": "Ganda", "RW": "Kinyarwanda",
    "BI": "Kirundi", "TZ": "Swahili", "SS": "Dinka",

    # Southern Africa
    "MZ": "Makhuwa", "MW": "Chichewa", "ZM": "Bemba", "ZW": "Shona",
    "MG": "Malagasy", "KM": "Comorian", "MU": "Mauritian Creole",
    "SC": "Seychellois Creole",
    "ZA": "Zulu", "NA": "Oshiwambo", "BW": "Tswana", "SZ": "Swazi",
    "LS": "Sotho", "AO": "Umbundu",

    # Oceania
    "AU": "English", "NZ": "English", "PG": "Tok Pisin", "FJ": "Fijian",
    "SB": "Solomon Islands Pijin", "VU": "Bislama", "WS": "Samoan",
    "TO": "Tongan", "KI": "Gilbertese", "NR": "Nauruan", "TV": "Tuvaluan",
    "MH": "Marshallese", "FM": "Chuukese", "PW": "Palauan",
    "NC": "French", "PF": "Tahitian", "GU": "Chamorro",

    # Caribbean dependencies
    "CW": "Papiamentu", "SX": "English", "AW": "Papiamento",
    "BL": "French", "MF": "French", "PM": "French", "WF": "Wallisian",
}


# ── Admin1-level language overrides ──────────────────────────────────────────
# ACTUAL home language for each region. If the language isn't in LanguageBench,
# that's fine — the region will correctly show as "poorly served."

ADMIN1_LANGUAGES = {}

# ── INDIA ────────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    # Hindi belt
    "IN-UP": "Hindi", "IN-MP": "Hindi", "IN-RJ": "Hindi", "IN-BR": "Hindi",
    "IN-JH": "Hindi", "IN-CT": "Chhattisgarhi", "IN-HR": "Hindi",
    "IN-HP": "Hindi", "IN-UT": "Hindi", "IN-DL": "Hindi", "IN-CH": "Hindi",
    "IN-AN": "Hindi",
    # Dravidian south
    "IN-TN": "Tamil", "IN-KA": "Kannada", "IN-KL": "Malayalam",
    "IN-AP": "Telugu", "IN-TG": "Telugu", "IN-PY": "Tamil",
    "IN-LD": "Malayalam",
    # Eastern
    "IN-WB": "Bengali", "IN-OR": "Odia", "IN-AS": "Assamese",
    "IN-TR": "Bengali",
    # Western
    "IN-GJ": "Gujarati", "IN-MH": "Marathi", "IN-GA": "Konkani",
    "IN-DH": "Gujarati",
    # Punjab
    "IN-PB": "Punjabi",
    # Northeast — use plurality home language
    "IN-NL": "Naga",     # Nagaland: 16+ Naga languages; Konyak largest (~17%)
    "IN-MN": "Meitei",   # ~53% Meitei
    "IN-MZ": "Mizo",     # ~87% Mizo
    "IN-ML": "Khasi",    # ~48% Khasi — clear plurality
    "IN-AR": "Nishi",    # Arunachal: Nyishi largest tribe (~20-25%)
    "IN-SK": "Nepali",   # ~63% Nepali
    # Kashmir/Ladakh
    "IN-JK": "Urdu", "IN-LA": "Ladakhi",
})

# ── CHINA ────────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "CN-GD": "Cantonese",
    "CN-XZ": "Tibetan",
    "CN-XJ": "Chinese",     # Xinjiang: Uyghur ~45%, Han ~42%, below 50% threshold
    "CN-NM": "Chinese",     # Inner Mongolia: Mongolian ~17%, Han ~79%
    "CN-FJ": "Chinese",     # Fujian: Min Nan ~45-50%, fragmented; Mandarin majority
    "CN-SH": "Chinese",     # Shanghai: Wu ~40-45%, Mandarin majority from migration
    "CN-ZJ": "Wu Chinese",  # Zhejiang: Wu ~75%+
    "CN-GX": "Chinese",     # Guangxi: Zhuang ~33%, Han ~62%
    "CN-YN": "Chinese",     # Extremely diverse but Mandarin dominant
    "CN-GZ": "Chinese",     # Miao/Dong minorities, Mandarin dominant
    "CN-QH": "Chinese",     # Tibetan/Hui minorities
    "CN-HI": "Chinese",     # Hainan — local Min dialect
    "CN-JL": "Chinese",     # Some Korean minority areas
    "CN-BJ": "Chinese", "CN-TJ": "Chinese", "CN-HE": "Chinese",
    "CN-SX": "Chinese", "CN-LN": "Chinese",
    "CN-HL": "Chinese", "CN-JS": "Chinese", "CN-AH": "Chinese",
    "CN-JX": "Chinese", "CN-SD": "Chinese", "CN-HA": "Chinese",
    "CN-HB": "Chinese", "CN-HN": "Chinese",
    "CN-CQ": "Chinese", "CN-SC": "Chinese", "CN-GS": "Chinese",
    "CN-NX": "Chinese", "CN-SN": "Chinese",
})

# ── RUSSIA ───────────────────────────────────────────────────────────────────
# Assign ACTUAL titular/majority language for each republic
ADMIN1_LANGUAGES.update({
    # Caucasus — titular ≥50% of population → keep ethnic language
    "RU-CE": "Chechen",     # ~95% Chechen
    "RU-IN": "Ingush",      # ~94% Ingush
    "RU-DA": "Avar",        # ~80% non-Russian (Avar largest group)
    "RU-KB": "Kabardian",   # ~57% Kabardian+Balkar
    "RU-KC": "Russian",     # Karachay-Cherkessia: ~41% Karachay, ~32% Russian
    "RU-SE": "Ossetian",    # ~65% Ossetian
    "RU-KL": "Kalmyk",      # ~57% Kalmyk
    # Caucasus — titular <50% → Russian
    "RU-AD": "Russian",     # Adygea: ~25% Adyghe
    # Volga-Ural — titular ≥50%
    "RU-TA": "Tatar",       # ~53% Tatar
    "RU-CU": "Chuvash",     # ~67% Chuvash
    # Volga-Ural — titular <50% → Russian
    "RU-BA": "Russian",     # Bashkortostan: ~30% Bashkir
    "RU-ME": "Russian",     # Mari El: ~43% Mari
    "RU-MO": "Russian",     # Mordovia: ~40% Mordvin
    "RU-UD": "Russian",     # Udmurtia: ~28% Udmurt
    # Siberian — titular ≥50%
    "RU-TY": "Tuvan",       # ~82% Tuvan
    "RU-SA": "Yakut",       # ~50% Yakut
    # Siberian — titular <50% → Russian
    "RU-BU": "Russian",     # Buryatia: ~30% Buryat
    "RU-AL": "Russian",     # Altai Republic: ~34% Altai
    "RU-KK": "Russian",     # Khakassia: ~12% Khakas
    # Finno-Ugric — titular <50% → Russian
    "RU-KO": "Russian",     # Komi: ~24% Komi
    "RU-KR": "Russian",     # Karelia: ~7% Karelian
    # Far North/East — titular <50% → Russian
    "RU-CHU": "Russian",    # Chukotka: ~25% Chukchi
    "RU-NEN": "Russian",    # Nenets AO: ~18% Nenets
    "RU-YAN": "Russian",    # Yamal-Nenets: ~6% Nenets
    "RU-KHM": "Russian",    # Khanty-Mansi: ~2% Khanty
    "RU-YEV": "Russian",    # Jewish AO — Russian spoken
    # All regular oblasts/krais → Russian (country default)
})

# ── NIGERIA ──────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    # Hausa-dominant north
    "NG-KN": "Hausa", "NG-KT": "Hausa", "NG-SO": "Hausa", "NG-ZA": "Hausa",
    "NG-JI": "Hausa", "NG-YO": "Hausa", "NG-BA": "Hausa",
    "NG-GO": "Hausa", "NG-KE": "Hausa", "NG-KD": "Hausa", "NG-NI": "Hausa",
    "NG-AD": "Hausa", "NG-FC": "Hausa", "NG-NA": "Hausa", "NG-TA": "Hausa",
    "NG-PL": "Hausa",
    # Kanuri northeast
    "NG-BO": "Kanuri",      # NOT in LB
    # Yoruba southwest
    "NG-OY": "Yoruba", "NG-OG": "Yoruba", "NG-ON": "Yoruba",
    "NG-OS": "Yoruba", "NG-EK": "Yoruba", "NG-LA": "Yoruba",
    "NG-KW": "Yoruba", "NG-KO": "Yoruba",
    # Igbo southeast
    "NG-AN": "Igbo", "NG-EN": "Igbo", "NG-EB": "Igbo",
    "NG-IM": "Igbo", "NG-AB": "Igbo",
    # Niger Delta — various minority languages, Nigerian Pidgin as lingua franca
    "NG-RI": "Nigerian Pidgin", "NG-BY": "Ijaw",  # NOT in LB
    "NG-CR": "Efik",        # NOT in LB
    "NG-AK": "Ibibio",      # NOT in LB
    "NG-ED": "Edo",          # NOT in LB
    "NG-DE": "Urhobo",       # NOT in LB
    # Benue
    "NG-BE": "Tiv",          # NOT in LB
})

# ── ETHIOPIA ─────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "ET-AM": "Amharic", "ET-AA": "Amharic", "ET-BE": "Amharic",
    "ET-OR": "Oromo", "ET-GA": "Oromo",
    "ET-TI": "Tigrinya",
    "ET-SO": "Somali",
    "ET-AF": "Afar",
    "ET-SN": "Sidama",      # SNNPR — Sidama is largest, NOT in LB
    "ET-HA": "Oromo",       # Harari region: ~55% Oromo, ~7% Harari
    "ET-DD": "Oromo",       # Dire Dawa — Oromo plurality
})

# ── PAKISTAN ──────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "PK-PB": "Punjabi",
    "PK-SD": "Sindhi",
    "PK-KP": "Pashto",
    "PK-BA": "Balochi",     # NOT in LB → correctly Tier 3
    "PK-IS": "Urdu",
    "PK-GB": "Shina",       # NOT in LB
    "PK-JK": "Kashmiri",    # NOT in LB
    "PK-TA": "Pashto",
})

# ── INDONESIA ────────────────────────────────────────────────────────────────
# Assign actual regional languages, not Indonesian lingua franca
ADMIN1_LANGUAGES.update({
    # Java
    "ID-JT": "Javanese", "ID-JI": "Javanese", "ID-YO": "Javanese",
    "ID-JB": "Sundanese", "ID-BT": "Sundanese",
    "ID-JK": "Indonesian",  # Jakarta — cosmopolitan, Indonesian at home
    # Sumatra — actual home languages where >50%
    "ID-AC": "Acehnese",    # ~55% Acehnese — NOT in LB
    "ID-SU": "Indonesian",  # N. Sumatra: Batak ~45% but fragmented (Toba/Karo/etc)
    "ID-SB": "Minangkabau", # ~85% Minangkabau — NOT in LB
    "ID-RI": "Malay",
    "ID-SS": "Indonesian",  # S. Sumatra: diverse, Musi Malay <50%
    "ID-BE": "Indonesian",  # Bengkulu: Rejang ~30-35%
    "ID-JA": "Malay",
    "ID-LA": "Indonesian",  # Lampung: Lampungese ~12-15%, Javanese ~60%
    "ID-BB": "Malay",
    "ID-KR": "Malay",
    # Kalimantan
    "ID-KB": "Malay",       # West — Malay variant
    "ID-KS": "Banjarese",   # ~75% Banjar — NOT in LB
    "ID-KT": "Indonesian",  # E. Kalimantan: Dayak ~20-25%
    "ID-KI": "Indonesian",  # N. Kalimantan: diverse, no majority
    # Sulawesi
    "ID-SA": "Indonesian",  # N. Sulawesi: Minahasan fragmented, Manado Malay lingua franca
    "ID-SN": "Indonesian",  # S. Sulawesi: Makassarese ~25%, Buginese ~45%
    "ID-ST": "Indonesian",  # C. Sulawesi: Kaili ~25-30%
    "ID-SG": "Indonesian",  # SE Sulawesi: Tolaki ~25-30%
    "ID-SR": "Indonesian",  # W. Sulawesi: Mandar ~40-50%, borderline
    "ID-GO": "Gorontalo",   # ~75% Gorontalo — NOT in LB
    # Bali / Nusa Tenggara
    "ID-BA": "Balinese",    # ~85% Balinese — NOT in LB
    "ID-NB": "Sasak",       # ~85% Sasak — NOT in LB
    "ID-NT": "Indonesian",  # E. Nusa Tenggara: 40+ languages, no majority
    # Maluku / Papua
    "ID-MA": "Indonesian",  # Maluku: diverse, Indonesian lingua franca
    "ID-MU": "Indonesian",  # N. Maluku: diverse
    "ID-PA": "Indonesian",  # Papua: 200+ languages, Indonesian lingua franca
    "ID-PB": "Indonesian",  # W. Papua: same
})

# ── PHILIPPINES ──────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    # Metro Manila + Central/Southern Luzon — Filipino/Tagalog
    "PH-MNL": "Filipino", "PH-CAV": "Filipino", "PH-LAG": "Filipino",
    "PH-BTG": "Filipino", "PH-RIZ": "Filipino", "PH-BUL": "Filipino",
    "PH-PAM": "Kapampangan", "PH-NUE": "Filipino", "PH-TAR": "Filipino",
    "PH-ZMB": "Filipino", "PH-AUR": "Filipino", "PH-BAN": "Filipino",
    "PH-QUE": "Filipino", "PH-MAD": "Filipino", "PH-MDC": "Filipino",
    "PH-MDR": "Filipino", "PH-ROM": "Filipino", "PH-PLW": "Filipino",
    # Ilocos / Northern Luzon — Ilocano (NOT in LB)
    "PH-ILN": "Ilocano", "PH-ILS": "Ilocano", "PH-PAN": "Pangasinan",
    "PH-LUN": "Ilocano", "PH-CAG": "Ilocano", "PH-ISA": "Ilocano",
    "PH-NUV": "Ilocano", "PH-QUI": "Ilocano",
    "PH-ABR": "Ilocano", "PH-APA": "Ilocano",
    # Cordillera — Igorot languages (NOT in LB)
    "PH-BEN": "Ibaloi", "PH-IFU": "Ifugao", "PH-KAL": "Kalinga",
    "PH-MOU": "Kankanaey", "PH-BTN": "Ivatan",
    # Bicol region — Bicolano (NOT in LB)
    "PH-CAN": "Bicolano", "PH-CAS": "Bicolano", "PH-ALB": "Bicolano",
    "PH-SOR": "Bicolano", "PH-CAT": "Bicolano", "PH-MAS": "Bicolano",
    # Visayas — Cebuano
    "PH-CEB": "Cebuano", "PH-BOH": "Cebuano", "PH-SIG": "Cebuano",
    "PH-NER": "Cebuano", "PH-LEY": "Waray",  # Eastern Visayas — Waray (NOT in LB)
    "PH-BIL": "Waray", "PH-SLE": "Waray",
    "PH-EAS": "Waray", "PH-NSA": "Waray", "PH-WSA": "Waray",
    # Western Visayas — Hiligaynon (NOT in LB)
    "PH-ILI": "Hiligaynon", "PH-AKL": "Aklanon", "PH-ANT": "Kinaray-a",
    "PH-CAP": "Hiligaynon", "PH-GUI": "Hiligaynon",
    "PH-NEC": "Hiligaynon",
    # Mindanao — Cebuano in north/east
    "PH-AGN": "Cebuano", "PH-AGS": "Cebuano", "PH-SUN": "Cebuano",
    "PH-SUR": "Cebuano", "PH-BUK": "Cebuano", "PH-CAM": "Cebuano",
    "PH-MSR": "Cebuano", "PH-MSC": "Cebuano", "PH-LAN": "Cebuano",
    "PH-DAV": "Cebuano", "PH-DAS": "Cebuano", "PH-DAO": "Cebuano",
    "PH-COM": "Cebuano", "PH-SCO": "Cebuano", "PH-SAR": "Cebuano",
    # Moro areas — Maguindanaon/Tausug/Maranao (NOT in LB)
    "PH-MAG": "Maguindanaon", "PH-LAS": "Maranao",
    "PH-NCO": "Cebuano",  # N. Cotabato: Cebuano settler majority
    "PH-SUK": "Maguindanaon",
    "PH-BAS": "Yakan", "PH-SLU": "Tausug", "PH-TAW": "Tausug",
    # Zamboanga — Chavacano (NOT in LB)
    "PH-ZAN": "Cebuano",    # Zamboanga del Norte: Cebuano majority
    "PH-ZAS": "Cebuano",    # Zamboanga del Sur: Cebuano majority
    "PH-ZSI": "Subanen",
    # Cities
    "PH-BCD": "Hiligaynon", "PH-LAP": "Cebuano", "PH-MDE": "Cebuano",
})

# ── TURKEY ───────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    # Kurdish-majority provinces (Kurmanji Kurdish)
    "TR-21": "Kurdish", "TR-30": "Kurdish", "TR-56": "Kurdish",
    "TR-73": "Kurdish", "TR-72": "Kurdish", "TR-49": "Kurdish",
    "TR-13": "Kurdish", "TR-65": "Kurdish", "TR-12": "Kurdish",
    "TR-62": "Kurdish", "TR-04": "Kurdish", "TR-76": "Kurdish",
    "TR-47": "Kurdish", "TR-63": "Kurdish",
    # Zaza-speaking areas
    "TR-62": "Zaza",  # Tunceli — Zaza NOT in LB
})

# ── IRAQ ─────────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "IQ-AR": "Kurdish", "IQ-DA": "Kurdish",
    "IQ-SU": "Kurdish", "IQ-TS": "Kurdish",
})

# ── IRAN ─────────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "IR-01": "Azerbaijani", "IR-02": "Azerbaijani",
    "IR-03": "Azerbaijani", "IR-04": "Azerbaijani",
    "IR-16": "Kurdish", "IR-17": "Kurdish", "IR-05": "Kurdish",
    "IR-10": "Arabic",
    "IR-13": "Balochi",  # NOT in LB
})

# ── AFGHANISTAN ──────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    # Pashto south and east
    "AF-KAN": "Pashto", "AF-HEL": "Pashto", "AF-ZAB": "Pashto",
    "AF-URU": "Pashto", "AF-PKA": "Pashto", "AF-PIA": "Pashto",
    "AF-KHO": "Pashto", "AF-NAN": "Pashto", "AF-LAG": "Pashto",
    "AF-KNR": "Pashto", "AF-NUR": "Nuristani",  # NOT in LB
    "AF-LOG": "Pashto", "AF-WAR": "Pashto", "AF-GHA": "Pashto",
    # Dari north and west
    "AF-KAB": "Persian", "AF-HER": "Persian", "AF-BAL": "Persian",
    "AF-BAM": "Hazaragi",  # NOT in LB (Hazara dialect of Persian)
    "AF-PAR": "Persian", "AF-KAP": "Persian",
    "AF-BGL": "Persian", "AF-TAK": "Persian", "AF-BDS": "Persian",
    "AF-KDZ": "Persian", "AF-SAM": "Persian", "AF-GHO": "Persian",
    "AF-FRA": "Persian", "AF-NIM": "Balochi",  # NOT in LB
    # Uzbek/Turkmen north
    "AF-JOW": "Uzbek", "AF-FYB": "Uzbek", "AF-SAR": "Uzbek",
    "AF-BDG": "Persian",
})

# ── UKRAINE ──────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "UA-09": "Russian",  # Luhansk
    "UA-14": "Russian",  # Donetsk
    "UA-40": "Russian",  # Sevastopol
    "UA-43": "Russian",  # Crimea
})

# ── SWITZERLAND ──────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "CH-GE": "French", "CH-VD": "French", "CH-NE": "French",
    "CH-JU": "French", "CH-FR": "French", "CH-VS": "French",
    "CH-TI": "Italian",
    "CH-GR": "German",   # Graubünden: Romansh ~14%, German ~75%
    "CH-ZH": "German", "CH-BE": "German", "CH-LU": "German",
    "CH-UR": "German", "CH-SZ": "German", "CH-OW": "German",
    "CH-NW": "German", "CH-GL": "German", "CH-ZG": "German",
    "CH-SO": "German", "CH-BS": "German", "CH-BL": "German",
    "CH-SH": "German", "CH-AR": "German", "CH-AI": "German",
    "CH-SG": "German", "CH-AG": "German", "CH-TG": "German",
})

# ── BELGIUM ──────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "BE-VAN": "Dutch", "BE-VBR": "Dutch", "BE-VLI": "Dutch",
    "BE-VOV": "Dutch", "BE-VWV": "Dutch",
    "BE-WBR": "French", "BE-WHT": "French", "BE-WLG": "French",
    "BE-WLX": "French", "BE-WNA": "French",
    "BE-BRU": "French",
})

# ── SPAIN ────────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "ES-B": "Catalan", "ES-GI": "Catalan", "ES-L": "Catalan", "ES-T": "Catalan",
    "ES-PM": "Catalan",
    "ES-V": "Spanish", "ES-A": "Spanish", "ES-CS": "Spanish",  # Valencia: ~35-40% Valencian
    "ES-SS": "Basque",  # Gipuzkoa: ~50% Basque
    "ES-BI": "Spanish", "ES-VI": "Spanish",  # Bizkaia ~25%, Álava ~15% Basque
    "ES-C": "Galician", "ES-LU": "Galician", "ES-OR": "Galician", "ES-PO": "Galician",
})

# ── CANADA ───────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "CA-QC": "French",
    "CA-NU": "Inuktitut",  # NOT in LB
})

# ── DRC ──────────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "CD-KN": "Lingala", "CD-EQ": "Lingala", "CD-BN": "Lingala",
    "CD-OR": "Lingala",
    "CD-NK": "Swahili", "CD-SK": "Swahili", "CD-MA": "Swahili",
    "CD-KA": "Swahili",
    "CD-BC": "Kikongo",
    "CD-KE": "Tshiluba", "CD-KW": "Tshiluba",
})

# ── SOUTH AFRICA ─────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "ZA-NL": "Zulu", "ZA-EC": "Xhosa", "ZA-WC": "Afrikaans",
    "ZA-NC": "Afrikaans", "ZA-GT": "Zulu", "ZA-FS": "Sotho",
    "ZA-NW": "Tswana", "ZA-LP": "Northern Sotho",  # Sepedi, NOT in LB
    "ZA-MP": "Swazi",
})

# ── CAMEROON ─────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "CM-NW": "Pidgin English", "CM-SW": "Pidgin English",  # NOT in LB
    "CM-CE": "French",      # Centre: Ewondo ~30-35%, French dominant in Yaoundé
    "CM-LT": "French",      # Littoral: Douala ~15-20%, French dominant in Douala
    "CM-OU": "French",      # Ouest: Ghomala ~20-25%, diverse Bamileke groups
    "CM-SU": "Bulu",        # NOT in LB
    "CM-ES": "French",
    "CM-AD": "Fulfulde",    # NOT in LB
    "CM-NO": "Fulfulde",    # NOT in LB
    "CM-EN": "Fulfulde",    # NOT in LB
})

# ── MYANMAR ──────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "MM-01": "Burmese",  # Sagaing — Burmese
    "MM-02": "Burmese",  # Bago
    "MM-03": "Burmese",  # Magway
    "MM-04": "Burmese",  # Mandalay
    "MM-05": "Burmese",  # Tanintharyi
    "MM-06": "Burmese",  # Yangon
    "MM-07": "Burmese",  # Ayeyarwady
    "MM-11": "Kachin",   # NOT in LB
    "MM-12": "Karen",    # NOT in LB
    "MM-13": "Karen",    # NOT in LB
    "MM-14": "Chin",     # NOT in LB
    "MM-15": "Burmese",  # Mon State: ~30-35% Mon, Burmese majority
    "MM-16": "Rakhine",  # NOT in LB
    "MM-17": "Shan",     # NOT in LB
})

# ── SRI LANKA ────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "LK-41": "Tamil", "LK-42": "Tamil", "LK-43": "Tamil",
    "LK-44": "Tamil", "LK-45": "Tamil",
    "LK-51": "Tamil", "LK-52": "Tamil", "LK-53": "Tamil",
})

# ── NEPAL ────────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "NP-JA": "Maithili", "NP-SA": "Nepali", "NP-KO": "Nepali",
    "NP-ME": "Nepali",   # Province 1: Limbu ~10-15%, Nepali ~50%+
})

# ── THAILAND ─────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    # Deep south — Pattani Malay
    "TH-94": "Pattani Malay", "TH-95": "Pattani Malay", "TH-96": "Pattani Malay",
    # Isan northeast — Isan/Lao
    "TH-30": "Isan", "TH-31": "Isan", "TH-32": "Isan", "TH-33": "Isan",
    "TH-34": "Isan", "TH-35": "Isan", "TH-36": "Isan", "TH-37": "Isan",
    "TH-38": "Isan", "TH-39": "Isan", "TH-40": "Isan", "TH-41": "Isan",
    "TH-42": "Isan", "TH-43": "Isan", "TH-44": "Isan", "TH-45": "Isan",
    "TH-46": "Isan", "TH-47": "Isan", "TH-48": "Isan", "TH-49": "Isan",
    # Northern Thai — Kam Muang
    "TH-50": "Northern Thai", "TH-51": "Northern Thai", "TH-52": "Northern Thai",
    "TH-53": "Northern Thai", "TH-54": "Northern Thai", "TH-55": "Northern Thai",
    "TH-56": "Northern Thai", "TH-57": "Northern Thai", "TH-58": "Northern Thai",
})

# ── MOROCCO ──────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "MA-13": "Tashelhit",   # NOT in LB — Souss Berber
    "MA-03": "Tarifit",     # NOT in LB — Rif Berber
    "MA-06": "Tamazight",   # NOT in LB — Middle Atlas
})

# ── ALGERIA ──────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "DZ-15": "Kabyle",      # NOT in LB
    "DZ-06": "Kabyle",
    "DZ-10": "Kabyle",
    "DZ-35": "Kabyle",
    "DZ-11": "Tamasheq",    # Tamanghasset — Tuareg, NOT in LB
    "DZ-33": "Tamasheq",    # Illizi — Tuareg
    "DZ-47": "Mzab",        # Ghardaia — Mzab Berber, NOT in LB
})

# ── KENYA ────────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "KE-500": "Somali",
    "KE-600": "Dholuo",     # Nyanza — Luo language, NOT in LB
    "KE-800": "Luhya",      # Western — Luhya languages, NOT in LB
    "KE-200": "Kikuyu",     # Central — Kikuyu
})

# ── UGANDA ───────────────────────────────────────────────────────────────────
# Very diverse; Ganda in central, Luo in north, etc.
# Many districts — use regional groupings
for code in ["UG-101", "UG-102", "UG-103", "UG-104", "UG-105", "UG-106",
             "UG-107", "UG-108", "UG-109", "UG-110", "UG-111", "UG-112",
             "UG-113", "UG-114", "UG-115", "UG-116", "UG-117", "UG-118",
             "UG-119", "UG-120", "UG-121", "UG-122", "UG-123", "UG-124"]:
    ADMIN1_LANGUAGES[code] = "Ganda"  # Central region — Luganda
for code in ["UG-201", "UG-202", "UG-203", "UG-204", "UG-205", "UG-206",
             "UG-207", "UG-208", "UG-209", "UG-210", "UG-211", "UG-212",
             "UG-213", "UG-214", "UG-215", "UG-216", "UG-217", "UG-218",
             "UG-219", "UG-220", "UG-221", "UG-222", "UG-223", "UG-224",
             "UG-225", "UG-226", "UG-227", "UG-228", "UG-229", "UG-230",
             "UG-231", "UG-232"]:
    ADMIN1_LANGUAGES[code] = "Lusoga"  # Eastern — NOT in LB
for code in ["UG-301", "UG-302", "UG-303", "UG-304", "UG-305", "UG-306",
             "UG-307", "UG-308", "UG-309", "UG-310", "UG-311", "UG-312",
             "UG-313", "UG-314", "UG-315", "UG-316", "UG-317", "UG-318",
             "UG-319", "UG-320", "UG-321", "UG-322", "UG-323", "UG-324",
             "UG-325", "UG-326", "UG-327", "UG-328", "UG-329", "UG-330",
             "UG-331"]:
    ADMIN1_LANGUAGES[code] = "Acholi"  # Northern — NOT in LB
for code in ["UG-401", "UG-402", "UG-403", "UG-404", "UG-405", "UG-406",
             "UG-407", "UG-408", "UG-409", "UG-410", "UG-411", "UG-412",
             "UG-413", "UG-414", "UG-415", "UG-416", "UG-417", "UG-419",
             "UG-420", "UG-421", "UG-422", "UG-423", "UG-424", "UG-425"]:
    ADMIN1_LANGUAGES[code] = "Runyankole"  # Western — NOT in LB

# ── TANZANIA ─────────────────────────────────────────────────────────────────
# Swahili is universal lingua franca, but home languages vary
ADMIN1_LANGUAGES.update({
    "TZ-06": "Swahili",     # Pemba — Swahili ~95%+
    "TZ-07": "Swahili",     # Unguja — Swahili ~95%+
    "TZ-10": "Swahili",     # Pemba South
    "TZ-11": "Swahili",     # Zanzibar South
    "TZ-15": "Swahili",     # Zanzibar West
    # Mainland — various Bantu languages, Swahili as lingua franca
    "TZ-09": "Chagga",      # Kilimanjaro — NOT in LB
    "TZ-13": "Kuria",       # Mara — NOT in LB
    "TZ-18": "Sukuma",      # Mwanza — NOT in LB (largest ethnic group)
    "TZ-22": "Sukuma",      # Shinyanga
    "TZ-30": "Sukuma",      # Simiyu
})

# ── GHANA ────────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "GH-NP": "Dagbani",     # Northern — NOT in LB
    "GH-UE": "Frafra",      # Upper East — NOT in LB
    "GH-UW": "Dagaare",     # Upper West — NOT in LB
    "GH-TV": "Ewe",         # Volta
    "GH-AH": "Twi",         # Ashanti
    "GH-AA": "Ga",          # Greater Accra — NOT in LB
})

# ── MALI ─────────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "ML-6": "Songhai",      # Timbuktu — NOT in LB
    "ML-7": "Songhai",      # Gao
    "ML-8": "Tamasheq",     # Kidal — Tuareg, NOT in LB
    "ML-3": "Senufo",       # Sikasso — NOT in LB
    "ML-5": "Fulfulde",     # Mopti — NOT in LB
})

# ── SENEGAL ──────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "SN-ZG": "Jola",        # Ziguinchor/Casamance — NOT in LB
    "SN-KD": "Fulfulde",    # Kolda — NOT in LB
    "SN-SE": "Jola",        # Sédhiou — NOT in LB
    "SN-MT": "Pulaar",      # Matam — NOT in LB
    "SN-SL": "Pulaar",      # Saint-Louis — Fula variant
})

# ── BURKINA FASO ─────────────────────────────────────────────────────────────
# Mossi (Mooré) dominant in center; many other languages in periphery
ADMIN1_LANGUAGES.update({
    "BF-SEN": "Fulfulde",   # Séno — NOT in LB
    "BF-OUD": "Fulfulde",   # Oudalan
    "BF-SOM": "Fulfulde",   # Soum
    "BF-KEN": "Senufo",     # Kénédougou — NOT in LB
    "BF-LER": "Senufo",     # Léraba
    "BF-COM": "Lobi",       # Komoé — NOT in LB
})

# ── ZIMBABWE ─────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "ZW-MN": "Ndebele",     # NOT in LB (close to Zulu but distinct)
    "ZW-MS": "Ndebele",
    "ZW-BU": "Ndebele",
})

# ── MOZAMBIQUE ───────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "MZ-N": "Makhuwa",      # NOT in LB
    "MZ-P": "Makonde",      # NOT in LB
    "MZ-Q": "Lomwe",        # NOT in LB
    "MZ-S": "Sena",         # NOT in LB
    "MZ-B": "Shona",        # Manica — Shona variant
    "MZ-T": "Nyungwe",      # NOT in LB
    "MZ-G": "Tsonga",       # NOT in LB
    "MZ-I": "Tsonga",       # NOT in LB
    "MZ-L": "Tsonga",       # Maputo
    "MZ-A": "Yao",          # Niassa — NOT in LB
})

# ── ZAMBIA ───────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "ZM-01": "Lozi",        # Western — NOT in LB
    "ZM-03": "Chewa",       # Eastern — Chichewa variant
    "ZM-04": "Bemba",       # Luapula
    "ZM-05": "Bemba",       # Northern
    "ZM-06": "Kaonde",      # North-Western — NOT in LB
    "ZM-07": "Tonga",       # Southern — NOT in LB
    "ZM-10": "Bemba",       # Muchinga
})

# ── PERU ─────────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "PE-CUS": "Quechua",   # ~55% Quechua
    "PE-APU": "Quechua",   # ~70% Quechua
    "PE-AYA": "Quechua",   # ~60% Quechua
    "PE-HUV": "Quechua",   # ~60-65% Quechua
    "PE-PUN": "Aymara",    # Puno — Aymara ~50%+
    "PE-HUC": "Quechua",   # ~50%+ Quechua
    "PE-ANC": "Spanish",   # Ancash: Quechua ~30-35%, Spanish majority
})

# ── BOLIVIA ──────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "BO-L": "Aymara",
    "BO-C": "Quechua", "BO-H": "Quechua",
    "BO-P": "Quechua",   # ~55-60% Quechua
    "BO-O": "Spanish",   # Oruro: Quechua ~35-40%, Spanish ~40-45%
})

# ── GUATEMALA ────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "GT-QC": "K'iche'",        # NOT in LB
    "GT-SO": "Kaqchikel",      # NOT in LB
    "GT-HU": "Mam",            # NOT in LB
    "GT-TO": "K'iche'",        # NOT in LB
    "GT-AV": "Q'eqchi'",       # NOT in LB
    "GT-CM": "Kaqchikel",      # NOT in LB
    "GT-QZ": "K'iche'",        # NOT in LB
    "GT-BV": "Achi",           # NOT in LB
    "GT-SM": "Mam",            # NOT in LB
})

# ── CHAD ─────────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "TD-LO": "Sara",  # NOT in LB
    "TD-LR": "Sara", "TD-MA": "Sara", "TD-MC": "Sara",
    "TD-ME": "Sara", "TD-MO": "Sara", "TD-TA": "Sara",
    "TD-ND": "Arabic",  # N'Djamena — Chadian Arabic
})

# ── MADAGASCAR ───────────────────────────────────────────────────────────────
# Malagasy everywhere (default handles it)

# ── SUDAN ────────────────────────────────────────────────────────────────────
ADMIN1_LANGUAGES.update({
    "SD-DE": "Fur",          # Central Darfur: Fur ~60%+ — NOT in LB
    "SD-DN": "Arabic",       # North Darfur: diverse, Arabic lingua franca
    "SD-DS": "Arabic",       # South Darfur: Arab groups significant, Arabic dominant
    "SD-DW": "Masalit",      # West Darfur — NOT in LB
    "SD-KS": "Nuba",         # South Kordofan — NOT in LB
    "SD-NB": "Funj",         # Blue Nile — NOT in LB
})

# ── SOUTH SUDAN ──────────────────────────────────────────────────────────────
# (handled by country default = Dinka)


def get_language_for_region(iso_code, iso2, name):
    """Get the primary spoken language for an admin1 region."""
    if iso_code and iso_code in ADMIN1_LANGUAGES:
        return ADMIN1_LANGUAGES[iso_code]
    if iso2 and iso2 in COUNTRY_LANGUAGE:
        return COUNTRY_LANGUAGE[iso2]
    return None
