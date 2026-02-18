"""
Compute comprehensive GDP statistics for California article.
"""
import json
import duckdb
import pandas as pd
import numpy as np

# Load the world GDP data
with open('/Users/azizsunderji/Dropbox/Home Economics/2026_02_08_GDPPC/data/states_vs_world_gdp.json') as f:
    data = json.load(f)

# Build a dict: name -> {year: value} and {year: rank}
gdp = {}
ranks = {}
for entity in data:
    name = entity['name']
    gdp[name] = {p['year']: p['value'] for p in entity['points']}
    ranks[name] = {p['year']: p['rank'] for p in entity['points']}

entities = list(gdp.keys())
years = sorted(gdp[entities[0]].keys())

print("=" * 80)
print("CALIFORNIA GDP STATISTICS")
print("=" * 80)

# 1. California absolute GDP and growth
ca_1997 = gdp['California'][1997]
ca_2024 = gdp['California'][2024]
ca_multiple = ca_2024 / ca_1997
ca_cagr = (ca_2024 / ca_1997) ** (1/27) - 1
print(f"\nCalifornia GDP 1997: ${ca_1997:.2f}B")
print(f"California GDP 2024: ${ca_2024:.2f}B")
print(f"Growth multiple: {ca_multiple:.2f}x")
print(f"CAGR 1997-2024: {ca_cagr*100:.2f}%")
print(f"California rank 1997: #{ranks['California'][1997]}")
print(f"California rank 2024: #{ranks['California'][2024]}")

# 2. When California overtook each country
print("\n" + "-" * 60)
print("CALIFORNIA OVERTAKING YEARS")
print("-" * 60)
countries_to_check = ['Italy', 'France', 'United Kingdom', 'Germany', 'Japan']
for country in countries_to_check:
    overtake_year = None
    for y in years:
        if gdp['California'][y] > gdp[country][y]:
            overtake_year = y
            break
    if overtake_year:
        print(f"California overtook {country} in {overtake_year}")
        print(f"  CA: ${gdp['California'][overtake_year]:.2f}B vs {country}: ${gdp[country][overtake_year]:.2f}B")
        # Check if it was sustained or if it flipped back
        flipped_back = False
        for y2 in range(overtake_year + 1, 2025):
            if gdp['California'][y2] < gdp[country][y2]:
                flipped_back = True
                print(f"  BUT {country} passed CA back in {y2}: {country} ${gdp[country][y2]:.2f}B vs CA ${gdp['California'][y2]:.2f}B")
                # Find when CA overtook again permanently
                for y3 in range(y2+1, 2025):
                    if gdp['California'][y3] > gdp[country][y3]:
                        # Check if permanent from here
                        permanent = True
                        for y4 in range(y3+1, 2025):
                            if gdp['California'][y4] < gdp[country][y4]:
                                permanent = False
                                break
                        if permanent:
                            print(f"  CA permanently overtook {country} in {y3}: CA ${gdp['California'][y3]:.2f}B vs {country} ${gdp[country][y3]:.2f}B")
                            break
                break
    else:
        print(f"California has NOT overtaken {country} by 2024")
        # Show how close
        print(f"  2024: CA ${gdp['California'][2024]:.2f}B vs {country}: ${gdp[country][2024]:.2f}B")
        diff = gdp[country][2024] - gdp['California'][2024]
        pct = diff / gdp[country][2024] * 100
        print(f"  Gap: ${diff:.2f}B ({pct:.1f}%)")

# 3. California vs each country growth rates
print("\n" + "-" * 60)
print("GROWTH RATES 1997-2024 (CAGR)")
print("-" * 60)
for name in entities:
    v1997 = gdp[name][1997]
    v2024 = gdp[name][2024]
    mult = v2024 / v1997
    cagr = (v2024 / v1997) ** (1/27) - 1
    print(f"{name:20s}: ${v1997:>10.2f}B -> ${v2024:>10.2f}B | {mult:.2f}x | CAGR {cagr*100:.2f}%")

# 4. China details
print("\n" + "=" * 80)
print("CHINA TRAJECTORY")
print("=" * 80)
cn_1997 = gdp['China'][1997]
cn_2024 = gdp['China'][2024]
cn_multiple = cn_2024 / cn_1997
cn_cagr = (cn_2024 / cn_1997) ** (1/27) - 1
print(f"China GDP 1997: ${cn_1997:.2f}B")
print(f"China GDP 2024: ${cn_2024:.2f}B")
print(f"Growth multiple: {cn_multiple:.2f}x")
print(f"CAGR 1997-2024: {cn_cagr*100:.2f}%")
print(f"China rank 1997: #{ranks['China'][1997]}")
print(f"China rank 2024: #{ranks['China'][2024]}")

# When China passed each entity
print("\nChina overtaking timeline:")
for country in ['Italy', 'France', 'United Kingdom', 'California', 'Germany', 'Japan']:
    for y in years:
        if gdp['China'][y] > gdp[country][y]:
            print(f"  China passed {country} in {y}: China ${gdp['China'][y]:.2f}B vs {country} ${gdp[country][y]:.2f}B")
            break

