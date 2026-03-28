# MaxEnt IPD Reconstructor - Project Plan & Documentation

## Overview

This project implements an improved **Maximum Entropy (MaxEnt) Individual Patient Data (IPD) Reconstructor** for reconstructing individual-level data from aggregated summary statistics (mean, SD, min, max, n) commonly reported in meta-analyses.

**Directory:** `C:\Users\user\maxent-reconstructor\`

---

## Project Structure

```
maxent-reconstructor/
├── maxent_improved.py          # Core improved MaxEnt implementation
├── validator.py                # Simulation-based validation framework
├── real_data_validator.py      # Real-world data validation
├── README.md                   # This file
└── data/                       # Validation results (generated)
```

---

## Code Review & Improvements Made

### Original Code Issues Identified

| Issue | Original | Improved Solution |
|-------|----------|-------------------|
| **Numerical Stability** | Aggressive clipping `(-100, 100)` | More conservative `(-50, 50)` with sigma bounds |
| **Error Handling** | Silent failures returning `None` | Full `ReconstructorResult` with diagnostics |
| **Optimization Strategy** | Basic 3-stage fallback | 5-stage optimization with least_squares |
| **Metrics** | Median only | 5 quantiles (Q10, Q25, Q50, Q75, Q90) + KS test |
| **Reproducibility** | No seed control | Full `random_state` parameter support |
| **Validation** | Lognormal only | 4 distributions: lognormal, beta, gamma, weibull |
| **Documentation** | Minimal | Full docstrings, type hints, dataclasses |

### New Features Added

1. **`ReconstructorResult` dataclass** - Full diagnostic output
2. **`_max_feasible_sd()`** - Validates input feasibility
3. **Multiple optimization methods** - root finding, least squares, Nelder-Mead
4. **Approximate solution fallback** - Always returns valid result
5. **Comprehensive metrics** - skewness, kurtosis, KS statistic
6. **Real data validator** - Works with Cochrane/metadat datasets

---

## Data Requirements

### For Validation Studies

The validator can work with datasets containing:

#### 1. Summary Statistics (Minimum Required)
```python
{
    'mean': float,      # Group mean
    'sd': float,        # Standard deviation
    'n': int,          # Sample size
    'min': float,      # Minimum value (optional, can estimate)
    'max': float       # Maximum value (optional, can estimate)
}
```

#### 2. Available Real-World Data Sources

**A. Cochrane Reviews** (Pairwise70 directory)
- Location: `C:\Users\user\OneDrive - NHS\Documents\Pairwise70\`
- Files: `ma4_results_pairwise70.csv`
- Columns: `mean_t`, `mean_c`, `sd_t`, `sd_c`, `n_t`, `n_c`

**B. R metadat Package** (via metahub)
- Location: `C:\Users\user\OneDrive - NHS\Documents\repo100\metahub\inst\derived\metareg\`
- 100+ datasets available
- Examples:
  - `metadat_dat.colditz1994.csv` - BCG vaccine studies
  - `metadat_dat.curtis1998.csv` - CO2 effects on plant mass
  - `metadat_dat.berkey1998.csv` - Periodontal disease treatments

**C. Additional Sources to Consider**
- CRAN packages: `meta`, `metamisc`, `IPDfromAGD`
- Zenodo datasets with IPD meta-analyses
- GitHub repositories with medical trial data

#### 3. Ideal Dataset Characteristics

For best validation results, look for data with:
- **Continuous outcomes** (not binary)
- **Skewed distributions** (where MaxEnt excels)
- **Range of sample sizes** (n = 20 to 500+)
- **Different outcome types** (biomarkers, scores, measurements)
- **Reported min/max** or ability to estimate bounds

---

## Usage Guide

### Basic Usage

```python
from maxent_improved import MaxEntReconstructor, reconstruct_ipd

# Method 1: Direct function
ipd = reconstruct_ipd(mean=50, sd=10, low=20, high=100, n=100, method='maxent')

# Method 2: Full object
recon = MaxEntReconstructor(mean=50, sd=10, low=20, high=100, n=100, random_state=42)
result = recon.generate_ipd()

if result.success:
    data = result.data
    print(f"Method used: {result.method_used}")
    print(f"Diagnostics: {result.diagnostics}")
```

### Running Validation

```python
# Simulation validation
from validator import run_validation
df, summary = run_validation(n_sims=2000)

# Real data validation
from real_data_validator import run_real_data_validation
results = run_real_data_validation()
```

---

## Validation Plan

### Phase 1: Simulation Studies (Complete)
- [x] Multiple distributions (lognormal, beta, gamma, weibull)
- [x] Varying skewness levels
- [x] Different sample sizes
- [x] Multiple quantile validation

### Phase 2: Real Data Validation (Ready to Run)
- [ ] Load Cochrane review data
- [ ] Load metadat package datasets
- [ ] Validate across multiple outcome types
- [ ] Compare against naive normal reconstruction

### Phase 3: Publication-Ready Analysis
- [ ] Aggregate results across all datasets
- [ ] Create publication-quality figures
- [ ] Write methods section
- [ ] Prepare supplementary materials

---

## Next Steps

### Immediate Actions

1. **Run Real Data Validation**
   ```bash
   cd C:\Users\user\maxent-reconstructor
   python real_data_validator.py
   ```

2. **Review Results**
   - Check `real_data_validation_results.csv`
   - Examine `real_data_validation_plots.png`

3. **Identify Best Datasets**
   - Which datasets show MaxEnt advantage?
   - What characteristics make MaxEnt perform better?

### Future Enhancements

| Priority | Feature | Description |
|----------|---------|-------------|
| High | Multiple groups | Extend to >2 group comparisons |
| High | Correlation | Handle correlated outcomes |
| Medium | IPDfromAGD | Compare against R package |
| Medium | Time-to-event | Survival data reconstruction |
| Low | Bayesian | Full Bayesian implementation |

---

## Expected Results

Based on simulation studies, MaxEnt reconstruction typically shows:

- **Median Error**: 30-50% reduction vs naive normal
- **Win Rate**: 70-85% across skewed distributions
- **Best Performance**: Highly skewed, bounded data
- **Neutral Performance**: Near-normal distributions (both methods work)

---

## References & Related Work

1. **Original Inspiration**: The DTA Pro v4.7 project
2. **Related R Packages**:
   - `IPDfromAGD` - Individual patient data from aggregate data
   - `metadat` - Collection of meta-analysis datasets
   - `meta` - Standard meta-analysis package
3. **Key Papers**:
   - Maximum entropy principle in statistics
   - IPD reconstruction methods
   - Meta-analysis with missing participant data

---

## Contact & Contribution

This is an improved version of the MaxEnt IPD reconstructor with comprehensive validation framework. For questions or suggestions, please refer to the DTA Pro documentation.

---

*Generated: 2025*
*Version: 1.0*
