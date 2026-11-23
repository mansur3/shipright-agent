"""Independent, stdlib-only recomputation from the original CSVs must agree with the application (see checks/reconcile_source.py)."""
from checks.reconcile_source import compute


def test_every_independent_reconciliation_agrees():
    bad = [r for r in compute() if not r["ok"]]
    assert not bad, bad
