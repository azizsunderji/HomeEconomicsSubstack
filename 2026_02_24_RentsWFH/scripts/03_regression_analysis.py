"""
03_regression_analysis.py — Regression models and DC decomposition.

Models:
1. Annual panel: rent_change ~ permits_pc + emp_growth + wfh_share (+ year FEs)
2. Leave-one-out (exclude DC) — same spec as Model 1

DC decomposition uses Model 1 coefficients.

2025 WFH fix: ACS 2025 was carried forward from 2024 (no real data).
We apply Bloom SWAA 2024→2025 decline ratios:
  DC: ×0.924 (-7.6%), all others: ×0.976 (-2.4%)

Output: data/regression_results.json, data/dc_decomposition.parquet
"""

import pandas as pd
import numpy as np
import duckdb
import json
import warnings
warnings.filterwarnings('ignore')

PROJECT = "/Users/azizsunderji/Dropbox/Home Economics/2026_02_23_DCRentDecline"
DATA = f"{PROJECT}/data"

con = duckdb.connect()

# ═══════════════════════════════════════════
# Load panels
# ═══════════════════════════════════════════
print("Loading panels...")
annual = con.execute(f"SELECT * FROM '{DATA}/metro_panel_annual.parquet'").df()
monthly = con.execute(f"SELECT * FROM '{DATA}/metro_panel_monthly.parquet'").df()

print(f"Annual panel: {annual.shape}, {annual['cbsa'].nunique()} metros")
print(f"Monthly panel: {monthly.shape}, {monthly['cbsa'].nunique()} metros")

# ═══════════════════════════════════════════
# Fix 2025 WFH using Bloom SWAA decline ratios
# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("FIXING 2025 WFH (ACS carried forward → Bloom SWAA adjustment)")
print("=" * 60)

wfh_xlsx = f"{PROJECT}/WFHtimeseries_monthly.xlsx"
wfh_city = pd.read_excel(wfh_xlsx, sheet_name="WFH by city")
wfh_city["date"] = pd.to_datetime(wfh_city["date"])
wfh_city["year"] = wfh_city["date"].dt.year

bloom = wfh_city.groupby("year").agg(
    dc=("wfhcovid_series_MA6_DC", "mean"),
    top10=("wfhcovid_series_top10_MA6_", "mean"),
    mid=("wfhcovid_series_11to50_MA6_", "mean"),
    other=("wfhcovid_series_other_MA6_", "mean"),
).reset_index()
bloom["national"] = (bloom["top10"] + bloom["mid"] + bloom["other"]) / 3

dc_ratio = bloom.loc[bloom["year"] == 2025, "dc"].values[0] / bloom.loc[bloom["year"] == 2024, "dc"].values[0]
nat_ratio = bloom.loc[bloom["year"] == 2025, "national"].values[0] / bloom.loc[bloom["year"] == 2024, "national"].values[0]

print(f"  Bloom DC decline 2024→2025: {(dc_ratio-1)*100:.1f}%")
print(f"  Bloom national decline 2024→2025: {(nat_ratio-1)*100:.1f}%")

# Apply to 2025 rows
mask_2025 = annual["year"] == 2025
mask_dc = annual["cbsa"] == "47900"
old_dc_wfh = annual.loc[mask_2025 & mask_dc, "wfh_pct"].values[0]
old_nat_wfh = annual.loc[mask_2025 & ~mask_dc, "wfh_pct"].mean()

annual.loc[mask_2025 & mask_dc, "wfh_pct"] = annual.loc[mask_2025 & mask_dc, "wfh_pct"] * dc_ratio
annual.loc[mask_2025 & ~mask_dc, "wfh_pct"] = annual.loc[mask_2025 & ~mask_dc, "wfh_pct"] * nat_ratio

new_dc_wfh = annual.loc[mask_2025 & mask_dc, "wfh_pct"].values[0]
new_nat_wfh = annual.loc[mask_2025 & ~mask_dc, "wfh_pct"].mean()
print(f"  DC WFH 2025: {old_dc_wfh:.2f}% → {new_dc_wfh:.2f}%")
print(f"  National avg WFH 2025: {old_nat_wfh:.2f}% → {new_nat_wfh:.2f}%")

