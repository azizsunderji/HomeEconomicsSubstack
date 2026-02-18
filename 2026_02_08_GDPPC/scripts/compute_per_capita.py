"""
Compute California GDP per capita using BEA nominal GDP + population data.
"""
import json
import duckdb
import numpy as np

conn = duckdb.connect()

# Get California population from BEA data
pop_df = conn.execute("""
    SELECT TimePeriod as year, CAST(DataValue AS BIGINT) as population
    FROM '/Users/azizsunderji/Dropbox/Home Economics/2026_02_08_GDPPC/data/bea_state_population.parquet'
    WHERE GeoName = 'California'
    AND TimePeriod >= 1997
    ORDER BY TimePeriod
""").df()

# Get California nominal GDP from the JSON (in billions)
with open('/Users/azizsunderji/Dropbox/Home Economics/2026_02_08_GDPPC/data/states_vs_world_gdp.json') as f:
    data = json.load(f)

ca_data = [e for e in data if e['name'] == 'California'][0]
ca_gdp = {p['year']: p['value'] for p in ca_data['points']}

print("=" * 80)
print("CALIFORNIA GDP PER CAPITA (Nominal)")
print("=" * 80)
print(f"\n{'Year':>6s}  {'GDP ($B)':>12s}  {'Population':>14s}  {'GDP/Cap':>12s}")
print("-" * 50)

gdp_per_cap = {}
for _, row in pop_df.iterrows():
    year = row['year']
    pop = row['population']
    if year in ca_gdp:
        gdp_billions = ca_gdp[year]
        gpc = (gdp_billions * 1e9) / pop
        gdp_per_cap[year] = gpc
        print(f"{year:>6d}  ${gdp_billions:>10.2f}B  {pop:>14,d}  ${gpc:>10,.0f}")

# Growth stats
gpc_1997 = gdp_per_cap[1997]
gpc_2024 = gdp_per_cap[2024]
gpc_multiple = gpc_2024 / gpc_1997
gpc_cagr = (gpc_2024 / gpc_1997) ** (1/27) - 1

print(f"\nGDP per capita 1997: ${gpc_1997:,.0f}")
print(f"GDP per capita 2024: ${gpc_2024:,.0f}")
print(f"Growth multiple: {gpc_multiple:.2f}x")
print(f"CAGR: {gpc_cagr*100:.2f}%")

# Population growth
pop_1997 = pop_df[pop_df['year'] == 1997]['population'].values[0]
pop_2024 = pop_df[pop_df['year'] == 2024]['population'].values[0]
pop_peak_row = pop_df.loc[pop_df['population'].idxmax()]
pop_peak_year = pop_peak_row['year']
pop_peak = pop_peak_row['population']

print(f"\n{'='*80}")
print("CALIFORNIA POPULATION")
print("=" * 80)
print(f"Population 1997: {pop_1997:,d}")
print(f"Population 2024: {pop_2024:,d}")
print(f"Growth: {(pop_2024/pop_1997 - 1)*100:.1f}%")
print(f"Population CAGR: {((pop_2024/pop_1997)**(1/27) - 1)*100:.2f}%")
print(f"Peak population: {pop_peak:,d} in {pop_peak_year}")
print(f"Decline from peak to 2024: {pop_peak - pop_2024:,d} ({(pop_peak - pop_2024)/pop_peak*100:.2f}%)")

# Also get REAL GDP per capita
print(f"\n{'='*80}")
print("CALIFORNIA REAL GDP PER CAPITA (Chained 2017 $)")
print("=" * 80)

real_gdp_df = conn.execute("""
    SELECT TimePeriod as year, DataValue as real_gdp_millions
    FROM '/Users/azizsunderji/Dropbox/Home Economics/2026_02_08_GDPPC/data/bea_state_real_gdp.parquet'
    WHERE GeoName = 'California'
    AND TimePeriod >= 1997
    ORDER BY TimePeriod
""").df()

print(f"\n{'Year':>6s}  {'Real GDP ($M)':>16s}  {'Population':>14s}  {'Real GDP/Cap':>14s}")
print("-" * 56)

