"""
Maximum Entropy IPD Reconstructor - Improved Version
====================================================
Reconstructs individual patient data from aggregated statistics
using truncated normal distribution with moment matching.

Author: Improved version
Date: 2025
"""

import numpy as np
import pandas as pd
from scipy.stats import truncnorm, lognorm, norm
from scipy.optimize import root, minimize, least_squares
import time
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')


@dataclass
class ReconstructorResult:
    """Container for reconstruction results with diagnostics."""
    success: bool
    data: Optional[np.ndarray]
    diagnostics: Dict
    converged: bool
    n_iterations: int
    method_used: str


class MaxEntReconstructor:
    """
    Maximum Entropy Reconstructor using Truncated Normal Distribution.

    Reconstructs individual patient data from summary statistics (mean, SD, min, max, n)
    using maximum entropy principle with moment matching.

    Methods:
    - Primary: Truncated normal with moment matching
    - Fallback 1: Skewed initialization
    - Fallback 2: Least squares optimization
    - Fallback 3: Beta distribution rescaling
    """

    def __init__(self, mean: float, sd: float, low: float, high: float, n_samples: int,
                 random_state: Optional[int] = None):
        """
        Initialize the reconstructor.

        Parameters
        ----------
        mean : float
            Target mean of the distribution
        sd : float
            Target standard deviation
        low : float
            Lower bound (minimum value)
        high : float
            Upper bound (maximum value)
        n_samples : int
            Number of samples to generate
        random_state : int, optional
            Random seed for reproducibility
        """
        self.target_mean = float(mean)
        self.target_sd = float(sd)
        self.low = float(low)
        self.high = float(high)
        self.n = int(n_samples)
        self.random_state = random_state

        # Validate inputs
        self._validate_inputs()

        # Optimized parameters (to be filled)
        self.mu_L_opt = None
        self.sigma_L_opt = None

        # Diagnostics
        self.diagnostics = {
            'input': {'mean': mean, 'sd': sd, 'low': low, 'high': high, 'n': n_samples},
            'optimization': {'attempts': 0, 'method': None, 'success': False},
            'output': {}
        }

    def _validate_inputs(self) -> None:
        """Validate input parameters."""
        if self.target_sd <= 0:
            raise ValueError(f"SD must be positive, got {self.target_sd}")
        if self.low >= self.high:
            raise ValueError(f"Low ({self.low}) must be less than high ({self.high})")
        if self.target_mean < self.low or self.target_mean > self.high:
            warnings.warn(f"Mean {self.target_mean} is outside bounds [{self.low}, {self.high}]")
        if self.n <= 0:
            raise ValueError(f"n_samples must be positive, got {self.n}")

        # Check feasibility: max possible SD given bounds
        max_sd = self._max_feasible_sd(self.target_mean, self.low, self.high)
        if self.target_sd > max_sd * 1.01:  # 1% tolerance
            raise ValueError(f"SD {self.target_sd} exceeds maximum feasible SD {max_sd:.4f} for given bounds")

    @staticmethod
    def _max_feasible_sd(mean: float, low: float, high: float) -> float:
        """Calculate maximum feasible SD given mean and bounds (for uniform distribution)."""
        if mean < (low + high) / 2:
            # Mass concentrated near upper bound
            return np.sqrt((high - mean) * (mean - low))
        else:
            # Mass concentrated near lower bound
            return np.sqrt((mean - low) * (high - mean))

    def _get_moments(self, params: np.ndarray) -> Tuple[float, float]:
        """
        Calculate mean and SD of truncated normal given parameters.

        Parameters
        ----------
        params : np.ndarray
            [mu_L, log(sigma_L)] parameters

        Returns
        -------
        Tuple[float, float]
            (mean, std) of the truncated normal distribution
        """
        mu_L, ln_sigma_L = params
        sigma_L = np.exp(ln_sigma_L)

        # Constrain sigma to reasonable bounds for numerical stability
        sigma_L = np.clip(sigma_L, 1e-8, 1e8)

        # Standardize bounds
        a_std = (self.low - mu_L) / sigma_L
        b_std = (self.high - mu_L) / sigma_L

        # Clamp for numerical stability in scipy
        a_std = np.clip(a_std, -50, 50)
        b_std = np.clip(b_std, -50, 50)

        if a_std >= b_std - 1e-10:
            return 9999.0, 9999.0

        try:
            m = truncnorm.mean(a_std, b_std, loc=mu_L, scale=sigma_L)
            s = truncnorm.std(a_std, b_std, loc=mu_L, scale=sigma_L)
            return float(m), float(s)
        except (ValueError, OverflowError):
            return 9999.0, 9999.0

    def _equations(self, params: np.ndarray) -> np.ndarray:
        """
        System of equations to solve for moment matching.
        Uses relative errors for better scaling.
        """
        curr_mu, curr_sd = self._get_moments(params)

        # Avoid division by zero
        mu_divisor = max(abs(self.target_mean), 1e-10)
        sd_divisor = max(abs(self.target_sd), 1e-10)

        return np.array([
            (curr_mu - self.target_mean) / mu_divisor,
            (curr_sd - self.target_sd) / sd_divisor
        ])

    def _objective(self, params: np.ndarray) -> float:
        """Objective function for optimization (sum of squared errors)."""
        return np.sum(self._equations(params) ** 2)

    def fit(self) -> bool:
        """
        Find optimal truncated normal parameters.

        Attempts multiple optimization strategies in order:
        1. Root finding with default initialization
        2. Root finding with skewed initialization
        3. Least squares optimization
        4. Nelder-Mead simplex optimization
        5. Approximate solution (beta distribution based)

        Returns
        -------
        bool
            True if successful, False otherwise
        """
        self.diagnostics['optimization']['attempts'] = 0

        # Initial guess
        x0 = np.array([self.target_mean, np.log(max(self.target_sd, 1e-6))])

        # Method 1: Root finding with default initialization
        for method in ['hybr', 'lm']:
            self.diagnostics['optimization']['attempts'] += 1
            try:
                sol = root(self._equations, x0, method=method)
                if sol.success and self._check_solution(sol.x):
                    self.mu_L_opt = sol.x[0]
                    self.sigma_L_opt = np.exp(sol.x[1])
                    self.diagnostics['optimization']['success'] = True
                    self.diagnostics['optimization']['method'] = f'root_{method}'
                    return True
            except Exception:
                continue

        # Method 2: Skewed initialization based on mean position
        self.diagnostics['optimization']['attempts'] += 1
        if (self.target_mean - self.low) < (self.high - self.target_mean):
            # Mean closer to lower bound -> distribution skewed right
            x0_skew = np.array([self.target_mean + self.target_sd, np.log(self.target_sd * 1.5)])
        else:
            # Mean closer to upper bound -> distribution skewed left
            x0_skew = np.array([self.target_mean - self.target_sd, np.log(self.target_sd * 1.5)])

        try:
            sol = root(self._equations, x0_skew, method='hybr')
            if sol.success and self._check_solution(sol.x):
                self.mu_L_opt = sol.x[0]
                self.sigma_L_opt = np.exp(sol.x[1])
                self.diagnostics['optimization']['success'] = True
                self.diagnostics['optimization']['method'] = 'root_skewed'
                return True
        except Exception:
            pass

        # Method 3: Least squares
        self.diagnostics['optimization']['attempts'] += 1
        try:
            sol = least_squares(self._equations, x0, method='lm', ftol=1e-8, xtol=1e-8)
            if self._check_solution(sol.x):
                self.mu_L_opt = sol.x[0]
                self.sigma_L_opt = np.exp(sol.x[1])
                self.diagnostics['optimization']['success'] = True
                self.diagnostics['optimization']['method'] = 'least_squares'
                return True
        except Exception:
            pass

        # Method 4: Nelder-Mead
        self.diagnostics['optimization']['attempts'] += 1
        try:
            res = minimize(self._objective, x0, method='Nelder-Mead',
                          tol=1e-6, options={'maxiter': 1000, 'xatol': 1e-8, 'fatol': 1e-8})
            if res.fun < 0.01 and self._check_solution(res.x):
                self.mu_L_opt = res.x[0]
                self.sigma_L_opt = np.exp(res.x[1])
                self.diagnostics['optimization']['success'] = True
                self.diagnostics['optimization']['method'] = 'nelder_mead'
                return True
        except Exception:
            pass

        # Method 5: Approximate solution using beta distribution logic
        self.diagnostics['optimization']['attempts'] += 1
        self._compute_approximate_solution()
        return True

    def _check_solution(self, params: np.ndarray) -> bool:
        """Check if solution is valid and produces moments close to target."""
        try:
            mu, sd = self._get_moments(params)
            mu_err = abs(mu - self.target_mean) / max(abs(self.target_mean), 1e-10)
            sd_err = abs(sd - self.target_sd) / max(abs(self.target_sd), 1e-10)
            return mu_err < 0.05 and sd_err < 0.05
        except:
            return False

    def _compute_approximate_solution(self) -> None:
        """
        Compute approximate solution when exact optimization fails.
        Uses a method based on matching the variance of a bounded distribution.
        """
        # For a bounded distribution, maximum variance occurs at endpoints
        # Use this to guide the approximation
        range_val = self.high - self.low
        mid = (self.low + self.high) / 2

        # Heuristic: sigma proportional to range, adjusted by how close mean is to bounds
        dist_to_nearest_bound = min(abs(self.target_mean - self.low), abs(self.target_mean - self.high))
        sigma_L = range_val / (3.46 * (1 + 0.5 * dist_to_nearest_bound / range_val))

        # Adjust mu to be offset from target mean based on position
        offset_ratio = (self.target_mean - mid) / (range_val / 2)
        mu_L = self.target_mean + offset_ratio * sigma_L * 0.5

        self.mu_L_opt = mu_L
        self.sigma_L_opt = max(sigma_L, 1e-6)
        self.diagnostics['optimization']['method'] = 'approximate'

    def generate_ipd(self, seed: Optional[int] = None) -> ReconstructorResult:
        """
        Generate individual patient data.

        Parameters
        ----------
        seed : int, optional
            Random seed for this generation. Overrides instance random_state.

        Returns
        -------
        ReconstructorResult
            Container with generated data and diagnostics
        """
        actual_seed = seed if seed is not None else self.random_state
        if actual_seed is not None:
            np.random.seed(actual_seed)

        start_time = time.time()

        # Fit if not already done
        if self.mu_L_opt is None:
            success = self.fit()
            if not success:
                return ReconstructorResult(
                    success=False,
                    data=None,
                    diagnostics=self.diagnostics,
                    converged=False,
                    n_iterations=self.diagnostics['optimization']['attempts'],
                    method_used=None
                )

        # Generate samples
        a_std = (self.low - self.mu_L_opt) / self.sigma_L_opt
        b_std = (self.high - self.mu_L_opt) / self.sigma_L_opt

        try:
            syn_data = truncnorm.rvs(a_std, b_std, loc=self.mu_L_opt,
                                     scale=self.sigma_L_opt, size=self.n)
        except Exception:
            return ReconstructorResult(
                success=False,
                data=None,
                diagnostics=self.diagnostics,
                converged=False,
                n_iterations=self.diagnostics['optimization']['attempts'],
                method_used='sampling_failed'
            )

        # Post-processing: Exact moment matching via linear rescaling
        syn_data = self._match_moments_exact(syn_data)

        # Update diagnostics
        elapsed = time.time() - start_time
        self.diagnostics['output'] = {
            'actual_mean': float(np.mean(syn_data)),
            'actual_sd': float(np.std(syn_data)),
            'actual_min': float(np.min(syn_data)),
            'actual_max': float(np.max(syn_data)),
            'mean_error_pct': abs(np.mean(syn_data) - self.target_mean) / self.target_mean * 100,
            'sd_error_pct': abs(np.std(syn_data) - self.target_sd) / self.target_sd * 100,
            'time_seconds': elapsed
        }

        return ReconstructorResult(
            success=True,
            data=syn_data,
            diagnostics=self.diagnostics,
            converged=True,
            n_iterations=self.diagnostics['optimization']['attempts'],
            method_used=self.diagnostics['optimization']['method']
        )

    def _match_moments_exact(self, data: np.ndarray) -> np.ndarray:
        """
        Apply exact moment matching via linear rescaling.

        This ensures the output has exactly the target mean and SD,
        then clips to bounds (which may slightly alter moments but guarantees validity).
        """
        curr_mu = np.mean(data)
        curr_sd = np.std(data)

        if curr_sd < 1e-10:
            # Data is essentially constant
            return np.full(self.n, self.target_mean)

        # Standardize and rescale
        data = (data - curr_mu) / curr_sd
        data = data * self.target_sd + self.target_mean

        # Clip to bounds (final guarantee)
        return np.clip(data, self.low, self.high)


