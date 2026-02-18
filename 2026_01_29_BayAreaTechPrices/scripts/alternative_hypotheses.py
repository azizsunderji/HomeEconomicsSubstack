"""
Test alternative hypotheses for Bay Area SFR price gains:
1. Price level effect: expensive homes appreciate more
3. Mean reversion: areas that fell more 2022-2025 bounced back more Aug-Dec
"""

import pandas as pd
import numpy as np
import duckdb
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from scipy import stats

# Font setup
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'
plt.rcParams['svg.fonttype'] = 'none'

BLUE = '#0BB4FF'
BLACK = '#3D3733'
BG_CREAM = '#F6F7F3'
RED = '#F4743B'
GREEN = '#67A275'
YELLOW = '#FEC439'

# Load the analysis CSV (has tech share + Aug-Dec change)
df = pd.read_csv('/Users/azizsunderji/Dropbox/Home Economics/2026_01_29_BayAreaTechPrices/data/bay_area_zip_analysis.csv')
df['zip'] = df['zip'].astype(str).str.zfill(5)

# Pull prior-period change from the SFR file (May 2022 -> Aug 2025)
query = '''
SELECT
    CAST(RegionName AS VARCHAR) as zip,
    "2022-05-31" as price_may22,
    "2025-08-31" as price_aug25,
    "2025-08-31" as price_level,
    ("2025-08-31" - "2022-05-31") / "2022-05-31" * 100 as change_may22_aug25
FROM read_csv_auto('/Users/azizsunderji/Dropbox/Home Economics/2026_01_29_BayAreaTechPrices/data/Zip_zhvi_uc_sfr_sm_sa_month.csv')
WHERE StateName = 'CA'
  AND (Metro LIKE '%San Francisco%' OR Metro LIKE '%San Jose%')
  AND "2022-05-31" IS NOT NULL
  AND "2025-08-31" IS NOT NULL
'''
prior_df = duckdb.query(query).df()
prior_df['zip'] = prior_df['zip'].astype(str).str.zfill(5)

# Merge
df = df.merge(prior_df[['zip', 'price_level', 'change_may22_aug25']], on='zip', how='inner')
df = df.dropna(subset=['price_level', 'change_may22_aug25', 'change_aug_dec', 'info_pct'])

print(f"Working with {len(df)} zip codes\n")

# ── Bivariate correlations ──
r_tech, p_tech = stats.pearsonr(df['info_pct'], df['change_aug_dec'])
r_price, p_price = stats.pearsonr(df['price_level'], df['change_aug_dec'])
r_prior, p_prior = stats.pearsonr(df['change_may22_aug25'], df['change_aug_dec'])

print("=" * 60)
print("BIVARIATE CORRELATIONS WITH AUG-DEC PRICE CHANGE")
print("=" * 60)
print(f"  Tech share (info_pct):        r = {r_tech:+.3f}  (p = {p_tech:.4f})")
print(f"  Price level (Aug 2025):       r = {r_price:+.3f}  (p = {p_price:.4f})")
print(f"  Prior change (May22-Aug25):   r = {r_prior:+.3f}  (p = {p_prior:.4f})")

# ── Multivariate: OLS with all three ──
from numpy.linalg import lstsq

X = df[['info_pct', 'price_level', 'change_may22_aug25']].copy()
X['price_level_M'] = X['price_level'] / 1e6  # scale to millions
X = X.drop(columns='price_level')
y = df['change_aug_dec'].values

# Standardize for comparable coefficients
X_std = (X - X.mean()) / X.std()
X_std['const'] = 1
betas, residuals, rank, sv = lstsq(X_std.values, y, rcond=None)

# Get standard errors and t-stats
n = len(y)
k = X_std.shape[1]
y_hat = X_std.values @ betas
resid = y - y_hat
ss_res = np.sum(resid**2)
mse = ss_res / (n - k)
cov = mse * np.linalg.inv(X_std.values.T @ X_std.values)
se = np.sqrt(np.diag(cov))
t_stats = betas / se
r2 = 1 - ss_res / np.sum((y - y.mean())**2)

