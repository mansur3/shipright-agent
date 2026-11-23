# Frontend, backend and agent gap report

Pipeline traced: client CSVs -> `data_loader` / `clean.py` -> `claim_checks.py`, `analysis.py` -> `recovery.py`, `opportunities.py` -> FastAPI routers -> Next.js pages -> user. Pages are statically exported into `backend/public` and served by the same app.

## 1. KPI path table

| KPI on screen | Page | API | Backend source | Agent | Validated by | Gap found | Status |
|---|---|---|---|---|---|---|---|
| Credited against policy rules INR 51.53 L | Recovery | `/api/analytics/recovery` | `recovery.build()` | Recovery Analyst, Gatekeeper | `test_recovery.py`, reconciliation (T1 + T2, late claims) | headline wording said every claim "broke" a rule although T2 is only probable | wording corrected |
| T1 / T2 split, hold, review, unverifiable | Recovery | same | same | same | tests pin to ledger | none | ok |
| Scheme-pushed returns above target | Recovery | now `/api/analytics/opportunities` | `opportunities._scheme_returns_vs_target` | Scheme Order Gate | `test_opportunities.py` | **was a hardcoded string "₹2.7-3.4 cr a year"** with no computation behind it | replaced by computed INR 3.45 cr |
| Top stockists | Recovery | `/api/analytics/recovery` | `recovery.by_stockist` | Recovery Analyst | sums to headline (reconciliation) | none | ok |
| Opportunity cards, formulas, evidence | Recovery Register (new) | `/api/analytics/opportunities` | `opportunities.build()` | per opportunity | 7 unit tests + 2 API tests | n/a | new |
| Claim verdict | Check a Claim | `/api/audit-claim` | `claim_checks` | Gatekeeper | check set 20/20 | none | ok |
| Fill rate, cover, FEFO, cap | Allocation, FEFO, Cap | `/api/stock-cover`, `/api/dispatch-quality`, `/api/scheme-cap` | `analysis.py` | Supply and FEFO Watcher, Scheme Order Gate | `test_analysis.py` | shortage text implied "most of the shortage is allocation" from a six-month sum | latest month-end added, text qualified |
| Scheme returns by quarter | Scheme Returns | `/api/quarter-spike` | `analysis.phasing`, `scheme_claim_rates` | Scheme Order Gate | tests | none | ok |
| Answers with evidence | Ask AI | `/api/chat/ask` | `graph.run_question` | Ask Analyst | guardrail tests | no check that figures came from a tool | grounding check added |
| Stockist risk scores | (removed) | `/api/analytics/stockist-risk` | batch profiles | Recovery Analyst | none | showed whole-claim "zero invoice" and "duplicate" totals that overstate leakage | page removed from UI |

## 2. Gaps found and disposition

| # | Layer | Gap | Disposition |
|---|---|---|---|
| 1 | Frontend | Hardcoded dashboard KPI | fixed |
| 2 | Frontend | Stockists page presented unsupported leakage-like metrics | removed (page, nav, unused types) |
| 3 | Frontend | No single place to see every opportunity with evidence, owner and agent | Recovery Register added |
| 4 | Frontend | Headline overstated T2 certainty | reworded |
| 5 | Frontend | Terminology: UI says "Sankalp AI", repo and brief say ShipRight Agent | documented, not changed (the case name is Sankalp; renaming touches login, titles and docs) |
| 6 | Backend | Shortfall summed across six month-ends | latest month-end used for opportunity; six-month kept, labelled |
| 7 | Backend | No deterministic check of model figures | added |
| 8 | Backend | No independent reconciliation to source | added (23 checks) |
| 9 | Backend | No timeout on model calls | 30 s and one retry |
| 10 | Backend | `/api/analytics/summary` still exposes `zero_invoice_inr` and `duplicate_excess_inr` from the batch run | left (admin and finance use; meanings are explained in the response); no UI shows them now |
| 11 | Backend | Admin batch has no run lock | open, low risk (admin only) |
| 12 | Agents | Reply wording could add figures | fixed |
| 13 | Drill-down | Recovery List shows claim-level rows with clause and reason; the register links in words, not by deep link | open: no click-through from a register card to the filtered list |
| 14 | Filters | Quarter and SKU filters exist on Scheme Returns only; dashboard has no date filter | open: window is fixed at 30 months and stated on screen |
| 15 | Stale data | Data is static files; the page shows the window and the batch run time | acceptable, stated |
| 16 | Tests | No frontend unit or end-to-end tests exist | open; pages were checked by hand in a browser |

## 3. Pages after simplification (11)

Recovery, Recovery Register, Check a Claim, Recovery List, Scheme Returns, Allocation FEFO Cap, Ask AI, File a Claim, Review Queue, Agents, Admin. Each answers one of: where we lose money, how much, evidence, which agent, validated or not, what to do next.
