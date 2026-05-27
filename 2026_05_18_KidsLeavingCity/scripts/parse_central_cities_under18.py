"""
Parse NHGIS place-level extract → under-18 totals per central city per decade.

For each of the top-50 1950-SMA central cities (60 city-name entries since some SMAs
have multiple central cities), sum under-18 ages from the place-level data.

Matching: by state + place name (PLACE column), case-insensitive.

Output:
  data/under18_central_cities.csv  (year, place_name, state, under18)
"""
from pathlib import Path
import pandas as pd
import duckdb

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
NHGIS = DATA / "nhgis_place_raw" / "nhgis0124_csv"

# Central city lookup: (state_fips_2, place_name, sma_code) — full 196-city version
lookup = pd.read_csv(DATA / "central_city_place_fips_all172.csv", dtype=str)

# State FIPS to state name (Census standard)
STATE_FIPS_TO_NAME = {
    "01": "Alabama", "02": "Alaska", "04": "Arizona", "05": "Arkansas",
    "06": "California", "08": "Colorado", "09": "Connecticut", "10": "Delaware",
    "11": "District Of Columbia", "12": "Florida", "13": "Georgia", "15": "Hawaii",
    "16": "Idaho", "17": "Illinois", "18": "Indiana", "19": "Iowa",
    "20": "Kansas", "21": "Kentucky", "22": "Louisiana", "23": "Maine",
    "24": "Maryland", "25": "Massachusetts", "26": "Michigan", "27": "Minnesota",
    "28": "Mississippi", "29": "Missouri", "30": "Montana", "31": "Nebraska",
    "32": "Nevada", "33": "New Hampshire", "34": "New Jersey", "35": "New Mexico",
    "36": "New York", "37": "North Carolina", "38": "North Dakota", "39": "Ohio",
    "40": "Oklahoma", "41": "Oregon", "42": "Pennsylvania", "44": "Rhode Island",
    "45": "South Carolina", "46": "South Dakota", "47": "Tennessee", "48": "Texas",
    "49": "Utah", "50": "Vermont", "51": "Virginia", "53": "Washington",
    "54": "West Virginia", "55": "Wisconsin", "56": "Wyoming",
    "72": "Puerto Rico",
}
lookup["state_name"] = lookup["state_fips"].map(STATE_FIPS_TO_NAME)

# Strip state-disambiguation suffix from central city name
lookup["central_city"] = lookup["central_city"].str.replace(r" (MO|KS|IN|VA|MA|RI|NY|NJ|PA|CT|OH|IL|WI|MN|TX|GA|KY|LA|TN|WA|OR|CA|MD|AL|DC|CO|FL|MI)$", "", regex=True)

# Per-city alias patterns for cities with non-standard place names (consolidated city-counties)
ALIASES = {
    "Indianapolis": [
        "Indianapolis", "Indianapolis city", "Indianapolis (remainder)",
        "Indianapolis city (remainder)", "Indianapolis city (balance)",
    ],
    "Louisville": [
        "Louisville", "Louisville city",
        "Louisville/Jefferson County metro government (balance)",
    ],
    "Nashville": [
        "Nashville", "Nashville city",
        "Nashville-Davidson metropolitan government (balance)",
        "Nashville-Davidson (balance)",
        "Nashville-Davidson metropolitan government",
    ],
    "Lexington": [
        "Lexington", "Lexington city",
        "Lexington-Fayette urban county",
        "Lexington-Fayette",
        "Lexington-Fayette urban county government",
    ],
    "Jacksonville": [
        "Jacksonville", "Jacksonville city",
        "Jacksonville (balance)",
    ],
    "Augusta": [
        "Augusta", "Augusta city",
        "Augusta-Richmond County consolidated government (balance)",
        "Augusta-Richmond County",
    ],
    "Columbus": [
        "Columbus", "Columbus city", "Columbus city (balance)",
    ],
    "Macon": [
        "Macon", "Macon city",
        "Macon-Bibb County",
        "Macon-Bibb County (balance)",
    ],
    "Honolulu": [
        "Honolulu", "Honolulu CDP", "Urban Honolulu CDP", "Urban Honolulu",
    ],
    "Greensboro-High Point": [
        "Greensboro", "Greensboro city",
    ],
    "San Juan": [
        "San Juan", "San Juan zona urbana", "San Juan municipio",
    ],
    "Ponce": [
        "Ponce", "Ponce zona urbana",
    ],
    "Mayaguez": [
        "Mayaguez", "Mayagüez", "Mayagüez zona urbana", "Mayaguez zona urbana",
    ],
    "Rio Piedras": [
        "Rio Piedras", "Río Piedras", "San Juan", "San Juan zona urbana",
    ],
}

