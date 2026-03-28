# MaxEnt IPD Reconstructor - Improvement Plan to 1000 Simulations

**Current Status:** 1,077 comparisons across 30 datasets
**Target:** 10,000+ comparisons with 1000+ simulations per scenario

---

## Executive Summary

Scale validation from ~1,000 to **10,000+ comparisons** using:
- Parallel processing (4-8 cores)
- Cloud computing (optional)
- Algorithm optimizations
- Extended data sources
- Enhanced metrics

---

## Phase 1: Infrastructure Scaling (Week 1-2)

### 1.1 Parallel Processing Implementation

**Current:** Sequential processing (~2 hours for 30 datasets)
**Target:** Parallel processing (~15 minutes)

```python
# parallel_processor.py
from multiprocessing import Pool, cpu_count
from concurrent.futures import ProcessPoolExecutor
import joblib

class ParallelMaxEntValidator:
    """Parallel validation framework for 1000+ simulations"""

    def __init__(self, n_workers=None):
        self.n_workers = n_workers or cpu_count()
        print(f"Using {self.n_workers} workers")

    def run_parallel_validation(self, n_sims=1000, n_workers=None):
        """Run 1000+ simulations in parallel"""
        n_workers = n_workers or self.n_workers

        # Split simulations into chunks
        chunk_size = n_sims // n_workers

        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            futures = []
            for i in range(n_workers):
                start = i * chunk_size
                end = (i + 1) * chunk_size if i < n_workers - 1 else n_sims
                future = executor.submit(
                    self._run_simulation_chunk,
                    start, end, n_sims
                )
                futures.append(future)

            # Collect results
            results = []
            for future in futures:
                results.extend(future.result())

        return pd.DataFrame(results)

    def _run_simulation_chunk(self, start, end, total_sims):
        """Run a chunk of simulations"""
        chunk_results = []
        for i in range(start, end):
            result = self._single_simulation(i)
            chunk_results.append(result)
        return chunk_results
```

### 1.2 GPU Acceleration (Optional)

```python
# gpu_processor.py
import cupy as cp
from cupyx.scipy.stats import truncnorm

class GPUMaxEntReconstructor:
    """GPU-accelerated MaxEnt for massive simulations"""

    def generate_batch_ipd(self, params_list, batch_size=1000):
        """Generate IPD for 1000+ cases on GPU"""
        # Transfer to GPU
        means = cp.array([p['mean'] for p in params_list])
        sds = cp.array([p['sd'] for p in params_list])

        # Batch processing
        results = self._gpu_batch_generate(means, sds, params_list)

        return results
```

### 1.3 Cloud Computing Setup

**AWS Batch / Google Cloud Run:**

```yaml
# cloud_config.yaml
cloud:
  provider: aws
  service: batch

  compute:
    vcpus: 16
    memory: 32GB
    spot_instances: true  # Cost optimization

  storage:
    s3_bucket: maxent-validation-results
    local_cache: /tmp/maxent_cache

  monitoring:
    cloudwatch: true
    alerts: completion, failure
```

---

## Phase 2: Algorithm Optimization (Week 3-4)

### 2.1 Vectorized Operations

**Current:** Loop-based processing
**Target:** Vectorized for 10x speedup

```python
# vectorized_maxent.py
import numpy as np
from scipy.optimize import root
import numba

@numba.jit(nopython=True, parallel=True)
def vectorized_moments(mu_L, sigma_L, low, high):
    """Vectorized moment calculation"""
    n = len(mu_L)
    means = np.empty(n)
    stds = np.empty(n)

    for i in numba.prange(n):
        a = (low[i] - mu_L[i]) / sigma_L[i]
        b = (high[i] - mu_L[i]) / sigma_L[i]

        # Vectorized truncnorm moments
        from scipy.stats import truncnorm
        means[i] = truncnorm.mean(a, b, loc=mu_L[i], scale=sigma_L[i])
        stds[i] = truncnorm.std(a, b, loc=mu_L[i], scale=sigma_L[i])

    return means, stds

class VectorizedMaxEntReconstructor:
    """Vectorized for batch processing"""

    def fit_batch(self, params_df):
        """Fit multiple cases at once"""
        results = self._parallel_fit(params_df)
        return results
```

### 2.2 Caching & Memoization

