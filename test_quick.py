"""
Quick test script to verify MaxEnt reconstructor works correctly.
"""

import numpy as np
import sys
sys.path.insert(0, 'C:/Users/user/maxent-reconstructor')

from maxent_improved import MaxEntReconstructor, NaiveReconstructor

print("="*60)
print("MaxEnt Reconstructor - Quick Test")
print("="*60)

# Test case 1: Basic functionality
print("\nTest 1: Basic functionality")
recon = MaxEntReconstructor(mean=50, sd=10, low=20, high=100, n_samples=100, random_state=42)
result = recon.generate_ipd()

if result.success:
    print(f"[OK] Success! Method: {result.method_used}")
    print(f"  Generated {len(result.data)} samples")
    print(f"  Mean: {np.mean(result.data):.2f} (target: 50)")
    print(f"  SD: {np.std(result.data):.2f} (target: 10)")
    print(f"  Min: {np.min(result.data):.2f}, Max: {np.max(result.data):.2f}")
else:
    print("[FAIL] Failed!")

# Test case 2: Skewed distribution
print("\nTest 2: Skewed distribution (lognormal-like)")
from scipy.stats import lognorm
np.random.seed(42)
true_data = lognorm.rvs(s=1.0, scale=50, size=200)

recon = MaxEntReconstructor(
    mean=np.mean(true_data),
    sd=np.std(true_data),
    low=np.min(true_data),
    high=np.max(true_data),
    n_samples=200,
    random_state=42
)

# Naive baseline
naive = NaiveReconstructor(
    mean=np.mean(true_data),
    sd=np.std(true_data),
    low=np.min(true_data),
    high=np.max(true_data),
    n_samples=200,
    random_state=42
)

naive_data = naive.generate_ipd()
maxent_result = recon.generate_ipd()

if maxent_result.success:
    true_median = np.median(true_data)
    naive_median = np.median(naive_data)
    maxent_median = np.median(maxent_result.data)

    naive_err = abs(naive_median - true_median) / true_median * 100
    maxent_err = abs(maxent_median - true_median) / true_median * 100

    print(f"  True Median: {true_median:.2f}")
    print(f"  Naive Median: {naive_median:.2f} (error: {naive_err:.2f}%)")
    print(f"  MaxEnt Median: {maxent_median:.2f} (error: {maxent_err:.2f}%)")
    print(f"  Winner: {'MaxEnt' if maxent_err < naive_err else 'Naive'}")

# Test case 3: Edge cases
print("\nTest 3: Edge cases")

# Very narrow range
try:
    recon = MaxEntReconstructor(mean=50, sd=1, low=48, high=52, n_samples=50, random_state=42)
    result = recon.generate_ipd()
    print(f"  [OK] Narrow range: {'Success' if result.success else 'Failed'}")
except Exception as e:
    print(f"  [FAIL] Narrow range: {e}")

# High variability
try:
    recon = MaxEntReconstructor(mean=50, sd=20, low=0, high=150, n_samples=50, random_state=42)
    result = recon.generate_ipd()
    print(f"  [OK] High variability: {'Success' if result.success else 'Failed'}")
except Exception as e:
    print(f"  [FAIL] High variability: {e}")

print("\n" + "="*60)
print("All tests completed!")
print("="*60)
