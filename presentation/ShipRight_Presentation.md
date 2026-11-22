> **SUPERSEDED (Step 8, 20 Nov 2026).** The rupee figures in this file (INR 10.7 Cr addressable, 79.2L duplicates, 82.7L zero-match, 9.1 Cr and 22.1 Cr at risk, 334 FEFO violations) were audited and replaced. Use verification/05_findings_ledger.md and verification/07_design_audit.md. Do not present this file.

# Project Sankalp AI — Pfizer Channel Intelligence Platform

## Slide 1: Cover

**Sankalp AI**

An AI agent that validates pharma trade claims, detects at-risk inventory, and recovers money lost to duplicate credits and expiry returns.

Presented by: ShipRight Logistics Consulting

---

## Slide 2: Context and Objectives (01)

**Client:** Pfizer Limited, General Medicines trade channel — 36 SKUs, 6 C&F territories, 156 stockists, ~₹200 Cr/year primary sales.

**The CFO's request:** "An AI demand forecasting tool before the next quarter-end." Discovery showed the real problem is different.

**Problems identified:**

1. **Duplicate / zero-invoice claim credits**
   - ₹79.2L excess duplicates already credited
   - ₹82.7L zero-match claims already credited
   - Same batches and invoices paid out multiple times against the same stockist

2. **At-risk CNF inventory approaching expiry**
   - ₹9.1 Cr of stock within 90 days of expiry
   - Spread across all 6 C&F locations
   - FEFO discipline broken at the CNF layer

3. **Quarter-end scheme spike**
   - 30-34% of sales land in the last 9 days of the quarter
   - Drives future expiry returns of ₹2-2.7 Cr per quarter
   - Forecast accuracy won't fix an incentive-design problem

**Headline figure:** **₹10.7 Cr total addressable** — current recovery plus future prevention.

---

## Slide 3: Discovery — How We Worked Through Information (02)

| Source type | What we did | Evidence |
|---|---|---|
| Client documents | Extracted every rule with a number from CO-POL-014 v4.2 (claim windows, quantity limits, scheme caps) | Policy clauses → code in rules.py |
| Data extracts | Cleaned, joined, validated the full dataset | 93,809 sales rows + 4,526 claims + 5,015 CNF snapshot rows |
| Interviews and inbox | Listed each stakeholder claim, then tested it against the data | Neha: "duplicate more than once" → 449 duplicate groups found |
| Voice recordings | Transcribed 6 voice notes, cross-checked each claim | Hooghly CNF: "will destroy everything" → 334 FEFO violations confirmed |
| Industry research | Mapped the regulatory and trade landscape | DPCO 2013 pricing, NLEM 2022, AIOCD trade practices, pharma channel structure |

Every number in the system traces back to one of these five sources.

---

## Slide 4: Discovery — Industry and Domain Research (02)

1. **How the Indian pharma trade channel works**
   - Plant → C&F → Stockist → Chemist → Patient
   - Primary sales are visible to Pfizer; secondary sales are not
   - Pfizer's line of sight ends at the stockist

2. **Commercial practices**
   - PTS / PTR / MRP margin ladder structures every transaction
   - Quarter-end schemes (10+2, 10+3) front-load demand
   - 30-day credit is the trade norm

3. **Regulation**
   - DPCO 2013 para 14 sets ceiling prices on scheduled formulations
   - NLEM 2022 defines the scheduled formulation list
   - GST applies to credit notes issued against claims

4. **Industry benchmarks**
   - Expiry returns industry average: 0.5-1%
   - Pfizer at 2.75% — **3x above the norm**
   - The gap is recoverable; it is a process problem, not a market one

---

## Slide 5: Discovery — Key Problems and Business Impact (02)

