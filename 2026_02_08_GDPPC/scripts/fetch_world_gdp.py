"""
Fetch nominal GDP for US states (CA, TX, NY, FL) and top world economies,
combine into a single ranking for a bump chart.
"""

import requests
import pandas as pd
import duckdb
import json
import os
import time

BEA_API_KEY = "4A811E05-9121-4653-9C82-45DC4A2F8114"
BEA_URL = "https://apps.bea.gov/api/data/"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# States to include
STATES = {
    "06000": "California",
    "48000": "Texas",
}

def fetch_state_nominal_gdp():
    """Fetch current-dollar GDP by state from BEA (SAGDP2, LineCode=1)."""
    params = {
        "UserID": BEA_API_KEY,
        "method": "GetData",
        "datasetname": "Regional",
        "TableName": "SAGDP2N",
        "LineCode": 1,
        "GeoFips": "STATE",
        "Year": "ALL",
        "ResultFormat": "JSON",
    }
    print("Fetching state nominal GDP (SAGDP2N)...")
    resp = requests.get(BEA_URL, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    if "Error" in data.get("BEAAPI", {}):
        # Try SAGDP2 instead
        print("SAGDP2N failed, trying SAGDP2...")
        params["TableName"] = "SAGDP2"
        resp = requests.get(BEA_URL, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()

    results = data["BEAAPI"]["Results"]
    if "Data" not in results:
        print("ERROR:", json.dumps(results, indent=2)[:2000])
        raise ValueError("No data returned")

    records = results["Data"]
    print(f"  Got {len(records)} records")

    rows = []
    for r in records:
        fips = r["GeoFips"]
        if fips not in STATES:
            continue
        year = int(r["TimePeriod"])
        if year < 1997 or year > 2024:
            continue
        val = r["DataValue"]
        if val in ("(NA)", "(D)"):
            continue
        # Value is in millions of current dollars
        gdp_millions = float(val.replace(",", ""))
        rows.append({
            "name": STATES[fips],
            "year": year,
            "gdp_usd": gdp_millions * 1e6,  # Convert to actual USD
        })

    df = pd.DataFrame(rows)
    print(f"  State GDP: {len(df)} rows, years {df['year'].min()}-{df['year'].max()}")
    print(f"  States: {df['name'].unique().tolist()}")
    # Quick check
    ca2024 = df[(df['name'] == 'California') & (df['year'] == 2024)]
    if len(ca2024) > 0:
        print(f"  CA 2024 GDP: ${ca2024['gdp_usd'].iloc[0]/1e12:.2f}T")
    return df


def fetch_world_bank_gdp():
    """Fetch GDP (current USD) from World Bank API for major economies."""
    # Top economies by recent GDP (ISO2 codes) — fetch in small batches
    countries = [
        "US", "CN", "JP", "DE", "IN", "GB", "FR", "IT", "BR", "CA",
        "RU", "MX", "AU", "KR", "ES", "ID", "NL", "SA", "TR", "CH",
        "PL", "SE", "BE", "AR", "NO", "IE", "IL", "AT", "TH", "NG",
    ]

    indicator = "NY.GDP.MKTP.CD"  # GDP current USD
    all_data = []

    # Fetch in batches of 5 countries to avoid timeouts
    batch_size = 5
    for i in range(0, len(countries), batch_size):
        batch = countries[i:i+batch_size]
        country_str = ";".join(batch)

        for attempt in range(3):
            try:
                url = f"https://api.worldbank.org/v2/country/{country_str}/indicator/{indicator}"
                params = {
                    "date": "1997:2024",
                    "format": "json",
                    "per_page": 500,
                }
                print(f"Fetching World Bank GDP: {batch} (attempt {attempt+1})...")
                resp = requests.get(url, params=params, timeout=90)
                resp.raise_for_status()
                result = resp.json()

                if len(result) < 2 or not result[1]:
                    print("  No data returned")
                    break

                records = result[1]
                for r in records:
                    if r["value"] is None:
                        continue
                    all_data.append({
                        "iso2": r["country"]["id"],
                        "name": r["country"]["value"],
                        "year": int(r["date"]),
                        "gdp_usd": float(r["value"]),
                    })
                print(f"  Got {len(records)} records")
                break  # success
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                print(f"  Timeout/error: {e}")
                if attempt < 2:
                    time.sleep(5)
                else:
                    print(f"  FAILED after 3 attempts for {batch}")

        time.sleep(1)  # Be nice to API

    df = pd.DataFrame(all_data)
    print(f"  World Bank: {len(df)} rows, {df['name'].nunique()} countries")
    print(f"  Years: {df['year'].min()}-{df['year'].max()}")

    # Rename some countries for brevity
    name_map = {
        "United States": "United States",
        "China": "China",
        "Japan": "Japan",
        "Germany": "Germany",
        "United Kingdom": "United Kingdom",
        "India": "India",
        "France": "France",
        "Italy": "Italy",
        "Brazil": "Brazil",
        "Canada": "Canada",  # Note: will be confusing with California
        "Russian Federation": "Russia",
        "Korea, Rep.": "South Korea",
        "Australia": "Australia",
        "Spain": "Spain",
        "Mexico": "Mexico",
        "Indonesia": "Indonesia",
        "Netherlands": "Netherlands",
        "Saudi Arabia": "Saudi Arabia",
        "Turkiye": "Turkey",
        "Switzerland": "Switzerland",
        "Poland": "Poland",
        "Sweden": "Sweden",
        "Belgium": "Belgium",
        "Argentina": "Argentina",
        "Norway": "Norway",
        "Ireland": "Ireland",
        "Israel": "Israel",
        "Austria": "Austria",
        "Thailand": "Thailand",
        "Nigeria": "Nigeria",
    }
    df["name"] = df["name"].map(lambda x: name_map.get(x, x))

    return df


def build_combined_ranking():
    """Combine state and country GDP, rank, and export for D3."""
    os.makedirs(DATA_DIR, exist_ok=True)

    state_df = fetch_state_nominal_gdp()
    world_df = fetch_world_bank_gdp()

    # Keep US in world data (showing US total alongside states)

    # Mark source
    state_df["type"] = "state"
    world_df["type"] = "country"

    # Combine
    combined = pd.concat([
        state_df[["name", "year", "gdp_usd", "type"]],
        world_df[["name", "year", "gdp_usd", "type"]],
    ], ignore_index=True)

    print(f"\nCombined: {len(combined)} rows, {combined['name'].nunique()} entities")

    # Check what years have good coverage
    year_counts = combined.groupby("year")["name"].nunique()
    print(f"Entity counts by year:\n{year_counts.to_string()}")

    # Find the max year with World Bank data
    wb_max_year = world_df["year"].max()
    state_max_year = state_df["year"].max()
    print(f"\nWorld Bank max year: {wb_max_year}")
    print(f"State GDP max year: {state_max_year}")

    # Use DuckDB to rank
    con = duckdb.connect()
    con.register("combined", combined)

    # Rank per year
    ranked = con.execute("""
        SELECT *,
            RANK() OVER (PARTITION BY year ORDER BY gdp_usd DESC) AS gdp_rank
        FROM combined
        ORDER BY year, gdp_rank
    """).df()

    # Show California's rank over time
    ca = ranked[ranked["name"] == "California"].sort_values("year")
    print(f"\nCalifornia rankings:")
    for _, row in ca.iterrows():
        print(f"  {int(row['year'])}: #{int(row['gdp_rank'])} (${row['gdp_usd']/1e12:.2f}T)")

    # Determine which entities to include: top 20 by final year + always include the 4 states
    final_year = min(wb_max_year, state_max_year)
    print(f"\nUsing {final_year} as final year for rankings")

    # Filter to years where we have both state and country data
    min_year = 1997
    ranked = ranked[(ranked["year"] >= min_year) & (ranked["year"] <= final_year)]

    # Get top 10 by final year ranking
    final_ranked = ranked[ranked["year"] == final_year].nsmallest(10, "gdp_rank")
    top_entities = set(final_ranked["name"].tolist())

    # Always include our 2 states
    for state in STATES.values():
        top_entities.add(state)

    filtered = ranked[ranked["name"].isin(top_entities)].copy()

    # Re-rank among ALL entities (keep original rank which is global)
    print(f"\nEntities in chart: {sorted(top_entities)}")
    print(f"Final year rankings:")
    final = filtered[filtered["year"] == final_year].sort_values("gdp_rank")
    for _, row in final.iterrows():
        marker = " ★" if row["type"] == "state" else ""
        print(f"  #{int(row['gdp_rank'])} {row['name']} (${row['gdp_usd']/1e12:.2f}T){marker}")

    # Export JSON
    entities = []
    for name in filtered["name"].unique():
        edata = filtered[filtered["name"] == name].sort_values("year")
        etype = edata["type"].iloc[0]
        points = []
        for _, row in edata.iterrows():
            points.append({
                "year": int(row["year"]),
                "rank": int(row["gdp_rank"]),
                "value": round(row["gdp_usd"] / 1e9, 2),  # Billions USD
            })
        entities.append({
            "name": name,
            "type": etype,
            "points": points,
        })

    with open(os.path.join(DATA_DIR, "states_vs_world_gdp.json"), "w") as f:
        json.dump(entities, f, indent=2)

    print(f"\nExported {len(entities)} entities to data/states_vs_world_gdp.json")
    return entities


if __name__ == "__main__":
    build_combined_ranking()
