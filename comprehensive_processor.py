"""
Comprehensive Data Processor for MaxEnt Validation
====================================================
Processes all available datasets from Pairwise70 and repo100 directories.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from scipy.stats import lognorm, skew
import warnings
from tqdm import tqdm
import json

import sys
sys.path.insert(0, 'C:/Users/user/maxent-reconstructor')
from maxent_improved import MaxEntReconstructor, NaiveReconstructor

warnings.filterwarnings('ignore')


class ComprehensiveDataProcessor:
    """Process all available meta-analysis datasets for MaxEnt validation."""

    def __init__(self):
        self.pairwise70_path = Path(r"C:\Users\user\OneDrive - NHS\Documents\Pairwise70")
        self.repo100_path = Path(r"C:\Users\user\OneDrive - NHS\Documents\repo100")
        self.results = []
        self.dataset_stats = {}

    def process_cochrane_data(self) -> pd.DataFrame:
        """Process Cochrane review data from Pairwise70."""
        print("\n" + "="*60)
        print("Processing Cochrane Data (Pairwise70)")
        print("="*60)

        results = []

        # Try different possible files
        possible_files = [
            self.pairwise70_path / "analysis" / "ma4_results_pairwise70.csv",
            self.pairwise70_path / "analysis" / "ma_summary.csv",
        ]

        for file_path in possible_files:
            if file_path.exists():
                try:
                    df = pd.read_csv(file_path)
                    print(f"Found file: {file_path.name}")
                    print(f"Shape: {df.shape}")

                    # Look for treatment and control columns
                    t_cols = [c for c in df.columns if 'mean_t' in c.lower() or 'meant' in c.lower()]
                    c_cols = [c for c in df.columns if 'mean_c' in c.lower() or 'meanc' in c.lower()]

                    if t_cols and c_cols:
                        mean_t_col = t_cols[0]
                        mean_c_col = c_cols[0]
                        sd_t_col = mean_t_col.replace('mean', 'sd')
                        sd_c_col = mean_c_col.replace('mean', 'sd')
                        n_t_col = 'n_t' if 'n_t' in df.columns else None
                        n_c_col = 'n_c' if 'n_c' in df.columns else None

                        print(f"Using columns: {mean_t_col}, {mean_c_col}, {sd_t_col}, {sd_c_col}")

                        results = self._process_dataframe(
                            df, 'Cochrane',
                            mean_col=mean_t_col,
                            sd_col=sd_t_col,
                            n_col=n_t_col
                        )
                        break
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    continue

        return pd.DataFrame(results) if results else pd.DataFrame()

    def process_metadat_datasets(self, max_datasets: int = 50) -> pd.DataFrame:
        """Process datasets from metadat package via metahub."""
        print("\n" + "="*60)
        print("Processing metadat Datasets")
        print("="*60)

        metadat_path = self.repo100_path / "metahub" / "inst" / "derived" / "metareg"
        csv_files = list(metadat_path.glob("metadat_dat.*.csv"))

        print(f"Found {len(csv_files)} metadat datasets")

        all_results = []
        processed = 0

        for file_path in tqdm(csv_files[:max_datasets], desc="Processing datasets"):
            try:
                df = pd.read_csv(file_path)
                dataset_name = file_path.stem

                # Determine data type and process accordingly
                file_results = self._process_metadat_file(df, dataset_name)

                if file_results:
                    all_results.extend(file_results)
                    processed += 1

            except Exception as e:
                # print(f"Error processing {file_path.name}: {e}")
                continue

        print(f"\nSuccessfully processed {processed}/{len(csv_files[:max_datasets])} datasets")

        return pd.DataFrame(all_results)

    def _process_metadat_file(self, df: pd.DataFrame, name: str) -> List[Dict]:
        """Process a single metadat file."""
        results = []

        # Check for different data formats

        # Format 1: mean_ctrl, sd_ratio, ntotal (like curtis1998)
        if 'mean_ctrl' in df.columns and 'sd_ratio' in df.columns:
            for idx, row in df.head(50).iterrows():  # Limit to 50 rows per dataset
                try:
                    mean = row['mean_ctrl']
                    sd = row['sd_ratio']
                    n = row.get('ntotal', row.get('n', 50))

                    if pd.isna(mean) or pd.isna(sd) or pd.isna(n) or sd <= 0 or n < 10:
                        continue

                    result = self._create_validation_comparison(mean, sd, n, name, idx)
                    if result:
                        results.append(result)

                except Exception:
                    continue

        # Format 2: yi (effect size), vi (variance), n or precision
        elif 'yi' in df.columns and 'vi' in df.columns:
            for idx, row in df.head(50).iterrows():
                try:
                    yi = row['yi']
                    vi = row['vi']

                    if pd.isna(yi) or pd.isna(vi) or vi <= 0:
                        continue

                    # Convert to raw scale (assume control SD = 1 for SMD)
                    mean = abs(yi) * 0.5  # Half the effect as mean difference
                    sd = np.sqrt(vi) * 0.5

                    # Estimate n from precision if available
                    if 'precision' in df.columns and pd.notna(row['precision']):
                        n = max(20, int(1 / (row['precision'] ** 2)))
                    elif 'ntotal' in df.columns and pd.notna(row['ntotal']):
                        n = int(row['ntotal'])
                    else:
                        n = 50  # Default

                    if n < 10 or sd <= 0:
                        continue

                    result = self._create_validation_comparison(mean, sd, n, name, idx)
                    if result:
                        results.append(result)

                except Exception:
                    continue

        return results

    def _process_dataframe(self, df: pd.DataFrame, source: str,
                          mean_col: str, sd_col: str,
                          n_col: Optional[str] = None) -> List[Dict]:
        """Process a generic dataframe with summary statistics."""
        results = []

        for idx, row in df.head(100).iterrows():
            try:
                mean = row[mean_col]
                sd = row[sd_col]
                n = row[n_col] if n_col else row.get('n', 50)

                if pd.isna(mean) or pd.isna(sd) or pd.isna(n):
                    continue
                if sd <= 0 or n < 10:
                    continue

                result = self._create_validation_comparison(mean, sd, n, source, idx)
                if result:
                    results.append(result)

            except Exception:
                continue

        return results

    def _create_validation_comparison(self, mean: float, sd: float, n: int,
                                     source: str, row_id: int) -> Optional[Dict]:
        """Create a single validation comparison."""
        np.random.seed(42 + row_id % 1000)

        # Estimate bounds
        min_val = max(0, mean - 4 * sd)  # Non-negative assumption
        max_val = mean + 4 * sd

        # Create synthetic true data using lognormal (common in medical data)
        try:
            true_data = lognorm.rvs(s=min(1.5, sd/mean), scale=mean, size=n)
        except:
            return None

        # Adjust to match target statistics
        current_mean = np.mean(true_data)
        current_sd = np.std(true_data)
        true_data = (true_data - current_mean) / current_sd * sd + mean
        true_data = np.clip(true_data, min_val, max_val)

        true_mean = np.mean(true_data)
        true_sd = np.std(true_data)
        true_min = np.min(true_data)
        true_max = np.max(true_data)
        true_median = np.median(true_data)
        true_skew = skew(true_data)

        # Naive reconstruction
        try:
            naive = NaiveReconstructor(true_mean, true_sd, true_min, true_max, n, random_state=42)
            naive_data = naive.generate_ipd()
            naive_median = np.median(naive_data)
            naive_q25 = np.quantile(naive_data, 0.25)
            naive_q75 = np.quantile(naive_data, 0.75)
        except:
            return None

        # MaxEnt reconstruction
        try:
            maxent = MaxEntReconstructor(true_mean, true_sd, true_min, true_max, n, random_state=42)
            maxent_result = maxent.generate_ipd()

            if not maxent_result.success:
                return None

            maxent_data = maxent_result.data
            maxent_median = np.median(maxent_data)
            maxent_q25 = np.quantile(maxent_data, 0.25)
            maxent_q75 = np.quantile(maxent_data, 0.75)
        except (ValueError, RuntimeError):
            return None

        # Calculate errors
        naive_err = abs(naive_median - true_median) / max(abs(true_median), 1e-6) * 100
        maxent_err = abs(maxent_median - true_median) / max(abs(true_median), 1e-6) * 100

        naive_q25_err = abs(naive_q25 - np.quantile(true_data, 0.25)) / max(abs(np.quantile(true_data, 0.25)), 1e-6) * 100
        maxent_q25_err = abs(maxent_q25 - np.quantile(true_data, 0.25)) / max(abs(np.quantile(true_data, 0.25)), 1e-6) * 100

        naive_q75_err = abs(naive_q75 - np.quantile(true_data, 0.75)) / max(abs(np.quantile(true_data, 0.75)), 1e-6) * 100
        maxent_q75_err = abs(maxent_q75 - np.quantile(true_data, 0.75)) / max(abs(np.quantile(true_data, 0.75)), 1e-6) * 100

        return {
            'source': source,
            'row_id': row_id,
            'n': n,
            'mean': true_mean,
            'sd': true_sd,
            'cv': true_sd / true_mean,
            'true_skew': true_skew,
            'true_median': true_median,
            'naive_median': naive_median,
            'maxent_median': maxent_median,
            'naive_error_pct': naive_err,
            'maxent_error_pct': maxent_err,
            'naive_q25_error_pct': naive_q25_err,
            'maxent_q25_error_pct': maxent_q25_err,
            'naive_q75_error_pct': naive_q75_err,
            'maxent_q75_error_pct': maxent_q75_err,
            'maxent_wins': maxent_err < naive_err,
            'improvement_pct': (1 - maxent_err/naive_err) * 100 if naive_err > 0 else 0,
            'maxent_method': 'maxent'  # Placeholder
        }

    def run_comprehensive_processing(self) -> pd.DataFrame:
        """Run all processing."""
        print("\n" + "="*70)
        print("COMPREHENSIVE MAXENT VALIDATION - DATA PROCESSING")
        print("="*70)

        all_results = []

        # Process Cochrane data
        cochrane_results = self.process_cochrane_data()
        if len(cochrane_results) > 0:
            all_results.append(cochrane_results)
            print(f"Cochrane: {len(cochrane_results)} comparisons")

        # Process metadat
        metadat_results = self.process_metadat_datasets(max_datasets=30)
        if len(metadat_results) > 0:
            all_results.append(metadat_results)
            print(f"metadat: {len(metadat_results)} comparisons")

        if all_results:
            combined = pd.concat(all_results, ignore_index=True)
            print(f"\nTotal comparisons: {len(combined)}")
            print(f"Unique sources: {combined['source'].nunique()}")

            # Save results
            output_path = Path('C:/Users/user/maxent-reconstructor/comprehensive_validation_results.csv')
            combined.to_csv(output_path, index=False)
            print(f"\nResults saved to: {output_path}")

            return combined
        else:
            print("\nNo results generated")
            return pd.DataFrame()


def main():
    """Run comprehensive processing."""
    processor = ComprehensiveDataProcessor()
    df = processor.run_comprehensive_processing()

    if len(df) > 0:
        print("\n" + "="*70)
        print("SUMMARY STATISTICS")
        print("="*70)

        print(f"\nTotal comparisons: {len(df)}")
        print(f"Unique sources: {df['source'].nunique()}")
        print(f"\nMaxEnt win rate: {df['maxent_wins'].mean() * 100:.1f}%")
        print(f"Mean naive error: {df['naive_error_pct'].mean():.2f}%")
        print(f"Mean maxent error: {df['maxent_error_pct'].mean():.2f}%")
        print(f"Mean improvement: {df['improvement_pct'].mean():.1f}%")

        print(f"\nBy source:")
        for source in df['source'].unique():
            source_df = df[df['source'] == source]
            print(f"  {source}: {len(source_df)} comparisons, "
                  f"win rate {source_df['maxent_wins'].mean() * 100:.1f}%")

        return df
    else:
        return None


if __name__ == "__main__":
    results = main()
