"""
06_gap_sweep.py
Comprehensive sweep: what produces the biggest happiness gaps?
"""
import pandas as pd
import numpy as np
import duckdb

con = duckdb.connect()

df = con.execute('''
SELECT
    CASEID, CAST(STATEFIP AS INT) as STATEFIP,
    CAST(SCHAPPY AS INT) as SCHAPPY, CAST(AWBWT AS DOUBLE) as AWBWT,
    CAST(AGE AS INT) as AGE, CAST(SEX AS INT) as SEX,
    CAST(EDUC AS INT) as EDUC, CAST(RACE AS INT) as RACE,
    CAST(HISPAN AS INT) as HISPAN, CAST(MARST AS INT) as MARST,
    CAST(EMPSTAT AS INT) as EMPSTAT, CAST(FAMINCOME AS INT) as FAMINCOME,
    CAST(HHTENURE AS INT) as HHTENURE, CAST(HH_CHILD AS INT) as HH_CHILD,
    CAST(GENHEALTH AS INT) as GENHEALTH, CAST(METRO AS INT) as METRO,
    CAST(REGION AS INT) as REGION, CAST(MSASIZE AS INT) as MSASIZE,
    CAST(HH_SIZE AS INT) as HH_SIZE, CAST(CLWKR AS INT) as CLWKR,
    CAST(DIFFANY AS INT) as DIFFANY, CAST(VETSTAT AS INT) as VETSTAT
FROM read_parquet("/Users/azizsunderji/Dropbox/Home Economics/Data/atus_ipums.parquet")
WHERE CAST(SCHAPPY AS INT) BETWEEN 0 AND 6
''').df()

# Person-level: mean happiness + first value of all demographic columns
person = df.groupby('CASEID').agg(mean_happy=('SCHAPPY', 'mean')).reset_index()
demo_cols = ['AGE','SEX','EDUC','RACE','HISPAN','MARST','EMPSTAT','FAMINCOME',
             'HHTENURE','HH_CHILD','GENHEALTH','METRO','REGION','MSASIZE',
             'HH_SIZE','CLWKR','DIFFANY','VETSTAT','STATEFIP']
first_vals = df.drop_duplicates('CASEID').set_index('CASEID')[demo_cols]
person = person.join(first_vals, on='CASEID')

print(f'{len(person)} people, mean happiness = {person["mean_happy"].mean():.3f}')

results = []

def gap(label, a_name, a, b_name, b):
    if len(a) < 50 or len(b) < 50:
        return
    g = a['mean_happy'].mean() - b['mean_happy'].mean()
    results.append({'dimension': label, 'high': a_name, 'low': b_name,
        'mean_high': a['mean_happy'].mean(), 'mean_low': b['mean_happy'].mean(),
        'gap': g, 'n_high': len(a), 'n_low': len(b)})

p = person  # shorthand

# HEALTH (biggest expected gap)
gap('Excellent vs Poor health', 'Excellent', p[p['GENHEALTH']==1], 'Poor', p[p['GENHEALTH']==5])
gap('Excellent vs Fair health', 'Excellent', p[p['GENHEALTH']==1], 'Fair', p[p['GENHEALTH']==4])
gap('Excellent vs Good health', 'Excellent', p[p['GENHEALTH']==1], 'Good', p[p['GENHEALTH']==3])

# MARITAL
gap('Married vs Never married', 'Married', p[p['MARST']==1], 'Never married', p[p['MARST']==6])
gap('Married vs Divorced/Sep', 'Married', p[p['MARST']==1], 'Divorced/Sep', p[p['MARST'].isin([3,4])])
gap('Married vs Widowed', 'Married', p[p['MARST']==1], 'Widowed', p[p['MARST']==5])

# SEX
gap('Male vs Female', 'Male', p[p['SEX']==1], 'Female', p[p['SEX']==2])

# AGE
gap('Age 65+ vs 35-54', '65+', p[p['AGE']>=65], '35-54', p[p['AGE'].between(35,54)])
gap('Age 15-24 vs 35-54', '15-24', p[p['AGE'].between(15,24)], '35-54', p[p['AGE'].between(35,54)])

# EDUCATION
gap('Grad vs <HS', 'Grad degree', p[p['EDUC']>=43], '<HS', p[p['EDUC']<21])
gap("Bachelor's vs HS", "Bachelor's", p[p['EDUC'].between(40,42)], 'HS diploma', p[p['EDUC'].between(21,30)])

# INCOME
gap('Income $75k+ vs <$25k', '$75k+', p[p['FAMINCOME'].between(14,16)], '<$25k', p[p['FAMINCOME'].between(1,6)])
gap('Income $100k+ vs <$15k', '$100k+', p[p['FAMINCOME']==16], '<$15k', p[p['FAMINCOME'].between(1,4)])

# HOMEOWNERSHIP
gap('Owner vs Renter', 'Owner', p[p['HHTENURE']==1], 'Renter', p[p['HHTENURE']==2])

# KIDS
gap('Has kids vs No kids', 'Has kids', p[p['HH_CHILD']>0], 'No kids', p[p['HH_CHILD']==0])

# RACE
gap('White vs Black', 'White', p[p['RACE']==100], 'Black', p[p['RACE']==200])
hispanic = p[p['HISPAN'].between(100,412)]
nh_white = p[(p['RACE']==100) & (~p['HISPAN'].between(100,412))]
gap('Hispanic vs NH White', 'Hispanic', hispanic, 'NH White', nh_white)

# EMPLOYMENT
gap('Employed vs Unemployed', 'Employed', p[p['EMPSTAT']==1], 'Unemployed', p[p['EMPSTAT']==3])

