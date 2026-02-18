"""
07_activity_level_regression.py
Redo core analysis at the activity level — the proper unit of analysis.
SCHAPPY ~ activity_type + demographics + geography, weighted by AWBWT.
"""
import pandas as pd
import numpy as np
import duckdb
import statsmodels.formula.api as smf
import statsmodels.api as sm

con = duckdb.connect()

df = con.execute('''
SELECT CASEID, CAST(YEAR AS INT) as YEAR,
    CAST(STATEFIP AS INT) as STATEFIP,
    CAST(COUNTY AS INT) as COUNTY,
    CAST(SCHAPPY AS INT) as SCHAPPY,
    CAST(ACTIVITY AS INT) as ACTIVITY,
    CAST(DURATION AS INT) as DURATION,
    CAST(AWBWT AS DOUBLE) as AWBWT,
    CAST(AGE AS INT) as AGE, CAST(SEX AS INT) as SEX,
    CAST(EDUC AS INT) as EDUC, CAST(RACE AS INT) as RACE,
    CAST(HISPAN AS INT) as HISPAN, CAST(MARST AS INT) as MARST,
    CAST(GENHEALTH AS INT) as GENHEALTH,
    CAST(METRO AS INT) as METRO, CAST(REGION AS INT) as REGION,
    CAST(FAMINCOME AS INT) as FAMINCOME,
    CAST(HH_SIZE AS INT) as HH_SIZE,
    CAST(HH_CHILD AS INT) as HH_CHILD,
    CAST(EMPSTAT AS INT) as EMPSTAT
FROM read_parquet("/Users/azizsunderji/Dropbox/Home Economics/Data/atus_ipums.parquet")
WHERE CAST(SCHAPPY AS INT) BETWEEN 0 AND 6
  AND CAST(GENHEALTH AS INT) BETWEEN 1 AND 5
''').df()

print(f"Loaded {len(df):,} activity-level observations, {df['CASEID'].nunique():,} people")

# =============================================
# Build variables
# =============================================

# Activity major category
def major_cat(code):
    m = code // 10000
    cats = {1:'PersonalCare',2:'Housework',3:'Childcare',4:'CareNonHH',
            5:'Work',6:'Education',7:'Shopping',8:'ProfServices',
            11:'Eating',12:'Socializing',13:'Sports',14:'Religious',
            15:'Volunteering',16:'PhoneCalls',18:'Travel'}
    return cats.get(m, 'Other')

df['activity_cat'] = df['ACTIVITY'].apply(major_cat)

# Demographics
df['married'] = (df['MARST'] == 1).astype(int)
df['female'] = (df['SEX'] == 2).astype(int)
df['age_c'] = df['AGE'] - 45  # centered
df['age_c_sq'] = df['age_c'] ** 2
df['college'] = (df['EDUC'] >= 40).astype(int)
df['non_metro'] = df['METRO'].isin([3, 4]).astype(int)
df['has_kids'] = (df['HH_CHILD'] > 0).astype(int)
df['black'] = (df['RACE'] == 200).astype(int)
df['hispanic'] = df['HISPAN'].between(100, 412).astype(int)

# Health dummies (reference = Good/3)
df['health_excellent'] = (df['GENHEALTH'] == 1).astype(int)
df['health_verygood'] = (df['GENHEALTH'] == 2).astype(int)
df['health_fair'] = (df['GENHEALTH'] == 4).astype(int)
df['health_poor'] = (df['GENHEALTH'] == 5).astype(int)

# Income buckets (reference = middle)
df['inc_low'] = df['FAMINCOME'].between(1, 6).astype(int)      # <$25k
df['inc_high'] = df['FAMINCOME'].between(14, 16).astype(int)    # $75k+

# Region dummies (reference = Northeast)
df['south'] = (df['REGION'] == 3).astype(int)
df['midwest'] = (df['REGION'] == 2).astype(int)
df['west'] = (df['REGION'] == 4).astype(int)

# Political lean from county/state data
votes_county = pd.read_parquet('data/county_votes_2020.parquet')
votes_state = pd.read_parquet('data/state_votes_2020.parquet')

