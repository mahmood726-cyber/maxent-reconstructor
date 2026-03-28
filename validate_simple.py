"""
Simple focused validation using one metadat dataset.
"""

import numpy as np
import pandas as pd
import sys
sys.path.insert(0, 'C:/Users/user/maxent-reconstructor')

from maxent_improved import MaxEntReconstructor, NaiveReconstructor
from scipy.stats import lognorm

print("="*60)
print("Focused MaxEnt Validation")
print("="*60)

# Test 1: Load a specific dataset
print("\nTest 1: Loading Curtis1998 dataset...")
df = pd.read_csv(r"C:\Users\user\OneDrive - NHS\Documents\repo100\metahub\inst\derived\metareg\metadat_dat.curtis1998.csv")
print(f"Loaded {len(df)} rows")

# Test 2: Process first 10 rows
print("\nTest 2: Processing first 10 valid rows...")
results = []
processed = 0

for idx, row in df.head(20).iterrows():
    # Extract summary stats
    mean_ctrl = row.get('mean_ctrl', np.nan)
    sd_ratio = row.get('sd_ratio', np.nan)
    ntotal = row.get('ntotal', np.nan)

    if pd.isna(mean_ctrl) or pd.isna(sd_ratio) or pd.isna(ntotal):
        continue

    if ntotal < 10 or sd_ratio <= 0:
        continue

    processed += 1
    print(f"\n  Row {idx}: mean={mean_ctrl:.2f}, sd={sd_ratio:.2f}, n={int(ntotal)}")

    # Create synthetic true data
    np.random.seed(42)
    true_data = lognorm.rvs(s=0.8, scale=mean_ctrl, size=int(ntotal))
    true_mean = np.mean(true_data)
    true_sd = np.std(true_data)
    true_min = np.min(true_data)
    true_max = np.max(true_data)
    true_median = np.median(true_data)

    # Adjust to match target stats
    true_data = (true_data - np.mean(true_data)) / np.std(true_data) * sd_ratio + mean_ctrl
    true_data = np.clip(true_data, max(0, mean_ctrl - 4*sd_ratio), mean_ctrl + 4*sd_ratio)
    true_median = np.median(true_data)

    # Naive
    try:
        naive = NaiveReconstructor(true_mean, true_sd, true_min, true_max, int(ntotal), random_state=42)
        naive_data = naive.generate_ipd()
        naive_median = np.median(naive_data)
        naive_err = abs(naive_median - true_median) / abs(true_median) * 100
    except:
        continue

    # MaxEnt
    try:
        maxent = MaxEntReconstructor(true_mean, true_sd, true_min, true_max, int(ntotal), random_state=42)
        maxent_result = maxent.generate_ipd()
        if not maxent_result.success:
            print(f"    MaxEnt failed: {maxent_result.method_used}")
            continue
        maxent_data = maxent_result.data
        maxent_median = np.median(maxent_data)
        maxent_err = abs(maxent_median - true_median) / abs(true_median) * 100
    except Exception as e:
        print(f"    MaxEnt error: {e}")
        continue

    winner = "MaxEnt" if maxent_err < naive_err else "Naive"
    improvement = (1 - maxent_err/naive_err) * 100 if naive_err > 0 else 0

    results.append({
        'row': idx,
        'true_median': true_median,
        'naive_median': naive_median,
        'maxent_median': maxent_median,
        'naive_error': naive_err,
        'maxent_error': maxent_err,
        'winner': winner,
        'improvement': improvement
    })

    print(f"    True median: {true_median:.2f}")
    print(f"    Naive: {naive_median:.2f} (error: {naive_err:.2f}%)")
    print(f"    MaxEnt: {maxent_median:.2f} (error: {maxent_err:.2f}%)")
    print(f"    Winner: {winner} (improvement: {improvement:.1f}%)")

    if processed >= 10:
        break

# Summary
print("\n" + "="*60)
print("SUMMARY")
print("="*60)
if results:
    results_df = pd.DataFrame(results)
    print(f"Valid comparisons: {len(results_df)}")
    print(f"MaxEnt win rate: {(results_df['winner']=='MaxEnt').mean() * 100:.1f}%")
    print(f"Mean naive error: {results_df['naive_error'].mean():.2f}%")
    print(f"Mean maxent error: {results_df['maxent_error'].mean():.2f}%")
    print(f"Mean improvement: {results_df['improvement'].mean():.1f}%")
else:
    print("No valid results")
