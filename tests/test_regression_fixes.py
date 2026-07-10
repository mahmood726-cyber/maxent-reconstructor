"""Regression tests for audit fixes.

F5 (maxent_improved.py): diagnostics ``mean_error_pct`` must stay finite when
    the target mean is exactly 0 (legal for bounds that straddle 0). Before the
    fix the code divided by ``self.target_mean`` directly, yielding inf/nan.

F4 (validator.py): ``calculate_metrics`` must always emit every ``{q}_error_pct``
    key, even when a true quantile is exactly 0. Before the fix it only wrote
    that key in the nonzero branch, so downstream consumers hit a KeyError.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from maxent_improved import MaxEntReconstructor
from validator import ReconstructionValidator


def test_zero_target_mean_diagnostics_are_finite():
    # mean=0 is legal because the bounds straddle 0.
    recon = MaxEntReconstructor(mean=0.0, sd=1.0, low=-3.0, high=3.0,
                                n_samples=200, random_state=42)
    result = recon.generate_ipd()
    assert result.success
    out = result.diagnostics['output']
    # Before the fix these divided by target_mean=0 -> inf/nan.
    assert np.isfinite(out['mean_error_pct'])
    assert np.isfinite(out['sd_error_pct'])


def test_calculate_metrics_emits_all_quantile_pct_keys_when_true_quantile_zero():
    # 60% zeros -> q10, q25, q50 true quantiles are exactly 0.
    true_data = np.concatenate([np.zeros(60), np.linspace(1.0, 10.0, 40)])
    recon_data = np.linspace(0.0, 10.0, 100)

    true_q = ReconstructionValidator.get_quantiles(true_data, [0.1, 0.25, 0.5])
    assert true_q['q10'] == 0 and true_q['q25'] == 0 and true_q['q50'] == 0

    metrics = ReconstructionValidator.calculate_metrics(true_data, recon_data)

    # Every quantile must have its _error_pct key present and finite, even for
    # the zero-valued true quantiles (regression: previously missing -> KeyError
    # in simulate_single_scenario / generate_summary_report).
    for q in ('q10', 'q25', 'q50', 'q75', 'q90'):
        key = f'{q}_error_pct'
        assert key in metrics, f'missing {key}'
        assert np.isfinite(metrics[key])