| # | Problem | Evidence (file + rows) | Owner |
|---|---|---|---|
| 1 | Duplicate excess credits | `expiry_claims.csv` — 449 groups, 871 credits issued, ₹79.2L | Neha Bansal (Claims Finance) |
| 2 | At-risk inventory | `cnf_stock_snapshot.csv` — 444 lines within 180 days, ₹22.1 Cr | Kavita Rao (Supply Chain) |
| 3 | Quarter-end spike | `primary_sales.csv` — 30-34% of sales in last 9 days | Rohan Mehta (CFO) |

**On the CFO's original request:**

> "The CFO asked for forecasting. The data says the problem is incentive design + claim validation, not forecast accuracy."

A more accurate forecast of a demand pattern you created by your own schemes does not stop the bleeding.

---

## Slide 6: Solution — Who Uses It and How It Works (03)

**Who:** Neha Bansal, Claims Finance. She runs it every day to validate incoming claims *before* they reach her 2-person team.

**LangGraph flow:**

```
START → input_guard → model → tool_guard → run_tools → model → output_guard → END
```

**Code steps (deterministic):**
- `rules.py` — claim windows, quantity limits, duplicate detection
- `tools.py` — 7 tools reading directly off the CSV data layer
- `guardrails.py` — 3 gates guarding entry, tool use, and output

**Model steps (LLM):**
- Intent classification
- Natural-language response generation

**The decision that moves money:** the `validate_claim` tool. If `risk_score >= 50`, the claim is held for manual review. That threshold lives in code, not in the model — so it is auditable and cannot drift.

---

## Slide 7: Demo and Accuracy (04)

**Live URL:** [your-pilot.vercel.app]

**Record 1 (typical):**
- Claim CLM-2404-04177, STK0145, batch K2310408, 38 strips, ₹3,936
- Validated → duplicate found → flagged **HIGH RISK**

**Record 2 (awkward):**
- Claim with no invoice ref; batch never sold to that stockist
- `zero_invoice_match` flag raised → score 65 → held

**Record 3 (needs a person):**
- Claim filed outside the 90-day policy window
- Flagged → routed to manual review (not auto-rejected)

**Check set:** **132 tests passing** — covering rules, tools, API, guardrails, and the claims agent end-to-end.

---

## Slide 8: Cost, Guardrails and Scale (05)

**Cost:**
- ~₹0.025 per request (claude-haiku, ~800 input + 300 output tokens)
- ₹0.05/day at 100 claims/day

**Cost reduction:**
- Keyword intent routing skips the LLM entirely for simple queries
- `max_tokens=1024`, `temperature=0` — capped and deterministic

**Guardrails — 3 gates, each tested:**
- `input_guard` — prompt injection blocked
- `tool_guard` — unknown / unauthorised tools blocked
- `output_guard` — file paths and API keys scrubbed from responses

**At 10× volume:**
- CSV loading cached via `lru_cache` — no re-parse per request
- SQLite WAL mode for concurrent reads
- Batch processing is O(n) on claim count
- Model calls capped at 6 trips per claim

---

## Slide 9: Impact and Next Steps (06)

**₹10.7 Cr a year saved or protected:**
- ₹79.2L duplicate credit recovery
- ₹82.7L zero-match investigation
- ₹9.1 Cr inventory redistribution
- ₹2 Cr future spike prevention

**Coverage:**

| Workstream | Status |
|---|---|
| Duplicate credits | ADDRESSED |
| Zero-invoice credits | ADDRESSED |
| At-risk inventory | ADDRESSED |
| Quarter-end spike | PARTLY (detected, not yet auto-capped) |
| Allocation shares | NOT YET |

**Our request:** Approve the claims-validation pilot for Q2 FY27; assign Neha Bansal as primary user.

**Main risk:** The NSM may perceive the tool as anti-scheme. Manage by framing it as a "scheme stock eligibility check," not a claim blocker.

**Next step:** Deploy the pilot, run for 30 days, measure duplicate credits prevented.

---

## Slide 10: Closing

> "Every number your tool shows must be right and must show where it came from."

That is the one rule this system was built around.