# ═══════════════════════════════════════════
# Prepare regression variables
# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("Preparing regression variables...")

# Annual panel: Use 2018-2025 (need lag + base year)
reg = annual[annual['year'].between(2018, 2025)].copy()

# Dependent variable: YoY rent change
# Independent variables:
# - permits_5plus_lag1_pc: 5+ unit permits per 1000 workers, lagged 1 year
# - emp_yoy: total nonfarm employment YoY growth (%)
# - wfh_pct: WFH share of workers (%)

reg = reg.sort_values(['cbsa', 'year'])

# Drop rows with missing key variables
reg_complete = reg.dropna(subset=['zori_yoy', 'permits_5plus_lag1_pc', 'emp_yoy', 'wfh_pct'])
print(f"Complete cases: {len(reg_complete)} ({reg_complete['cbsa'].nunique()} metros)")
print(f"Year range: {reg_complete['year'].min()}-{reg_complete['year'].max()}")

# Summary stats
print("\nSummary statistics:")
for col in ['zori_yoy', 'permits_5plus_lag1_pc', 'emp_yoy', 'wfh_pct']:
    if col in reg_complete.columns:
        s = reg_complete[col].dropna()
        print(f"  {col:25s}: mean={s.mean():7.2f}, sd={s.std():7.2f}, min={s.min():7.2f}, max={s.max():7.2f}, n={len(s)}")

# ═══════════════════════════════════════════
# Model 1: Core regression (year FEs)
# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("MODEL 1: rent_change ~ permits_pc_lag1 + emp_growth + wfh_pct + year_FE")

try:
    import statsmodels.api as sm
    from statsmodels.formula.api import ols