```python
# cached_maxent.py
from functools import lru_cache
import hashlib

class CachedMaxEntReconstructor:
    """Cache results for identical parameter sets"""

    def __init__(self, cache_size=10000):
        self.cache = {}
        self.cache_size = cache_size

    def get_cache_key(self, mean, sd, low, high, n):
        """Generate cache key"""
        key = hashlib.md5(
            f"{mean:.6f}_{sd:.6f}_{low:.6f}_{high:.6f}_{n}".encode()
        ).hexdigest()
        return key

    def generate_ipd_cached(self, mean, sd, low, high, n):
        """Generate with caching"""
        key = self.get_cache_key(mean, sd, low, high, n)

        if key in self.cache:
            return self.cache[key]

        result = self._generate_ipd(mean, sd, low, high, n)

        if len(self.cache) < self.cache_size:
            self.cache[key] = result

        return result
```

### 2.3 Adaptive Algorithm Selection

```python
# adaptive_maxent.py
class AdaptiveMaxEntReconstructor:
    """Choose optimal method based on data characteristics"""

    def select_method(self, mean, sd, low, high, n):
        """Select fastest appropriate method"""
        cv = sd / mean
        range_ratio = (high - low) / sd

        if cv < 0.2 and range_ratio > 6:
            return 'naive'  # Normal is fine
        elif cv < 0.5:
            return 'maxent_fast'  # Simplified MaxEnt
        else:
            return 'maxent_full'  # Full 5-stage

    def generate_adaptive_ipd(self, mean, sd, low, high, n):
        """Generate using selected method"""
        method = self.select_method(mean, sd, low, high, n)

        if method == 'naive':
            return self._naive_generation(mean, sd, low, high, n)
        elif method == 'maxent_fast':
            return self._fast_maxent(mean, sd, low, high, n)
        else:
            return self._full_maxent(mean, sd, low, high, n)
```

---

## Phase 3: Extended Validation Framework (Week 5-6)

### 3.1 1000-Simulation Scenarios

```python
# validation_1000.py
class ThousandSimulationValidator:
    """Run 1000 simulations per scenario"""

    SCENARIOS = {
        'lognormal_low_skew': {
            'distribution': 'lognormal',
            's': (0.1, 0.5),
            'scale': (10, 100),
            'n_sims': 1000
        },
        'lognormal_med_skew': {
            'distribution': 'lognormal',
            's': (0.5, 1.5),
            'scale': (10, 100),
            'n_sims': 1000
        },
        'lognormal_high_skew': {
            'distribution': 'lognormal',
            's': (1.5, 3.0),
            'scale': (10, 100),
            'n_sims': 1000
        },
        'beta_symmetric': {
            'distribution': 'beta',
            'a': (2, 10),
            'b': (2, 10),
            'n_sims': 1000
        },
        'beta_skewed': {
            'distribution': 'beta',
            'a': (0.5, 2),
            'b': (2, 10),
            'n_sims': 1000
        },
        'gamma_shape_varied': {
            'distribution': 'gamma',
            'a': (0.5, 5),
            'scale': (5, 50),
            'n_sims': 1000
        },
        'weibull_varied': {
            'distribution': 'weibull_min',
            'c': (0.5, 3),
            'scale': (10, 100),
            'n_sims': 1000
        },
        # Mixed distributions
        'bimodal': {
            'distribution': 'mixture',
            'components': 2,
            'n_sims': 1000
        },
        'truncated_normal': {
            'distribution': 'truncnorm',
            'clip': (2, 4),
            'n_sims': 1000
        },
    }

    def run_all_scenarios_1000(self):
        """Run 1000 simulations for each scenario"""
        results = {}

        for scenario_name, config in self.SCENARIOS.items():
            print(f"\nRunning {scenario_name}: 1000 simulations")
            results[scenario_name] = self._run_scenario_1000(config)

        return self._aggregate_1000_results(results)

    def _run_scenario_1000(self, config):
        """Run 1000 simulations for a single scenario"""
        # Use parallel processing
        validator = ParallelMaxEntValidator(n_workers=8)
        df = validator.run_parallel_validation(
            n_sims=config['n_sims'],
            distribution=config['distribution']
        )
        return df
```

### 3.2 Enhanced Metrics