# Per-decade: (file, age_columns_under18_function returning list of cols)
def age_cols_1980():
    # Male: C68001-C68011 (under1, 1-2, 3-4, 5, 6, 7-9, 10-13, 14, 15, 16, 17)
    # Female: C68027-C68037
    return [f"C68{n:03d}" for n in range(1, 12)] + [f"C68{n:03d}" for n in range(27, 38)]


def age_cols_1990():
    # ET4 = Race × Sex × Age. Under-18 = first 12 ages of each Race-Sex block.
    # Starting offsets: White-M 001, White-F 032, Black-M 063, Black-F 094,
    # AIAN-M 125, AIAN-F 156, API-M 187, API-F 218, Other-M 249, Other-F 280.
    starts = [1, 32, 63, 94, 125, 156, 187, 218, 249, 280]
    cols = []
    for s in starts:
        cols += [f"ET4{s+i:03d}" for i in range(0, 12)]
    return cols


def age_cols_2000():
    return [f"FMZ{n:03d}" for n in range(1, 5)] + [f"FMZ{n:03d}" for n in range(24, 28)]


def age_cols_2010():
    return [f"H76{n:03d}" for n in range(3, 7)] + [f"H76{n:03d}" for n in range(27, 31)]


def age_cols_2020():
    return [f"U7S{n:03d}" for n in range(3, 7)] + [f"U7S{n:03d}" for n in range(27, 31)]


SPECS = {
    1980: ("nhgis0124_ds104_1980_place.csv", age_cols_1980),
    1990: ("nhgis0124_ds120_1990_place.csv", age_cols_1990),
    2000: ("nhgis0124_ds146_2000_place.csv", age_cols_2000),
    2010: ("nhgis0124_ds172_2010_place.csv", age_cols_2010),
    2020: ("nhgis0124_ds258_2020_place.csv", age_cols_2020),
}


def fetch_year(year, file, cols):
    path = NHGIS / file
    sum_expr = " + ".join([f'COALESCE("{c}", 0)' for c in cols])
    q = f"""
    SELECT STATE, PLACE, STATEA, PLACEA, ({sum_expr}) AS under18
    FROM read_csv_auto('{path}', sample_size = 200000)
    """
    df = duckdb.query(q).df()
    df["year"] = year
    return df


# Pull all decades
all_places = []
for yr, (file, ac) in SPECS.items():
    cols = ac()
    print(f"--- {yr}: {file} ---")
    print(f"  {len(cols)} age columns to sum")
    df = fetch_year(yr, file, cols)
    print(f"  {len(df):,} place-rows; total under-18 = {df['under18'].sum()/1e6:.1f}M")
    all_places.append(df)


# Match each lookup row to its place per year
def match(lookup_row, year_df):
    state_name = lookup_row["state_name"]
    city = lookup_row["central_city"]
    # Build candidate patterns: alias list if available, else standard suffix variants
    candidates = ALIASES.get(city, [city, f"{city} city", f"{city} town", f"{city} village"])
    # State filter is case-insensitive
    state_mask = year_df["STATE"].str.lower() == state_name.lower()
    sub = year_df[state_mask]
    for p in candidates:
        m = sub[sub["PLACE"].str.lower() == p.lower()]
        if len(m) >= 1:
            return m.iloc[0]["under18"], m.iloc[0]["PLACE"]
    return None, None


rows = []
for yr_idx, year_df in enumerate(all_places):
    year = list(SPECS.keys())[yr_idx]
    for _, row in lookup.iterrows():
        v, match_name = match(row, year_df)
        rows.append({
            "year": year,
            "sma_code": row["sma_code"],
            "sma_name": row["sma_name"],
            "central_city": row["central_city"],
            "state_fips": row["state_fips"],
            "matched_place_name": match_name,
            "under18": v,
        })

out = pd.DataFrame(rows)
out.to_csv(DATA / "under18_central_cities_all172.csv", index=False)

# Coverage check
print("\nMatch coverage per year:")
for yr in SPECS.keys():
    sub = out[out["year"] == yr]
    matched = sub["under18"].notna().sum()
    print(f"  {yr}: {matched}/{len(sub)} cities matched, total under-18 = {sub['under18'].sum()/1e6:.2f}M")

# Show any unmatched
print("\nUnmatched (any year):")
unmatched = out[out["under18"].isna()][["year", "central_city", "state_fips"]].drop_duplicates(["central_city", "state_fips"])
print(unmatched.to_string(index=False) if len(unmatched) else "  (none)")
