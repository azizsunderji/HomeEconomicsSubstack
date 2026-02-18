"""
Download Census Population Estimates (Vintage 2025) and historical vintages
Creates consolidated parquet files for the data lake
"""

import requests
import pandas as pd
from pathlib import Path

API_KEY = "06048dc3bd32068702b5ef9b49875ec0c5ca56ce"
OUTPUT_DIR = Path("/Users/azizsunderji/Dropbox/Home Economics/Data/PopulationEstimates")
OUTPUT_DIR.mkdir(exist_ok=True)

def fetch_census_data(url):
    """Fetch data from Census API and return as DataFrame"""
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    df = pd.DataFrame(data[1:], columns=data[0])
    return df

# =============================================================================
# 1. NATIONAL POPULATION & COMPONENTS (Vintage 2025)
# =============================================================================
print("Fetching National population estimates (Vintage 2025)...")

# National totals and components 2020-2025
national_url = f"https://api.census.gov/data/2025/pep/natmonthly?get=NAME,POP,DENSITY,BIRTHS,DEATHS,NATURALCHG,INTERNATIONALMIG,DOMESTICMIG,NETMIG&for=us:*&key={API_KEY}"

try:
    national_df = fetch_census_data(national_url)
    print(f"  National data: {len(national_df)} rows")
except Exception as e:
    print(f"  National monthly endpoint not available: {e}")
    print("  Trying annual endpoint...")

# Try the annual components endpoint
national_url = f"https://api.census.gov/data/2025/pep/population?get=NAME,POP,DENSITY,DATE_CODE,DATE_DESC&for=us:*&key={API_KEY}"
try:
    national_df = fetch_census_data(national_url)
    print(f"  National data: {len(national_df)} rows")
    print(national_df.head(10))
except Exception as e:
    print(f"  Error: {e}")

# =============================================================================
# 2. STATE POPULATION & COMPONENTS (Vintage 2025)
# =============================================================================
print("\nFetching State population estimates (Vintage 2025)...")

state_url = f"https://api.census.gov/data/2025/pep/population?get=NAME,POP,DENSITY,DATE_CODE,DATE_DESC&for=state:*&key={API_KEY}"

try:
    state_df = fetch_census_data(state_url)
    print(f"  State data: {len(state_df)} rows")
    print(state_df.head())
except Exception as e:
    print(f"  Error with Vintage 2025: {e}")
    print("  Trying Vintage 2024...")

    state_url = f"https://api.census.gov/data/2024/pep/population?get=NAME,POP,DENSITY,DATE_CODE,DATE_DESC&for=state:*&key={API_KEY}"
    try:
        state_df = fetch_census_data(state_url)
        print(f"  State data (V2024): {len(state_df)} rows")
    except Exception as e2:
        print(f"  Error: {e2}")

# =============================================================================
# 3. STATE COMPONENTS OF CHANGE (Vintage 2025)
# =============================================================================
print("\nFetching State components of change (Vintage 2025)...")

components_url = f"https://api.census.gov/data/2025/pep/components?get=NAME,BIRTHS,DEATHS,NATURALCHG,INTERNATIONALMIG,DOMESTICMIG,NETMIG,PERIOD_CODE,PERIOD_DESC&for=state:*&key={API_KEY}"

try:
    components_df = fetch_census_data(components_url)
    print(f"  Components data: {len(components_df)} rows")
    print(components_df.head())
except Exception as e:
    print(f"  Error with Vintage 2025: {e}")
    print("  Trying Vintage 2024...")

    components_url = f"https://api.census.gov/data/2024/pep/components?get=NAME,BIRTHS,DEATHS,NATURALCHG,INTERNATIONALMIG,DOMESTICMIG,NETMIG,PERIOD_CODE,PERIOD_DESC&for=state:*&key={API_KEY}"
    try:
        components_df = fetch_census_data(components_url)
        print(f"  Components data (V2024): {len(components_df)} rows")
    except Exception as e2:
        print(f"  Error: {e2}")

# =============================================================================
# 4. COUNTY POPULATION & COMPONENTS (Vintage 2025)
# =============================================================================
print("\nFetching County population estimates (Vintage 2025)...")

county_url = f"https://api.census.gov/data/2025/pep/population?get=NAME,POP,DENSITY,DATE_CODE,DATE_DESC&for=county:*&key={API_KEY}"

try:
    county_df = fetch_census_data(county_url)
    print(f"  County data: {len(county_df)} rows")
except Exception as e:
    print(f"  Error with Vintage 2025: {e}")
    print("  Trying Vintage 2024...")

    county_url = f"https://api.census.gov/data/2024/pep/population?get=NAME,POP,DENSITY,DATE_CODE,DATE_DESC&for=county:*&key={API_KEY}"
    try:
        county_df = fetch_census_data(county_url)
        print(f"  County data (V2024): {len(county_df)} rows")
    except Exception as e2:
        print(f"  Error: {e2}")

print("\n=== Checking what vintage years are available ===")
# List available endpoints
for year in [2025, 2024, 2023, 2022, 2021]:
    test_url = f"https://api.census.gov/data/{year}/pep/population?get=NAME&for=us:*&key={API_KEY}"
    try:
        response = requests.get(test_url)
        if response.status_code == 200:
            print(f"  Vintage {year}: Available")
        else:
            print(f"  Vintage {year}: Not available (status {response.status_code})")
    except Exception as e:
        print(f"  Vintage {year}: Error - {e}")