df['state_fips'] = df['STATEFIP'].astype(str).str.zfill(2)
df['county_fips'] = np.where(
    df['COUNTY'] % 1000 > 0,
    df['STATEFIP'].astype(str).str.zfill(2) + (df['COUNTY'] % 1000).astype(str).str.zfill(3),
    None
)
county_map = votes_county.set_index('county_fips')['trump_share'].to_dict()
state_map = votes_state.set_index('state_fips')['trump_share'].to_dict()
df['trump_share'] = df['county_fips'].map(county_map).fillna(df['state_fips'].map(state_map))
df['trump_share_c'] = (df['trump_share'] - 50) / 10  # centered at 50, units = 10pp

# Drop categories with tiny samples
keep = df['activity_cat'].value_counts()
keep = keep[keep >= 100].index
df = df[df['activity_cat'].isin(keep)].copy()

# Normalize weights for WLS
df['wt'] = df['AWBWT'] / df['AWBWT'].mean()

print(f"After filtering: {len(df):,} observations")
print(f"Activity categories: {sorted(df['activity_cat'].unique())}")

# =============================================
# MODEL 1: Activity FE only (baseline)
# =============================================
print("\n" + "="*70)
print("MODEL 1: Activity fixed effects only")
print("="*70)

m1 = smf.wls('SCHAPPY ~ C(activity_cat)', data=df, weights=df['wt']).fit()
print(f"R² = {m1.rsquared:.4f}")

# =============================================
# MODEL 2: Activity FE + demographics
# =============================================
print("\n" + "="*70)
print("MODEL 2: Activity FE + demographics")
print("="*70)

formula2 = ('SCHAPPY ~ C(activity_cat) + married + female + age_c + age_c_sq + college '
            '+ has_kids + health_excellent + health_verygood + health_fair + health_poor '
            '+ inc_low + inc_high + black + hispanic + non_metro')
m2 = smf.wls(formula2, data=df, weights=df['wt']).fit()
print(f"R² = {m2.rsquared:.4f}")
print(f"ΔR² from adding demographics: {m2.rsquared - m1.rsquared:.4f}")

# Print coefficients sorted by magnitude
demo_vars = ['married','female','age_c','age_c_sq','college','has_kids',
             'health_excellent','health_verygood','health_fair','health_poor',
             'inc_low','inc_high','black','hispanic','non_metro']
print(f"\n{'Variable':25s} {'Coeff':>8s} {'Std Err':>8s} {'t':>7s} {'p':>7s}")
print("-"*60)
coefs = [(v, m2.params[v], m2.bse[v], m2.tvalues[v], m2.pvalues[v]) for v in demo_vars]
coefs.sort(key=lambda x: abs(x[1]), reverse=True)
for v, c, se, t, p in coefs:
    sig = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''
    print(f"  {v:23s} {c:+8.4f} {se:8.4f} {t:7.2f} {p:7.4f} {sig}")

# =============================================
# MODEL 3: Activity FE + demographics + region
# =============================================
print("\n" + "="*70)
print("MODEL 3: + Region")
print("="*70)

formula3 = formula2 + ' + south + midwest + west'
m3 = smf.wls(formula3, data=df, weights=df['wt']).fit()
print(f"R² = {m3.rsquared:.4f}")
print(f"ΔR² from adding region: {m3.rsquared - m2.rsquared:.4f}")
for v in ['south','midwest','west']:
    print(f"  {v:15s}: {m3.params[v]:+.4f} (p={m3.pvalues[v]:.4f})")

# =============================================
# MODEL 4: Activity FE + demographics + Trump share
# =============================================
print("\n" + "="*70)
print("MODEL 4: + Trump share (continuous)")
print("="*70)

formula4 = formula2 + ' + trump_share_c'
m4 = smf.wls(formula4, data=df, weights=df['wt']).fit()
print(f"R² = {m4.rsquared:.4f}")
print(f"Trump share coeff: {m4.params['trump_share_c']:+.4f} per 10pp (p={m4.pvalues['trump_share_c']:.4f})")
print("(This is the red-blue effect AFTER controlling for activity type and demographics)")