# 5. Japan details
print("\n" + "=" * 80)
print("JAPAN TRAJECTORY")
print("=" * 80)
jp_1997 = gdp['Japan'][1997]
jp_2024 = gdp['Japan'][2024]
print(f"Japan GDP 1997: ${jp_1997:.2f}B")
print(f"Japan GDP 2024: ${jp_2024:.2f}B")
print(f"Change: ${jp_2024 - jp_1997:.2f}B ({(jp_2024/jp_1997 - 1)*100:.1f}%)")
print(f"Japan rank 1997: #{ranks['Japan'][1997]}")
print(f"Japan rank 2024: #{ranks['Japan'][2024]}")
jp_peak_year = max(years, key=lambda y: gdp['Japan'][y])
print(f"Japan peak year: {jp_peak_year} at ${gdp['Japan'][jp_peak_year]:.2f}B")
print(f"Decline from peak: ${gdp['Japan'][jp_peak_year] - jp_2024:.2f}B ({(1 - jp_2024/gdp['Japan'][jp_peak_year])*100:.1f}%)")

# 6. European countries
print("\n" + "=" * 80)
print("EUROPEAN COUNTRIES 1997 vs 2024")
print("=" * 80)
for country in ['Germany', 'United Kingdom', 'France', 'Italy']:
    v1997 = gdp[country][1997]
    v2024 = gdp[country][2024]
    mult = v2024 / v1997
    cagr = (v2024 / v1997) ** (1/27) - 1
    print(f"\n{country}:")
    print(f"  1997: ${v1997:.2f}B (rank #{ranks[country][1997]})")
    print(f"  2024: ${v2024:.2f}B (rank #{ranks[country][2024]})")
    print(f"  Growth: {mult:.2f}x | CAGR: {cagr*100:.2f}%")

# 7. India trajectory
print("\n" + "=" * 80)
print("INDIA TRAJECTORY")
print("=" * 80)
in_1997 = gdp['India'][1997]
in_2024 = gdp['India'][2024]
in_multiple = in_2024 / in_1997
in_cagr = (in_2024 / in_1997) ** (1/27) - 1
print(f"India GDP 1997: ${in_1997:.2f}B (rank #{ranks['India'][1997]})")
print(f"India GDP 2024: ${in_2024:.2f}B (rank #{ranks['India'][2024]})")
print(f"Growth multiple: {in_multiple:.2f}x")
print(f"CAGR: {in_cagr*100:.2f}%")

# 8. Texas trajectory
print("\n" + "=" * 80)
print("TEXAS TRAJECTORY")
print("=" * 80)
tx_1997 = gdp['Texas'][1997]
tx_2024 = gdp['Texas'][2024]
tx_multiple = tx_2024 / tx_1997
tx_cagr = (tx_2024 / tx_1997) ** (1/27) - 1
print(f"Texas GDP 1997: ${tx_1997:.2f}B (rank #{ranks['Texas'][1997]})")
print(f"Texas GDP 2024: ${tx_2024:.2f}B (rank #{ranks['Texas'][2024]})")
print(f"Growth multiple: {tx_multiple:.2f}x")
print(f"CAGR: {tx_cagr*100:.2f}%")

# 9. US vs China convergence projection
print("\n" + "=" * 80)
print("US vs CHINA CONVERGENCE PROJECTION")
print("=" * 80)
# 2020-2024 CAGR for each
us_2020 = gdp['United States'][2020]
us_2024 = gdp['United States'][2024]
us_cagr_recent = (us_2024 / us_2020) ** (1/4) - 1

cn_2020 = gdp['China'][2020]
cn_2024_v = gdp['China'][2024]
cn_cagr_recent = (cn_2024_v / cn_2020) ** (1/4) - 1

print(f"US 2020-2024 CAGR: {us_cagr_recent*100:.2f}%")
print(f"China 2020-2024 CAGR: {cn_cagr_recent*100:.2f}%")
print(f"US GDP 2024: ${us_2024:.2f}B")
print(f"China GDP 2024: ${cn_2024_v:.2f}B")
print(f"Gap: ${us_2024 - cn_2024_v:.2f}B")

# Project forward
if cn_cagr_recent > us_cagr_recent:
    for future_year in range(2025, 2100):
        years_ahead = future_year - 2024
        us_proj = us_2024 * (1 + us_cagr_recent) ** years_ahead
        cn_proj = cn_2024_v * (1 + cn_cagr_recent) ** years_ahead
        if cn_proj >= us_proj:
            print(f"\nChina would equal US GDP in {future_year}")
            print(f"  US projected: ${us_proj:.0f}B")
            print(f"  China projected: ${cn_proj:.0f}B")
            break
    else:
        print("China would not catch US by 2100 at these rates")
