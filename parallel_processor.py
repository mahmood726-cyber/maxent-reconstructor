"""
Parallel Processing Framework for 1000+ MaxEnt Validations
============================================================
Enables scaling from ~100 to 10,000+ simulations using multiprocessing.
"""

import numpy as np
import pandas as pd
from scipy.stats import lognorm, beta, gamma, weibull_min
from scipy import stats
from multiprocessing import Pool, cpu_count, Manager
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
import warnings
from typing import List, Dict, Callable, Optional
from dataclasses import dataclass
import time

import sys
sys.path.insert(0, 'C:/Users/user/maxent-reconstructor')
from maxent_improved import MaxEntReconstructor, NaiveReconstructor

warnings.filterwarnings('ignore')


@dataclass
class SimulationResult:
    """Container for simulation results."""
    scenario: str
    sim_id: int
    distribution: str
    params: Dict
    n: int
    true_median: float
    naive_median: float
    maxent_median: float
    naive_error_pct: float
    maxent_error_pct: float
    maxent_wins: bool
    improvement_pct: float
    cv: float
    true_skew: float


class ParallelMaxEntValidator:
    """
    Parallel validation framework for 1000+ simulations.

    Uses multiprocessing to run simulations in parallel across all CPU cores.
    """

    def __init__(self, n_workers: Optional[int] = None, verbose: bool = True):
        """
        Initialize parallel validator.

        Parameters
        ----------
        n_workers : int, optional
            Number of worker processes. Defaults to CPU count.
        verbose : bool
            Whether to print progress information.
        """
        self.n_workers = n_workers or cpu_count()
        self.verbose = verbose
        if self.verbose:
            print(f"Initialized ParallelMaxEntValidator with {self.n_workers} workers")

    def run_parallel_validation(
        self,
        n_sims: int = 1000,
        scenarios: Optional[List[Dict]] = None,
        distribution: str = 'lognormal',
        seed_start: int = 42
    ) -> pd.DataFrame:
        """
        Run simulations in parallel.

        Parameters
        ----------
        n_sims : int
            Number of simulations to run
        scenarios : list of dict, optional
            Scenario definitions. If None, uses default scenarios.
        distribution : str
            Distribution type for data generation
        seed_start : int
            Starting seed for reproducibility

        Returns
        -------
        pd.DataFrame
            Results dataframe with all simulation outcomes
        """
        if scenarios is None:
            scenarios = self._get_default_scenarios()

        if self.verbose:
            print(f"\nRunning {n_sims} simulations across {self.n_workers} workers...")

        start_time = time.time()

        # Create simulation tasks
        tasks = []
        for i in range(n_sims):
            scenario = np.random.choice(scenarios)
            task = {
                'sim_id': i,
                'seed': seed_start + i,
                'scenario': scenario,
                'distribution': distribution
            }
            tasks.append(task)

        # Run in parallel
        results = self._run_parallel_tasks(tasks)

        elapsed = time.time() - start_time

        if self.verbose:
            print(f"\nCompleted {n_sims} simulations in {elapsed:.1f}s ({elapsed/n_sims:.2f}s per sim)")
            print(f"Throughput: {n_sims/elapsed:.1f} simulations/second")

        # Convert to dataframe
        df = pd.DataFrame([self._result_to_dict(r) for r in results])

        # Save results
        output_path = f'C:/Users/user/maxent-reconstructor/parallel_validation_{n_sims}.csv'
        df.to_csv(output_path, index=False)

        if self.verbose:
            print(f"\nResults saved to: {output_path}")

        return df

    def run_scenario_validation(
        self,
        scenario_configs: Dict[str, Dict],
        n_per_scenario: int = 1000
    ) -> Dict[str, pd.DataFrame]:
        """
        Run validation for multiple scenarios.

        Parameters
        ----------
        scenario_configs : dict
            Dictionary mapping scenario names to configuration dicts
        n_per_scenario : int
            Number of simulations per scenario

        Returns
        -------
        dict
            Dictionary mapping scenario names to result dataframes
        """
        results = {}

        for scenario_name, config in scenario_configs.items():
            if self.verbose:
                print(f"\n{'='*60}")
                print(f"Running scenario: {scenario_name}")
                print(f"{'='*60}")

            df = self.run_parallel_validation(
                n_sims=n_per_scenario,
                scenarios=[config],
                seed_start=42
            )

            results[scenario_name] = df

            if self.verbose:
                win_rate = df['maxent_wins'].mean() * 100
                print(f"MaxEnt win rate: {win_rate:.1f}%")

        return results

    def _run_parallel_tasks(self, tasks: List[Dict]) -> List[SimulationResult]:
        """Run tasks in parallel using ProcessPoolExecutor."""
        results = []

        with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(self._single_simulation, task): task
                for task in tasks
            }

            # Collect results with progress bar
            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="Running simulations",
                disable=not self.verbose
            ):
                try:
                    result = future.result(timeout=60)
                    if result is not None:
                        results.append(result)
                except Exception as e:
                    if self.verbose:
                        print(f"Error in simulation: {e}")
                    continue

        return results

    @staticmethod
    def _single_simulation(task: Dict) -> Optional[SimulationResult]:
        """
        Run a single simulation.

        This must be a static method for pickle compatibility with multiprocessing.
        """
        sim_id = task['sim_id']
        seed = task['seed']
        scenario = task['scenario']
        distribution = task['distribution']

        np.random.seed(seed)

        # Generate true data based on scenario
        try:
            true_data, params = ParallelMaxEntValidator._generate_data(
                distribution, scenario, seed
            )
        except Exception:
            return None

        # Get summary statistics
        true_mean = np.mean(true_data)
        true_sd = np.std(true_data)
        true_min = np.min(true_data)
        true_max = np.max(true_data)
        true_median = np.median(true_data)
        n = len(true_data)

        # Skip if invalid
        if true_sd <= 0 or n < 10:
            return None

        # Naive reconstruction
        try:
            naive = NaiveReconstructor(true_mean, true_sd, true_min, true_max, n, random_state=seed+1000)
            naive_data = naive.generate_ipd()
            naive_median = np.median(naive_data)
        except:
            return None

        # MaxEnt reconstruction
        try:
            maxent = MaxEntReconstructor(true_mean, true_sd, true_min, true_max, n, random_state=seed+2000)
            maxent_result = maxent.generate_ipd()

            if not maxent_result.success:
                return None

            maxent_data = maxent_result.data
            maxent_median = np.median(maxent_data)
        except:
            return None

        # Calculate metrics
        naive_error = abs(naive_median - true_median) / max(abs(true_median), 1e-6) * 100
        maxent_error = abs(maxent_median - true_median) / max(abs(true_median), 1e-6) * 100

        result = SimulationResult(
            scenario=scenario.get('name', distribution),
            sim_id=sim_id,
            distribution=distribution,
            params=params,
            n=n,
            true_median=true_median,
            naive_median=naive_median,
            maxent_median=maxent_median,
            naive_error_pct=naive_error,
            maxent_error_pct=maxent_error,
            maxent_wins=maxent_error < naive_error,
            improvement_pct=(1 - maxent_error/naive_error) * 100 if naive_error > 0 else 0,
            cv=true_sd / true_mean,
            true_skew=stats.skew(true_data)
        )

        return result

    @staticmethod
    def _generate_data(distribution: str, scenario: Dict, seed: int):
        """Generate synthetic data based on distribution and scenario."""
        np.random.seed(seed)

        if distribution == 'lognormal':
            s = scenario.get('s', np.random.uniform(0.3, 2.0))
            scale = scenario.get('scale', np.random.uniform(10, 100))
            n = scenario.get('n', np.random.choice([20, 50, 100, 200, 500]))

            data = lognorm.rvs(s=s, scale=scale, size=n)
            params = {'s': s, 'scale': scale}

        elif distribution == 'beta':
            a = scenario.get('a', np.random.uniform(0.5, 5))
            b = scenario.get('b', np.random.uniform(0.5, 5))
            loc = scenario.get('loc', 0)
            scale_param = scenario.get('scale', 100)
            n = scenario.get('n', np.random.choice([20, 50, 100, 200, 500]))

            data = beta.rvs(a=a, b=b, loc=loc, scale=scale_param, size=n)
            params = {'a': a, 'b': b, 'loc': loc, 'scale': scale_param}

        elif distribution == 'gamma':
            a = scenario.get('a', np.random.uniform(0.5, 5))
            scale = scenario.get('scale', np.random.uniform(5, 50))
            n = scenario.get('n', np.random.choice([20, 50, 100, 200, 500]))

            data = gamma.rvs(a=a, scale=scale, size=n)
            params = {'a': a, 'scale': scale}

        elif distribution == 'weibull':
            c = scenario.get('c', np.random.uniform(0.5, 3))
            scale = scenario.get('scale', np.random.uniform(10, 100))
            n = scenario.get('n', np.random.choice([20, 50, 100, 200, 500]))

            data = weibull_min.rvs(c=c, scale=scale, size=n)
            params = {'c': c, 'scale': scale}

        else:
            # Default to lognormal
            data = lognorm.rvs(s=1.0, scale=50, size=100)
            params = {'s': 1.0, 'scale': 50}

        return data, params

    @staticmethod
    def _get_default_scenarios() -> List[Dict]:
        """Get default scenario configurations."""
        return [
            {'name': 'low_skew', 's': (0.3, 0.5), 'scale': (10, 100)},
            {'name': 'medium_skew', 's': (0.5, 1.5), 'scale': (10, 100)},
            {'name': 'high_skew', 's': (1.5, 3.0), 'scale': (10, 100)},
        ]

    @staticmethod
    def _result_to_dict(result: SimulationResult) -> Dict:
        """Convert SimulationResult to dictionary."""
        return {
            'scenario': result.scenario,
            'sim_id': result.sim_id,
            'distribution': result.distribution,
            'n': result.n,
            'cv': result.cv,
            'true_skew': result.true_skew,
            'true_median': result.true_median,
            'naive_median': result.naive_median,
            'maxent_median': result.maxent_median,
            'naive_error_pct': result.naive_error_pct,
            'maxent_error_pct': result.maxent_error_pct,
            'maxent_wins': result.maxent_wins,
            'improvement_pct': result.improvement_pct,
        }