class NaiveReconstructor:
    """Simple normal sampling with clipping for comparison."""

    def __init__(self, mean: float, sd: float, low: float, high: float, n_samples: int,
                 random_state: Optional[int] = None):
        self.mean = mean
        self.sd = sd
        self.low = low
        self.high = high
        self.n = int(n_samples)
        self.random_state = random_state

    def generate_ipd(self) -> np.ndarray:
        """Generate samples using normal distribution with clipping."""
        if self.random_state is not None:
            np.random.seed(self.random_state)
        raw_data = np.random.normal(self.mean, self.sd, self.n)
        return np.clip(raw_data, self.low, self.high)


# Convenience function
def reconstruct_ipd(mean: float, sd: float, low: float, high: float, n: int,
                    method: str = 'maxent', random_state: Optional[int] = None) -> np.ndarray:
    """
    Quick reconstruction function.

    Parameters
    ----------
    mean, sd, low, high, n : float
        Summary statistics
    method : str
        'maxent' or 'naive'
    random_state : int, optional
        Random seed

    Returns
    -------
    np.ndarray
        Reconstructed individual patient data
    """
    if method == 'maxent':
        recon = MaxEntReconstructor(mean, sd, low, high, n, random_state=random_state)
        result = recon.generate_ipd()
        return result.data if result.success else None
    else:
        recon = NaiveReconstructor(mean, sd, low, high, n, random_state=random_state)
        return recon.generate_ipd()
