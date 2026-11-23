# Data audit report

Scope: the original client data pack (`data-pack/data`, seven CSVs; PDFs and voice notes as context). `backend/data` was checked byte-for-byte against `data-pack/data` (`diff -rq`: identical). No source file was modified.

## 1. Datasets

| File | Rows | Grain | Key fields | Money / quantity fields |
|---|---|---|---|---|
| primary_sales.csv | 93,809 raw, 93,063 clean | one invoice line | invoice_no + sku + batch | ordered/invoiced/free qty, pts_inr, net_value_inr |
| expiry_claims.csv | 4,526 raw, 4,503 clean | one claim | claim_no | qty_claimed, claim_value_inr, credit_value_inr |
| batch_master.csv | 663 | one batch | batch_no | batch_qty_packs, expiry_date |
| cnf_stock_snapshot.csv | 5,015 raw, 4,163 clean keys | C&F x SKU x batch x month-end | snapshot_date + cnf + batch | qty_on_hand_packs, avg_monthly_outward_packs |
| sku_master.csv | 36 | SKU | sku_code | pts_inr, mrp_inr, shelf_life_months |
| stockist_master.csv | 156 | stockist | stockist_code | none |
| claim_emails.csv | 30 emails (101 physical lines) | email | email_id | free text |

Joins used: sales/claims to batch_master on `batch_no`; to sku_master on `sku_code` (one PTS per SKU, so value = qty x PTS); claims to sales on `original_invoice_ref` + batch + stockist; stock to sales by C&F and SKU. Orphans in stockist, SKU, batch or C&F: 0 (blank batch means a line not supplied).

## 2. Data quality findings (all preserved, none silently fixed)

| Issue | Evidence | Handling |
|---|---|---|
| Exact repeated sales rows | 745 byte-identical rows plus 1 repeat that differs only in `scheme_code` ('' vs '-'), 746 in total | removed in `agent/clean.py` rule S1; raw file untouched |
| Inconsistent codes | stockist codes as `stk0039` and `STK0039 ` (case, trailing space) | normalised in the clean layer |
| Scheme code variants | blank, '-', 'NA' all mean "no scheme" | one value in the clean layer |
| Repeated claim numbers | 23 claims repeated with identical content | collapsed (rule C3) |
| Split stock rows | 831 snapshot keys held 2 or 3 rows | summed, not dropped; ties to the QBR |
| Mixed date formats | `dd-mm-yyyy`, `yyyy-mm-dd`, `dd-Mon-yyyy` | all parse, 0 failures |
| Credit value as text with commas | `"3,936.80"` | parsed; blank credit filled from claim value (a small, documented gap) |
| Claims on batches older than the batch master | 971 credited claims, INR 85.45 L | tier T4, "cannot be checked", never counted as leakage |

Trust tests carried from `verification/04_data_quality.md` and re-confirmed this audit: cleaned primary sales tie to the QBR to two decimals in all five quarters; PTS on invoices equals sku_master on every line; `net_value_inr` = invoiced x PTS.

## 3. Independent reconciliation (new in this audit)

`backend/checks/reconcile_source.py` recomputes figures with the standard library only, without importing the application's cleaning or analysis code, and compares them with the application. Result: **23 of 23 agree** (also run by `tests/test_reconcile_source.py`).

| Check | Independent | Application |
|---|---|---|
| Sales rows after removing repeats | 93,063 | 93,063 |
| Claim rows after removing repeats | 4,503 | 4,503 |
| Primary sales per fiscal quarter (10 quarters, INR) | equal | equal |
| Free goods above the 3% cap, last 4 quarters | 6,826,435 | 6,826,434 |
| Credited claims / value | 4,112 / 71,598,025 | same |
| Pending claims | 360 | 360 |
| Claims credited over 90 days after expiry | 64 claims, INR 1,069,311 | same |
| T1 + T2, and by-stockist rows sum to the headline | 5,152,767.39 | same |
| Invoice lines whose PTS differs from sku_master | 0 | 0 |

The audit first found 4 disagreements. Each was a flaw in the reconciliation script (it did not normalise codes or the scheme-code variants), not in the application; fixing the script made all 23 agree. This is recorded because it shows the application's cleaning rules are doing real work.

## 4. Source-to-metric mapping

| Metric | Source | Columns | Formula and filters | Value |
|---|---|---|---|---|
| Confirmed leakage (T1) | expiry_claims, primary_sales, batch_master | credit_value_inr, claim_date, expiry_date, qty, invoiced_qty, free_qty | late > 90 days after expiry (full credit) or over-supply (excess packs x PTS); status Credited; claims replayed in date order | INR 12.49 L, 104 claims |
| Potentially recoverable (T2) | same | same | outside the 90-day windows, or exact repeat | INR 39.04 L, 374 claims |
| Hold now | expiry_claims status Pending | claim_value_inr | T1/T2 rules on pending claims | INR 20.99 L, 69 claims |
| Free goods above cap | primary_sales | free_qty, invoiced_qty, pts_inr, invoice_date | per fiscal quarter max(0, free x PTS - 3% x invoiced x PTS), last 4 quarters | INR 68.26 L (INR 3.95 cr since FY25 Q3) |
| Returns above 1% target | expiry_claims, primary_sales | claim_value_inr (types Near expiry, Expired), invoiced x PTS | claims logged in last 4 quarters - 1% of invoiced value | INR 3.45 cr (logged 5.46, target 2.01) |
| Reallocation opportunity | cnf_stock_snapshot, sku_master | qty_on_hand_packs, avg_monthly_outward_packs, pts_inr | per SKU min(shortage to 1 month cover, spare above 1 month) x PTS, latest month-end only | INR 1.04 cr (of 2.88 cr shortfall) |
| Kolkata FEFO | primary_sales, batch_master | batch expiry order per invoice | lines shipping a newer batch while an older one had stock | 1,713 of 2,898 lines (59%), last two quarters |

## 5. Data-related defects found

1. **Cumulative shortfall counted a persistent gap repeatedly.** `unfilled_shortfall(6)` sums six month-end snapshots (INR 10.18 cr, 58% fixable). A shortage at one C&F that lasts six months is counted six times. It is valid as exposure over time, not as one amount. The register now uses the latest month-end (INR 2.88 cr, INR 1.04 cr = 36% fixable). The six-month figure remains in the Ask tool and agent catalogue text, clearly labelled.
2. **Returns estimate versus the ledger.** Live computation gives INR 3.45 cr above the CFO's 1% target; the findings ledger quotes INR 3.39 cr (range 2.7 to 3.4). The INR 0.06 cr gap was not traced to a cause (claim-date versus other cut-offs). Treated as medium confidence.
3. **Kolkata FEFO value.** Ledger INR 9.49 cr; this audit's last-two-quarter computation INR 8.53 cr. Different quarter spans; the breach rate (59% against the ledger's 54% to 64%) agrees.
4. **Not testable from the pack:** April 2026 MRP revision, allocation share table, demand forecast, margins, stockist-to-chemist sales.

## 6. Outliers and double counting

Free-goods cap, scheme returns and short-dated dispatch describe overlapping scheme effects; the register flags them as not additive. T1, T2, hold, needs-a-person and unverifiable are mutually exclusive tiers.