def run_1000_simulations_quick():
    """
    Quick test of 1000 simulations.
    """
    print("="*70)
    print("1000 SIMULATION VALIDATION - QUICK TEST")
    print("="*70)

    validator = ParallelMaxEntValidator(n_workers=4, verbose=True)

    # Define scenarios
    scenarios = {
        'lognormal_low_skew': {'s': 0.3, 'scale': 50, 'n': 100},
        'lognormal_med_skew': {'s': 1.0, 'scale': 50, 'n': 100},
        'lognormal_high_skew': {'s': 2.0, 'scale': 50, 'n': 100},
    }

    # Run 1000 simulations across scenarios
    results = validator.run_scenario_validation(
        scenario_configs=scenarios,
        n_per_scenario=333  # ~1000 total
    )

    # Aggregate results
    all_df = pd.concat(results.values(), ignore_index=True)

    print("\n" + "="*70)
    print("AGGREGATED RESULTS")
    print("="*70)
    print(f"Total comparisons: {len(all_df)}")
    print(f"MaxEnt win rate: {all_df['maxent_wins'].mean() * 100:.1f}%")
    print(f"Mean naive error: {all_df['naive_error_pct'].mean():.2f}%")
    print(f"Mean maxent error: {all_df['maxent_error_pct'].mean():.2f}%")
    print(f"Mean improvement: {all_df['improvement_pct'].mean():.1f}%")

    return all_df


if __name__ == "__main__":
    # Run quick test with 1000 simulations
    results = run_1000_simulations_quick()
