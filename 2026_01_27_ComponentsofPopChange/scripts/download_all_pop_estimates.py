"""
Comprehensive download of Census Population Estimates
All geographies, all vintages, all components of change
"""

import requests
import pandas as pd
from pathlib import Path
from io import StringIO

OUTPUT_DIR = Path("/Users/azizsunderji/Dropbox/Home Economics/Data/PopulationEstimates")
OUTPUT_DIR.mkdir(exist_ok=True)

def download_csv(url, name):
    """Download CSV and save as parquet"""
    print(f"  Downloading {name}...")
    try:
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            # Try different encodings
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    df = pd.read_csv(StringIO(response.content.decode(encoding)))
                    outfile = OUTPUT_DIR / f"{name}.parquet"
                    df.to_parquet(outfile, index=False)
                    print(f"    ✓ {len(df):,} rows, {len(df.columns)} cols -> {outfile.name}")
                    return df
                except:
                    continue
            print(f"    ✗ Could not parse CSV")
            return None
        else:
            print(f"    ✗ Status {response.status_code}")
            return None
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return None

# =============================================================================
# MASTER LIST OF ALL AVAILABLE FILES
# =============================================================================

files_to_download = {
    # =========================================================================
    # 2020s DECADE (Vintage 2025 - today's release!)
    # =========================================================================

    # State - Vintage 2025 (FRESH!)
    "state_v2025": "https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/state/totals/NST-EST2025-ALLDATA.csv",

    # State - Vintage 2024
    "state_v2024": "https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/state/totals/NST-EST2024-ALLDATA.csv",

    # County - Vintage 2024 (V2025 not yet available)
    "county_v2024": "https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/totals/co-est2024-alldata.csv",

    # Metro (CBSA) - Vintage 2024
    "metro_cbsa_v2024": "https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/metro/totals/cbsa-est2024-alldata.csv",

    # Metro (CSA) - Vintage 2024
    "metro_csa_v2024": "https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/metro/totals/csa-est2024-alldata.csv",

    # Cities/Towns - Vintage 2024
    "cities_v2024": "https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/cities/totals/sub-est2024_all.csv",

    # National - Vintage 2024
    "national_v2024": "https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/national/totals/NST-EST2024-ALLDATA.csv",

    # =========================================================================
    # 2010s DECADE (Vintage 2020)
    # =========================================================================

    # State
    "state_2010s": "https://www2.census.gov/programs-surveys/popest/datasets/2010-2020/state/totals/nst-est2020-alldata.csv",

    # County
    "county_2010s": "https://www2.census.gov/programs-surveys/popest/datasets/2010-2020/counties/totals/co-est2020-alldata.csv",

    # Metro (CBSA)
    "metro_cbsa_2010s": "https://www2.census.gov/programs-surveys/popest/datasets/2010-2020/metro/totals/cbsa-est2020-alldata.csv",

    # Metro (CSA)
    "metro_csa_2010s": "https://www2.census.gov/programs-surveys/popest/datasets/2010-2020/metro/totals/csa-est2020-alldata.csv",

    # Cities/Towns
    "cities_2010s": "https://www2.census.gov/programs-surveys/popest/datasets/2010-2020/cities/totals/sub-est2020_all.csv",

    # National
    "national_2010s": "https://www2.census.gov/programs-surveys/popest/datasets/2010-2020/national/totals/nst-est2020-alldata.csv",

    # =========================================================================
    # 2000s DECADE (Intercensal - bridged to 2010 census)
    # =========================================================================

    # State intercensal
    "state_2000s_intercensal": "https://www2.census.gov/programs-surveys/popest/datasets/2000-2010/intercensal/state/st-est00int-alldata.csv",

    # County intercensal
    "county_2000s_intercensal": "https://www2.census.gov/programs-surveys/popest/datasets/2000-2010/intercensal/county/co-est00int-alldata.csv",

    # =========================================================================
    # 1990s DECADE
    # =========================================================================

    # State 1990s (components)
    "state_1990s_components": "https://www2.census.gov/programs-surveys/popest/datasets/1990-2000/state/asrh/st_int_asrh.txt",

    # County 1990s intercensal
    "county_1990s_intercensal": "https://www2.census.gov/programs-surveys/popest/datasets/1990-2000/counties/totals/co-est2001-12-00.csv",
}

print("=" * 60)
print("DOWNLOADING CENSUS POPULATION ESTIMATES")
print("=" * 60)

results = {}
for name, url in files_to_download.items():
    print(f"\n{name}:")
    df = download_csv(url, name)
    if df is not None:
        results[name] = len(df)

print("\n" + "=" * 60)
print("DOWNLOAD SUMMARY")
print("=" * 60)
for name, count in results.items():
    print(f"  {name}: {count:,} rows")

print(f"\nTotal files downloaded: {len(results)}")
print(f"Output directory: {OUTPUT_DIR}")

# List all parquet files
print("\n" + "=" * 60)
print("FILES IN DATA LAKE")
print("=" * 60)
for f in sorted(OUTPUT_DIR.glob("*.parquet")):
    size_mb = f.stat().st_size / 1024 / 1024
    print(f"  {f.name}: {size_mb:.2f} MB")