real_gpc = {}
for _, row in real_gdp_df.iterrows():
    year = row['year']
    rgdp_m = row['real_gdp_millions']
    pop_row = pop_df[pop_df['year'] == year]
    if len(pop_row) > 0:
        pop = pop_row['population'].values[0]
        rgpc = (rgdp_m * 1e6) / pop
        real_gpc[year] = rgpc
        print(f"{year:>6d}  ${rgdp_m:>14,.1f}M  {pop:>14,d}  ${rgpc:>12,.0f}")

rgpc_1997 = real_gpc[1997]
rgpc_2024 = real_gpc[2024]
rgpc_multiple = rgpc_2024 / rgpc_1997
rgpc_cagr = (rgpc_2024 / rgpc_1997) ** (1/27) - 1

print(f"\nReal GDP per capita 1997: ${rgpc_1997:,.0f}")
print(f"Real GDP per capita 2024: ${rgpc_2024:,.0f}")
print(f"Growth multiple: {rgpc_multiple:.2f}x")
print(f"Real CAGR: {rgpc_cagr*100:.2f}%")

# Decompose nominal GDP per capita growth into: real GDP/cap growth + price growth
print(f"\n{'='*80}")
print("DECOMPOSITION OF CALIFORNIA NOMINAL GDP PER CAPITA GROWTH")
print("=" * 80)
print(f"Nominal GDP/cap growth (1997-2024): {(gpc_multiple - 1)*100:.1f}%")
print(f"  = Real GDP/cap growth: {(rgpc_multiple - 1)*100:.1f}%")
implicit_deflator_growth = gpc_multiple / rgpc_multiple
print(f"  x Price level change: {(implicit_deflator_growth - 1)*100:.1f}%")
print(f"\nSo real productivity gains account for {(rgpc_multiple - 1)/(gpc_multiple - 1)*100:.0f}% of nominal growth")
print(f"And price increases account for {(implicit_deflator_growth - 1)/(gpc_multiple - 1)*100:.0f}%")

# Additional key stats
print(f"\n{'='*80}")
print("KEY COMPARATIVE STATS")
print("=" * 80)

# California GDP as share of US
us_data = [e for e in data if e['name'] == 'United States'][0]
us_gdp = {p['year']: p['value'] for p in us_data['points']}
ca_share_1997 = ca_gdp[1997] / us_gdp[1997] * 100
ca_share_2024 = ca_gdp[2024] / us_gdp[2024] * 100
print(f"California as % of US GDP:")
print(f"  1997: {ca_share_1997:.1f}%")
print(f"  2024: {ca_share_2024:.1f}%")

# California GDP growth vs US GDP growth
us_cagr = (us_gdp[2024] / us_gdp[1997]) ** (1/27) - 1
ca_cagr = (ca_gdp[2024] / ca_gdp[1997]) ** (1/27) - 1
print(f"\nCAGR comparison 1997-2024:")
print(f"  California: {ca_cagr*100:.2f}%")
print(f"  United States: {us_cagr*100:.2f}%")
print(f"  California excess growth: {(ca_cagr - us_cagr)*100:.2f} percentage points/year")

# How much bigger is CA than the next entity (Japan) in 2024?
jp_2024 = [e for e in data if e['name'] == 'Japan'][0]
jp_2024_gdp = {p['year']: p['value'] for p in jp_2024['points']}[2024]
print(f"\nCalifornia vs Japan 2024:")
print(f"  California: ${ca_gdp[2024]:.2f}B")
print(f"  Japan: ${jp_2024_gdp:.2f}B")
print(f"  California lead: ${ca_gdp[2024] - jp_2024_gdp:.2f}B")

# When did California surpass Japan for the first time, even if briefly?
print(f"\nYear-by-year California vs Japan:")
for y in range(2020, 2025):
    diff = ca_gdp[y] - jp_2024_gdp_dict[y] if y in ca_gdp else None

# Fix: use proper dict
jp_gdp = {p['year']: p['value'] for p in [e for e in data if e['name'] == 'Japan'][0]['points']}
for y in range(2018, 2025):
    ca_v = ca_gdp[y]
    jp_v = jp_gdp[y]
    diff = ca_v - jp_v
    marker = " <-- CA passes Japan!" if diff > 0 and (y == 1997 or ca_gdp[y-1] < jp_gdp[y-1]) else ""
    print(f"  {y}: CA ${ca_v:.2f}B vs JP ${jp_v:.2f}B (diff: ${diff:+.2f}B){marker}")

conn.close()
