"""
The one place for every policy number and every judgement threshold, each with its source.
Nothing else in the code defines these. Policy = CO-POL-014 v4.2 (page in brackets). Judgement = ours, with the evidence named.
"""

# ── Claim windows: CO-POL-014 5.2 (p3) ────────────────────────────────────────
CLAIM_WINDOW_NE_DAYS: int = 90            # near expiry: from 90 days before expiry to the expiry date
CLAIM_WINDOW_POST_EXPIRY_DAYS: int = 90   # expired: from the expiry date to 90 days after; later is never accepted
CLAIM_WINDOW_BED_DAYS: int = 7            # breakage and short supply: within 7 days of the invoice

# ── Quantity: 5.5 (p3) ────────────────────────────────────────────────────────
# Claimed quantity for a batch must not exceed the packs invoiced to that stockist, free packs included. Cumulative across claims.

# ── Credit terms: 5.6 and 3.1 (pp2, 4) ────────────────────────────────────────
CREDIT_TAT_DAYS: int = 30                 # claim to credit note, Commercial Finance

# ── Schemes: 4.4, 4.5, Annex B (pp2-3, 5-6) ───────────────────────────────────
SCHEME_FREE_CAP_PCT: float = 3.0          # free goods at PTS <= 3% of the quarter's primary sales (CFO approves exceptions)
SCHEME_STOCK_NORM_MONTHS: float = 2.5     # no scheme to a stockist holding more than 2.5 months; RSM confirms, no secondary data exists
QS_MIN_ORDER_MULT: float = 1.5            # Annex B: minimum order 1.5x the stockist's average monthly purchase
SCHEME_TIER_A_SKUS = frozenset({"PFL1001", "PFL1002", "PFL1003", "PFL1101", "PFL1102", "PFL1103", "PFL1105", "PFL1202", "PFL1301", "PFL1303"})
SCHEME_TIER_B_SKUS = frozenset({"PFL1004", "PFL1104", "PFL1201", "PFL1302", "PFL1401"})

# ── Dispatch: 7.1 and C&F SOP 2.3 (p4) ────────────────────────────────────────
MIN_RSL_PCT: float = 0.60                 # residual shelf life at invoice >= 60% of the SKU's shelf life (policy)
MIN_DAYS_AT_DISPATCH: int = 60            # C&F must not dispatch with under 60 days left (SOP); a separate, weaker rule
BLOCK_MONTHS: float = 2.0                 # stock under 60 days to expiry is blocked and destroyed (7.2)
FREEZE_DAYS: int = 60                    # stock under 60 days to expiry may not be dispatched (7.1, 7.2)
FREEZE_WATCH_DAYS: tuple = (90, 120)     # R7: batches this many days before the freeze get a watch flag
IMBALANCE_HEAVY: float = 1.5             # R7: a C&F holding 1.5x its share of outward as stock is heavy
IMBALANCE_SHORT: float = 0.5             # R7: ... and under 0.5x is short

# ── Judgement thresholds (not policy). Evidence in verification/05_findings_ledger.md ────────
COVER_FLOOR_MONTHS: float = 1.0           # a C&F should hold at least one month of its own outward (policy tops up to two)
SPIKE_LAST_DAYS: int = 9                  # "last 9 days of the quarter" as the QBR defines it
SPIKE_BASELINE_PCT: float = 20.0          # last-9-day share before the December 2024 scheme change (FY25 H1 was 20% and 21%)
SPIKE_HIGH_PCT: float = 30.0              # FY25 Q3 to FY26 Q1 ran 33% to 34%
SPIKE_MEDIUM_PCT: float = 25.0

# ── Reference date: the data ends 30 Sep 2026; the engagement started 20 Oct 2026 ─────────────
DATA_REF_DATE: str = "2026-09-30"

# ── Retired (do not reintroduce) ──────────────────────────────────────────────
# A 15% "expected return rate" for last-9-day sales was an assumption with no source. The measured
# rate is in agent.analysis.scheme_claim_rates (13.0% of scheme packs, 12.2% to 19.7% by cohort).

# ── Model and cost ────────────────────────────────────────────────────────────
# Tokens and seconds are measured on every request (agent.graph.run_question). The rupee figure is an ESTIMATE from the two prices
# below. Both are assumptions to confirm on the provider's price page before quoting a rupee cost to the client.
import os as _os
MODEL_DEFAULT: str = "openai/gpt-4o-mini-2024-07-18"
MODEL: str = _os.getenv("MODEL", "").strip() or MODEL_DEFAULT
PRICE_USD_PER_M_INPUT: float = float(_os.getenv("PRICE_USD_PER_M_INPUT", "0.15"))     # assumption: provider list price, confirm
PRICE_USD_PER_M_OUTPUT: float = float(_os.getenv("PRICE_USD_PER_M_OUTPUT", "0.60"))   # assumption: provider list price, confirm
USD_INR: float = float(_os.getenv("USD_INR", "90"))                                   # assumption: confirm the day's rate