# =============================================
# MODEL 5: Full model with region + Trump share
# =============================================
print("\n" + "="*70)
print("MODEL 5: Activity FE + demographics + region + Trump share")
print("="*70)

formula5 = formula2 + ' + south + midwest + west + trump_share_c'
m5 = smf.wls(formula5, data=df, weights=df['wt']).fit()
print(f"R² = {m5.rsquared:.4f}")
print(f"\nFull coefficient table (demographics + geography):")
all_vars = demo_vars + ['south','midwest','west','trump_share_c']
coefs5 = [(v, m5.params[v], m5.bse[v], m5.tvalues[v], m5.pvalues[v]) for v in all_vars]
coefs5.sort(key=lambda x: abs(x[1]), reverse=True)
print(f"\n{'Variable':25s} {'Coeff':>8s} {'Std Err':>8s} {'t':>7s} {'p':>7s}")
print("-"*60)
for v, c, se, t, p in coefs5:
    sig = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''
    print(f"  {v:23s} {c:+8.4f} {se:8.4f} {t:7.2f} {p:7.4f} {sig}")

# =============================================
# SUMMARY: R² progression
# =============================================
print("\n" + "="*70)
print("R² PROGRESSION")
print("="*70)
print(f"  Activity type alone:                    {m1.rsquared:.4f}")
print(f"  + Demographics:                         {m2.rsquared:.4f}  (Δ = {m2.rsquared-m1.rsquared:.4f})")
print(f"  + Region:                               {m3.rsquared:.4f}  (Δ = {m3.rsquared-m2.rsquared:.4f})")
print(f"  + Trump share:                          {m4.rsquared:.4f}  (Δ = {m4.rsquared-m2.rsquared:.4f})")
print(f"  + Region + Trump share:                 {m5.rsquared:.4f}  (Δ = {m5.rsquared-m2.rsquared:.4f})")

# =============================================
# INTERACTION: Who benefits most from which activity?
# =============================================
print("\n" + "="*70)
print("INTERACTION: Married x Activity")
print("="*70)

# Which activities have the biggest married vs unmarried gap?
act_gaps = []
for cat in df['activity_cat'].unique():
    sub = df[df['activity_cat'] == cat]
    if len(sub) < 200:
        continue
    married_happy = np.average(sub[sub['married']==1]['SCHAPPY'], weights=sub[sub['married']==1]['wt'])
    single_happy = np.average(sub[sub['married']==0]['SCHAPPY'], weights=sub[sub['married']==0]['wt'])
    act_gaps.append({'activity': cat, 'married': married_happy, 'single': single_happy,
                     'gap': married_happy - single_happy, 'n': len(sub)})
act_gaps = pd.DataFrame(act_gaps).sort_values('gap', ascending=False)
print(f"\n{'Activity':20s} {'Married':>8s} {'Single':>8s} {'Gap':>8s}")
for _, r in act_gaps.iterrows():
    print(f"  {r['activity']:18s} {r['married']:8.3f} {r['single']:8.3f} {r['gap']:+8.3f}")

print("\n" + "="*70)
print("INTERACTION: Health x Activity")
print("="*70)

# Which activities have the biggest excellent vs poor health gap?
health_gaps = []
for cat in df['activity_cat'].unique():
    sub = df[df['activity_cat'] == cat]
    exc = sub[sub['health_excellent']==1]
    poor = sub[sub['health_poor']==1]
    if len(exc) < 30 or len(poor) < 30:
        continue
    exc_h = np.average(exc['SCHAPPY'], weights=exc['wt'])
    poor_h = np.average(poor['SCHAPPY'], weights=poor['wt'])
    health_gaps.append({'activity': cat, 'excellent': exc_h, 'poor': poor_h,
                        'gap': exc_h - poor_h})
health_gaps = pd.DataFrame(health_gaps).sort_values('gap', ascending=False)
print(f"\n{'Activity':20s} {'Excellent':>9s} {'Poor':>8s} {'Gap':>8s}")
for _, r in health_gaps.iterrows():
    print(f"  {r['activity']:18s} {r['excellent']:9.3f} {r['poor']:8.3f} {r['gap']:+8.3f}")
