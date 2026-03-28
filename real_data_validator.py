"""
Real-World Data Validator for MaxEnt IPD Reconstruction
========================================================
Validates the MaxEnt reconstructor using real meta-analysis datasets.

Data Requirements:
------------------
The validator works with datasets containing:
1. **Group-level summary statistics:**
   - Mean (mean_t, mean_c for treatment/control)
   - Standard deviation (sd_t, sd_c)
   - Sample size (n_t, n_c)
   - Min/max values (optional but recommended)

2. **Continuous outcomes:**
   - Effect sizes (SMD, MD, etc.)
   - Raw or standardized mean differences

3. **Data sources:**
   - Cochrane reviews
   - R metadat package
   - IPD meta-analysis datasets
"""

import numpy as np
import pandas as pd
from pathlib import Path
import warnings
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

from maxent_improved import MaxEntReconstructor, NaiveReconstructor


class RealDataValidator:
    """
    Validate MaxEnt reconstruction using real-world meta-analysis data.
    """

    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        self.datasets = {}
        self.results = []

    def load_cochrane_data(self) -> pd.DataFrame:
        """
        Load Cochrane review data from Pairwise70 directory.
        Looks for continuous outcome data with means and SDs.
        """
        cochrane_path = Path(r"C:\Users\user\OneDrive - NHS\Documents\Pairwise70")

        # Try to find suitable data files
        analysis_file = cochrane_path / "analysis" / "ma4_results_pairwise70.csv"

        if analysis_file.exists():
            df = pd.read_csv(analysis_file)

            # Filter for continuous outcomes (MD, SMD)
            continuous_cols = ['mean_t', 'mean_c', 'sd_t', 'sd_c', 'n_t', 'n_c']
            available_cols = [c for c in continuous_cols if c in df.columns]

            if len(available_cols) >= 4:
                return df[available_cols + ['study', 'outcome'] if 'study' in df.columns else available_cols]

        print("Warning: Cochrane data not found or incomplete")
        return None

    def load_metadat_datasets(self) -> Dict[str, pd.DataFrame]:
        """
        Load datasets from the metadat R package (via metahub).
        """
        metadat_path = Path(r"C:\Users\user\OneDrive - NHS\Documents\repo100\metahub\inst\derived\metareg")

        datasets = {}
        csv_files = list(metadat_path.glob("metadat_*.csv"))

        for file in csv_files:
            try:
                df = pd.read_csv(file)
                # Check for continuous data columns
                if any(col in df.columns for col in ['mean', 'mean_ctrl', 'yi']):
                    datasets[file.stem] = df
            except Exception as e:
                print(f"Could not load {file}: {e}")
                continue

        print(f"Loaded {len(datasets)} metadat datasets")
        return datasets

    def create_synthetic_ipd_from_summary(self, mean: float, sd: float, n: int,
                                          min_val: Optional[float] = None,
                                          max_val: Optional[float] = None,
                                          distribution: str = 'normal') -> np.ndarray:
        """
        Create a 'ground truth' IPD from summary statistics using distributional assumptions.

        This simulates the scenario where we have access to the original IPD
        by generating data that matches the summary statistics.
        """
        np.random.seed(42)

        if min_val is None:
            # Estimate bounds based on SD
            min_val = max(mean - 4 * sd, mean - sd * 3)  # At least 3 SD below mean
            if min_val < 0 and mean >= 0:
                min_val = max(0, mean - 4 * sd)

        if max_val is None:
            max_val = mean + 4 * sd

        # Generate data based on distribution assumption
        if distribution == 'lognormal':
            # Lognormal: matches mean and SD approximately
            from scipy.stats import lognorm
            # Estimate parameters
            var = sd**2
            mu = np.log(mean**2 / np.sqrt(var + mean**2))
            sigma = np.sqrt(np.log(1 + var / mean**2))
            data = lognorm.rvs(s=sigma, scale=np.exp(mu), size=n)
        elif distribution == 'skewed':
            # Gamma distribution for positive skew
            from scipy.stats import gamma
            theta = sd**2 / mean
            k = mean / theta
            data = gamma.rvs(a=k, scale=theta, size=n)
        else:
            # Normal with truncation at bounds
            from scipy.stats import truncnorm
            a = (min_val - mean) / sd
            b = (max_val - mean) / sd
            data = truncnorm.rvs(a, b, loc=mean, scale=sd, size=n)

        # Adjust to match exact moments
        current_mean = np.mean(data)
        current_sd = np.std(data)
        data = (data - current_mean) / current_sd * sd + mean

        return data

    def validate_from_summary_statistics(self, df: pd.DataFrame,
                                         mean_col: str = 'mean',
                                         sd_col: str = 'sd',
                                         n_col: str = 'n',
                                         min_col: Optional[str] = None,
                                         max_col: Optional[str] = None,
                                         dataset_name: str = 'unknown') -> pd.DataFrame:
        """
        Validate MaxEnt reconstruction from summary statistics.

        Simulates IPD from the summary stats and compares reconstruction methods.
        """
        results = []

        for idx, row in df.iterrows():
            mean = row[mean_col]
            sd = row[sd_col]
            n = int(row[n_col])

            # Skip invalid entries
            if pd.isna(mean) or pd.isna(sd) or pd.isna(n) or sd <= 0 or n < 10:
                continue

            # Get bounds if available
            min_val = row[min_col] if min_col and min_col in row and pd.notna(row[min_col]) else None
            max_val = row[max_col] if max_col and max_col in row and pd.notna(row[max_col]) else None

            # Estimate bounds if not provided
            if min_val is None:
                min_val = max(mean - 3.5 * sd, 0)  # Non-negative assumption
            if max_val is None:
                max_val = mean + 3.5 * sd

            # Create synthetic "true" IPD using lognormal assumption (common in medical data)
            true_ipd = self.create_synthetic_ipd_from_summary(
                mean, sd, n, min_val, max_val, distribution='lognormal'
            )

            # Get actual true stats
            true_mean = np.mean(true_ipd)
            true_sd = np.std(true_ipd)
            true_min = np.min(true_ipd)
            true_max = np.max(true_ipd)
            true_median = np.median(true_ipd)

            # Naive reconstruction (normal with clipping)
            naive_recon = NaiveReconstructor(mean, sd, min_val, max_val, n, random_state=42)
            naive_ipd = naive_recon.generate_ipd()

            # MaxEnt reconstruction
            try:
                maxent_recon = MaxEntReconstructor(mean, sd, min_val, max_val, n, random_state=42)
                maxent_result = maxent_recon.generate_ipd()
            except (ValueError, RuntimeError) as e:
                # Skip cases where summary statistics are inconsistent
                continue

            if not maxent_result.success:
                continue

            maxent_ipd = maxent_result.data

            # Calculate metrics
            naive_median = np.median(naive_ipd)
            maxent_median = np.median(maxent_ipd)

            # Quantile errors
            for q in [0.1, 0.25, 0.5, 0.75, 0.9]:
                true_q = np.quantile(true_ipd, q)
                naive_q = np.quantile(naive_ipd, q)
                maxent_q = np.quantile(maxent_ipd, q)

                results.append({
                    'dataset': dataset_name,
                    'row_id': idx,
                    'quantile': q,
                    'true_value': true_q,
                    'naive_value': naive_q,
                    'maxent_value': maxent_q,
                    'naive_error_pct': abs(naive_q - true_q) / max(abs(true_q), 1e-6) * 100,
                    'maxent_error_pct': abs(maxent_q - true_q) / max(abs(true_q), 1e-6) * 100,
                    'mean': mean,
                    'sd': sd,
                    'n': n,
                    'cv': sd / mean,
                    'true_skewness': stats.skew(true_ipd),
                })

        return pd.DataFrame(results)

    def run_comprehensive_validation(self) -> pd.DataFrame:
        """
        Run validation across multiple real datasets.
        """
        all_results = []

        # 1. Try Cochrane data
        print("Loading Cochrane data...")
        cochrane_df = self.load_cochrane_data()
        if cochrane_df is not None:
            results = self.validate_from_summary_statistics(
                cochrane_df,
                mean_col='mean_t',
                sd_col='sd_t',
                n_col='n_t',
                dataset_name='Cochrane_treatment'
            )
            all_results.append(results)

        # 2. Try metadat datasets
        print("Loading metadat datasets...")
        datasets = self.load_metadat_datasets()

        for name, df in list(datasets.items())[:10]:  # Process first 10 datasets
            print(f"Processing {name}...")

            # Try different column name combinations
            if 'mean_ctrl' in df.columns and 'sd_ratio' in df.columns:
                # Curtis1998 style data
                results = self.validate_from_summary_statistics(
                    df,
                    mean_col='mean_ctrl',
                    sd_col='sd_ratio',
                    n_col='ntotal',
                    dataset_name=name
                )
                if len(results) > 0:
                    all_results.append(results)

            elif 'yi' in df.columns and 'vi' in df.columns:
                # Effect size data - convert to raw scale
                # For SMD, yi = standardized mean difference, vi = variance
                # Simulate by assuming control SD = 1
                df_sim = df.copy()
                df_sim['mean'] = df_sim['yi'] * 0.5  # Convert SMD to raw mean difference
                df_sim['sd'] = np.sqrt(df_sim['vi'])
                df_sim['n'] = np.where(df_sim['precision'] > 0, 1 / df_sim['precision']**2, 50)

                results = self.validate_from_summary_statistics(
                    df_sim,
                    mean_col='mean',
                    sd_col='sd',
                    n_col='n',
                    dataset_name=name
                )
                if len(results) > 0:
                    all_results.append(results)

        if all_results:
            combined = pd.concat(all_results, ignore_index=True)
            combined.to_csv('C:/Users/user/maxent-reconstructor/real_data_validation_results.csv', index=False)
            return combined
        else:
            print("No valid datasets found for validation")
            return pd.DataFrame()

    def plot_real_data_results(self, df: pd.DataFrame, save_path: Optional[str] = None):
        """Create visualization of real data validation results."""

        if len(df) == 0:
            print("No results to plot")
            return

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # 1. Overall error comparison
        ax = axes[0, 0]
        median_errors = df[df['quantile'] == 0.5].groupby('dataset')[['naive_error_pct', 'maxent_error_pct']].mean()
        if len(median_errors) > 0:
            x = np.arange(len(median_errors))
            width = 0.35
            ax.bar(x - width/2, median_errors['naive_error_pct'], width, label='Naive', color='red', alpha=0.7)
            ax.bar(x + width/2, median_errors['maxent_error_pct'], width, label='MaxEnt', color='blue', alpha=0.7)
            ax.set_ylabel('Median Error (%)')
            ax.set_title('Median Estimation Error by Dataset')
            ax.set_xticks(x)
            ax.set_xticklabels(median_errors.index, rotation=45, ha='right', fontsize=8)
            ax.legend()

        # 2. Win rate by quantile
        ax = axes[0, 1]
        quantile_win_rates = df.groupby('quantile').apply(
            lambda x: (x['maxent_error_pct'] < x['naive_error_pct']).mean() * 100
        )
        quantile_labels = [f'Q{int(q*100)}' for q in quantile_win_rates.index]
        ax.bar(quantile_labels, quantile_win_rates.values, color='steelblue')
        ax.axhline(50, color='red', linestyle='--', label='Even')
        ax.set_ylabel('MaxEnt Win Rate (%)')
        ax.set_title('Win Rate by Quantile')
        ax.set_ylim(0, 100)
        ax.legend()

        # 3. Error vs CV
        ax = axes[1, 0]
        median_df = df[df['quantile'] == 0.5]
        ax.scatter(median_df['cv'], median_df['naive_error_pct'], alpha=0.3, color='red', s=10, label='Naive')
        ax.scatter(median_df['cv'], median_df['maxent_error_pct'], alpha=0.3, color='blue', s=10, label='MaxEnt')
        ax.set_xlabel('Coefficient of Variation')
        ax.set_ylabel('Median Error (%)')
        ax.set_title('Error vs. Data Variability')
        ax.legend()
        ax.set_ylim(0, min(100, median_df[['naive_error_pct', 'maxent_error_pct']].max().max() * 1.1))

        # 4. Summary statistics
        ax = axes[1, 1]
        ax.axis('off')

        summary_text = f"""
        REAL DATA VALIDATION SUMMARY

        Total comparisons: {len(df)}
        Datasets analyzed: {df['dataset'].nunique()}

        Median Error (Q50):
        - Naive: {df[df['quantile']==0.5]['naive_error_pct'].mean():.2f}%
        - MaxEnt: {df[df['quantile']==0.5]['maxent_error_pct'].mean():.2f}%
        - Improvement: {(1 - df[df['quantile']==0.5]['maxent_error_pct'].mean() / df[df['quantile']==0.5]['naive_error_pct'].mean()) * 100:.1f}%

        Overall Win Rate: {(df['maxent_error_pct'] < df['naive_error_pct']).mean() * 100:.1f}%

        Win Rate by Quantile:
        """
        for q in [0.1, 0.25, 0.5, 0.75, 0.9]:
            wr = (df[df['quantile']==q]['maxent_error_pct'] < df[df['quantile']==q]['naive_error_pct']).mean() * 100
            summary_text += f"Q{int(q*100)}: {wr:.1f}%\n"

        ax.text(0.1, 0.5, summary_text, fontsize=10, verticalalignment='center',
                fontfamily='monospace', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.show()


def run_real_data_validation():
    """Run the complete real data validation pipeline."""
    print("="*60)
    print("MaxEnt Real-World Data Validation")
    print("="*60)

    validator = RealDataValidator("data_path")

    # Run validation
    results_df = validator.run_comprehensive_validation()

    if len(results_df) > 0:
        print(f"\nCompleted validation with {len(results_df)} comparisons")

        # Calculate summary stats
        median_results = results_df[results_df['quantile'] == 0.5]
        print(f"\nMedian Estimation Error:")
        print(f"  Naive: {median_results['naive_error_pct'].mean():.2f}%")
        print(f"  MaxEnt: {median_results['maxent_error_pct'].mean():.2f}%")
        print(f"  Win Rate: {(median_results['maxent_error_pct'] < median_results['naive_error_pct']).mean() * 100:.1f}%")

        # Plot results
        validator.plot_real_data_results(
            results_df,
            save_path='C:/Users/user/maxent-reconstructor/real_data_validation_plots.png'
        )

        return results_df
    else:
        print("No validation results generated")
        return None


if __name__ == "__main__":
    results = run_real_data_validation()