print(f"\n{'=' * 60}")
print(f"MULTIVARIATE REGRESSION (standardized betas)")
print(f"{'=' * 60}")
print(f"  R² = {r2:.3f}   n = {n}")
print(f"  {'Variable':30s} {'Beta':>8s} {'SE':>8s} {'t':>8s}")
print(f"  {'-'*56}")
names = ['Tech share (%)', 'Price level ($M)', 'Prior change (May22-Aug25)', 'Constant']
for name, b, s, t in zip(names, betas, se, t_stats):
    sig = '***' if abs(t) > 3.29 else '**' if abs(t) > 2.58 else '*' if abs(t) > 1.96 else ''
    print(f"  {name:30s} {b:+8.3f} {s:8.3f} {t:+8.2f} {sig}")

# ── Create 2-panel scatter figure ──
fig, axes = plt.subplots(1, 2, figsize=(16, 7.5))
fig.patch.set_facecolor(BG_CREAM)

# Panel 1: Price level vs Aug-Dec change
ax = axes[0]
ax.set_facecolor(BG_CREAM)
ax.scatter(df['price_level'] / 1e6, df['change_aug_dec'],
           s=60, c=BLUE, alpha=0.5, edgecolors=BLACK, linewidth=0.3, zorder=5)

z = np.polyfit(df['price_level'] / 1e6, df['change_aug_dec'], 1)
p = np.poly1d(z)
x_line = np.linspace(df['price_level'].min() / 1e6, df['price_level'].max() / 1e6, 100)
ax.plot(x_line, p(x_line), '--', color=RED, linewidth=2, alpha=0.8)

ax.axhline(y=0, color=BLACK, linewidth=0.8, alpha=0.3)
ax.set_xlabel('SFR Price Level, Aug 2025 ($M)', fontsize=11, color=BLACK)
ax.set_ylabel('Price Change, Aug–Dec 2025 (%)', fontsize=11, color=BLACK)
ax.set_title(f'Hypothesis 1: Price Level Effect\nr = {r_price:.2f}', fontsize=13, fontweight='bold', color=BLACK)
ax.grid(True, alpha=0.3, linewidth=0.5)
ax.set_axisbelow(True)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(axis='y', length=0)
ax.tick_params(colors=BLACK)

# Panel 2: Prior change vs Aug-Dec change
ax = axes[1]
ax.set_facecolor(BG_CREAM)
ax.scatter(df['change_may22_aug25'], df['change_aug_dec'],
           s=60, c=GREEN, alpha=0.5, edgecolors=BLACK, linewidth=0.3, zorder=5)

z2 = np.polyfit(df['change_may22_aug25'], df['change_aug_dec'], 1)
p2 = np.poly1d(z2)
x_line2 = np.linspace(df['change_may22_aug25'].min(), df['change_may22_aug25'].max(), 100)
ax.plot(x_line2, p2(x_line2), '--', color=RED, linewidth=2, alpha=0.8)

ax.axhline(y=0, color=BLACK, linewidth=0.8, alpha=0.3)
ax.axvline(x=0, color=BLACK, linewidth=0.8, alpha=0.3)
ax.set_xlabel('Prior SFR Change, May 2022–Aug 2025 (%)', fontsize=11, color=BLACK)
ax.set_ylabel('Price Change, Aug–Dec 2025 (%)', fontsize=11, color=BLACK)
ax.set_title(f'Hypothesis 3: Mean Reversion\nr = {r_prior:.2f}', fontsize=13, fontweight='bold', color=BLACK)
ax.grid(True, alpha=0.3, linewidth=0.5)
ax.set_axisbelow(True)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(axis='y', length=0)
ax.tick_params(colors=BLACK)

fig.suptitle('Alternative Hypotheses: What Else Explains Aug–Dec SFR Gains?',
             fontsize=15, fontweight='bold', color=BLACK, y=1.02)

fig.text(0.01, -0.04, 'Source: Zillow ZHVI SFR (Dec 2025), ACS 2023 5-Year Estimates',
         fontsize=8, color='#888888', style='italic')

plt.tight_layout()
plt.savefig('/Users/azizsunderji/Dropbox/Home Economics/2026_01_29_BayAreaTechPrices/outputs/alternative_hypotheses.png',
            dpi=100, bbox_inches='tight', facecolor=BG_CREAM)
plt.savefig('/Users/azizsunderji/Dropbox/Home Economics/2026_01_29_BayAreaTechPrices/outputs/alternative_hypotheses.svg',
            bbox_inches='tight', facecolor=BG_CREAM)
print("\nChart saved to outputs/alternative_hypotheses.png")