except ImportError:
    print("Installing statsmodels...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'statsmodels'])
    import statsmodels.api as sm
    from statsmodels.formula.api import ols

# Create year dummies
reg_complete['year_str'] = reg_complete['year'].astype(str)

# OLS with year fixed effects
formula1 = 'zori_yoy ~ permits_5plus_lag1_pc + emp_yoy + wfh_pct + C(year_str)'
model1 = ols(formula1, data=reg_complete).fit(cov_type='cluster', cov_kwds={'groups': reg_complete['cbsa']})

print(model1.summary().tables[1].as_text())
print(f"\nR-squared: {model1.rsquared:.4f}")
print(f"Adj R-squared: {model1.rsquared_adj:.4f}")
print(f"N: {model1.nobs:.0f}")

# ═══════════════════════════════════════════
# Model 2: Without DC (leave-one-out)
# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("MODEL 2: Model 1 excluding DC (leave-one-out)")

reg_no_dc = reg_complete[reg_complete['cbsa'] != '47900']
model2 = ols(formula1, data=reg_no_dc).fit(cov_type='cluster', cov_kwds={'groups': reg_no_dc['cbsa']})

print(model2.summary().tables[1].as_text())
print(f"\nR-squared: {model2.rsquared:.4f}")
print(f"N: {model2.nobs:.0f}")

# Compare coefficients
print("\n" + "=" * 60)
print("COEFFICIENT COMPARISON (Model 1 vs Leave-one-out)")
for param in ['permits_5plus_lag1_pc', 'emp_yoy', 'wfh_pct']:
    if param in model1.params and param in model2.params:
        print(f"  {param:25s}: Full={model1.params[param]:7.3f}, No-DC={model2.params[param]:7.3f}")

# ═══════════════════════════════════════════
# DC DECOMPOSITION
# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("DC DECOMPOSITION")
print("=" * 60)

# Use Model 1 coefficients (permits + employment + WFH + year FEs)
# Decompose DC's rent change into:
# 1. National trend (year FE)
# 2. Supply effect (permits coefficient × DC permits)
# 3. Employment effect (emp coefficient × DC emp growth)
# 4. WFH effect (WFH coefficient × DC WFH share)
# 5. Residual

# Get coefficients
beta_permits = model1.params.get('permits_5plus_lag1_pc', 0)
beta_emp = model1.params.get('emp_yoy', 0)
beta_wfh = model1.params.get('wfh_pct', 0)
intercept = model1.params.get('Intercept', 0)

print(f"\nModel 1 coefficients:")
print(f"  Permits 5+ (lag1, per 1K workers): {beta_permits:.4f}")
print(f"  Employment growth (%):             {beta_emp:.4f}")
print(f"  WFH share (%):                     {beta_wfh:.4f}")

# DC values for each year
dc = reg_complete[reg_complete['cbsa'] == '47900'].sort_values('year')
print(f"\nDC values used for decomposition:")
print(dc[['year', 'zori_yoy', 'permits_5plus_lag1_pc', 'emp_yoy', 'wfh_pct']].to_string(index=False))

# Get national averages for comparison
national_means = reg_complete.groupby('year')[['permits_5plus_lag1_pc', 'emp_yoy', 'wfh_pct']].mean()
print(f"\nNational averages:")
print(national_means.to_string())

# Decomposition: compare DC to average metro
# DC's excess rent change = DC_actual - predicted_for_average_metro
# Attribution = β × (DC_value - national_avg)

decomp_records = []
for _, row in dc.iterrows():
    year = row['year']
    if year not in national_means.index:
        continue
    nat = national_means.loc[year]

    actual_yoy = row['zori_yoy']

    # Predicted for DC using model
    year_fe_key = f"C(year_str)[T.{int(year)}]"
    year_fe = model1.params.get(year_fe_key, 0) + intercept

    supply_effect = beta_permits * row['permits_5plus_lag1_pc']
    emp_effect = beta_emp * row['emp_yoy']
    wfh_effect = beta_wfh * row['wfh_pct']
    predicted = year_fe + supply_effect + emp_effect + wfh_effect
    residual = actual_yoy - predicted

    # Also decompose relative to national average
    supply_excess = beta_permits * (row['permits_5plus_lag1_pc'] - nat['permits_5plus_lag1_pc'])
    emp_excess = beta_emp * (row['emp_yoy'] - nat['emp_yoy'])
    wfh_excess = beta_wfh * (row['wfh_pct'] - nat['wfh_pct'])

    decomp_records.append({
        'year': int(year),
        'actual_yoy': actual_yoy,
        'year_fe': year_fe,
        'supply_effect': supply_effect,
        'emp_effect': emp_effect,
        'wfh_effect': wfh_effect,
        'predicted': predicted,
        'residual': residual,
        'supply_excess': supply_excess,
        'emp_excess': emp_excess,
        'wfh_excess': wfh_excess,
    })

decomp = pd.DataFrame(decomp_records)
print("\n" + "=" * 60)
print("DC DECOMPOSITION: Predicted vs Actual Rent Change (YoY %)")
print("=" * 60)
print(decomp[['year', 'actual_yoy', 'predicted', 'residual',
              'year_fe', 'supply_effect', 'emp_effect', 'wfh_effect']].to_string(index=False))

print("\n" + "=" * 60)
print("DC EXCESS vs NATIONAL AVERAGE (pp contribution)")
print("=" * 60)
print(decomp[['year', 'supply_excess', 'emp_excess', 'wfh_excess']].to_string(index=False))

# Cumulative decomposition: 2019 → latest
# What explains DC's rent trajectory relative to peers?
max_year = int(decomp['year'].max())
print("\n" + "=" * 60)
print(f"CUMULATIVE EXCESS (2019-{max_year} average, pp vs national avg)")
means = decomp[decomp['year'].between(2019, max_year)][['supply_excess', 'emp_excess', 'wfh_excess']].mean()
print(means.to_string())
print(f"Total excess: {means.sum():.2f} pp")

# Latest year (2024) decomposition for the waterfall chart
latest = decomp[decomp['year'] == decomp['year'].max()].iloc[0]
print(f"\nLatest year ({int(latest['year'])}) decomposition:")
print(f"  Actual rent change:  {latest['actual_yoy']:.2f}%")
print(f"  Year fixed effect:   {latest['year_fe']:.2f}%")
print(f"  Supply effect:       {latest['supply_effect']:.2f}%")
print(f"  Employment effect:   {latest['emp_effect']:.2f}%")
print(f"  WFH effect:          {latest['wfh_effect']:.2f}%")
print(f"  Predicted:           {latest['predicted']:.2f}%")
print(f"  Residual:            {latest['residual']:.2f}%")

# ═══════════════════════════════════════════
# Cross-metro scatter data
# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("SCATTER PLOT DATA")

# Latest year data for scatter plots
scatter_year = int(reg_complete['year'].max())
scatter = reg_complete[reg_complete['year'] == scatter_year].copy()
scatter['is_dc'] = scatter['cbsa'] == '47900'

print(f"\nMetros in {scatter_year}: {len(scatter)}")
scatter_cols = ['cbsa', 'RegionName', 'zori_yoy', 'permits_5plus_lag1_pc',
                'emp_yoy', 'wfh_pct', 'is_dc']
scatter_data = scatter[[c for c in scatter_cols if c in scatter.columns]].copy()
scatter_data.to_parquet(f"{DATA}/scatter_data_{scatter_year}.parquet", index=False)
print("Saved scatter data")

# Also compute 2019→latest cumulative rent change for scatter
latest_year = int(annual['year'].max())
rent_2019 = annual[annual['year'] == 2019][['cbsa', 'zori']].rename(columns={'zori': 'zori_2019'})
rent_latest = annual[annual['year'] == latest_year][['cbsa', 'zori']].rename(columns={'zori': f'zori_{latest_year}'})
rent_change = rent_2019.merge(rent_latest, on='cbsa')
rent_change['rent_change_pct'] = (rent_change[f'zori_{latest_year}'] / rent_change['zori_2019'] - 1) * 100

# Add cumulative permits (lag for what built by latest year)
permits_years = (2019, latest_year - 1)
permits_cum = annual[annual['year'].between(*permits_years)].groupby('cbsa').agg(
    cum_permits_5plus_lag1=('permits_5plus_lag1', 'sum'),
    avg_emp_yoy=('emp_yoy', 'mean'),
    avg_wfh=('wfh_pct', 'mean'),
).reset_index()

cum_scatter = rent_change.merge(permits_cum, on='cbsa', how='inner')
cum_scatter = cum_scatter.merge(
    annual[annual['year']==latest_year][['cbsa', 'RegionName', 'employed_pop']], on='cbsa', how='left')
# Normalize cumulative permits
cum_scatter['cum_permits_pc'] = cum_scatter['cum_permits_5plus_lag1'] / cum_scatter['employed_pop'] * 1000
cum_scatter['is_dc'] = cum_scatter['cbsa'] == '47900'

print(f"\nCumulative scatter (2019-{latest_year}): {len(cum_scatter)} metros")
print("\nDC in cumulative scatter:")
print(cum_scatter[cum_scatter['is_dc']][['cbsa', 'rent_change_pct', 'cum_permits_pc', 'avg_emp_yoy', 'avg_wfh']].to_string(index=False))

cum_scatter.to_parquet(f"{DATA}/scatter_cumulative.parquet", index=False)

# ═══════════════════════════════════════════
# Save all results
# ═══════════════════════════════════════════
# Cross-sectional model comparison (2025 only, no year FEs)
# Shows permits vs full model for within-year variation
# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("CROSS-SECTIONAL MODEL COMPARISON (2025 only)")

cs_2025 = reg_complete[reg_complete['year'] == 2025].copy()
print(f"2025 metros: {len(cs_2025)}")

# Permits-only (no year FE — single year)
formula_cs_permits = 'zori_yoy ~ permits_5plus_lag1_pc'
model_cs_permits = ols(formula_cs_permits, data=cs_2025).fit(
    cov_type='cluster', cov_kwds={'groups': cs_2025['cbsa']})
cs_2025['pred_permits'] = model_cs_permits.predict(cs_2025)

# Full model (no year FE)
formula_cs_full = 'zori_yoy ~ permits_5plus_lag1_pc + emp_yoy + wfh_pct'
model_cs_full = ols(formula_cs_full, data=cs_2025).fit(
    cov_type='cluster', cov_kwds={'groups': cs_2025['cbsa']})
cs_2025['pred_full'] = model_cs_full.predict(cs_2025)

# Permits + employment only (to show incremental value)
formula_cs_pe = 'zori_yoy ~ permits_5plus_lag1_pc + emp_yoy'
model_cs_pe = ols(formula_cs_pe, data=cs_2025).fit(
    cov_type='cluster', cov_kwds={'groups': cs_2025['cbsa']})
cs_2025['pred_permits_emp'] = model_cs_pe.predict(cs_2025)

cs_2025['is_dc'] = cs_2025['cbsa'] == '47900'

print(f"\nCross-sectional R² (2025, {len(cs_2025)} metros):")
print(f"  Permits only:          R² = {model_cs_permits.rsquared:.4f}")
print(f"  Permits + Employment:  R² = {model_cs_pe.rsquared:.4f}")
print(f"  Full (+ WFH):          R² = {model_cs_full.rsquared:.4f}")
print(f"\nPermits-only coefficients:")
print(model_cs_permits.summary().tables[1].as_text())
print(f"\nFull model coefficients:")
print(model_cs_full.summary().tables[1].as_text())

dc_cs = cs_2025[cs_2025['is_dc']].iloc[0]
print(f"\nDC 2025:")
print(f"  Actual:           {dc_cs['zori_yoy']:.2f}%")
print(f"  Permits-only:     {dc_cs['pred_permits']:.2f}%  (miss: {dc_cs['zori_yoy'] - dc_cs['pred_permits']:.2f}pp)")
print(f"  Permits + Emp:    {dc_cs['pred_permits_emp']:.2f}%  (miss: {dc_cs['zori_yoy'] - dc_cs['pred_permits_emp']:.2f}pp)")
print(f"  Full model:       {dc_cs['pred_full']:.2f}%  (miss: {dc_cs['zori_yoy'] - dc_cs['pred_full']:.2f}pp)")

# Save for chart
cs_chart = cs_2025[['cbsa', 'RegionName', 'zori_yoy', 'permits_5plus_lag1_pc', 'emp_yoy', 'wfh_pct',
                     'pred_permits', 'pred_permits_emp', 'pred_full', 'is_dc']].copy()
cs_chart.to_parquet(f"{DATA}/cross_sectional_2025.parquet", index=False)
print(f"\nSaved cross_sectional_2025.parquet ({len(cs_chart)} rows)")

# ═══════════════════════════════════════════
# Cumulative cross-sectional regressions (2019-2025, one obs per metro)
# These use scatter_cumulative.parquet which has cum rent change, avg emp, avg wfh, cum permits
# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("CUMULATIVE CROSS-SECTION (2019-2025)")

cum_df = con.execute(f"SELECT * FROM '{DATA}/scatter_cumulative.parquet'").df()
cum_df = cum_df.dropna(subset=['rent_change_pct', 'cum_permits_pc', 'avg_emp_yoy', 'avg_wfh'])
print(f"Metros: {len(cum_df)}")

model_cum_permits = ols('rent_change_pct ~ cum_permits_pc', data=cum_df).fit()
model_cum_full = ols('rent_change_pct ~ cum_permits_pc + avg_emp_yoy + avg_wfh', data=cum_df).fit()

cum_df['pred_permits'] = model_cum_permits.predict(cum_df)
cum_df['pred_full'] = model_cum_full.predict(cum_df)
cum_df['is_dc'] = cum_df['cbsa'] == '47900'
cum_df.to_parquet(f"{DATA}/scatter_cumulative.parquet", index=False)

r2_cum_permits = model_cum_permits.rsquared
r2_cum_full = model_cum_full.rsquared

print(f"  Permits only R²: {r2_cum_permits:.4f}")
print(f"  Full model R²:   {r2_cum_full:.4f}")
print(f"\nFull model coefficients:")
print(model_cum_full.summary().tables[1].as_text())

dc_cum = cum_df[cum_df['is_dc']].iloc[0]
print(f"\nDC cumulative:")
print(f"  Actual:       {dc_cum['rent_change_pct']:.1f}%")
print(f"  Permits-only: {dc_cum['pred_permits']:.1f}%  (miss: {dc_cum['rent_change_pct'] - dc_cum['pred_permits']:.1f}pp)")
print(f"  Full model:   {dc_cum['pred_full']:.1f}%  (miss: {dc_cum['rent_change_pct'] - dc_cum['pred_full']:.1f}pp)")

# ═══════════════════════════════════════════
results = {
    'model1_coefficients': {
        'permits_5plus_lag1_pc': float(beta_permits),
        'emp_yoy': float(beta_emp),
        'wfh_pct': float(beta_wfh),
        'intercept': float(intercept),
    },
    'model1_rsquared': float(model1.rsquared),
    'model1_nobs': int(model1.nobs),
    'model1_pvalues': {k: float(v) for k, v in model1.pvalues.items() if not k.startswith('C(')},
    'decomposition': decomp.to_dict(orient='records'),
    'dc_latest': {
        'year': int(latest['year']),
        'actual_yoy': float(latest['actual_yoy']),
        'supply_effect': float(latest['supply_effect']),
        'emp_effect': float(latest['emp_effect']),
        'wfh_effect': float(latest['wfh_effect']),
        'residual': float(latest['residual']),
    },
    'scatter_year_range': f"2019-{latest_year}",
    'cum_permits_r2': float(r2_cum_permits),
    'cum_full_r2': float(r2_cum_full),
}

with open(f"{DATA}/regression_results.json", 'w') as f:
    json.dump(results, f, indent=2)

decomp.to_parquet(f"{DATA}/dc_decomposition.parquet", index=False)
print("\nSaved regression results and decomposition")

# ═══════════════════════════════════════════
# Monthly rent trajectory data for chart
# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("RENT TRAJECTORY DATA")

# DC vs national rent index (Jan 2019 = 100)
zori = con.execute(f"""
    SELECT RegionName, date, zori
    FROM '{DATA}/zori_metro.parquet'
    WHERE RegionType = 'msa' OR RegionType = 'country'
""").df()

# Get DC and US
trajectory = zori[zori['RegionName'].isin(['Washington, DC', 'United States'])].copy()
trajectory = trajectory.sort_values(['RegionName', 'date'])

# Index to Jan 2019
for metro in trajectory['RegionName'].unique():
    mask = trajectory['RegionName'] == metro
    base_val = trajectory.loc[mask & (trajectory['date'] == '2019-01-31'), 'zori']
    if len(base_val) > 0:
        trajectory.loc[mask, 'rent_index'] = trajectory.loc[mask, 'zori'] / base_val.values[0] * 100

# Add a few comparison metros
comparison_metros = ['Austin, TX', 'Nashville, TN', 'New York, NY', 'San Francisco, CA',
                     'Phoenix, AZ', 'Seattle, WA', 'Raleigh, NC', 'Denver, CO']
for metro in comparison_metros:
    metro_data = zori[zori['RegionName'] == metro].copy()
    base_val = metro_data.loc[metro_data['date'] == '2019-01-31', 'zori']
    if len(base_val) > 0:
        metro_data['rent_index'] = metro_data['zori'] / base_val.values[0] * 100
        trajectory = pd.concat([trajectory, metro_data[['RegionName', 'date', 'zori', 'rent_index']]])

trajectory = trajectory[trajectory['date'] >= '2019-01-01']
trajectory.to_parquet(f"{DATA}/rent_trajectory.parquet", index=False)
print(f"Saved rent trajectory: {trajectory['RegionName'].nunique()} metros")

# Final DC vs national snapshot
dc_traj = trajectory[trajectory['RegionName'] == 'Washington, DC'].sort_values('date')
us_traj = trajectory[trajectory['RegionName'] == 'United States'].sort_values('date')
print(f"\nDC rent index: {dc_traj.iloc[-1]['rent_index']:.1f} (Jan 2019 = 100)")
print(f"US rent index: {us_traj.iloc[-1]['rent_index']:.1f} (Jan 2019 = 100)")
print(f"DC underperformance: {dc_traj.iloc[-1]['rent_index'] - us_traj.iloc[-1]['rent_index']:.1f} pp")