```python
# enhanced_metrics.py
class EnhancedMetrics:
    """Additional metrics for 1000+ validation"""

    @staticmethod
    def calculate_all_metrics(true_data, recon_data):
        """Calculate comprehensive metrics"""
        metrics = {}

        # Basic quantiles
        for q in [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95]:
            true_q = np.quantile(true_data, q)
            recon_q = np.quantile(recon_data, q)
            metrics[f'q{int(q*100)}_error'] = abs(recon_q - true_q)

        # Distribution metrics
        metrics['kl_divergence'] = EnhancedMetrics._kl_divergence(true_data, recon_data)
        metrics['js_divergence'] = EnhancedMetrics._js_divergence(true_data, recon_data)
        metrics['wasserstein'] = EnhancedMetrics._wasserstein(true_data, recon_data)

        # Shape metrics
        metrics['skewness_error'] = abs(stats.skew(recon_data) - stats.skew(true_data))
        metrics['kurtosis_error'] = abs(stats.kurtosis(recon_data) - stats.kurtosis(true_data))

        # Coverage metrics
        for level in [0.90, 0.95, 0.99]:
            ci_true = np.quantile(true_data, [(1-level)/2, 1-(1-level)/2])
            ci_recon = np.quantile(recon_data, [(1-level)/2, 1-(1-level)/2])
            coverage = (ci_true[0] >= ci_recon[0]) and (ci_true[1] <= ci_recon[1])
            metrics[f'coverage_{int(level*100)}'] = int(coverage)

        # Correlation metrics
        if len(true_data) > 1:
            # Sort and compare order statistics
            sorted_true = np.sort(true_data)
            sorted_recon = np.sort(recon_data)
            metrics['rank_correlation'] = stats.spearmanr(sorted_true, sorted_recon)[0]

        return metrics

    @staticmethod
    def _kl_divergence(p, q):
        """Kullback-Leibler divergence"""
        # Histogram-based estimation
        hist_p, bins = np.histogram(p, bins=50, density=True)
        hist_q, _ = np.histogram(q, bins=bins, density=True)

        # Avoid division by zero
        hist_p = hist_p + 1e-10
        hist_q = hist_q + 1e-10

        return np.sum(hist_p * np.log(hist_p / hist_q))

    @staticmethod
    def _js_divergence(p, q):
        """Jensen-Shannon divergence"""
        # Histogram-based estimation
        hist_p, bins = np.histogram(p, bins=50, density=True)
        hist_q, _ = np.histogram(q, bins=bins, density=True)

        m = (hist_p + hist_q) / 2

        kl_pm = np.sum(hist_p * np.log((hist_p + 1e-10) / (m + 1e-10)))
        kl_qm = np.sum(hist_q * np.log((hist_q + 1e-10) / (m + 1e-10)))

        return (kl_pm + kl_qm) / 2

    @staticmethod
    def _wasserstein(p, q):
        """Wasserstein distance (earth mover's distance)"""
        from scipy.stats import wasserstein_distance
        return wasserstein_distance(p, q)
```

### 3.3 Statistical Power Analysis

```python
# power_analysis.py
class ValidationPowerAnalysis:
    """Determine required sample size for validation"""

    def calculate_required_n(self, effect_size=0.5, power=0.8, alpha=0.05):
        """Calculate required simulations for significant results"""
        from scipy.stats import norm

        z_alpha = norm.ppf(1 - alpha/2)
        z_beta = norm.ppf(power)

        # Two-sample test
        n_per_group = 2 * ((z_alpha + z_beta)**2) / (effect_size**2)

        return int(np.ceil(n_per_group))

    def required_simulations_for_validation(self):
        """Calculate required simulations for robust validation"""
        # To detect 20% improvement with 80% power
        n = self.calculate_required_n(effect_size=0.5, power=0.9)
        return n

    def confidence_interval_win_rate(self, wins, total, confidence=0.95):
        """Calculate CI for win rate"""
        from statsmodels.stats.proportion import proportion_confint

        ci_low, ci_high = proportion_confint(
            wins, total, alpha=1-confidence, method='wilson'
        )

        return ci_low * 100, ci_high * 100
```

---

## Phase 4: Extended Data Collection (Week 7-8)

### 4.1 Real Data Sources - 1000+ Datasets

