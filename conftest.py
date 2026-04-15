"""Pytest config for maxent-reconstructor.

test_quick.py is a standalone demo SCRIPT (not pytest-compatible) — it runs
computation at module-import time and has no pytest-style test_* functions.
When pytest imports it for collection, the demo runs for ~2 minutes and
eventually exits with 0 items collected, producing a TEST-FAIL classification
in triage even though the demo passes.

Skip collection of test_quick.py so `pytest` is fast + clean for triage.

To run the demo manually:
    python test_quick.py
"""
collect_ignore_glob = ["test_quick.py"]
