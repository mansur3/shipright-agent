# Discovery note: Pfizer channel engagement (Sankalp)

Data: seven CSV extracts, Apr 2024 to Sep 2026 (30 months), cleaned and tied to the Q1 FY27 QBR. Every figure is computed in code (`backend/agent/opportunities.py`) and reconciled to the CSVs (`checks/reconcile_source.py`, 23 of 23 agree). Rupee kinds are never added: **C** cash credited, **F** future leakage, **R** revenue at PTS (not margin; margin is not in the pack), **S** stock. INR 1 L = 100,000; 1 cr = 10,000,000.

## Ranked problems

| # | Problem | Rupee size (kind) | Evidence: file, rows, page | Owner |
|---|---|---|---|---|
| 1 | Quarter-end schemes push packs that return as expiry claims | Expiry returns above the CFO's 1% target: INR 2.7 to 3.45 cr in the last 4 quarters (F; the ledger says 3.39, the live run 3.45, the INR 0.06 cr gap is untraced); forward range INR 2.83 to 4.55 cr. Scheme packs are claimed at 13% against 2.35% for normal packs | `expiry_claims.csv` x `primary_sales.csv`, last 4 quarters; QBR pack (doc 06); register OPP-05 | Arjun Sethi (NSM), Neha Bansal (accrual) |
| 2 | Credited claims with no history check | INR 51.5 L credited over 30 months, about INR 20.6 L a year (C): INR 12.5 L broke written policy (104 claims), INR 39.0 L probable (374). Plus INR 21.0 L on 69 pending claims failing a rule (not yet paid) | `expiry_claims.csv`, 4,503 rows; policy doc 02 clauses 5.2, 5.5, 5.6; `claim_checks.py`; OPP-01 to OPP-03 | Neha Bansal (Commercial Finance) |
| 3 | Free goods above the 3% cap in 7 of 10 quarters | INR 68.3 L in the last 4 quarters; INR 3.95 cr cumulative (F) | `primary_sales.csv`; policy doc 02 clause 4.4; QBR doc 06; OPP-04 | Rohan Mehta (CFO), Arjun Sethi |
| 4 | Allocation is still the FY25 split: Lucknow holds 2.4% of stock for 19% of outward (0.2 months cover) | Shortfall INR 2.88 cr at the latest month-end, of which INR 1.04 cr (36%) can be met from other C&Fs (R at PTS, not cash, not margin). The older six-month sum (INR 10.18 cr, 58%) counted a persistent gap once a month and is not used | `cnf_stock_snapshot.csv` (5,015 rows) x `primary_sales.csv`; C&F agreement doc 03; OPP-06 | Kavita Rao, Vaishali Kapoor |
| 5 | Kolkata (Hooghly) ships newer batches first | 59% of lines against 0% at the other five C&Fs; INR 8.53 cr shipped out of order (reference, loss not sized) | `primary_sales.csv` x `batch_master.csv` (663 rows); doc 03 FEFO clause; OPP-07 | Kavita Rao, Subhajit Banerjee |
| 6 | Credit notes raised after the GST adjustment limit | INR 3.50 cr credit value on 1,762 notes (exposure; tax effect not sized) | `expiry_claims.csv`; CBIC Circular 72/46/2018-GST | Neha Bansal |

Also found, not ranked: 800 claims (INR 1.44 cr) need a person; 971 claims (INR 85.5 L) are on batches older than the data and cannot be checked; 4,866 of 90,435 lines (INR 23.5 cr) shipped under 60% shelf life. The QBR fill rate counts free scheme packs as supplied: FY27 Q2 is 82.6% on ordered packs, not 84.8%.

Overlap: problems 1, 3 and the shelf-life dispatch all stem from quarter-end schemes, so they are not added. The register has no grand total by design.

## Our view on the CFO's ask

Rohan Mehta asked for an AI forecasting tool. His observation is right (short and long at the same time); the diagnosis is not. At 31 Jul 2026 Lucknow had no stock on 20 of 36 SKUs while the other C&Fs held about 20 months of its demand. Part of that gap is a split, not a forecast problem: at the latest month-end 36% (INR 1.04 cr of INR 2.88 cr) can be met by changing the next monthly allocation; the rest is stock the network lacks, where a forecast could help. A rule that knows only the quarter rhythm reaches about 10% error, against Demand Planning's 14% and 25% for a naive average, so the vendor's claimed gain from 14% lands near 10% with no AI. A forecast of demand that the schemes themselves create says how many packs will be pushed, not how many come back. **Recommendation:** reset allocation, check stock and expiry before the next scheme, control claims, fix Kolkata picking; buy a forecast after those.

## Problems and users we chose

We built for problem 2 first, with problems 3 to 5 as read-only views. A claim is a recurring, rule-bound decision with a named owner: **Neha Bansal, the Controller**, credits or rejects about 1,800 claims a year with two people. Every rule is policy text, so code applies it and cites the clause and file lines; the model only explains. **Kavita Rao and Vaishali Kapoor** see cover by C&F and FEFO before the monthly allocation; **Arjun Sethi and Rohan Mehta** see the cap and scheme order check before a circular. A person decides every credit. We did not build a forecast, a scheme planner or a GST tool: problem 1 needs a business decision on schemes, and problem 6 needs Finance to confirm rate and option.

## Open questions

1. **Allocation:** the share table, monthly top-ups and forecast file are not in the pack. Allocation is inferred from stock and outward.
2. **Lost sales:** INR 1.3 to 26.2 cr depending on method and order padding; we quote no single number.
3. **Unverifiable claims:** can Finance supply archived invoices for the 971 claims on older batches?
4. **Volume:** 4,503 claims in 30 months (about 1,800 a year) against "four thousand lines a year" in the interview.
5. **Partial claims:** is a split claim on one stockist and batch ever legitimate? It decides whether it is leakage or normal.
6. **GST:** rate by SKU, and whether late credit notes were left out of the GSTR-1 adjustment.
7. **Scheme effect:** an association in every SKU tested; no experiment is possible, so causation is argued, not proven.
8. **Sign-off:** the 20-record check-set answers are our draft until the claim owner signs them.