```python
# data_collector_1000.py
class ThousandDatasetCollector:
    """Collect 1000+ real datasets for validation"""

    SOURCES = {
        'clinical_trials_gov': {
            'url': 'https://clinicaltrials.gov/api/query/full_studies',
            'expected': 500+
        },
        'cochrane_reviews': {
            'path': 'C:/Users/user/OneDrive - NHS/Documents/Pairwise70',
            'expected': 300+
        },
        'metadat_package': {
            'path': 'C:/Users/user/OneDrive - NHS/Documents/repo100/metahub',
            'expected': 100+
        },
        'zenodo_ipd': {
            'query': 'individual patient data meta-analysis',
            'expected': 100+
        },
        'github_repos': {
            'repos': [
                'gertvanvalkenhaus/IPDfromAGD',
                'guido-s/meta',
                'wviechtb/metadat'
            ],
            'expected': 50+
        }
    }

    def collect_all_sources(self):
        """Collect data from all sources"""
        all_data = {}

        for source, config in self.SOURCES.items():
            print(f"Collecting from {source}...")
            data = self._collect_from_source(source, config)
            all_data[source] = data

        return self._combine_sources(all_data)

    def validate_dataset_quality(self, df):
        """Check if dataset meets quality criteria"""
        checks = {
            'has_mean': 'mean' in df.columns or 'mean_t' in df.columns,
            'has_sd': 'sd' in df.columns or 'sd_t' in df.columns,
            'has_n': 'n' in df.columns or 'n_t' in df.columns,
            'min_rows': len(df) >= 3,
            'has_bounds': 'min' in df.columns or 'low' in df.columns,
        }

        return sum(checks.values()) >= 4
```

### 4.2 Synthetic Data Generation

```python
# synthetic_data_1000.py
class SyntheticDataGenerator1000:
    """Generate 1000+ synthetic datasets"""

    def generate_validation_suite(self, n_datasets=1000):
        """Generate diverse synthetic datasets"""
        datasets = []

        # Distribution types
        distributions = [
            'lognormal', 'gamma', 'weibull', 'beta',
            'exponential', 'chi2', 'loglogistic', 'pareto'
        ]

        for i in range(n_datasets):
            # Random scenario
            dist = np.random.choice(distributions)
            n = np.random.choice([20, 50, 100, 200, 500, 1000])
            cv = np.random.uniform(0.1, 2.0)

            params = self._generate_params(dist, cv)
            data = self._generate_synthetic_dataset(dist, params, n)

            datasets.append({
                'id': i,
                'distribution': dist,
                'n': n,
                'params': params,
                'data': data
            })

        return datasets

    def _generate_synthetic_dataset(self, dist, params, n):
        """Generate single synthetic dataset"""
        if dist == 'lognormal':
            data = lognorm.rvs(s=params['s'], scale=params['scale'], size=n)
        elif dist == 'gamma':
            data = gamma.rvs(a=params['a'], scale=params['scale'], size=n)
        # ... other distributions

        return data
```

---

## Phase 5: Results Aggregation & Analysis (Week 9-10)

### 5.1 Multi-Level Meta-Analysis

```python
# meta_analysis_1000.py
class ThousandStudyMetaAnalysis:
    """Meta-analyze results from 1000+ simulations"""

    def aggregate_results(self, results_dict):
        """Aggregate results from all scenarios"""
        # Multi-level analysis
        # Level 1: Within-scenario
        # Level 2: Between-scenarios
        # Level 3: Overall

        summary = {
            'overall': self._overall_summary(results_dict),
            'by_scenario': self._scenario_summary(results_dict),
            'by_distribution': self._distribution_summary(results_dict),
            'by_sample_size': self._sample_size_summary(results_dict),
            'by_skewness': self._skewness_summary(results_dict),
        }

        return summary

    def _overall_summary(self, results):
        """Overall summary across all scenarios"""
        all_results = pd.concat(results.values())

        return {
            'total_comparisons': len(all_results),
            'maxent_win_rate': (all_results['maxent_wins']).mean() * 100,
            'win_rate_ci': self._calculate_ci(all_results['maxent_wins']),
            'mean_improvement': all_results['improvement_pct'].mean(),
            'median_improvement': all_results['improvement_pct'].median(),
        }

    def _calculate_ci(self, wins):
        """Calculate confidence interval for win rate"""
        from statsmodels.stats.proportion import proportion_confint

        n = len(wins)
        k = wins.sum()

        ci_low, ci_high = proportion_confint(k, n, alpha=0.05, method='wilson')

        return {
            'lower': ci_low * 100,
            'upper': ci_high * 100
        }
```

### 5.2 Publication-Quality Tables

