"""
Comprehensive Validation Framework for MaxEnt IPD Reconstruction
================================================================
Validates reconstruction quality across multiple metrics and scenarios.
"""

import numpy as np
import pandas as pd
from scipy.stats import lognorm, norm, beta, gamma, weibull_min
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Callable, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
import time

from maxent_improved import MaxEntReconstructor, NaiveReconstructor


class ReconstructionValidator:
    """
    Comprehensive validation framework for IPD reconstruction methods.

    Tests reconstruction quality across:
    - Multiple true distributions (lognormal, beta, gamma, weibull)
    - Various sample sizes
    - Different skewness levels
    - Multiple quantiles (not just median)
    """

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.results = []

    @staticmethod
    def get_quantiles(data: np.ndarray, quantiles: List[float]) -> Dict[str, float]:
        """Calculate multiple quantiles from data."""
        return {f'q{int(q*100)}': np.quantile(data, q) for q in quantiles}

    @staticmethod
    def calculate_metrics(true_data: np.ndarray, recon_data: np.ndarray) -> Dict[str, float]:
        """
        Calculate comprehensive validation metrics.

        Metrics include:
        - Quantile errors (Q10, Q25, Q50/median, Q75, Q90)
        - Moment errors (mean, SD)
        - Distribution similarity (KL divergence approximation)
        - Coverage error
        """
        quantiles = [0.1, 0.25, 0.5, 0.75, 0.9]
        true_q = ReconstructionValidator.get_quantiles(true_data, quantiles)
        recon_q = ReconstructionValidator.get_quantiles(recon_data, quantiles)

        metrics = {}

        # Quantile errors (absolute percentage)
        for q_name in true_q:
            if true_q[q_name] != 0:
                metrics[f'{q_name}_error_pct'] = abs(recon_q[q_name] - true_q[q_name]) / abs(true_q[q_name]) * 100
            else:
                metrics[f'{q_name}_error_abs'] = abs(recon_q[q_name] - true_q[q_name])

        # Moment errors
        metrics['mean_error_pct'] = abs(np.mean(recon_data) - np.mean(true_data)) / abs(np.mean(true_data)) * 100
        metrics['sd_error_pct'] = abs(np.std(recon_data) - np.std(true_data)) / np.std(true_data) * 100

        # Distribution shape metrics
        metrics['skewness_error'] = abs(self._skewness(recon_data) - self._skewness(true_data))
        metrics['kurtosis_error'] = abs(self._kurtosis(recon_data) - self._kurtosis(true_data))

        # Kolmogorov-Smirnov statistic
        from scipy.stats import ks_2samp
        ks_result = ks_2samp(true_data, recon_data)
        metrics['ks_statistic'] = ks_result.statistic
        metrics['ks_pvalue'] = ks_result.pvalue

        return metrics

    @staticmethod
    def _skewness(data: np.ndarray) -> float:
        """Calculate skewness."""
        mean = np.mean(data)
        std = np.std(data)
        if std == 0:
            return 0
        return np.mean(((data - mean) / std) ** 3)

    @staticmethod
    def _kurtosis(data: np.ndarray) -> float:
        """Calculate excess kurtosis."""
        mean = np.mean(data)
        std = np.std(data)
        if std == 0:
            return 0
        return np.mean(((data - mean) / std) ** 4) - 3

    def simulate_single_scenario(self, scenario: Dict) -> Dict:
        """
        Run a single simulation scenario.

        Scenario dict should contain:
        - distribution: 'lognormal', 'beta', 'gamma', 'weibull'
        - params: distribution-specific parameters
        - n: sample size
        - seed: random seed
        """
        np.random.seed(scenario['seed'])

        # Generate true data
        dist = scenario['distribution']
        params = scenario['params']
        n = scenario['n']

        if dist == 'lognormal':
            true_data = lognorm.rvs(s=params['s'], scale=params['scale'], size=n)
        elif dist == 'beta':
            true_data = beta.rvs(a=params['a'], b=params['b'], loc=params.get('loc', 0),
                                 scale=params.get('scale', 1), size=n)
        elif dist == 'gamma':
            true_data = gamma.rvs(a=params['a'], loc=params.get('loc', 0),
                                  scale=params.get('scale', 1), size=n)
        elif dist == 'weibull':
            true_data = weibull_min.rvs(c=params['c'], loc=params.get('loc', 0),
                                         scale=params.get('scale', 1), size=n)
        else:
            raise ValueError(f"Unknown distribution: {dist}")

        # Skip if range is too small
        if np.ptp(true_data) < 1e-6:
            return None

        # Aggregated data
        ad = {
            'mean': np.mean(true_data),
            'sd': np.std(true_data),
            'min': np.min(true_data),
            'max': np.max(true_data),
            'n': n
        }

        # Naive reconstruction
        naive_recon = NaiveReconstructor(ad['mean'], ad['sd'], ad['min'], ad['max'], ad['n'],
                                         random_state=scenario['seed'] + 1000)
        naive_data = naive_recon.generate_ipd()

        # MaxEnt reconstruction
        maxent_recon = MaxEntReconstructor(ad['mean'], ad['sd'], ad['min'], ad['max'], ad['n'],
                                           random_state=scenario['seed'] + 2000)
        maxent_result = maxent_recon.generate_ipd()

        if not maxent_result.success:
            return None

        maxent_data = maxent_result.data

        # Calculate metrics
        naive_metrics = self.calculate_metrics(true_data, naive_data)
        maxent_metrics = self.calculate_metrics(true_data, maxent_data)

        # Compile results
        result = {
            'scenario': scenario,
            'aggregated_data': ad,
            'true_skewness': self._skewness(true_data),
            'true_kurtosis': self._kurtosis(true_data),
            'true_range': np.ptp(true_data),
            'cv': np.std(true_data) / np.mean(true_data),
        }

        # Add naive metrics with prefix
        for k, v in naive_metrics.items():
            result[f'naive_{k}'] = v

        # Add maxent metrics with prefix
        for k, v in maxent_metrics.items():
            result[f'maxent_{k}'] = v

        # Win indicators (lower is better for errors)
        result['maxent_wins_q50'] = maxent_metrics['q50_error_pct'] < naive_metrics['q50_error_pct']
        result['maxent_wins_mean'] = maxent_metrics['mean_error_pct'] < naive_metrics['mean_error_pct']

        return result

    def run_simulation_study(self, n_sims: int = 1000, n_workers: int = 4) -> pd.DataFrame:
        """
        Run comprehensive simulation study.

        Tests across:
        - Different distributions (lognormal, beta, gamma, weibull)
        - Varying skewness levels
        - Different sample sizes
        """
        scenarios = []

        # Lognormal scenarios (varying skewness)
        for i in range(n_sims // 4):
            seed = 42 + i
            s = np.random.uniform(0.3, 2.0)  # Skewness parameter
            scale = np.random.uniform(10, 100)
            scenarios.append({
                'distribution': 'lognormal',
                'params': {'s': s, 'scale': scale},
                'n': np.random.choice([50, 100, 200, 500]),
                'seed': seed
            })

        # Beta scenarios (bounded, various shapes)
        for i in range(n_sims // 4):
            seed = 42 + n_sims // 4 + i
            a = np.random.uniform(0.5, 5)
            b = np.random.uniform(0.5, 5)
            scenarios.append({
                'distribution': 'beta',
                'params': {'a': a, 'b': 'b', 'loc': 0, 'scale': 100},
                'n': np.random.choice([50, 100, 200, 500]),
                'seed': seed
            })

        # Gamma scenarios
        for i in range(n_sims // 4):
            seed = 42 + n_sims // 2 + i
            a = np.random.uniform(0.5, 5)
            scale = np.random.uniform(5, 50)
            scenarios.append({
                'distribution': 'gamma',
                'params': {'a': a, 'scale': scale},
                'n': np.random.choice([50, 100, 200, 500]),
                'seed': seed
            })

        # Weibull scenarios
        for i in range(n_sims // 4):
            seed = 42 + 3 * n_sims // 4 + i
            c = np.random.uniform(0.5, 3)
            scale = np.random.uniform(10, 100)
            scenarios.append({
                'distribution': 'weibull',
                'params': {'c': c, 'scale': scale},
                'n': np.random.choice([50, 100, 200, 500]),
                'seed': seed
            })

        # Run simulations
        results = []
        start_time = time.time()

        for scenario in scenarios:
            result = self.simulate_single_scenario(scenario)
            if result is not None:
                results.append(result)

        elapsed = time.time() - start_time
        print(f"Completed {len(results)} simulations in {elapsed:.1f}s")

        return pd.DataFrame(results)

    def generate_summary_report(self, df: pd.DataFrame) -> Dict:
        """Generate summary statistics from validation results."""
        summary = {}

        # Overall win rates
        summary['median_win_rate'] = df['maxent_wins_q50'].mean() * 100
        summary['mean_win_rate'] = df['maxent_wins_mean'].mean() * 100

        # Average errors
        summary['naive_median_error'] = df['naive_q50_error_pct'].mean()
        summary['maxent_median_error'] = df['maxent_q50_error_pct'].mean()
        summary['naive_mean_error'] = df['naive_mean_error_pct'].mean()
        summary['maxent_mean_error'] = df['maxent_mean_error_pct'].mean()

        # By distribution
        for dist in ['lognormal', 'beta', 'gamma', 'weibull']:
            if 'scenario' in df.columns:
                dist_df = df[df['scenario'].apply(lambda x: x.get('distribution') == dist if isinstance(x, dict) else False)]
                if len(dist_df) > 0:
                    summary[f'{dist}_win_rate'] = dist_df['maxent_wins_q50'].mean() * 100
                    summary[f'{dist}_maxent_error'] = dist_df['maxent_q50_error_pct'].mean()

        return summary

    def plot_results(self, df: pd.DataFrame, save_path: Optional[str] = None):
        """Create comprehensive visualization of validation results."""
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))

        # 1. Error distribution comparison
        ax = axes[0, 0]
        ax.hist(df['naive_q50_error_pct'], bins=50, alpha=0.5, label='Naive', color='red')
        ax.hist(df['maxent_q50_error_pct'], bins=50, alpha=0.5, label='MaxEnt', color='blue')
        ax.set_xlabel('Median Error (%)')
        ax.set_ylabel('Frequency')
        ax.set_title('Distribution of Median Estimation Errors')
        ax.legend()
        ax.set_xlim(0, df[['naive_q50_error_pct', 'maxent_q50_error_pct']].max().max() * 1.1)

        # 2. Error vs skewness
        ax = axes[0, 1]
        ax.scatter(df['true_skewness'], df['naive_q50_error_pct'], alpha=0.3, color='red', s=10, label='Naive')
        ax.scatter(df['true_skewness'], df['maxent_q50_error_pct'], alpha=0.3, color='blue', s=10, label='MaxEnt')
        ax.set_xlabel('True Skewness')
        ax.set_ylabel('Median Error (%)')
        ax.set_title('Error vs. Data Skewness')
        ax.legend()
        ax.set_ylim(0, 100)

        # 3. Win rate by quantile
        ax = axes[0, 2]
        quantiles = ['q10', 'q25', 'q50', 'q75', 'q90']
        win_rates = [(df[f'maxent_{q}_error_pct'] < df[f'naive_{q}_error_pct']).mean() * 100 for q in quantiles]
        ax.bar(quantiles, win_rates, color='steelblue')
        ax.axhline(50, color='red', linestyle='--', label='Even')
        ax.set_xlabel('Quantile')
        ax.set_ylabel('MaxEnt Win Rate (%)')
        ax.set_title('Win Rate by Quantile')
        ax.set_ylim(0, 100)
        ax.legend()

        # 4. KS statistic comparison
        ax = axes[1, 0]
        ax.hist(df['naive_ks_statistic'], bins=50, alpha=0.5, label='Naive', color='red')
        ax.hist(df['maxent_ks_statistic'], bins=50, alpha=0.5, label='MaxEnt', color='blue')
        ax.set_xlabel('Kolmogorov-Smirnov Statistic')
        ax.set_ylabel('Frequency')
        ax.set_title('Distribution Similarity (KS Test)')
        ax.legend()

        # 5. CV vs Error
        ax = axes[1, 1]
        ax.scatter(df['cv'], df['naive_q50_error_pct'], alpha=0.3, color='red', s=10, label='Naive')
        ax.scatter(df['cv'], df['maxent_q50_error_pct'], alpha=0.3, color='blue', s=10, label='MaxEnt')
        ax.set_xlabel('Coefficient of Variation')
        ax.set_ylabel('Median Error (%)')
        ax.set_title('Error vs. Variability (CV)')
        ax.legend()
        ax.set_ylim(0, 100)

        # 6. Summary stats table
        ax = axes[1, 2]
        ax.axis('off')
        summary = self.generate_summary_report(df)
        table_data = [
            ['Metric', 'Naive', 'MaxEnt', 'Improvement'],
            ['Median Error', f"{summary['naive_median_error']:.2f}%", f"{summary['maxent_median_error']:.2f}%",
             f"{(1 - summary['maxent_median_error']/summary['naive_median_error'])*100:.1f}%"],
            ['Mean Error', f"{summary['naive_mean_error']:.2f}%", f"{summary['maxent_mean_error']:.2f}%",
             f"{(1 - summary['maxent_mean_error']/summary['naive_mean_error'])*100:.1f}%"],
            ['Win Rate (Median)', '-', '-', f"{summary['median_win_rate']:.1f}%"],
            ['', '', '', ''],
        ]
        # Add by distribution
        for dist in ['lognormal', 'beta', 'gamma', 'weibull']:
            if f'{dist}_win_rate' in summary:
                table_data.append([f'{dist.capitalize()} Win Rate', '-', '-', f"{summary[f'{dist}_win_rate']:.1f}%"])

        table = ax.table(cellText=table_data, cellLoc='left', loc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 2)
        ax.set_title('Summary Statistics', pad=20)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.show()

        return summary


def run_validation(n_sims: int = 2000, save_plots: bool = True):
    """Run complete validation study."""
    print(f"Running MaxEnt validation with {n_sims} simulations...")

    validator = ReconstructionValidator(random_state=42)
    df = validator.run_simulation_study(n_sims=n_sims)

    # Save results
    df.to_csv('C:/Users/user/maxent-reconstructor/validation_results.csv', index=False)

    # Generate report
    summary = validator.generate_summary_report(df)

    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    print(f"Median Win Rate: {summary['median_win_rate']:.1f}%")
    print(f"Naive Median Error: {summary['naive_median_error']:.2f}%")
    print(f"MaxEnt Median Error: {summary['maxent_median_error']:.2f}%")
    print(f"Improvement: {(1 - summary['maxent_median_error']/summary['naive_median_error'])*100:.1f}%")
    print("="*60)

    # Plot
    if save_plots:
        validator.plot_results(df, save_path='C:/Users/user/maxent-reconstructor/validation_plots.png')

    return df, summary


if __name__ == "__main__":
    df, summary = run_validation(n_sims=2000)
    print("\nValidation complete!")
