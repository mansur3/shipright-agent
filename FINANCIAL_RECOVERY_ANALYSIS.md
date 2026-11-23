# Financial recovery analysis

All figures are computed in code (`backend/agent/opportunities.py`, served at `/api/analytics/opportunities`, shown on the Recovery Register page) and reconciled to the source CSVs (see DATA_AUDIT_REPORT.md). Window: April 2024 to September 2026 (30 months). INR 1 L = 100,000; 1 cr = 10,000,000.

## Classes: what each rupee means

| Class | Meaning | Total |
|---|---|---|
| Confirmed leakage | credited cash, written policy text breached (T1) | INR 12.49 L |
| Potentially recoverable | credited cash, probable breach, owner confirms (T2) | INR 39.04 L |
| Cost avoidance | pending claims failing a rule; not yet paid | INR 20.99 L |
| Cost saving | recurring cost a scheme change would cut | not summed (overlapping) |
| Revenue opportunity | sales at PTS better allocation could serve; not cash, not margin | INR 1.04 cr |
| Operational risk | control failed; loss not sized | none |
| Exposure | cannot be called leakage from the pack | none |

**Headline:** INR 51.53 L (478 claims, about INR 20.6 L a year) of credited cash is available for set-off review: INR 12.49 L confirmed, INR 39.04 L potential. The classes are never added to each other; the register has no grand total by design.

## Opportunity register

| ID | Opportunity | Class | Amount | Confidence | Owner | Priority | Found by |
|---|---|---|---|---|---|---|---|
| OPP-01 | Credited claims that broke written policy text (104 claims) | Confirmed leakage | INR 12.49 L | High | Commercial Finance | 1 | Claim Gatekeeper, Recovery Analyst |
| OPP-02 | Credited claims with probable breach (374) | Potentially recoverable | INR 39.04 L | Medium | Commercial Finance | 2 | same |
| OPP-03 | Pending claims failing a rule (69) | Cost avoidance | INR 20.99 L | High | Commercial Finance | 1 | Claim Gatekeeper |
| OPP-04 | Free goods above the 3% cap, last 4 quarters (cap exceeded in 7 of 10 quarters; INR 3.95 cr cumulative) | Cost saving | INR 68.26 L | High on excess, medium on avoidability | CFO, NSM | 2 | Scheme Order Gate |
| OPP-05 | Expiry returns above the CFO's 1% target, last 4 quarters; forward range INR 2.83 to 4.55 cr from the last two quarters' scheme supply | Cost saving | INR 3.45 cr | Medium | NSM, CFO | 1 | Scheme Order Gate, Supply and FEFO Watcher |
| OPP-06 | Stock in the wrong place (Lucknow: 2.4% of stock, 19% of outward, 0.2 months cover) | Revenue opportunity | INR 1.04 cr | Medium | Supply Chain, Demand Planning | 2 | Supply and FEFO Watcher |
| OPP-07 | Kolkata ships newer batches first (59% of lines) | Operational risk | not sized (INR 8.53 cr shipped out of order, reference) | High on breach | Supply Chain | 3 | Supply and FEFO Watcher |
| OPP-08 | Claims that need a person (800) | Exposure | not sized (INR 1.44 cr, reference) | High | Commercial Finance | 3 | Mailbox Triage, Gatekeeper |
| OPP-09 | Claims on batches older than the data (971) | Exposure | not sized (INR 85.45 L, reference) | High that unverifiable | Commercial Finance | 3 | Recovery Analyst |
| OPP-10 | Dispatch below 60% shelf life (4,866 of 90,435 lines) | Operational risk | not sized (INR 23.5 cr shipped, reference) | Medium | Supply Chain | 3 | Supply and FEFO Watcher |

Each entry in the app also carries the problem statement, evidence (file and policy clause), scope, formula, feasibility, next action and validation flag.

## Overlap and double counting

- OPP-04, OPP-05 and OPP-10 all stem from quarter-end schemes. They are flagged as not additive (the register's `overlap` field and a test enforce the flag).
- OPP-01, OPP-02, OPP-08 and OPP-09 are mutually exclusive claim tiers; OPP-03 is pending claims only.
- OPP-06 uses one month-end. The prior headline (INR 10.18 cr shortfall, INR 5.91 cr fixable, summed over six month-ends) double-counted persistent gaps and was retired as an opportunity figure.

## What is not claimed

- No revenue opportunity or cost saving is presented as recovered cash.
- Lost sales are not quantified: the ledger brackets them between INR 1.3 and 26.2 cr depending on method and order padding; this audit did not narrow it.
- GST exposure on late credit notes (ledger: INR 3.50 cr of credit value on 1,762 notes) is not computed in the app; rate and option are unknown.
- Kolkata FEFO and short-dated dispatch have no loss figure because no stock is within 180 days of expiry.

## Realistic recovery view

Credit already issued is recovered by set-off against future credit notes, which Commercial Finance must agree with each stockist. T1 is the strongest case; T2 needs per-claim confirmation, so assume only part converts. The pending hold (INR 20.99 L) is the easiest saving because nothing has been paid. Nothing in the system moves money automatically.