# METRO/URBAN
gap('Suburban vs Central city', 'Suburban', p[p['METRO']==2], 'Central city', p[p['METRO']==1])
gap('Non-metro vs Central city', 'Non-metro', p[p['METRO'].isin([3,4])], 'Central city', p[p['METRO']==1])
gap('Non-metro vs Suburban', 'Non-metro', p[p['METRO'].isin([3,4])], 'Suburban', p[p['METRO']==2])
gap('Small MSA vs Large MSA', 'Small (<250k)', p[p['MSASIZE'].between(2,3)], 'Large (2.5M+)', p[p['MSASIZE'].between(6,7)])

# REGION
ne=p[p['REGION']==1]; mw=p[p['REGION']==2]; so=p[p['REGION']==3]; we=p[p['REGION']==4]
gap('Midwest vs West', 'Midwest', mw, 'West', we)
gap('South vs West', 'South', so, 'West', we)
gap('Midwest vs Northeast', 'Midwest', mw, 'Northeast', ne)
gap('South vs Northeast', 'South', so, 'Northeast', ne)
gap('West vs Northeast', 'West', we, 'Northeast', ne)
gap('Midwest vs South', 'Midwest', mw, 'South', so)

# DISABILITY
gap('No disability vs Disability', 'No disability', p[p['DIFFANY']==2], 'Disability', p[p['DIFFANY']==1])

# VETERAN
gap('Veteran vs Non-vet', 'Veteran', p[p['VETSTAT']==2], 'Non-vet', p[p['VETSTAT']==1])

# HH SIZE
gap('HH 4+ vs Alone', 'HH 4+', p[p['HH_SIZE']>=4], 'Alone', p[p['HH_SIZE']==1])

# SELF-EMPLOYED
gap('Self-employed vs Wage', 'Self-employed', p[p['CLWKR'].isin([1,2])], 'Wage', p[p['CLWKR'].isin([3,4,5,6])])

# GEOGRAPHY
sunbelt = [4,6,12,13,22,28,35,32,45,47,48,1]
gap('Sunbelt vs Non-Sunbelt', 'Sunbelt', p[p['STATEFIP'].isin(sunbelt)], 'Non-Sunbelt', p[~p['STATEFIP'].isin(sunbelt)])

deep_south = [1,13,22,28,45]
gap('Deep South vs Rest', 'Deep South', p[p['STATEFIP'].isin(deep_south)], 'Rest', p[~p['STATEFIP'].isin(deep_south)])

upper_mw = [19,27,38,46,55]
gap('Upper MW vs Rest', 'Upper MW', p[p['STATEFIP'].isin(upper_mw)], 'Rest', p[~p['STATEFIP'].isin(upper_mw)])

pacific = [6,41,53]
rust_belt = [17,18,26,39,42,54]
gap('Pacific vs Rust Belt', 'Pacific', p[p['STATEFIP'].isin(pacific)], 'Rust Belt', p[p['STATEFIP'].isin(rust_belt)])

mountain = [4,8,16,30,32,35,49,56]
gap('Mountain vs Pacific', 'Mountain', p[p['STATEFIP'].isin(mountain)], 'Pacific', p[p['STATEFIP'].isin(pacific)])

# Top/bottom states
state_means = p.groupby('STATEFIP').agg(m=('mean_happy','mean'), n=('mean_happy','count')).reset_index()
state_means = state_means[state_means['n'] >= 100]
top5 = state_means.nlargest(5, 'm')
bot5 = state_means.nsmallest(5, 'm')
top5_people = p[p['STATEFIP'].isin(top5['STATEFIP'])]
bot5_people = p[p['STATEFIP'].isin(bot5['STATEFIP'])]
gap('Happiest 5 states vs Unhappiest 5', 'Top 5 states', top5_people, 'Bottom 5 states', bot5_people)

# Print state ranking
print('\nState happiness ranking (n>=100):')
STATE_NAMES = {1:'AL',2:'AK',4:'AZ',5:'AR',6:'CA',8:'CO',9:'CT',10:'DE',11:'DC',12:'FL',13:'GA',
    15:'HI',16:'ID',17:'IL',18:'IN',19:'IA',20:'KS',21:'KY',22:'LA',23:'ME',24:'MD',25:'MA',
    26:'MI',27:'MN',28:'MS',29:'MO',30:'MT',31:'NE',32:'NV',33:'NH',34:'NJ',35:'NM',36:'NY',
    37:'NC',38:'ND',39:'OH',40:'OK',41:'OR',42:'PA',44:'RI',45:'SC',46:'SD',47:'TN',48:'TX',
    49:'UT',50:'VT',51:'VA',53:'WA',54:'WV',55:'WI',56:'WY'}
state_means['abbr'] = state_means['STATEFIP'].map(STATE_NAMES)
state_means = state_means.sort_values('m', ascending=False)
for _, r in state_means.head(10).iterrows():
    print(f"  {r['abbr']:4s} {r['m']:.3f} (n={r['n']})")
print('  ...')
for _, r in state_means.tail(10).iterrows():
    print(f"  {r['abbr']:4s} {r['m']:.3f} (n={r['n']})")

# SORT AND PRINT ALL GAPS
print('\n' + '='*115)
print('HAPPINESS GAPS — RANKED BY ABSOLUTE SIZE')
print('='*115)
res_df = pd.DataFrame(results)
res_df = res_df.sort_values('gap', key=abs, ascending=False)
for _, r in res_df.iterrows():
    print(f"  {r['dimension']:40s}  {r['high']:20s} {r['mean_high']:.3f}  vs  {r['low']:20s} {r['mean_low']:.3f}  gap={r['gap']:+.3f}  (n={r['n_high']:,} vs {r['n_low']:,})")