```python
# publication_tables_1000.py
class ThousandSimulationTables:
    """Generate publication tables for 1000+ validation"""

    def create_main_results_table(self, results):
        """Main results table"""
        table_data = []

        for scenario, df in results.items():
            n = len(df)
            win_rate = (df['maxent_wins']).mean() * 100
            ci_low, ci_high = self._calculate_ci(df['maxent_wins'])

            table_data.append({
                'Scenario': scenario,
                'N': n,
                'Win Rate (%)': f'{win_rate:.1f}',
                '95% CI': f'[{ci_low:.1f}, {ci_high:.1f}]',
                'Mean Improvement (%)': f'{df["improvement_pct"].mean():.1f}',
                'Median Improvement (%)': f'{df["improvement_pct"].median():.1f}',
            })

        return pd.DataFrame(table_data)

    def create_supplementary_tables(self, results):
        """Create all supplementary tables"""
        tables = {
            'S1_Detailed_Results': self._detailed_results_table(results),
            'S2_By_Distribution': self._by_distribution_table(results),
            'S3_By_Sample_Size': self._by_sample_size_table(results),
            'S4_By_Skewness': self._by_skewness_table(results),
            'S5_Performance_Metrics': self._metrics_table(results),
        }

        return tables
```

---

## Implementation Schedule

### Week 1-2: Infrastructure
- [ ] Implement parallel processing
- [ ] Set up GPU acceleration (optional)
- [ ] Configure cloud computing (optional)
- [ ] Benchmark performance improvements

### Week 3-4: Algorithm Optimization
- [ ] Vectorize core operations
- [ ] Implement caching
- [ ] Add adaptive method selection
- [ ] Profile and optimize

### Week 5-6: Extended Validation
- [ ] Define 1000-simulation scenarios
- [ ] Implement enhanced metrics
- [ ] Add power analysis
- [ ] Run pilot (100 sims per scenario)

### Week 7-8: Data Collection
- [ ] Collect from ClinicalTrials.gov
- [ ] Process Cochrane reviews
- [ ] Gather metadat datasets
- [ ] Generate synthetic datasets

### Week 9-10: Analysis & Reporting
- [ ] Run full 1000-simulation validation
- [ ] Meta-analyze results
- [ ] Create publication tables
- [ ] Generate supplementary materials

### Week 11-12: Documentation & Release
- [ ] Update all documentation
- [ ] Create tutorials
- [ ] Package for release
- [ ] Submit for publication

---

## Resource Requirements

### Computational Resources

| Resource | Current | Target | Cost |
|----------|---------|--------|------|
| **CPU** | 4 cores | 16 cores | $0.20/hour |
| **Memory** | 16GB | 64GB | $0.10/hour |
| **Storage** | 10GB | 100GB | $0.02/hour |
| **Time** | 2 hours | 30 min | - |

**Total estimated cost (AWS Spot):** $20-50 for full validation

### Software Stack

```python
# requirements_1000.txt
numpy>=1.24
pandas>=2.0
scipy>=1.11
numba>=0.58          # JIT compilation
cupy>=12.0           # GPU acceleration (optional)
dask>=2023.0         # Parallel computing
joblib>=1.3          # Caching
multiprocessing-logging  # Progress tracking
tqdm>=4.65           # Progress bars
```

---

## Expected Outcomes

### Validation Scale

| Metric | Current | Target |
|--------|---------|--------|
| Total simulations | 1,077 | **10,000+** |
| Scenarios tested | ~10 | **50+** |
| Distributions | 4 | **10+** |
| Real datasets | 30 | **1,000+** |
| Metrics tracked | 5 | **15+** |

### Statistical Power

| Comparison | Current Power | Target Power |
|-------------|---------------|--------------|
| Detect 10% improvement | Low (n=50) | High (n=1000) |
| Win rate CI width | ±14% | ±3% |
| Subgroup analysis | Not possible | Possible |

### Publications

1. **Main Paper:** Methods paper with 10,000+ validations
2. **Supplementary:** 50+ scenario analyses
3. **Software:** Python + R packages
4. **Data:** Open dataset for benchmarking

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| **Computational cost** | Use spot instances, local cluster |
| **Time constraints** | Parallel processing, incremental runs |
| **Data quality** | Automated quality checks |
| **Reproducibility** | Fixed random seeds, containerization |

---

*Document Version: 1.0*
*Last Updated: 2025*
*Status: Planning Phase*
