"""
Publication-Quality Visualizations for MaxEnt IPD Reconstruction
================================================================
Creates figures suitable for journal publication.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats
from typing import Optional

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


class PublicationVisualizer:
    """Create publication-quality figures for MaxEnt validation."""

    def __init__(self, results_df: pd.DataFrame, output_dir: str = 'C:/Users/user/maxent-reconstructor/figures'):
        self.df = results_df
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def create_figure_1_overview(self) -> None:
        """
        Figure 1: Overview of MaxEnt performance.
        Panel A: Error distribution comparison
        Panel B: Win rate by quantile
        Panel C: Cumulative distribution of errors
        """
        fig, axes = plt.subplots(1, 3, figsize=(14, 4))

        # Panel A: Error distribution
        ax = axes[0]
        ax.hist(self.df['naive_error_pct'], bins=50, alpha=0.6, label='Naive Normal',
                color='#E74C3C', edgecolor='white', linewidth=0.5)
        ax.hist(self.df['maxent_error_pct'], bins=50, alpha=0.6, label='MaxEnt',
                color='#3498DB', edgecolor='white', linewidth=0.5)
        ax.set_xlabel('Absolute Median Error (%)', fontweight='bold')
        ax.set_ylabel('Frequency', fontweight='bold')
        ax.set_title('(A) Distribution of Median Estimation Errors', fontweight='bold')
        ax.legend(loc='upper right', frameon=True, shadow=True)
        ax.set_xlim(0, min(100, self.df[['naive_error_pct', 'maxent_error_pct']].max().max() * 1.05))

        # Panel B: Win rate by metric
        ax = axes[1]
        metrics = ['Median\n(Q50)', 'Q25', 'Q75']
        win_rates = [
            (self.df['maxent_error_pct'] < self.df['naive_error_pct']).mean() * 100,
            (self.df['maxent_q25_error_pct'] < self.df['naive_q25_error_pct']).mean() * 100,
            (self.df['maxent_q75_error_pct'] < self.df['naive_q75_error_pct']).mean() * 100
        ]
        colors = ['#3498DB' if wr > 50 else '#E74C3C' for wr in win_rates]
        bars = ax.bar(metrics, win_rates, color=colors, edgecolor='black', linewidth=0.8, alpha=0.8)
        ax.axhline(50, color='gray', linestyle='--', linewidth=1, alpha=0.7)
        ax.set_ylabel('MaxEnt Win Rate (%)', fontweight='bold')
        ax.set_title('(B) Win Rate by Quantile', fontweight='bold')
        ax.set_ylim(0, 100)
        ax.grid(axis='y', alpha=0.3)

        # Add value labels on bars
        for bar, wr in zip(bars, win_rates):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                   f'{wr:.0f}%', ha='center', va='bottom', fontweight='bold', fontsize=9)

        # Panel C: Cumulative distribution
        ax = axes[2]
        naive_sorted = np.sort(self.df['naive_error_pct'])
        maxent_sorted = np.sort(self.df['maxent_error_pct'])
        ax.plot(naive_sorted, np.arange(1, len(naive_sorted) + 1) / len(naive_sorted) * 100,
               label='Naive Normal', color='#E74C3C', linewidth=2)
        ax.plot(maxent_sorted, np.arange(1, len(maxent_sorted) + 1) / len(maxent_sorted) * 100,
               label='MaxEnt', color='#3498DB', linewidth=2)
        ax.set_xlabel('Absolute Median Error (%)', fontweight='bold')
        ax.set_ylabel('Cumulative Percentage (%)', fontweight='bold')
        ax.set_title('(C) Cumulative Distribution of Errors', fontweight='bold')
        ax.legend(loc='lower right', frameon=True, shadow=True)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, min(100, max(naive_sorted[-1], maxent_sorted[-1]) * 1.05))

        plt.tight_layout()
        plt.savefig(self.output_dir / 'figure1_overview.png')
        plt.savefig(self.output_dir / 'figure1_overview.pdf')
        plt.show()

    def create_figure_2_performance_characteristics(self) -> None:
        """
        Figure 2: Performance characteristics across data features.
        Panel A: Error vs coefficient of variation
        Panel B: Error vs sample size
        Panel C: Win rate by data source
        """
        fig, axes = plt.subplots(1, 3, figsize=(14, 4))

        # Panel A: Error vs CV
        ax = axes[0]

        # Bin by CV
        self.df['cv_bin'] = pd.cut(self.df['cv'], bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0, 2.0],
                                    labels=['<0.2', '0.2-0.4', '0.4-0.6', '0.6-0.8', '0.8-1.0', '>1.0'])
        cv_summary = self.df.groupby('cv_bin', observed=True).agg({
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
        ax.set_title('(A) Error vs. Data Variability', fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(cv_summary.index, rotation=45, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)

        # Panel B: Error vs sample size
        ax = axes[1]

        self.df['n_bin'] = pd.cut(self.df['n'], bins=[0, 20, 50, 100, 200, 500, 10000],
                                   labels=['<=20', '21-50', '51-100', '101-200', '201-500', '>500'])
        n_summary = self.df.groupby('n_bin', observed=True).agg({
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

        # Panel C: Win rate by source
        ax = axes[2]

        if 'source' in self.df.columns:
            source_summary = self.df.groupby('source').apply(
                lambda x: (x['maxent_error_pct'] < x['naive_error_pct']).mean() * 100
            ).sort_values(ascending=False)

            colors = ['#3498DB' if wr > 50 else '#E74C3C' for wr in source_summary.values]
            bars = ax.barh(range(len(source_summary)), source_summary.values,
                          color=colors, edgecolor='black', linewidth=0.5, alpha=0.8)
            ax.set_yticks(range(len(source_summary)))
            ax.set_yticklabels([s[:20] + '...' if len(s) > 20 else s
                               for s in source_summary.index], fontsize=8)
            ax.set_xlabel('MaxEnt Win Rate (%)', fontweight='bold')
            ax.set_title('(C) Win Rate by Data Source', fontweight='bold')
            ax.axvline(50, color='gray', linestyle='--', linewidth=1, alpha=0.7)
            ax.grid(axis='x', alpha=0.3)
            ax.set_xlim(0, 100)

        plt.tight_layout()
        plt.savefig(self.output_dir / 'figure2_performance.png')
        plt.savefig(self.output_dir / 'figure2_performance.pdf')
        plt.show()

    def create_figure_3_scatter_comparison(self) -> None:
        """
        Figure 3: Scatter comparison of estimated vs true medians.
        Panel A: Naive method
        Panel B: MaxEnt method
        Panel C: Error comparison (MaxEnt vs Naive)
        """
        fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))

        # Panel A: Naive
        ax = axes[0]
        ax.scatter(self.df['true_median'], self.df['naive_median'],
                  alpha=0.4, color='#E74C3C', s=20, edgecolors='none')
        min_val = min(self.df['true_median'].min(), self.df['naive_median'].min())
        max_val = max(self.df['true_median'].max(), self.df['naive_median'].max())
        ax.plot([min_val, max_val], [min_val, max_val], 'k--', linewidth=1.5, alpha=0.7, label='Perfect')
        ax.set_xlabel('True Median', fontweight='bold')
        ax.set_ylabel('Estimated Median (Naive)', fontweight='bold')
        ax.set_title('(A) Naive Normal Reconstruction', fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Panel B: MaxEnt
        ax = axes[1]
        ax.scatter(self.df['true_median'], self.df['maxent_median'],
                  alpha=0.4, color='#3498DB', s=20, edgecolors='none')
        ax.plot([min_val, max_val], [min_val, max_val], 'k--', linewidth=1.5, alpha=0.7, label='Perfect')
        ax.set_xlabel('True Median', fontweight='bold')
        ax.set_ylabel('Estimated Median (MaxEnt)', fontweight='bold')
        ax.set_title('(B) MaxEnt Reconstruction', fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Panel C: Error comparison
        ax = axes[2]

        maxent_better = self.df['maxent_error_pct'] < self.df['naive_error_pct']
        ax.scatter(self.df.loc[~maxent_better, 'naive_error_pct'],
                  self.df.loc[~maxent_better, 'maxent_error_pct'],
                  alpha=0.5, color='#E74C3C', s=20, label='Naive Better', edgecolors='none')
        ax.scatter(self.df.loc[maxent_better, 'naive_error_pct'],
                  self.df.loc[maxent_better, 'maxent_error_pct'],
                  alpha=0.5, color='#3498DB', s=20, label='MaxEnt Better', edgecolors='none')
        ax.plot([0, self.df['naive_error_pct'].max() * 1.1],
               [0, self.df['naive_error_pct'].max() * 1.1],
               'k--', linewidth=1.5, alpha=0.7, label='Equal Performance')
        ax.set_xlabel('Naive Error (%)', fontweight='bold')
        ax.set_ylabel('MaxEnt Error (%)', fontweight='bold')
        ax.set_title('(C) Method Comparison', fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, self.df['naive_error_pct'].max() * 1.1)
        ax.set_ylim(0, self.df['maxent_error_pct'].max() * 1.1)

        plt.tight_layout()
        plt.savefig(self.output_dir / 'figure3_scatter.png')
        plt.savefig(self.output_dir / 'figure3_scatter.pdf')
        plt.show()

    def create_figure_4_improvement_distribution(self) -> None:
        """
        Figure 4: Distribution of improvements.
        Shows percentage improvement of MaxEnt over Naive.
        """
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))

        # Panel A: Improvement histogram
        ax = axes[0]
        improvement = self.df['improvement_pct']
        ax.hist(improvement, bins=50, color='#3498DB', edgecolor='white',
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

        summary_stats = [
            ['Metric', 'Value', ''],
            ['='*30, '='*30, ''],
            ['Total Comparisons', f'{len(self.df):,}', ''],
            ['MaxEnt Win Rate', f'{(self.df["maxent_wins"].mean() * 100):.1f}%', ''],
            ['', '', ''],
            ['Median Error', '', ''],
            ['  - Naive Normal', f'{self.df["naive_error_pct"].median():.2f}%', ''],
            ['  - MaxEnt', f'{self.df["maxent_error_pct"].median():.2f}%', ''],
            ['', '', ''],
            ['Mean Error', '', ''],
            ['  - Naive Normal', f'{self.df["naive_error_pct"].mean():.2f}%', ''],
            ['  - MaxEnt', f'{self.df["maxent_error_pct"].mean():.2f}%', ''],
            ['', '', ''],
            ['Improvement', f'{improvement.mean():.1f}%', '(mean)'],
            ['', f'{improvement.median():.1f}%', '(median)'],
            ['', '', ''],
            ['Win Rate by Quantile', '', ''],
            ['  - Q25', f'{(self.df["maxent_q25_error_pct"] < self.df["naive_q25_error_pct"]).mean() * 100:.1f}%', ''],
            ['  - Q50', f'{(self.df["maxent_error_pct"] < self.df["naive_error_pct"]).mean() * 100:.1f}%', ''],
            ['  - Q75', f'{(self.df["maxent_q75_error_pct"] < self.df["naive_q75_error_pct"]).mean() * 100:.1f}%', ''],
        ]

        table = ax.table(cellText=summary_stats, cellLoc='left', loc='center',
                        colWidths=[0.6, 0.3, 0.1])
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 2)

        # Style the header row
        for i in range(3):
            table[(0, i)].set_facecolor('#3498DB')
            table[(0, i)].set_text_props(weight='bold', color='white')

        ax.set_title('(B) Summary Statistics', fontweight='bold', pad=20)

        plt.tight_layout()
        plt.savefig(self.output_dir / 'figure4_improvement.png')
        plt.savefig(self.output_dir / 'figure4_improvement.pdf')
        plt.show()

    def create_all_figures(self) -> None:
        """Create all publication figures."""
        print("Creating publication-quality figures...")

        print("  Figure 1: Overview...")
        self.create_figure_1_overview()

        print("  Figure 2: Performance Characteristics...")
        self.create_figure_2_performance_characteristics()

        print("  Figure 3: Scatter Comparison...")
        self.create_figure_3_scatter_comparison()

        print("  Figure 4: Improvement Distribution...")
        self.create_figure_4_improvement_distribution()

        print(f"\nAll figures saved to: {self.output_dir}")


def main():
    """Create figures from validation results."""
    results_path = Path('C:/Users/user/maxent-reconstructor/comprehensive_validation_results.csv')

    if results_path.exists():
        df = pd.read_csv(results_path)
        print(f"Loaded {len(df)} validation results")

        visualizer = PublicationVisualizer(df)
        visualizer.create_all_figures()
    else:
        print("No validation results found. Run comprehensive_processor.py first.")


if __name__ == "__main__":
    main()
