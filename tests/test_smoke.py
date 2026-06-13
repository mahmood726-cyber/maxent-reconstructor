"""Minimal smoke tests for the MaxEnt IPD reconstructor.

These exercise the public API (import, fit, generate) plus one validator
beta scenario (which guards against the ``b='b'`` shape-param regression).
Kept fast so ``pytest -q`` is suitable for triage.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from maxent_improved import MaxEntReconstructor, NaiveReconstructor, reconstruct_ipd


def test_import_and_basic_reconstruction():
    recon = MaxEntReconstructor(mean=50, sd=10, low=20, high=100,
                                n_samples=200, random_state=42)
    result = recon.generate_ipd()
    assert result.success
    assert result.data is not None
    assert len(result.data) == 200
    # Output must respect the declared bounds.
    assert result.data.min() >= 20 - 1e-6
    assert result.data.max() <= 100 + 1e-6
    # Exact moment matching is applied as a post-step, so moments are close.
    assert abs(np.mean(result.data) - 50) < 5
    assert abs(np.std(result.data) - 10) < 5


def test_naive_reconstructor_clips_to_bounds():
    naive = NaiveReconstructor(mean=50, sd=20, low=0, high=100,
                               n_samples=100, random_state=1)
    data = naive.generate_ipd()
    assert len(data) == 100
    assert data.min() >= 0
    assert data.max() <= 100


def test_convenience_function():
    data = reconstruct_ipd(mean=10, sd=2, low=5, high=15, n=50,
                           method='maxent', random_state=7)
    assert data is not None
    assert len(data) == 50


def test_validator_beta_scenario_runs():
    """Beta scenarios must build a numeric shape param, not the string 'b'.

    This guards the regression where the scenario dict used ``'b': 'b'``,
    which crashed every beta simulation with a UFuncTypeError.
    """
    from validator import ReconstructionValidator

    validator = ReconstructionValidator(random_state=42)
    scenario = {
        'distribution': 'beta',
        'params': {'a': 2.0, 'b': 3.0, 'loc': 0, 'scale': 100},
        'n': 100,
        'seed': 42,
    }
    result = validator.simulate_single_scenario(scenario)
    assert result is not None
    assert 'maxent_q50_error_pct' in result