else:
    print(f"\nChina's recent CAGR ({cn_cagr_recent*100:.2f}%) is LOWER than US ({us_cagr_recent*100:.2f}%)")
    print("At these rates, China would NEVER catch the US — the gap would widen.")
    # Show gap widening
    for fy in [2030, 2040, 2050]:
        ya = fy - 2024
        us_p = us_2024 * (1 + us_cagr_recent) ** ya
        cn_p = cn_2024_v * (1 + cn_cagr_recent) ** ya
        print(f"  {fy}: US ${us_p:.0f}B vs China ${cn_p:.0f}B (gap: ${us_p - cn_p:.0f}B)")

# Also try with a slightly longer window for China
print("\n--- Alternative: 2015-2024 CAGRs ---")
us_2015 = gdp['United States'][2015]
cn_2015 = gdp['China'][2015]
us_cagr_9yr = (us_2024 / us_2015) ** (1/9) - 1
cn_cagr_9yr = (cn_2024_v / cn_2015) ** (1/9) - 1
print(f"US 2015-2024 CAGR: {us_cagr_9yr*100:.2f}%")
print(f"China 2015-2024 CAGR: {cn_cagr_9yr*100:.2f}%")

if cn_cagr_9yr > us_cagr_9yr:
    for future_year in range(2025, 2100):
        years_ahead = future_year - 2024
        us_proj = us_2024 * (1 + us_cagr_9yr) ** years_ahead
        cn_proj = cn_2024_v * (1 + cn_cagr_9yr) ** years_ahead
        if cn_proj >= us_proj:
            print(f"China would equal US GDP in {future_year}")
            print(f"  US projected: ${us_proj:.0f}B")
            print(f"  China projected: ${cn_proj:.0f}B")
            break
else:
    print("China 2015-2024 CAGR also lower than US — convergence receding")

print("\n--- Alternative: 2019-2024 CAGRs ---")
us_2019 = gdp['United States'][2019]
cn_2019 = gdp['China'][2019]
us_cagr_5yr = (us_2024 / us_2019) ** (1/5) - 1
cn_cagr_5yr = (cn_2024_v / cn_2019) ** (1/5) - 1
print(f"US 2019-2024 CAGR: {us_cagr_5yr*100:.2f}%")
print(f"China 2019-2024 CAGR: {cn_cagr_5yr*100:.2f}%")

if cn_cagr_5yr > us_cagr_5yr:
    for future_year in range(2025, 2100):
        years_ahead = future_year - 2024
        us_proj = us_2024 * (1 + us_cagr_5yr) ** years_ahead
        cn_proj = cn_2024_v * (1 + cn_cagr_5yr) ** years_ahead
        if cn_proj >= us_proj:
            print(f"China would equal US GDP in {future_year}")
            print(f"  US projected: ${us_proj:.0f}B")
            print(f"  China projected: ${cn_proj:.0f}B")
            break
else:
    print("China 2019-2024 CAGR also lower than US")

# 10. Full rank table by year
print("\n" + "=" * 80)
print("FULL RANK TABLE (among these 10 entities)")
print("=" * 80)
for y in [1997, 2000, 2005, 2010, 2015, 2020, 2024]:
    sorted_entities = sorted(entities, key=lambda e: gdp[e][y], reverse=True)
    print(f"\n{y}:")
    for i, e in enumerate(sorted_entities, 1):
        print(f"  {i:2d}. {e:20s} ${gdp[e][y]:>10.2f}B")

# 11. California per capita from BEA data
print("\n" + "=" * 80)
print("CALIFORNIA GDP PER CAPITA (from BEA data)")
print("=" * 80)

conn = duckdb.connect()

# Check what's in the BEA population file
print("\nBEA state population data sample:")
df_pop = conn.execute("""
    SELECT * FROM '/Users/azizsunderji/Dropbox/Home Economics/2026_02_08_GDPPC/data/bea_state_population.parquet'
    WHERE GeoName = 'California'
    ORDER BY TimePeriod
""").df()
print(df_pop.to_string())

print("\nBEA state real GDP data sample (California):")
df_gdp_bea = conn.execute("""
    SELECT * FROM '/Users/azizsunderji/Dropbox/Home Economics/2026_02_08_GDPPC/data/bea_state_real_gdp.parquet'
    WHERE GeoName = 'California'
    ORDER BY TimePeriod
""").df()
print(df_gdp_bea.to_string())

# Also check the PopulationEstimates data lake
print("\n\nPopulation Estimates data lake - California:")
try:
    df_pop_long = conn.execute("""
        SELECT * FROM '/Users/azizsunderji/Dropbox/Home Economics/Data/PopulationEstimates/state_pop_estimates_long.parquet'
        WHERE state_name = 'California' OR NAME = 'California'
        LIMIT 5
    """).df()
    print(df_pop_long.to_string())
except:
    # Check columns first
    cols = conn.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'state_pop_estimates_long'
    """).df()
    print("Couldn't find California - checking columns...")
    df_sample = conn.execute("""
        SELECT * FROM '/Users/azizsunderji/Dropbox/Home Economics/Data/PopulationEstimates/state_pop_estimates_long.parquet'
        LIMIT 3
    """).df()
    print(df_sample.columns.tolist())
    print(df_sample.head())

conn.close()
