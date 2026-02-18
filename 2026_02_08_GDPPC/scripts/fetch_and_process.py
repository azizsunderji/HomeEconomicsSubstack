"""
Fetch state GDP and population data from BEA Regional API,
process into rankings, and export JSON for D3 bump charts.
"""

import requests
import pandas as pd
import duckdb
import json
import os

BEA_API_KEY = "4A811E05-9121-4653-9C82-45DC4A2F8114"
BASE_URL = "https://apps.bea.gov/api/data/"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# Valid state FIPS codes (50 states + DC)
VALID_STATE_FIPS = {
    "01000", "02000", "04000", "05000", "06000", "08000", "09000", "10000",
    "11000", "12000", "13000", "15000", "16000", "17000", "18000", "19000",
    "20000", "21000", "22000", "23000", "24000", "25000", "26000", "27000",
    "28000", "29000", "30000", "31000", "32000", "33000", "34000", "35000",
    "36000", "37000", "38000", "39000", "40000", "41000", "42000", "44000",
    "45000", "46000", "47000", "48000", "49000", "50000", "51000", "53000",
    "54000", "55000", "56000",
}

def fetch_bea_regional(table_name, line_code):
    """Fetch data from BEA Regional API."""
    params = {
        "UserID": BEA_API_KEY,
        "method": "GetData",
        "datasetname": "Regional",
        "TableName": table_name,
        "LineCode": line_code,
        "GeoFips": "STATE",
        "Year": "ALL",
        "ResultFormat": "JSON",
    }
    print(f"Fetching {table_name} (LineCode={line_code})...")
    resp = requests.get(BASE_URL, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    if "BEAAPI" not in data or "Results" not in data["BEAAPI"]:
        print(f"ERROR: Unexpected response structure for {table_name}")
        print(json.dumps(data, indent=2)[:2000])
        raise ValueError(f"Bad response for {table_name}")

    results = data["BEAAPI"]["Results"]
    if "Data" not in results:
        print(f"ERROR: No 'Data' key in results for {table_name}")
        print(json.dumps(results, indent=2)[:2000])
        raise ValueError(f"No data for {table_name}")

    records = results["Data"]
    print(f"  Got {len(records)} records")
    return records


def process_data():
    """Fetch, process, and export GDP ranking data."""
    os.makedirs(DATA_DIR, exist_ok=True)

    # Fetch Real GDP (SAGDP9, LineCode=1) — millions of chained 2017 dollars
    gdp_records = fetch_bea_regional("SAGDP9", 1)
    gdp_df = pd.DataFrame(gdp_records)

    # Fetch Population (SAINC1, LineCode=2) — midperiod population
    pop_records = fetch_bea_regional("SAINC1", 2)
    pop_df = pd.DataFrame(pop_records)

    # Save raw data as parquet
    gdp_df.to_parquet(os.path.join(DATA_DIR, "bea_state_real_gdp.parquet"), index=False)
    pop_df.to_parquet(os.path.join(DATA_DIR, "bea_state_population.parquet"), index=False)

    # Source sidecars
    for fname, desc in [
        ("bea_state_real_gdp", "BEA SAGDP9N Real GDP by state, chained 2017$"),
        ("bea_state_population", "BEA SAINC1 State population"),
    ]:
        with open(os.path.join(DATA_DIR, f"{fname}.source.json"), "w") as f:
            json.dump({
                "type": "manual",
                "source": "BEA Regional API",
                "note": desc,
            }, f, indent=2)

    # Process with DuckDB
    con = duckdb.connect()

    # Register dataframes
    con.register("gdp_raw", gdp_df)
    con.register("pop_raw", pop_df)

    # Clean GDP data
    gdp_clean = con.execute("""
        SELECT
            GeoFips,
            GeoName,
            CAST(TimePeriod AS INTEGER) AS year,
            CASE
                WHEN DataValue = '(NA)' OR DataValue = '(D)' THEN NULL
                ELSE CAST(REPLACE(DataValue, ',', '') AS DOUBLE)
            END AS real_gdp_millions
        FROM gdp_raw
        WHERE GeoFips IN (SELECT UNNEST(?::VARCHAR[]))
          AND CAST(TimePeriod AS INTEGER) BETWEEN 1997 AND 2024
    """, [list(VALID_STATE_FIPS)]).df()

    # Clean population data
    pop_clean = con.execute("""
        SELECT
            GeoFips,
            GeoName,
            CAST(TimePeriod AS INTEGER) AS year,
            CASE
                WHEN DataValue = '(NA)' OR DataValue = '(D)' THEN NULL
                ELSE CAST(REPLACE(DataValue, ',', '') AS DOUBLE)
            END AS population
        FROM pop_raw
        WHERE GeoFips IN (SELECT UNNEST(?::VARCHAR[]))
          AND CAST(TimePeriod AS INTEGER) BETWEEN 1997 AND 2024
    """, [list(VALID_STATE_FIPS)]).df()

    print(f"\nGDP: {len(gdp_clean)} rows, {gdp_clean['year'].nunique()} years, {gdp_clean['GeoFips'].nunique()} states")
    print(f"Pop: {len(pop_clean)} rows, {pop_clean['year'].nunique()} years, {pop_clean['GeoFips'].nunique()} states")

    # Check for nulls
    gdp_nulls = gdp_clean['real_gdp_millions'].isna().sum()
    pop_nulls = pop_clean['population'].isna().sum()
    print(f"GDP nulls: {gdp_nulls}, Pop nulls: {pop_nulls}")

    # Merge
    con.register("gdp", gdp_clean)
    con.register("pop", pop_clean)

    merged = con.execute("""
        SELECT
            g.GeoFips,
            g.GeoName,
            g.year,
            g.real_gdp_millions,
            p.population,
            (g.real_gdp_millions * 1000000.0) / p.population AS gdp_per_capita
        FROM gdp g
        JOIN pop p ON g.GeoFips = p.GeoFips AND g.year = p.year
        WHERE g.real_gdp_millions IS NOT NULL
          AND p.population IS NOT NULL
          AND p.population > 0
        ORDER BY g.year, g.GeoFips
    """).df()

    print(f"\nMerged: {len(merged)} rows")
    print(f"GDP per capita range: ${merged['gdp_per_capita'].min():,.0f} - ${merged['gdp_per_capita'].max():,.0f}")

    # Rank states per year
    con.register("merged", merged)

    ranked = con.execute("""
        SELECT *,
            RANK() OVER (PARTITION BY year ORDER BY real_gdp_millions DESC) AS gdp_rank,
            RANK() OVER (PARTITION BY year ORDER BY gdp_per_capita DESC) AS gdp_pc_rank
        FROM merged
        ORDER BY year, gdp_rank
    """).df()

    # Save processed data
    ranked.to_parquet(os.path.join(DATA_DIR, "state_gdp_rankings.parquet"), index=False)

    # Verify California
    ca = ranked[ranked['GeoName'].str.contains('California')]
    print(f"\nCalifornia GDP ranks: {ca.groupby('year')['gdp_rank'].first().to_dict()}")
    print(f"California GDP/cap ranks: {ca.groupby('year')['gdp_pc_rank'].first().to_dict()}")

    # Top 12 by 2024 rank for absolute GDP
    top12_gdp_states = ranked[ranked['year'] == 2024].nsmallest(12, 'gdp_rank')['GeoFips'].tolist()
    top12_gdp = ranked[ranked['GeoFips'].isin(top12_gdp_states)].copy()

    # For GDP per capita: exclude DC, filter to states with 5M+ population (in 2024),
    # then re-rank within that subset
    con.register("ranked", ranked)
    big_states_pc = con.execute("""
        WITH big_states AS (
            SELECT DISTINCT GeoFips
            FROM ranked
            WHERE year = 2024
              AND population >= 5000000
              AND GeoFips != '11000'  -- exclude DC
        )
        SELECT r.*,
            RANK() OVER (PARTITION BY r.year ORDER BY r.gdp_per_capita DESC) AS gdp_pc_rank_filtered
        FROM ranked r
        WHERE r.GeoFips IN (SELECT GeoFips FROM big_states)
        ORDER BY r.year, gdp_pc_rank_filtered
    """).df()

    top12_pc_states = big_states_pc[big_states_pc['year'] == 2024].nsmallest(12, 'gdp_pc_rank_filtered')['GeoFips'].tolist()
    top12_pc = big_states_pc[big_states_pc['GeoFips'].isin(top12_pc_states)].copy()

    print(f"\nTop 12 GDP states (2024): {top12_gdp[top12_gdp['year']==2024][['GeoName','gdp_rank','real_gdp_millions']].to_string(index=False)}")
    print(f"\nTop 12 GDP/cap states (5M+ pop, excl DC, 2024): {top12_pc[top12_pc['year']==2024][['GeoName','gdp_pc_rank_filtered','gdp_per_capita']].to_string(index=False)}")

    # Export JSON for D3
    def to_d3_json(df, rank_col, value_col, value_label):
        """Convert to nested JSON structure for D3 bump chart."""
        states = []
        for fips in df['GeoFips'].unique():
            state_data = df[df['GeoFips'] == fips].sort_values('year')
            name = state_data['GeoName'].iloc[0]
            # Clean state name (remove trailing *)
            name = name.strip().rstrip('*').strip()
            points = []
            for _, row in state_data.iterrows():
                points.append({
                    "year": int(row['year']),
                    "rank": int(row[rank_col]),
                    "value": round(float(row[value_col]), 2),
                })
            states.append({
                "fips": fips,
                "name": name,
                "points": points,
            })
        return states

    gdp_json = to_d3_json(top12_gdp, 'gdp_rank', 'real_gdp_millions', 'Real GDP (millions)')
    pc_json = to_d3_json(top12_pc, 'gdp_pc_rank_filtered', 'gdp_per_capita', 'GDP per Capita')

    # Save JSON
    with open(os.path.join(DATA_DIR, "top12_gdp_rankings.json"), "w") as f:
        json.dump(gdp_json, f, indent=2)
    with open(os.path.join(DATA_DIR, "top12_gdp_per_capita_rankings.json"), "w") as f:
        json.dump(pc_json, f, indent=2)

    print("\nDone! JSON files saved to data/")
    return gdp_json, pc_json


if __name__ == "__main__":
    process_data()
