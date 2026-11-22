"""
Small pure helpers. The claim rules are not here: they live once, in agent/claim_checks.py.
Every constant comes from config.py (policy numbers with page references).
"""
from __future__ import annotations

from datetime import datetime

import config as P

# Re-exported so older imports keep working; the values live in config.py only.
CLAIM_WINDOW_NE_BEFORE_DAYS = P.CLAIM_WINDOW_NE_DAYS
CLAIM_WINDOW_POST_EXPIRY_DAYS = P.CLAIM_WINDOW_POST_EXPIRY_DAYS
CLAIM_WINDOW_BED_DAYS = P.CLAIM_WINDOW_BED_DAYS
SCHEME_STOCK_NORM_MONTHS = P.SCHEME_STOCK_NORM_MONTHS
QS_MIN_ORDER_MULT = P.QS_MIN_ORDER_MULT
CREDIT_TAT_DAYS = P.CREDIT_TAT_DAYS
SCHEME_CAP_PCT = P.SCHEME_FREE_CAP_PCT


def days_to_expiry(expiry_date: datetime, reference_date: datetime) -> int:
    """Positive = days remaining; negative = already expired."""
    return (expiry_date - reference_date).days


def at_risk_value(qty_packs: float, pts_inr: float) -> float:
    """INR value of qty at PTS."""
    return qty_packs * pts_inr


def over_free_goods_cap(free_value_inr: float, primary_value_inr: float) -> bool:
    """CO-POL-014 4.4: free goods at PTS must not exceed 3% of the quarter's primary sales."""
    return free_value_inr > P.SCHEME_FREE_CAP_PCT / 100 * primary_value_inr
