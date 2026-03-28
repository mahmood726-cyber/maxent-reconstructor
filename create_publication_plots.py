"""
Create publication-quality plots with available data.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats

# Set publication style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

# Publication settings
plt.rcParams.update({
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'figure.dpi': 150,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'axes.linewidth': 0.8,
    'grid.linewidth': 0.5,
})

# Create figures directory
fig_dir = Path('C:/Users/user/maxent-reconstructor/figures')
fig_dir.mkdir(exist_ok=True)

print("="*70)
print("CREATING PUBLICATION-QUALITY FIGURES")
print("="*70)

# Load data
print("\nLoading validation data...")
real_data = pd.read_csv('C:/Users/user/maxent-reconstructor/real_data_validation_results.csv')
ipdagd_data = pd.read_csv('C:/Users/user/maxent-reconstructor/ipdagd_comparison_results.csv')

print(f"Real data validation: {len(real_data)} rows")
print(f"IPDfromAGD comparison: {len(ipdagd_data)} rows")

# Focus on median (quantile = 0.5) for main analysis
real_median = real_data[real_data['quantile'] == 0.5].copy()

# ============================================================================
# FIGURE 1: Overview of MaxEnt Performance
# ============================================================================
print("\nCreating Figure 1: Overview...")

fig, axes = plt.subplots(1, 3, figsize=(14, 4))

# Panel A: Error distribution (real data)
ax = axes[0]
ax.hist(real_median['naive_error_pct'], bins=40, alpha=0.6, label='Naive Normal',
        color='#E74C3C', edgecolor='white', linewidth=0.5)
ax.hist(real_median['maxent_error_pct'], bins=40, alpha=0.6, label='MaxEnt',
        color='#3498DB', edgecolor='white', linewidth=0.5)
ax.set_xlabel('Absolute Median Error (%)', fontweight='bold')
ax.set_ylabel('Frequency', fontweight='bold')
ax.set_title('(A) Error Distribution', fontweight='bold')
ax.legend(loc='upper right', frameon=True, shadow=True)
max_err = min(100, real_median[['naive_error_pct', 'maxent_error_pct']].max().max() * 1.05)
ax.set_xlim(0, max_err)

# Panel B: Win rate by quantile
ax = axes[1]
quantiles = [0.1, 0.25, 0.5, 0.75, 0.9]
win_rates = []
for q in quantiles:
    q_data = real_data[real_data['quantile'] == q]
    wr = (q_data['maxent_error_pct'] < q_data['naive_error_pct']).mean() * 100
    win_rates.append(wr)

quantile_labels = ['Q10', 'Q25', 'Q50', 'Q75', 'Q90']
colors = ['#3498DB' if wr > 50 else '#E74C3C' for wr in win_rates]
bars = ax.bar(quantile_labels, win_rates, color=colors, edgecolor='black', linewidth=0.8, alpha=0.8)
ax.axhline(50, color='gray', linestyle='--', linewidth=1, alpha=0.7)
ax.set_ylabel('MaxEnt Win Rate (%)', fontweight='bold')
ax.set_title('(B) Win Rate by Quantile', fontweight='bold')
ax.set_ylim(0, 100)
ax.grid(axis='y', alpha=0.3)
for bar, wr in zip(bars, win_rates):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
           f'{wr:.0f}%', ha='center', va='bottom', fontweight='bold', fontsize=9)

# Panel C: IPDfromAGD comparison
ax = axes[2]
methods = ['Naive', 'MaxEnt']
mean_errors = [
    ipdagd_data['naive_error'].mean(),
    ipdagd_data['maxent_error'].mean()
]
median_errors = [
    ipdagd_data['naive_error'].median(),
    ipdagd_data['maxent_error'].median()
]

x = np.arange(len(methods))
width = 0.35
bars1 = ax.bar(x - width/2, mean_errors, width, label='Mean Error',
              color='#9B59B6', edgecolor='black', linewidth=0.5, alpha=0.8)
bars2 = ax.bar(x + width/2, median_errors, width, label='Median Error',
              color='#16A085', edgecolor='black', linewidth=0.5, alpha=0.8)
ax.set_ylabel('Error (%)', fontweight='bold')
ax.set_title('(C) IPDfromAGD Comparison (50 simulations)', fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(methods)
ax.legend()
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(fig_dir / 'figure1_overview.png')
plt.savefig(fig_dir / 'figure1_overview.pdf')
print(f"  Saved: {fig_dir / 'figure1_overview.png'}")

# ============================================================================
# FIGURE 2: Performance Characteristics
# ============================================================================
print("\nCreating Figure 2: Performance Characteristics...")

fig, axes = plt.subplots(1, 3, figsize=(14, 4))

# Panel A: Error vs CV
ax = axes[0]
cv_bins = pd.cut(real_median['cv'], bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0, 2.0],
                 labels=['<0.2', '0.2-0.4', '0.4-0.6', '0.6-0.8', '0.8-1.0', '>1.0'])
cv_summary = real_median.groupby(cv_bins, observed=True).agg({
    'naive_error_pct': 'mean',
    'maxent_error_pct': 'mean'
})

x = np.arange(len(cv_summary))
width = 0.35
ax.bar(x - width/2, cv_summary['naive_error_pct'], width, label='Naive Normal',
      color='#E74C3C', edgecolor='black', linewidth=0.5, alpha=0.8)
ax.bar(x + width/2, cv_summary['maxent_error_pct'], width, label='MaxEnt',
      color='#3498DB', edgecolor='black', linewidth=0.5, alpha=0.8)
ax.set_xlabel('Coefficient of Variation', fontweight='bold')
ax.set_ylabel('Mean Median Error (%)', fontweight='bold')
ax.set_title('(A) Error vs. Variability', fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(cv_summary.index, rotation=45, ha='right')
ax.legend()
ax.grid(axis='y', alpha=0.3)

# Panel B: Error vs Sample Size
ax = axes[1]
n_bins = pd.cut(real_median['n'], bins=[0, 20, 50, 100, 200, 500, 10000],
               labels=['<=20', '21-50', '51-100', '101-200', '201-500', '>500'])
n_summary = real_median.groupby(n_bins, observed=True).agg({
    'naive_error_pct': 'mean',
    'maxent_error_pct': 'mean'
})

x = np.arange(len(n_summary))
ax.bar(x - width/2, n_summary['naive_error_pct'], width, label='Naive Normal',
      color='#E74C3C', edgecolor='black', linewidth=0.5, alpha=0.8)
ax.bar(x + width/2, n_summary['maxent_error_pct'], width, label='MaxEnt',
      color='#3498DB', edgecolor='black', linewidth=0.5, alpha=0.8)
ax.set_xlabel('Sample Size (n)', fontweight='bold')
ax.set_ylabel('Mean Median Error (%)', fontweight='bold')
ax.set_title('(B) Error vs. Sample Size', fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(n_summary.index, rotation=45, ha='right')
ax.legend()
ax.grid(axis='y', alpha=0.3)

# Panel C: Win rate by dataset
ax = axes[2]
source_summary = real_median.groupby('dataset').apply(
    lambda x: (x['maxent_error_pct'] < x['naive_error_pct']).mean() * 100
).sort_values(ascending=False)

colors = ['#3498DB' if wr > 50 else '#E74C3C' for wr in source_summary.values]
bars = ax.barh(range(len(source_summary)), source_summary.values,
              color=colors, edgecolor='black', linewidth=0.5, alpha=0.8)
ax.set_yticks(range(len(source_summary)))
short_names = [s.replace('metadat_dat.', '')[:15] for s in source_summary.index]
ax.set_yticklabels(short_names, fontsize=8)
ax.set_xlabel('MaxEnt Win Rate (%)', fontweight='bold')
ax.set_title('(C) Win Rate by Dataset', fontweight='bold')
ax.axvline(50, color='gray', linestyle='--', linewidth=1, alpha=0.7)
ax.grid(axis='x', alpha=0.3)
ax.set_xlim(0, 100)

plt.tight_layout()
plt.savefig(fig_dir / 'figure2_performance.png')
plt.savefig(fig_dir / 'figure2_performance.pdf')
print(f"  Saved: {fig_dir / 'figure2_performance.png'}")

# ============================================================================
# FIGURE 3: Scatter Comparison
# ============================================================================
print("\nCreating Figure 3: Scatter Comparison...")

fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))

# Panel A: Naive
ax = axes[0]
ax.scatter(real_median['true_value'], real_median['naive_value'],
          alpha=0.4, color='#E74C3C', s=20, edgecolors='none')
min_val = min(real_median['true_value'].min(), real_median['naive_value'].min())
max_val = max(real_median['true_value'].max(), real_median['naive_value'].max())
ax.plot([min_val, max_val], [min_val, max_val], 'k--', linewidth=1.5, alpha=0.7)
ax.set_xlabel('True Median', fontweight='bold')
ax.set_ylabel('Estimated Median (Naive)', fontweight='bold')
ax.set_title('(A) Naive Normal', fontweight='bold')
ax.grid(True, alpha=0.3)

# Panel B: MaxEnt
ax = axes[1]
ax.scatter(real_median['true_value'], real_median['maxent_value'],
          alpha=0.4, color='#3498DB', s=20, edgecolors='none')
ax.plot([min_val, max_val], [min_val, max_val], 'k--', linewidth=1.5, alpha=0.7)
ax.set_xlabel('True Median', fontweight='bold')
ax.set_ylabel('Estimated Median (MaxEnt)', fontweight='bold')
ax.set_title('(B) MaxEnt', fontweight='bold')
ax.grid(True, alpha=0.3)

# Panel C: Error comparison
ax = axes[2]
maxent_better = real_median['maxent_error_pct'] < real_median['naive_error_pct']
ax.scatter(real_median.loc[~maxent_better, 'naive_error_pct'],
          real_median.loc[~maxent_better, 'maxent_error_pct'],
          alpha=0.5, color='#E74C3C', s=20, label='Naive Better', edgecolors='none')
ax.scatter(real_median.loc[maxent_better, 'naive_error_pct'],
          real_median.loc[maxent_better, 'maxent_error_pct'],
          alpha=0.5, color='#3498DB', s=20, label='MaxEnt Better', edgecolors='none')
max_err = max(real_median['naive_error_pct'].max(), real_median['maxent_error_pct'].max()) * 1.1
ax.plot([0, max_err], [0, max_err], 'k--', linewidth=1.5, alpha=0.7)
ax.set_xlabel('Naive Error (%)', fontweight='bold')
ax.set_ylabel('MaxEnt Error (%)', fontweight='bold')
ax.set_title('(C) Method Comparison', fontweight='bold')
ax.legend()
ax.grid(True, alpha=0.3)
ax.set_xlim(0, max_err)
ax.set_ylim(0, max_err)

plt.tight_layout()
plt.savefig(fig_dir / 'figure3_scatter.png')
plt.savefig(fig_dir / 'figure3_scatter.pdf')
print(f"  Saved: {fig_dir / 'figure3_scatter.png'}")

# ============================================================================
# FIGURE 4: Summary Statistics
# ============================================================================
print("\nCreating Figure 4: Summary...")

fig, axes = plt.subplots(1, 2, figsize=(12, 4))

# Panel A: Improvement histogram
ax = axes[0]
improvement = 100 * (1 - real_median['maxent_error_pct'] / real_median['naive_error_pct'])
ax.hist(improvement, bins=40, color='#3498DB', edgecolor='white',
       linewidth=0.5, alpha=0.7)
ax.axvline(0, color='black', linestyle='-', linewidth=1.5)
ax.axvline(improvement.mean(), color='green', linestyle='--',
          linewidth=2, label=f'Mean: {improvement.mean():.1f}%')
ax.axvline(improvement.median(), color='orange', linestyle='--',
          linewidth=2, label=f'Median: {improvement.median():.1f}%')
ax.set_xlabel('Percentage Improvement', fontweight='bold')
ax.set_ylabel('Frequency', fontweight='bold')
ax.set_title('(A) Distribution of MaxEnt Improvements', fontweight='bold')
ax.legend()
ax.grid(axis='y', alpha=0.3)

# Panel B: Summary table
ax = axes[1]
ax.axis('off')

win_rate = (real_median['maxent_error_pct'] < real_median['naive_error_pct']).mean() * 100

summary_stats = [
    ['Metric', 'Value', ''],
    ['='*30, '='*30, ''],
    ['Total Comparisons', f'{len(real_median):,}', ''],
    ['MaxEnt Win Rate', f'{win_rate:.1f}%', ''],
    ['', '', ''],
    ['Median Error (Q50)', '', ''],
    ['  - Naive Normal', f'{real_median["naive_error_pct"].median():.2f}%', ''],
    ['  - MaxEnt', f'{real_median["maxent_error_pct"].median():.2f}%', ''],
    ['', '', ''],
    ['Mean Error (Q50)', '', ''],
    ['  - Naive Normal', f'{real_median["naive_error_pct"].mean():.2f}%', ''],
    ['  - MaxEnt', f'{real_median["maxent_error_pct"].mean():.2f}%', ''],
    ['', '', ''],
    ['Improvement', f'{improvement.mean():.1f}%', '(mean)'],
    ['', f'{improvement.median():.1f}%', '(median)'],
]

table = ax.table(cellText=summary_stats, cellLoc='left', loc='center',
                colWidths=[0.6, 0.3, 0.1])
table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1, 2)

for i in range(3):
    table[(0, i)].set_facecolor('#3498DB')
    table[(0, i)].set_text_props(weight='bold', color='white')

ax.set_title('(B) Summary Statistics', fontweight='bold', pad=20)

plt.tight_layout()
plt.savefig(fig_dir / 'figure4_summary.png')
plt.savefig(fig_dir / 'figure4_summary.pdf')
print(f"  Saved: {fig_dir / 'figure4_summary.png'}")

# ============================================================================
# SUMMARY STATISTICS
# ============================================================================
print("\n" + "="*70)
print("VALIDATION SUMMARY")
print("="*70)

print(f"\nReal Data Validation ({len(real_median)} comparisons):")
print(f"  MaxEnt win rate: {win_rate:.1f}%")
print(f"  Naive median error: {real_median['naive_error_pct'].median():.2f}%")
print(f"  MaxEnt median error: {real_median['maxent_error_pct'].median():.2f}%")
print(f"  Mean improvement: {improvement.mean():.1f}%")

print(f"\nIPDfromAGD Comparison ({len(ipdagd_data)} simulations):")
print(f"  Naive median error: {ipdagd_data['naive_error'].median():.2f}%")
print(f"  MaxEnt median error: {ipdagd_data['maxent_error'].median():.2f}%")
print(f"  Improvement: {(1 - ipdagd_data['maxent_error'].median()/ipdagd_data['naive_error'].median())*100:.1f}%")

print(f"\nAll figures saved to: {fig_dir}")
print("="*70)
