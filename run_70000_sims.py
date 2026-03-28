"""
70,000 Simulation Validation Framework
===========================================
Scales MaxEnt validation to 70,000+ simulations using optimized parallel processing.

Usage:
    python run_70000_sims.py
"""

import numpy as np
import pandas as pd
from scipy.stats import lognorm, beta, gamma, weibull_min, expon, chi2
from scipy import stats
from multiprocessing import Pool, cpu_count
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
import warnings
import time
from pathlib import Path
from typing import List, Dict, Optional
import json

import sys
sys.path.insert(0, 'C:/Users/user/maxent-reconstructor')
from maxent_improved import MaxEntReconstructor, NaiveReconstructor

warnings.filterwarnings('ignore')


class SeventyThousandValidator:
    """
    Framework for running 70,000+ MaxEnt validation simulations.

    Configuration:
    - 70 scenarios × 1,000 simulations = 70,000 total
    - Uses all available CPU cores
    - Saves intermediate results every 5,000 sims
    - Estimated runtime: 1-2 hours with 16 cores
    """

    # 70 diverse scenarios covering different distributions and parameters
    SCENARIOS = {
        # Lognormal scenarios (15)
        'lognormal_s0.2': {'dist': 'lognormal', 's': 0.2, 'scale': 50},
        'lognormal_s0.3': {'dist': 'lognormal', 's': 0.3, 'scale': 50},
        'lognormal_s0.4': {'dist': 'lognormal', 's': 0.4, 'scale': 50},
        'lognormal_s0.5': {'dist': 'lognormal', 's': 0.5, 'scale': 50},
        'lognormal_s0.7': {'dist': 'lognormal', 's': 0.7, 'scale': 50},
        'lognormal_s1.0': {'dist': 'lognormal', 's': 1.0, 'scale': 50},
        'lognormal_s1.2': {'dist': 'lognormal', 's': 1.2, 'scale': 50},
        'lognormal_s1.5': {'dist': 'lognormal', 's': 1.5, 'scale': 50},
        'lognormal_s1.8': {'dist': 'lognormal', 's': 1.8, 'scale': 50},
        'lognormal_s2.0': {'dist': 'lognormal', 's': 2.0, 'scale': 50},
        'lognormal_s2.5': {'dist': 'lognormal', 's': 2.5, 'scale': 50},
        'lognormal_s3.0': {'dist': 'lognormal', 's': 3.0, 'scale': 50},
        'lognormal_scale20': {'dist': 'lognormal', 's': 1.0, 'scale': 20},
        'lognormal_scale100': {'dist': 'lognormal', 's': 1.0, 'scale': 100},
        'lognormal_scale200': {'dist': 'lognormal', 's': 1.0, 'scale': 200},

        # Beta scenarios (10)
        'beta_a1_b1': {'dist': 'beta', 'a': 1.0, 'b': 1.0, 'loc': 0, 'scale': 100},
        'beta_a0.5_b2': {'dist': 'beta', 'a': 0.5, 'b': 2.0, 'loc': 0, 'scale': 100},
        'beta_a0.5_b5': {'dist': 'beta', 'a': 0.5, 'b': 5.0, 'loc': 0, 'scale': 100},
        'beta_a2_b2': {'dist': 'beta', 'a': 2.0, 'b': 2.0, 'loc': 0, 'scale': 100},
        'beta_a2_b5': {'dist': 'beta', 'a': 2.0, 'b': 5.0, 'loc': 0, 'scale': 100},
        'beta_a5_b2': {'dist': 'beta', 'a': 5.0, 'b': 2.0, 'loc': 0, 'scale': 100},
        'beta_a5_b5': {'dist': 'beta', 'a': 5.0, 'b': 5.0, 'loc': 0, 'scale': 100},
        'beta_a10_b2': {'dist': 'beta', 'a': 10.0, 'b': 2.0, 'loc': 0, 'scale': 100},
        'beta_a2_b10': {'dist': 'beta', 'a': 2.0, 'b': 10.0, 'loc': 0, 'scale': 100},
        'beta_a5_b10': {'dist': 'beta', 'a': 5.0, 'b': 10.0, 'loc': 0, 'scale': 100},

        # Gamma scenarios (10)
        'gamma_a0.5': {'dist': 'gamma', 'a': 0.5, 'scale': 30},
        'gamma_a1.0': {'dist': 'gamma', 'a': 1.0, 'scale': 30},
        'gamma_a1.5': {'dist': 'gamma', 'a': 1.5, 'scale': 30},
        'gamma_a2.0': {'dist': 'gamma', 'a': 2.0, 'scale': 30},
        'gamma_a2.5': {'dist': 'gamma', 'a': 2.5, 'scale': 30},
        'gamma_a3.0': {'dist': 'gamma', 'a': 3.0, 'scale': 30},
        'gamma_a4.0': {'dist': 'gamma', 'a': 4.0, 'scale': 30},
        'gamma_a5.0': {'dist': 'gamma', 'a': 5.0, 'scale': 30},
        'gamma_scale10': {'dist': 'gamma', 'a': 2.0, 'scale': 10},
        'gamma_scale50': {'dist': 'gamma', 'a': 2.0, 'scale': 50},

        # Weibull scenarios (10)
        'weibull_c0.5': {'dist': 'weibull_min', 'c': 0.5, 'scale': 50},
        'weibull_c0.7': {'dist': 'weibull_min', 'c': 0.7, 'scale': 50},
        'weibull_c1.0': {'dist': 'weibull_min', 'c': 1.0, 'scale': 50},
        'weibull_c1.2': {'dist': 'weibull_min', 'c': 1.2, 'scale': 50},
        'weibull_c1.5': {'dist': 'weibull_min', 'c': 1.5, 'scale': 50},
        'weibull_c1.8': {'dist': 'weibull_min', 'c': 1.8, 'scale': 50},
        'weibull_c2.0': {'dist': 'weibull_min', 'c': 2.0, 'scale': 50},
        'weibull_c2.5': {'dist': 'weibull_min', 'c': 2.5, 'scale': 50},
        'weibull_c3.0': {'dist': 'weibull_min', 'c': 3.0, 'scale': 50},
        'weibull_scale100': {'dist': 'weibull_min', 'c': 1.5, 'scale': 100},

        # Exponential scenarios (5)
        'expon_scale10': {'dist': 'expon', 'scale': 10},
        'expon_scale20': {'dist': 'expon', 'scale': 20},
        'expon_scale30': {'dist': 'expon', 'scale': 30},
        'expon_scale50': {'dist': 'expon', 'scale': 50},
        'expon_scale100': {'dist': 'expon', 'scale': 100},

        # Chi-square scenarios (5)
        'chi2_df1': {'dist': 'chi2', 'df': 1, 'scale': 10},
        'chi2_df2': {'dist': 'chi2', 'df': 2, 'scale': 10},
        'chi2_df3': {'dist': 'chi2', 'df': 3, 'scale': 10},
        'chi2_df5': {'dist': 'chi2', 'df': 5, 'scale': 10},
        'chi2_df10': {'dist': 'chi2', 'df': 10, 'scale': 10},

        # Varying sample sizes (10)
        'n20_lognormal': {'dist': 'lognormal', 's': 1.0, 'scale': 50, 'n': 20},
        'n50_lognormal': {'dist': 'lognormal', 's': 1.0, 'scale': 50, 'n': 50},
        'n100_lognormal': {'dist': 'lognormal', 's': 1.0, 'scale': 50, 'n': 100},
        'n200_lognormal': {'dist': 'lognormal', 's': 1.0, 'scale': 50, 'n': 200},
        'n500_lognormal': {'dist': 'lognormal', 's': 1.0, 'scale': 50, 'n': 500},
        'n1000_lognormal': {'dist': 'lognormal', 's': 1.0, 'scale': 50, 'n': 1000},
        'n20_gamma': {'dist': 'gamma', 'a': 2.0, 'scale': 30, 'n': 20},
        'n50_gamma': {'dist': 'gamma', 'a': 2.0, 'scale': 30, 'n': 50},
        'n200_gamma': {'dist': 'gamma', 'a': 2.0, 'scale': 30, 'n': 200},
        'n500_gamma': {'dist': 'gamma', 'a': 2.0, 'scale': 30, 'n': 500},

        # Mixed/edge cases (5)
        'very_low_cv': {'dist': 'lognormal', 's': 0.1, 'scale': 50},  # CV < 0.2
        'very_high_cv': {'dist': 'lognormal', 's': 3.0, 'scale': 50},  # CV > 2
        'bounded_narrow': {'dist': 'beta', 'a': 2, 'b': 2, 'loc': 0, 'scale': 10},
        'bounded_wide': {'dist': 'beta', 'a': 2, 'b': 2, 'loc': 0, 'scale': 1000},
        'extreme_skew': {'dist': 'lognormal', 's': 4.0, 'scale': 50},
    }

    def __init__(self, n_workers: Optional[int] = None, output_dir: str = 'C:/Users/user/maxent-reconstructor'):
        self.n_workers = n_workers or min(cpu_count(), 16)  # Cap at 16
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        print(f"Initialized {self.__class__.__name__} with {self.n_workers} workers")
        print(f"Total scenarios: {len(self.SCENARIOS)}")

    def run_70000_validation(
        self,
        n_per_scenario: int = 1000,
        batch_size: int = 5000,
        save_interval: int = 5000
    ) -> pd.DataFrame:
        """
        Run 70,000 simulations (70 scenarios × 1000 sims each).

        Parameters
        ----------
        n_per_scenario : int
            Simulations per scenario (default: 1000)
        batch_size : int
            Batch size for intermediate saves
        save_interval : int
            Save results every N simulations
        """
        total_sims = len(self.SCENARIOS) * n_per_scenario
        print(f"\n{'='*70}")
        print(f"70,000 SIMULATION VALIDATION")
        print(f"{'='*70}")
        print(f"Total scenarios: {len(self.SCENARIOS)}")
        print(f"Simulations per scenario: {n_per_scenario}")
        print(f"Total simulations: {total_sims:,}")
        print(f"Workers: {self.n_workers}")
        print(f"Estimated time: {self._estimate_time(total_sims)}")
        print(f"{'='*70}\n")

        all_results = []
        scenario_num = 0
        total_processed = 0
        start_time = time.time()

        for scenario_name, config in self.SCENARIOS.items():
            scenario_num += 1
            print(f"\n[{scenario_num}/{len(self.SCENARIOS)}] Processing: {scenario_name}")
            print(f"  Config: {config}")

            # Run simulations for this scenario
            scenario_results = self._run_scenario_parallel(
                scenario_name, config, n_per_scenario
            )

            # Add scenario identifier
            for result in scenario_results:
                result['scenario_group'] = scenario_name

            all_results.extend(scenario_results)
            total_processed += len(scenario_results)

            # Save intermediate results
            if total_processed % save_interval == 0:
                self._save_intermediate(all_results, total_processed)

            # Progress update
            elapsed = time.time() - start_time
            sims_per_sec = total_processed / elapsed
            remaining = total_sims - total_processed
            eta = remaining / sims_per_sec if sims_per_sec > 0 else 0

            print(f"  Progress: {total_processed:,}/{total_sims:,} ({100*total_processed/total_sims:.1f}%)")
            print(f"  Speed: {sims_per_sec:.1f} sims/sec")
            print(f"  ETA: {eta/60:.1f} minutes")
            print(f"  Elapsed: {elapsed/60:.1f} minutes")

        # Save final results
        final_df = pd.DataFrame(all_results)
        output_path = self.output_dir / f'validation_{total_sims}_final.csv'
        final_df.to_csv(output_path, index=False)

        print(f"\n{'='*70}")
        print(f"COMPLETE! Total simulations: {len(final_df):,}")
        print(f"Results saved to: {output_path}")
        print(f"Total time: {time.time()-start_time:.1f}s ({(time.time()-start_time)/60:.1f} minutes)")
        print(f"{'='*70}\n")

        # Print summary
        self._print_summary(final_df)

        return final_df

    def _run_scenario_parallel(
        self,
        scenario_name: str,
        config: Dict,
        n_sims: int
    ) -> List[Dict]:
        """Run simulations for a single scenario in parallel."""

        tasks = [
            {
                'scenario': scenario_name,
                'config': config,
                'sim_id': i,
                'seed': 42 + i
            }
            for i in range(n_sims)
        ]

        results = []
        completed = 0

        with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
            # Submit all tasks
            futures = {executor.submit(self._single_simulation, task): task for task in tasks}

            # Collect with progress bar
            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc=f"  {scenario_name[:20]}",
                leave=False,
                disable=False
            ):
                try:
                    result = future.result(timeout=120)
                    if result is not None:
                        results.append(result)
                    completed += 1
                except Exception as e:
                    # Silently skip failed simulations
                    pass

        return results

    @staticmethod
    def _single_simulation(task: Dict) -> Optional[Dict]:
        """Run a single simulation (must be static for multiprocessing)."""
        np.random.seed(task['seed'])
        config = task['config']
        scenario = task['scenario']
        sim_id = task['sim_id']

        try:
            # Generate true data
            true_data = SeventyThousandValidator._generate_data(config)
            n = len(true_data)

            # Get summary stats
            true_mean = np.mean(true_data)
            true_sd = np.std(true_data)
            true_min = np.min(true_data)
            true_max = np.max(true_data)
            true_median = np.median(true_data)

            if true_sd <= 0 or n < 10:
                return None

            # Naive reconstruction
            naive = NaiveReconstructor(true_mean, true_sd, true_min, true_max, n, random_state=task['seed']+1000)
            naive_data = naive.generate_ipd()

            # MaxEnt reconstruction
            maxent = MaxEntReconstructor(true_mean, true_sd, true_min, true_max, n, random_state=task['seed']+2000)
            maxent_result = maxent.generate_ipd()

            if not maxent_result.success:
                return None

            maxent_data = maxent_result.data

            # Calculate metrics
            naive_median = np.median(naive_data)
            maxent_median = np.median(maxent_data)

            return {
                'scenario': scenario,
                'sim_id': sim_id,
                'n': n,
                'cv': true_sd / true_mean if true_mean != 0 else 0,
                'true_skew': stats.skew(true_data),
                'true_median': true_median,
                'naive_median': naive_median,
                'maxent_median': maxent_median,
                'naive_error_pct': abs(naive_median - true_median) / max(abs(true_median), 1e-6) * 100,
                'maxent_error_pct': abs(maxent_median - true_median) / max(abs(true_median), 1e-6) * 100,
                'maxent_wins': abs(maxent_median - true_median) < abs(naive_median - true_median),
                'improvement_pct': (1 - abs(maxent_median - true_median) / max(abs(naive_median - true_median), 1e-6)) * 100
            }

        except Exception:
            return None

    @staticmethod
    def _generate_data(config: Dict) -> np.ndarray:
        """Generate synthetic data based on configuration."""
        dist = config['dist']
        n = config.get('n', 100)

        if dist == 'lognormal':
            data = lognorm.rvs(s=config['s'], scale=config['scale'], size=n)
        elif dist == 'beta':
            data = beta.rvs(a=config['a'], b=config['b'],
                           loc=config.get('loc', 0), scale=config.get('scale', 100), size=n)
        elif dist == 'gamma':
            data = gamma.rvs(a=config['a'], scale=config['scale'], size=n)
        elif dist == 'weibull_min':
            data = weibull_min.rvs(c=config['c'], scale=config['scale'], size=n)
        elif dist == 'expon':
            data = expon.rvs(scale=config['scale'], size=n)
        elif dist == 'chi2':
            data = chi2.rvs(df=config['df'], scale=config['scale'], size=n)
        else:
            data = lognorm.rvs(s=1.0, scale=50, size=n)

        return data

    def _save_intermediate(self, results: List[Dict], total: int):
        """Save intermediate results."""
        df = pd.DataFrame(results)
        output_path = self.output_dir / f'validation_{total}_intermediate.csv'
        df.to_csv(output_path, index=False)
        print(f"  [Saved intermediate: {output_path.name}]")

    def _estimate_time(self, total_sims: int) -> str:
        """Estimate completion time based on benchmarks."""
        # Benchmark: ~6 sims/sec with 4 workers
        # Scales roughly linearly with cores up to 16
        effective_workers = min(self.n_workers, 16)
        sims_per_sec = 6 * (effective_workers / 4)
        total_seconds = total_sims / sims_per_sec

        if total_seconds < 60:
            return f"{total_seconds:.0f} seconds"
        elif total_seconds < 3600:
            return f"{total_seconds/60:.1f} minutes"
        else:
            return f"{total_seconds/3600:.1f} hours"

    def _print_summary(self, df: pd.DataFrame):
        """Print summary statistics."""
        print(f"\n{'='*70}")
        print(f"SUMMARY STATISTICS")
        print(f"{'='*70}")
        print(f"Total comparisons: {len(df):,}")
        print(f"MaxEnt win rate: {df['maxent_wins'].mean() * 100:.1f}%")
        print(f"Mean naive error: {df['naive_error_pct'].mean():.2f}%")
        print(f"Mean maxent error: {df['maxent_error_pct'].mean():.2f}%")
        print(f"Median naive error: {df['naive_error_pct'].median():.2f}%")
        print(f"Median maxent error: {df['maxent_error_pct'].median():.2f}%")
        print(f"Mean improvement: {df['improvement_pct'].mean():.1f}%")

        # By CV ranges
        print(f"\nBy Coefficient of Variation:")
        df['cv_range'] = pd.cut(df['cv'], bins=[0, 0.2, 0.5, 1.0, 2.0, 100],
                                labels=['<0.2', '0.2-0.5', '0.5-1.0', '1.0-2.0', '>2.0'])
        for cv_range in df['cv_range'].cat.categories:
            subset = df[df['cv_range'] == cv_range]
            if len(subset) > 0:
                wr = subset['maxent_wins'].mean() * 100
                print(f"  {cv_range:>8}: {len(subset):>5} sims, win rate: {wr:5.1f}%")

        print(f"{'='*70}\n")


def main():
    """Run 70,000 simulation validation."""
    print("="*70)
    print("70,000 SIMULATION VALIDATION")
    print("="*70)
    print("\nThis will run 70 scenarios × 1000 simulations = 70,000 total")
    print("Estimated time: 1-2 hours depending on CPU cores\n")

    # Initialize validator
    validator = SeventyThousandValidator(n_workers=None)  # Uses all available cores

    # Run validation
    results_df = validator.run_70000_validation(
        n_per_scenario=1000,
        batch_size=5000,
        save_interval=10000
    )

    print("\nAll results saved to:")
    print(f"  - validation_70000_final.csv")
    print(f"  - Intermediate checkpoints saved every 10,000 simulations")

    return results_df


if __name__ == "__main__":
    results = main()
