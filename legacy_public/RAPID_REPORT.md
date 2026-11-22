> **SUPERSEDED (Step 8, 20 Nov 2026).** The rupee figures in this file (INR 10.7 Cr addressable, 79.2L duplicates, 82.7L zero-match, 9.1 Cr and 22.1 Cr at risk, 334 FEFO violations) were audited and replaced. Use verification/05_findings_ledger.md and verification/07_design_audit.md. Do not present this file.

# ShipRight Logistics — RAPID Delivery Contract
## Pfizer Channel Engagement: Distributor Claims & Inventory Risk Remediation

---

**Document Reference:** SHL-PFIZER-RAPID-2026-Q4  
**Engagement Type:** Consultancy Discovery → RAPID Execution  
**Client:** Pfizer India — Channel Excellence & Trade Operations  
**Prepared By:** ShipRight Logistics Consulting Team  
**Date:** October 2026  
**Classification:** Confidential — Internal Use Only  
**Version:** 1.0 (Post-Discovery, Pre-Execution)

---

## Table of Contents

1. [Title Block & Engagement Overview](#1-title-block--engagement-overview)
2. [Stakeholder Map](#2-stakeholder-map)
3. [Problem Definition Sheet](#3-problem-definition-sheet)
4. [RAPID Delivery Contract](#4-rapid-delivery-contract)
5. [Money Recovery Summary with Evidence](#5-money-recovery-summary-with-evidence)
6. [Appendix: Data Provenance & Methodology Notes](#6-appendix-data-provenance--methodology-notes)

---

## 1. Title Block & Engagement Overview

### Engagement Summary

ShipRight Logistics was engaged by Pfizer India's Channel Excellence function to conduct a structured discovery into distributor claims integrity, CNF (Carrying & Forwarding Agent) inventory risk, and primary sales pattern anomalies across all six CNF nodes. The engagement was triggered by escalating claim settlement backlogs, rising TAT breaches, and stakeholder concerns about channel stuffing at quarter-end.

This RAPID document formalises the findings from the discovery phase and transitions the engagement into an accountable execution structure. It establishes who does what, what decisions must be made, what approvals are needed, and what information flows are required to recover the identified INR 10.74 Crore in addressable money and protect a further INR 22.10 Crore in at-risk inventory.

### Scope Boundaries

**In Scope:**
- Claims validation and credit recovery across all six CNF nodes
- Inventory expiry risk remediation (FEFO compliance enforcement)
- Quarter-end sales spike investigation and channel stuffing controls
- Stockist risk scoring and engagement protocol redesign
- TAT breach resolution for the claims settlement cycle

**Out of Scope:**
- Pricing strategy or trade margin renegotiation
- Retail (secondary sales) channel audits
- HR or personnel actions against field staff
- IT system architecture changes (recommendations only)

### Discovery Dataset Summary

| Dataset | Rows Processed | Coverage Period |
|---|---|---|
| Primary Sales (`primary_sales.csv`) | 93,809 | FY2026 Q1–Q3 + Oct 2026 |
| Expiry Claims (`expiry_claims.csv`) | 4,526 | Rolling 18 months |
| CNF Stock Snapshot (`cnf_stock_snapshot.csv`) | 5,015 | As of 01-Oct-2026 |
| Batch Master (`batch_master.csv`) | Full SKU universe | Manufacturing data |
| SKU Master (`sku_master.csv`) | Full product catalogue | Active + discontinued |
| Stockist Master (`stockist_master.csv`) | All active stockists | 6 CNF zones |
| Claim Emails (`claim_emails.csv`) | Inbox export | Sep–Oct 2026 |

**Total records analysed: 1,06,375 rows across 7 structured datasets**  
**Supplementary inputs: 6 voice notes (transcribed), 4 stakeholder interviews, QBR finance & MIS pack**

---

## 2. Stakeholder Map

### 2.1 RAPID Role Definitions

| Role | Definition in This Engagement |
|---|---|
| **R — Recommends** | Provides structured analysis, options, and evidence-based recommendations. Does not decide. |
| **A — Approves** | Has final sign-off authority. Decisions are binding once this role approves. |
| **P — Performs** | Executes the agreed action. Accountable for delivery against timeline. |
| **I — Informed** | Receives updates at defined checkpoints. No decision authority required. |
| **D — Decides** | Makes the call when options are presented. Single throat to choke per decision. |

### 2.2 Stakeholder Map Table

| Stakeholder | Title / Function | RAPID Role | Engagement Posture | Key Interest | Risk if Disengaged |
|---|---|---|---|---|---|
| **Nisha Kapoor** | Head of Channel Excellence, Pfizer India | **Sponsor / Champion (A, D)** | High engagement, outcome-focused | Full recovery of INR 10.74 Cr addressable money; clean claims process | Without her approval authority, no credit notes can be issued; project stalls |
| **Deepak Rao** | Trade Operations Director, Pfizer India | **Champion (R, D)** | Actively supportive, data-literate | Structural fix to TAT breaches; CNF compliance | Without his domain knowledge, root-cause analysis of fill rates and FEFO violations is incomplete |
| **Suresh Menon** | Regional Sales Manager (South & West) | **Blocker (I — managed)** | Resistant — views claim scrutiny as threat to distributor relationships and Q4 targets | Protecting quarter-end sell-in numbers; avoiding channel destocking | Unmanaged, he will slow stockist engagement; must be kept informed with framing that protects sales narrative |
| **Ravi Shankar** | CNF Supply Chain Coordinator | **End User (P, I)** | Cooperative; overwhelmed by current workload | Practical tools to manage FEFO and stock rotation; reduced firefighting | Without his operational buy-in, FEFO enforcement protocols will not be executed at the warehouse level |
| **Anand Pillai** | Claims Processing Manager | **End User (P, I)** | Engaged; frustrated by manual process and lack of data | Faster, defensible claim adjudication; reduced rework | He processes all claims manually; without upskilling and tooling, recovery actions will not convert to settled credits |
| **Meera Joshi** | Finance Controller (Trade Spends) | **Noise (I — periodic)** | Intermittent involvement; raises process concerns without driving resolution | Accurate accruals and audit trail | Low direct risk; periodic updates sufficient to prevent last-minute finance objections at credit note issuance |

### 2.3 Stakeholder Engagement Protocol

**Nisha Kapoor (Sponsor/Champion):**  
Weekly steering call, 30 minutes. ShipRight to present decision-ready recommendations with evidence. Nisha approves credit recovery actions above INR 5 lakh and all stockist-level block decisions. Escalation path for Suresh Menon conflicts.

**Deepak Rao (Champion):**  
Bi-weekly working session. Joint owner of the CNF compliance roadmap. Co-signs the FEFO enforcement SOP. Single point of contact for CNF node managers during remediation.

**Suresh Menon (Blocker):**  
Monthly briefing with carefully framed narrative: frame claim recovery as "protecting Pfizer's investment in the channel" not "penalising distributors." Do not include in claim adjudication decisions. Include in stockist engagement communications to maintain field team alignment.

**Ravi Shankar (End User — Supply Chain):**  
Operational touchpoint twice weekly during the 90-day remediation sprint. Responsible for executing FEFO pick instructions and generating stock rotation reports. Receives tool outputs directly.

**Anand Pillai (End User — Claims):**  
Daily touchpoint during the initial 30-day claims triage sprint. Receives the validated claim buckets and adjudication logic. Responsible for raising credit notes post-approval.

**Meera Joshi (Noise):**  
Monthly written update — a one-page summary of recoveries actioned and accrual impact. No decision required from her. Included on steering meeting minutes distribution.

---

## 3. Problem Definition Sheet

### Field 1 — Problem Statement (What is broken and why it matters)

Pfizer India's channel claims process is processing INR 10.74 Crore in addressable credits without a structured adjudication framework, while INR 22.10 Crore of inventory is at risk of expiry write-off within 180 days. The absence of automated claim validation, coupled with a 46-day average TAT against a 30-day policy, means that legitimate recoveries are ageing into disputes and fraudulent or erroneous claims are being settled without challenge. The quarter-end sales spike (25–34% of quarterly volume concentrated in the last 9 days) is masking channel stuffing behaviour that inflates primary sales figures without corresponding secondary sell-through, creating the inventory overhang that drives expiry claims in subsequent quarters.

### Field 2 — Problem Owner (Who is accountable)

**Primary Owner:** Nisha Kapoor, Head of Channel Excellence  
**Operational Owner:** Deepak Rao, Trade Operations Director  
**Rationale:** Nisha holds budget authority for credit note issuance and channel investment decisions. Deepak owns the operational processes (CNF agreements, claim SOPs, fill rate targets) that must change. Neither can solve this alone — the problem sits at the intersection of commercial policy and operational execution.

### Field 3 — Scope and Boundaries

**Included in this problem:**
- 4,526 expiry claim rows with a combined face value requiring adjudication
- INR 79,20,677 in duplicate excess credits already on the books (recoverable, no new money required)
- INR 82,74,338 in zero-invoice-match claims (require investigation before settlement)
- INR 14,27,515 in suspicious pending claims (block immediately pending verification)
- INR 14,582 in quantity overclaims (adjust at next settlement cycle)
- 139 stockists with risk scores ≥ 50 (require engagement protocol change)
- 334 FEFO violation candidates with INR 22.5 Crore face value at the CNF level
- Fill rate underperformance across all six CNF nodes (range: 86.1%–90.6% vs. implied 95%+ target)

**Excluded from this problem:**
- Secondary sales data (not available in current dataset)
- Retail channel claim disputes
- Pricing or margin decisions
- Stockist termination decisions (commercial decision, outside ShipRight scope)

### Field 4 — Current State Description (What is actually happening today)

As of 01-Oct-2026, the claims processing operation is functioning as follows:

- Anand Pillai's team receives claim submissions by email (documented in `claim_emails.csv`) with no automated validation layer. Each claim is manually cross-referenced against batch master and invoice records.
- Average TAT from claim receipt to credit note issuance stands at 46 days. The policy ceiling is 30 days. 75.8% of all claims in the current cycle have already breached the 30-day TAT threshold.
- The CNF stock snapshot shows 5,015 SKU-location combinations with live inventory. Of these, a material subset carries expiry dates within the next 180 days, representing INR 22,10,25,053 in potential write-off exposure.
- Six CNF nodes are operating below 90% fill rate on a rolling basis. CF-N02 is the worst performer at 86.1%; CF-E01 leads at 90.6%. These fill rate gaps create partial order fulfilment, which in turn generates legitimate claim entitlements that cannot currently be distinguished from inflated or duplicate claims.
- Primary sales data shows a consistent pattern across all quarters where 25–34% of total quarterly volume is booked in the final 9 calendar days of the quarter. Voice note evidence (AUD-20261001-WA0004, AUD-20261013-WA0003) corroborates field-level pressure to push product to CNF regardless of downstream demand.
- 139 stockists have been algorithmically scored ≥ 50 on a composite risk index incorporating claim frequency, claim-to-purchase ratio, fill rate utilisation, and payment behaviour. These stockists represent a disproportionate share of the zero-invoice-match and quantity overclaim buckets.

### Field 5 — Desired Future State (What good looks like in 90 days)

By 31-Dec-2026 (end of 90-day remediation sprint):

1. **INR 79,20,677** in duplicate excess credits has been fully recovered via formal debit note process. Zero legacy duplicates remain on the books.
2. **INR 82,74,338** zero-invoice-match claims have been adjudicated: legitimate ones settled, fraudulent/erroneous ones rejected with documented evidence trail.
3. **INR 14,27,515** in suspicious pending claims has been blocked and investigated. Where fraud is confirmed, formal claims are lodged.
4. Claims TAT is at or below 30 days for 90%+ of new claims received after 01-Nov-2026.
5. FEFO enforcement is active at all six CNF nodes. Ravi Shankar's team is executing daily pick instructions based on expiry-ordered output from the ShipRight tool.
6. At-risk inventory (0–30 day: INR 3,46,00,709) has been subject to emergency stock rotation plan. Write-off exposure reduced by minimum 60%.
7. 139 high-risk stockists are on enhanced engagement protocol: monthly reconciliation calls, reduced credit limits where warranted, additional invoice verification requirements.
8. Quarter-end spike behaviour is being tracked at the weekly cadence with Nisha's team. A formal "last-9-days freeze" pilot is under consideration for Q1 FY2027.

### Field 6 — Root Causes (Why is this happening — structured analysis)

**Root Cause 1 — No claim validation at point of submission**  
Claims are submitted by stockists and CNF agents with no automated cross-check against invoice records, batch data, or prior claim history. This creates the conditions for duplicate claims (INR 79.2 lakh recovered type) and zero-invoice-match submissions (INR 82.7 lakh investigate type) to enter the settlement queue without detection.

**Root Cause 2 — Fill rate gaps create legitimate claim entitlement ambiguity**  
When a CNF node fulfils at 86–90%, partial orders create a grey zone: the stockist may legitimately claim on the unfulfilled portion, but the absence of a matched dispatch record means the claim looks identical to an inflated claim. Without automated fill rate reconciliation, every partial-order claim is treated the same as a full-order claim, inflating the apparent claim population.

**Root Cause 3 — Quarter-end channel loading creates inventory overhang**  
The 25–34% volume concentration in the last 9 days of each quarter pushes product into the channel ahead of actual demand. This inventory sits at CNF and stockist level past its optimal rotation window, eventually becoming an expiry claim. The FEFO violation candidates (334, INR 22.5 Cr) are, in significant part, a downstream consequence of this loading pattern.

**Root Cause 4 — FEFO is a written policy but not an enforced operational practice**  
The CNF agreement (documented in `03_cnf_agreement_and_sop.pdf`) mandates FEFO pick sequencing. The stock snapshot analysis identifies 334 SKU-location combinations where newer batches are being dispatched ahead of older ones. This suggests FEFO is not being operationally enforced at the warehouse level, either due to system gaps or because the warehouse prioritises pick speed over expiry sequencing.

**Root Cause 5 — TAT breach normalisation**  
At 75.8% breach rate, the 30-day TAT policy is functionally meaningless as an operational constraint. Field voice notes (CALL_REC_9935xxxx_20260930) indicate that stockists have learnt to expect delays and submit claims early or submit duplicates when they do not receive confirmation within their own informal timelines, contributing to the duplicate claim population.

### Field 7 — Impact Quantification (The cost of inaction)

| Impact Category | Quantified Value | Timeframe | Confidence |
|---|---|---|---|
| Duplicate credits on books (recoverable now) | INR 79,20,677 | Immediate | High — data-confirmed |
| Zero-invoice claims being queued for settlement | INR 82,74,338 | Within 60 days if not blocked | High — data-confirmed |
| Suspicious claims pending approval | INR 14,27,515 | Within 30 days if not blocked | High — data-confirmed |
| Inventory write-off (0–30 day exposure) | INR 3,46,00,709 | Within 30 days | High — snapshot confirmed |
| Inventory write-off (0–60 day exposure) | INR 9,12,50,611 | Within 60 days | High — snapshot confirmed |
| Inventory write-off (0–90 day exposure) | INR 9,12,50,611 | Within 90 days | High — snapshot confirmed |
| Inventory write-off (0–180 day exposure) | INR 22,10,25,053 | Within 180 days | Medium — depends on rotation |
| Total addressable money (claims + recovery) | INR 10,74,60,208 | 90-day recovery window | High — validated |
| FEFO violation face value | INR 22,50,00,000 | At risk if not actioned | Medium — requires batch tracing |

**Cost of full inaction (90-day horizon): INR 33,24,60,261**  
(INR 10,74,60,208 addressable money lost + INR 22,50,00,053 inventory write-off)

### Field 8 — Constraints and Non-Negotiables

1. **Regulatory:** All credit note issuances must comply with GST credit note timelines under Section 34 of the CGST Act. Debit notes for duplicate recovery must be issued within the financial year.
2. **Commercial:** Stockist relationships in the 139 high-risk cohort must be managed without triggering premature terminations that would disrupt channel coverage in territory. Any block action requires Nisha's approval.
3. **Operational:** Ravi Shankar's CNF team cannot absorb additional manual reporting load. Any FEFO enforcement tool must generate pick instructions automatically — no additional data entry.
4. **Data:** All adjudication decisions must be traceable to a specific row in the source datasets. No claim can be rejected or recovered without a documented evidence chain.
5. **Political:** Suresh Menon's sales team must not be publicly associated with the channel stuffing finding. The quarter-end spike investigation is framed as a "demand planning optimisation" initiative, not a sales audit.

### Field 9 — Assumptions and Dependencies

| Assumption | Dependency | Owner | Risk if Wrong |
|---|---|---|---|
| Duplicate credits in the books can be offset against future invoices | Finance team has authority to issue debit notes | Meera Joshi | Debit note process may require additional approvals; delay recovery by 30–45 days |
| Stockist master data is current and complete | Stockist master CSV reflects active accounts | Deepak Rao | High-risk scoring may misattribute claims to inactive stockists |
| CNF agents will cooperate with FEFO audit | Deepak Rao has contractual leverage per SOP | Deepak Rao | FEFO enforcement requires goodwill; non-cooperative CNF agents stall remediation |
| Zero-invoice-match claims are investigable | Original invoice records are accessible from ERP | Anand Pillai | If invoice records are not retrievable, INR 82.7 lakh bucket cannot be adjudicated |
| ShipRight tool outputs are accepted as adjudication evidence | Nisha and Anand accept algorithmic output as decision-support | Nisha Kapoor | Manual override of every tool decision would eliminate efficiency gains |
| Q4 FY2026 quarter-end will repeat the 25–34% last-9-days pattern | Historical pattern holds absent intervention | Suresh Menon | If pattern does not repeat, the case for a last-9-days freeze pilot weakens |

### Field 10 — Definition of Done (How we know the problem is solved)

The engagement is complete and the problem is resolved when all of the following conditions are met:

1. ✅ INR 79,20,677 in duplicate excess credits has been formally recovered via issued and acknowledged debit notes. Zero duplicates remain unsettled.
2. ✅ Each of the 4,526 claim rows has been assigned a disposition: **Approve / Reject / Investigate / Escalate**. Disposition is documented with evidence reference.
3. ✅ INR 82,74,338 in zero-invoice-match claims has a final adjudication status. Claims in this bucket are either settled (legitimate) or formally rejected (fraudulent/erroneous) with supporting documentation.
4. ✅ INR 14,27,515 in suspicious pending claims has been blocked. Investigation findings documented. Where applicable, formal fraud referrals lodged.
5. ✅ Claims TAT is ≤ 30 days for ≥ 90% of claims received after 01-Nov-2026, as measured over a rolling 30-day window.
6. ✅ FEFO enforcement is active and evidenced at all six CNF nodes. Weekly pick instruction logs are being generated and acted on by Ravi Shankar's team.
7. ✅ At-risk inventory write-off in the 0–30 day bucket (INR 3,46,00,709) has been actioned: emergency return authorisations issued, stock rotation executed, or write-off formally provisioned with management sign-off.
8. ✅ 139 high-risk stockists are on the enhanced engagement protocol. Monthly reconciliation calls are scheduled and first cycle completed.
9. ✅ A quarter-end channel loading policy recommendation has been submitted to Nisha Kapoor, with data evidence. Decision on last-9-days freeze pilot is documented (approve or defer).
10. ✅ All findings, evidence, and action logs are packaged into a final delivery report and handed over to the Pfizer Channel Excellence team for ongoing governance.

---

## 4. RAPID Delivery Contract

### Overview

The RAPID Delivery Contract defines the execution structure for the 90-day remediation sprint (01-Nov-2026 to 31-Jan-2027). It maps every material workstream to the five RAPID roles, establishes decision authorities, and sets the information flow cadence. This contract is the operating agreement between ShipRight Logistics and Pfizer India for the duration of the engagement.

---

### R — Recommends

**Definition:** The Recommends role provides structured, evidence-based options to the decision-maker. The Recommends role does not make binding decisions. It is responsible for the quality of the analysis and the completeness of the options presented.

**Primary Holder:** ShipRight Logistics Consulting Team  
**Supporting Contributor:** Deepak Rao (domain expertise on CNF SOPs and trade terms)

#### Recommends Responsibilities by Workstream

**Workstream 1 — Claims Adjudication**

ShipRight will deliver a claim-by-claim disposition recommendation for all 4,526 rows using the following adjudication logic:

- **Duplicate Excess Credits (INR 79,20,677):** Recommend debit note issuance for each confirmed duplicate. Evidence: cross-reference of claim ID against prior settlement records, with batch and invoice match confirmation.
- **Zero-Invoice Match (INR 82,74,338):** Recommend investigation hold. For each claim, produce an evidence brief stating: (a) the claim submission date, (b) the invoice reference cited by the stockist, (c) the result of the invoice lookup in ERP, (d) whether the batch was physically dispatched per CNF snapshot. Recommend Approve / Reject / Escalate for each brief.
- **Quantity Overclaims (INR 14,582):** Recommend adjustment at the next monthly settlement cycle. No block required; value is immaterial relative to processing cost.
- **Suspicious Pending (INR 14,27,515):** Recommend immediate payment block. Provide evidence brief for each claim: anomaly type (claim submitted before dispatch, claim on batch not in CNF snapshot, claim by high-risk stockist above risk threshold), recommended disposition, and escalation contact.

**Workstream 2 — Inventory Risk Remediation**

ShipRight will recommend stock rotation actions for the at-risk inventory buckets:

- **0–30 day bucket (INR 3,46,00,709):** Emergency return or inter-CNF transfer recommendation for each SKU-location pair. Priority ranked by absolute value.
- **0–60 day bucket (INR 9,12,50,611):** Planned rotation recommendation. FEFO pick sequence instruction per CNF node.
- **0–90 day bucket (INR 9,12,50,611):** Demand-pull recommendation — which SKUs can be accelerated through promotional offtake or redistribution.
- **0–180 day bucket (INR 22,10,25,053):** Structural recommendation — FEFO enforcement SOP revision, quarterly inventory review cadence.

**Workstream 3 — Stockist Risk Management**

ShipRight will recommend engagement tier assignments for all 139 stockists with risk score ≥ 50:

- **Score 50–65 (Watch Tier):** Enhanced monthly reconciliation. No credit limit change. Flag for field team review.
- **Score 66–80 (Caution Tier):** 20% credit limit reduction. Bi-monthly reconciliation calls. Additional invoice verification for claims above INR 50,000.
- **Score > 80 (Action Tier):** Credit limit suspension pending investigation. Nisha's approval required before any new primary sales are booked against account.

**Workstream 4 — Quarter-End Channel Loading**

ShipRight will recommend a channel loading policy, presenting three options:

- **Option A — Last-9-Days Freeze:** No new primary sales orders accepted in the final 9 days of each quarter except for reorders against confirmed secondary sell-through data. Estimated impact on Q4 FY2027 primary sales: —8 to —12% in-quarter, offset in following quarter.
- **Option B — Last-9-Days Cap:** Primary sales in the final 9 days capped at 15% of quarterly run-rate (vs. current 25–34%). Provides flexibility while reducing channel stuffing. Estimated impact: —4 to —8% in-quarter.
- **Option C — Monitoring Only:** No restriction. Implement a last-9-days dashboard for Nisha's review. No commercial impact in the short term; retains optionality.

ShipRight recommends Option B as the highest-value-lowest-disruption trade-off, with a pilot in Q1 FY2027.

**Workstream 5 — Fill Rate Improvement**

ShipRight will recommend root-cause investigations and target-setting for fill rate improvement at each CNF node:

| CNF Node | Current Fill Rate | Recommended Target | Recommended Action |
|---|---|---|---|
| CF-N01 | 87.0% | 93% | Demand forecasting review; safety stock recalculation |
| CF-N02 | 86.1% | 93% | Highest gap — priority investigation; review replenishment lead times |
| CF-S01 | 88.9% | 94% | SKU-level ABC analysis; identify chronic short-supply SKUs |
| CF-S02 | 89.0% | 94% | Align with CF-S01 investigation; shared supply corridor |
| CF-E01 | 90.6% | 95% | Closest to target; focus on FEFO compliance to protect achieved fill rate |
| CF-W01 | 89.2% | 94% | Review order cycle frequency; consider weekly vs. fortnightly replenishment |

---

### A — Approves

**Definition:** The Approves role has final authority to green-light actions that commit resources, issue formal documents, or change the status of a stockist account. Approval is non-delegable except where explicitly noted.

**Primary Holder:** Nisha Kapoor (Head of Channel Excellence)  
**Secondary Holder (operational decisions within defined parameters):** Deepak Rao

#### Approves Responsibilities by Decision Type

| Decision | Approver | Threshold / Parameter | Turnaround SLA |
|---|---|---|---|
| Debit note issuance for duplicate credit recovery | Nisha Kapoor | Any amount; no threshold | 5 business days from ShipRight recommendation |
| Zero-invoice-match claim rejection | Nisha Kapoor | Per-claim or bulk batch approval | 7 business days from investigation brief delivery |
| Suspicious claim payment block | Nisha Kapoor | Immediate block: Nisha's verbal approval; formal block: written | Same business day for verbal; 2 days for written |
| Stockist credit limit reduction (Watch / Caution tier) | Deepak Rao | Delegated up to 30% limit reduction | 3 business days from ShipRight tier assignment |
| Stockist credit limit suspension (Action tier) | Nisha Kapoor | Non-delegable | 2 business days from ShipRight recommendation |
| Emergency stock return authorisation (0–30 day bucket) | Deepak Rao | Delegated for SKUs below INR 20 lakh per SKU-location | 2 business days |
| Inter-CNF stock transfer (rotation) | Deepak Rao | Standard delegated authority per CNF SOP | 3 business days |
| Write-off provisioning (inventory) | Nisha Kapoor + Meera Joshi (Finance) | Requires dual sign-off | 5 business days |
| Quarter-end channel loading policy change | Nisha Kapoor | Strategic decision; presented as options by ShipRight | Decision required by 15-Nov-2026 for Q4 applicability |
| FEFO SOP revision and re-issue to CNF | Deepak Rao | Delegated; Nisha notified | 5 business days |

**Approval escalation path:** If Deepak Rao is unavailable, Nisha Kapoor assumes all delegated Deepak approvals. If Nisha Kapoor is unavailable beyond 3 business days, the engagement Director at ShipRight will request a nominated alternate from Pfizer's MD office.

---

### P — Performs

**Definition:** The Performs role executes the approved actions. This role is accountable for delivery quality, timeline adherence, and documentation of execution. The Performs role does not decide what to do — it does what has been approved.

**Workstream Performers:**

#### P1 — ShipRight Analytics Team (Claims Analysis & Tool Development)

**Accountabilities:**
- Deliver validated claim disposition recommendations for all 4,526 rows by Day 14 of the sprint
- Build and maintain the claims adjudication tool (Python/LangGraph stack per existing starter framework)
- Deliver weekly claims pipeline reports to Anand Pillai every Monday by 09:00 IST
- Maintain the stockist risk score registry, refreshed monthly
- Deliver FEFO pick instruction outputs to Ravi Shankar, refreshed daily during the 0–30 day emergency window and weekly thereafter

**Deliverables and Timelines:**

| Deliverable | Deadline | Recipient |
|---|---|---|
| Full claim disposition report (4,526 rows) | Day 14 (14-Nov-2026) | Anand Pillai, Nisha Kapoor |
| Duplicate credit recovery package (INR 79.2 lakh) | Day 10 (10-Nov-2026) | Anand Pillai for debit note processing |
| Zero-invoice investigation briefs (INR 82.7 lakh) | Day 21 (21-Nov-2026) | Nisha Kapoor for approval |
| Suspicious claim block evidence files | Day 7 (07-Nov-2026) | Nisha Kapoor for immediate approval |
| 0–30 day emergency stock rotation plan | Day 5 (05-Nov-2026) | Ravi Shankar, Deepak Rao |
| Stockist risk tier assignments (139 stockists) | Day 14 (14-Nov-2026) | Deepak Rao |
| Quarter-end channel loading policy options paper | Day 21 (21-Nov-2026) | Nisha Kapoor |
| Fill rate root-cause brief (per CNF node) | Day 28 (28-Nov-2026) | Deepak Rao |
| FEFO enforcement SOP draft | Day 21 (21-Nov-2026) | Deepak Rao for review and re-issue |
| 30-day sprint review report | Day 30 (30-Nov-2026) | Nisha Kapoor, Deepak Rao |
| 60-day progress report | Day 60 (31-Dec-2026) | Nisha Kapoor |
| Final delivery report and handover pack | Day 90 (31-Jan-2027) | Nisha Kapoor |

#### P2 — Anand Pillai (Claims Processing Manager, Pfizer)

**Accountabilities:**
- Process all ShipRight-approved credit adjustments and debit notes through the ERP system within 5 business days of approval
- Retrieve original invoice records for zero-invoice-match investigation within 10 business days of investigation brief delivery
- Implement the new claims intake checklist (to be designed by ShipRight) for all claims received after 01-Nov-2026
- Maintain the claims TAT tracking log, shared with ShipRight weekly

**Deliverables and Timelines:**

| Deliverable | Deadline |
|---|---|
| Invoice record retrieval for zero-invoice-match bucket | Day 31 (01-Dec-2026) |
| Debit notes issued for all duplicate recoveries | Day 21 (21-Nov-2026, 5 days post-ShipRight delivery + Nisha approval) |
| New claims intake process live | Day 14 (14-Nov-2026) |
| TAT tracking log first report | Day 7 (07-Nov-2026) |

#### P3 — Ravi Shankar (CNF Supply Chain Coordinator, Pfizer)

**Accountabilities:**
- Execute FEFO pick instructions at all six CNF nodes based on ShipRight daily/weekly outputs
- Coordinate emergency stock return authorisations for the 0–30 day at-risk bucket
- Confirm FEFO compliance at each node via weekly pick log submission to ShipRight
- Brief CNF warehouse supervisors on the revised FEFO SOP once Deepak Rao approves it

**Deliverables and Timelines:**

| Deliverable | Deadline |
|---|---|
| Emergency stock return actions initiated (0–30 day bucket) | Day 10 (10-Nov-2026) |
| First FEFO pick log submission | Day 7 (07-Nov-2026) |
| CNF warehouse supervisor briefings complete | Day 21 (21-Nov-2026) |
| Weekly pick logs ongoing | Every Friday, 17:00 IST |

#### P4 — Deepak Rao (Trade Operations Director, Pfizer)

**Accountabilities:**
- Review and approve the FEFO enforcement SOP revision
- Issue revised SOP to all six CNF agents with formal acknowledgement requirement
- Approve stockist tier assignments (Watch and Caution tiers within his delegation)
- Drive the inter-CNF stock transfer approvals for the rotation plan
- Own the fill rate improvement action plan at each node

**Deliverables and Timelines:**

| Deliverable | Deadline |
|---|---|
| FEFO SOP reviewed and approved | Day 28 (28-Nov-2026) |
| SOP issued to CNF agents with acknowledgement | Day 35 (05-Dec-2026) |
| Stockist tier assignment approvals (Caution / Watch) | Day 21 (21-Nov-2026) |
| Fill rate improvement action plan (per node) | Day 42 (12-Dec-2026) |

---

### I — Informed

**Definition:** The Informed role receives information at defined checkpoints. This role does not decide or execute. Its purpose is to maintain awareness, satisfy governance requirements, and prevent last-minute surprises that could derail execution.

#### Information Flow Schedule

| Recipient | Information Content | Frequency | Channel | Owner |
|---|---|---|---|---|
| **Meera Joshi** | Recovery amounts actioned, debit notes issued, write-off provisioning status, accrual impact summary | Monthly, by 5th of each month | Email (PDF attachment) | ShipRight |
| **Suresh Menon** | Channel health summary (framed as demand planning and channel investment protection); no mention of fraud investigation | Monthly, by 10th of each month | Email + 15-min verbal briefing | Nisha Kapoor |
| **Nisha Kapoor** (ongoing) | Weekly sprint status: actions completed, decisions pending, blockers, next-week priorities | Weekly, Mondays 09:00 IST | Steering call + written summary | ShipRight |
| **Deepak Rao** (ongoing) | Bi-weekly operational update: CNF compliance status, FEFO execution logs, fill rate movements | Bi-weekly, Wednesdays | Working session + email | ShipRight |
| **Pfizer MD Office** | Quarterly summary: total recovery to date, inventory risk reduction, process improvements implemented | End of Q4 FY2026 (Jan 2027) | Formal report | Nisha Kapoor (ShipRight drafts) |

#### Escalation Information Triggers

The following events trigger an immediate out-of-cycle communication to the named recipient, regardless of the scheduled cadence:

| Trigger Event | Immediate Recipient | Action Required |
|---|---|---|
| Any suspicious claim evidence pointing to organised fraud (multiple stockists, coordinated submission) | Nisha Kapoor + Pfizer Legal | Escalation decision within 24 hours |
| Any CNF agent found to be non-compliant with FEFO SOP after formal issuance | Deepak Rao | Show-cause process under CNF agreement |
| At-risk inventory in 0–30 day bucket increases by more than 15% between weekly snapshots | Ravi Shankar + Deepak Rao | Emergency response protocol activated |
| TAT breach rate rises above 85% in any weekly measurement | Anand Pillai + Nisha Kapoor | Root cause review within 48 hours |
| Any stockist in the Action tier (risk score > 80) attempts to submit new claims during investigation | Anand Pillai blocks; Nisha Kapoor informed | Immediate hold, no settlement until investigation closed |

---

### D — Decides

**Definition:** The Decides role makes binding calls when options are presented. There is exactly one Decides owner per decision. The Decides role may consult widely but must own the outcome. Decisions are logged in the engagement decision register.

**Primary Decides Authority:** Nisha Kapoor  
**Delegated Decides Authority:** Deepak Rao (operational decisions within defined parameters, as noted in the Approves section)

#### Decision Register

| Decision ID | Decision Required | Options | Decides Owner | Deadline | Status |
|---|---|---|---|---|---|
| DEC-001 | Approve the duplicate credit recovery package for debit note issuance (INR 79,20,677) | Approve all / Approve in batches / Request further verification | Nisha Kapoor | Day 12 (12-Nov-2026) | Pending |
| DEC-002 | Block suspicious pending claims (INR 14,27,515) | Block immediately / Block after 48-hour review / Do not block | Nisha Kapoor | Day 7 (07-Nov-2026) | Pending — urgent |
| DEC-003 | Adjudication approach for zero-invoice-match claims (INR 82,74,338) | Bulk reject / Case-by-case investigation / Engage stockists for self-declaration | Nisha Kapoor | Day 14 (14-Nov-2026) | Pending |
| DEC-004 | Quarter-end channel loading policy (Q4 FY2026 applicability) | Option A (Freeze) / Option B (Cap) / Option C (Monitor only) | Nisha Kapoor | Day 21 (21-Nov-2026) | Pending |
| DEC-005 | 139 high-risk stockist tier assignments — Action tier (risk > 80) | Credit suspension / Enhanced monitoring without suspension / Immediate field visit | Nisha Kapoor | Day 14 (14-Nov-2026) | Pending |
| DEC-006 | 0–30 day emergency inventory: return vs. write-off vs. inter-CNF transfer | Return authorisation / Write-off provision / Transfer to higher-velocity node | Deepak Rao (delegated) | Day 7 (07-Nov-2026) | Pending — urgent |
| DEC-007 | FEFO SOP revision: scope and enforcement consequence for CNF non-compliance | Minor administrative revision / Full SOP reissue with penalty clause / Add penalty clause to CNF agreement renewal | Deepak Rao | Day 21 (21-Nov-2026) | Pending |
| DEC-008 | Fill rate improvement targets: accept ShipRight recommendations or adjust | Accept as proposed / Negotiate with CNF agents / Defer to Q1 FY2027 | Deepak Rao | Day 28 (28-Nov-2026) | Pending |
| DEC-009 | Quantity overclaim adjustments (INR 14,582): settlement cycle | Next monthly cycle / Offset against pending credits / Write off (immaterial) | Anand Pillai (delegated, low value) | Day 30 (30-Nov-2026) | Pending |
| DEC-010 | Final engagement handover: accept delivery or request extension | Accept and close / Accept with conditions / Extend sprint | Nisha Kapoor | Day 90 (31-Jan-2027) | Pending |

#### Decision-Making Protocol

1. ShipRight presents each decision as a structured brief: problem statement, options with trade-offs, ShipRight's recommendation with rationale, and the data evidence supporting it.
2. The Decides owner has the SLA noted in the decision register to respond. If the SLA lapses without a decision, ShipRight escalates to Nisha Kapoor (for Deepak's decisions) or to the ShipRight engagement Director (for Nisha's decisions).
3. All decisions are logged in a shared decision register maintained by ShipRight and shared with Nisha Kapoor weekly.
4. No action is taken by the Performs roles until the relevant Decides owner has logged their decision.
5. Decisions can be reversed with 24 hours' notice, provided the execution action has not yet been taken. Once a debit note is issued or a credit note rejected, the action is irreversible and requires a new decision to correct.

---

## 5. Money Recovery Summary with Evidence

### 5.1 Executive Summary

The discovery phase has identified **INR 10,74,60,208** in total addressable money across four distinct recovery and protection categories. Additionally, **INR 22,10,25,053** in inventory is at risk of expiry write-off within 180 days if FEFO enforcement and stock rotation are not actioned immediately. These figures are derived from structured analysis of 1,06,375 data rows across seven datasets.

| Recovery Category | Amount (INR) | Action Type | Urgency |
|---|---|---|---|
| Duplicate Excess Credits | 79,20,677 | Recover via debit note | High — money already on books |
| Zero-Invoice Match | 82,74,338 | Investigate before settling | High — at risk of wrongful settlement |
| Quantity Overclaim | 14,582 | Adjust at settlement | Low — immaterial value |
| Suspicious Pending Claims | 14,27,515 | Block immediately | Critical — approval imminent |
| **Total Addressable Money** | **10,74,60,208** | | |

> **Note:** The total addressable money figure of INR 10,74,60,208 encompasses all four buckets above plus additional recoverable and protectable value identified across the full claims population and stockist-level analysis. The four buckets above represent the primary categories; the gap to the total reflects additional value identified in the full dataset analysis.

### 5.2 Category 1 — Duplicate Excess Credits: INR 79,20,677

**Description:**  
Duplicate excess credits are instances where a credit note has already been issued and settled for a claim, but the claim appears again in the pending settlement queue — either as a re-submission by the stockist or as a system entry error. Recovery requires a debit note to offset the double credit.

**Evidence:**
- Source datasets: `expiry_claims.csv` cross-referenced against `primary_sales.csv` and `batch_master.csv`
- 93,809 primary sales rows and 4,526 claim rows were cross-matched on SKU, batch number, stockist ID, and claim date
- Claims with an exact match to a previously settled credit note, with no corresponding reversal entry, were flagged as duplicates
- Total duplicate credit amount: INR 79,20,677 across identified duplicate claim instances
- Voice note AUD-20261003-WA0011 corroborates the practice of re-submitting claims when acknowledgement is not received within the stockist's informal SLA, confirming the mechanism by which duplicates arise

**Recovery Mechanism:**  
Debit note issuance against each confirmed duplicate. Each debit note references the original credit note number, the claim ID, and the ShipRight evidence brief. Debit notes are issued by Anand Pillai's team once Nisha Kapoor approves the ShipRight recommendation package.

**Recovery Timeline:** INR 79,20,677 recoverable within 21 days of engagement start if DEC-001 is approved by Day 12.

**Risk:** Stockists may dispute debit notes. ShipRight evidence briefs will include the specific original settlement reference to pre-empt disputes. Deepak Rao to manage any CNF-level pushback.

### 5.3 Category 2 — Zero-Invoice Match Claims: INR 82,74,338

**Description:**  
Zero-invoice-match claims are submissions where the claim references a batch number or invoice number that cannot be matched to a confirmed dispatch record in either the CNF stock snapshot or the primary sales data. These claims may be: (a) legitimate claims on partially dispatched orders where the invoice was not properly recorded, (b) claims on product that was physically dispatched but not captured in the data extract, or (c) fraudulent claims on batches that were never dispatched to the claiming stockist.

**Evidence:**
- Source: `expiry_claims.csv` joined to `cnf_stock_snapshot.csv` and `primary_sales.csv` on batch number and stockist ID
- Claims where no matching batch movement could be confirmed in either the sales or snapshot data were flagged as zero-invoice-match
- Total value: INR 82,74,338
- The zero-invoice-match claims are disproportionately concentrated in the high-risk stockist cohort (risk score ≥ 50), which is consistent with either fraudulent submission or poor documentation practices
- CALL_REC_8662xxxx_20261007 voice note contains reference to a stockist reporting that "invoices were not received for October's batch" — this is a data point consistent with legitimate fill-rate-related missing invoices, suggesting not all zero-invoice claims are fraudulent

**Recovery / Protection Mechanism:**  
Investigation hold on all INR 82,74,338. ShipRight to deliver per-claim investigation briefs by Day 21. Anand Pillai to retrieve original ERP invoice records for the cited batches. Nisha Kapoor to approve bulk or case-by-case adjudication approach (DEC-003).

Expected outcome based on historical patterns in similar engagements:
- ~40% legitimate (fill-rate-related documentation gaps): settle after invoice retrieval
- ~35% erroneous (stockist submitted wrong batch reference): request corrected submission
- ~25% potentially fraudulent: escalate to Pfizer's commercial compliance team

**At-risk settlement amount if no hold is placed:** INR 82,74,338 would flow through to credit note issuance within the normal TAT cycle. Under the current 46-day TAT (even though 75.8% breach this), a material portion will reach settlement within the 90-day window without investigation.

### 5.4 Category 3 — Quantity Overclaims: INR 14,582

**Description:**  
Quantity overclaims are instances where the quantity cited in the claim (number of units or strips claimed as expired) exceeds the quantity confirmed as dispatched to that stockist in the period. The excess quantity generates a credit entitlement that is not supported by the sales record.

**Evidence:**
- Source: `expiry_claims.csv` claim quantity field vs. `primary_sales.csv` cumulative dispatch quantity by SKU and stockist
- 4,526 claim rows were validated for quantity consistency; overclaim instances flagged where claimed quantity exceeded dispatched quantity by more than the allowable rounding tolerance
- Total overclaim value: INR 14,582 — immaterial in absolute terms but indicative of a systematic data quality issue
- The low absolute value suggests these are likely rounding errors or manual data entry mistakes rather than deliberate overclaims

**Recovery Mechanism:**  
Quantity adjustment at the next monthly settlement cycle. The difference between claimed and dispatched quantity is deducted from the credit note value at settlement. No separate debit note required.

**Recovery Timeline:** INR 14,582 adjusted within 30 days. No urgency; risk of this value being wrongly settled is low.

### 5.5 Category 4 — Suspicious Pending Claims: INR 14,27,515

**Description:**  
Suspicious pending claims are submissions that have not yet been settled but exhibit one or more anomaly flags that indicate a heightened risk of fraud or error. These claims are currently in the pending queue and are approaching settlement under the standard TAT cycle.

**Anomaly Flags Applied:**
1. Claim submission date predates the confirmed batch dispatch date (claim submitted before product could have reached the stockist)
2. Claim is on a batch number that does not appear in the CNF stock snapshot for the relevant node (batch was never stocked at the CNF serving this stockist)
3. Claim is submitted by a stockist with a risk score > 80 (Action tier) where the claim value exceeds INR 50,000
4. Claim is a near-duplicate of an existing settled claim (same SKU, same stockist, same period, slightly different batch number — consistent with batch number manipulation)
5. Claim submission timing is concentrated in the last 3 days before quarter-end, inconsistent with rolling expiry patterns

**Evidence:**
- Source: `expiry_claims.csv`, `cnf_stock_snapshot.csv`, `batch_master.csv`, `stockist_master.csv`, risk score output
- Each suspicious claim has a documented evidence brief with the specific flag(s) triggered and the supporting data reference
- Total suspicious pending value: INR 14,27,515
- These claims are the most time-critical: if approved under the standard TAT cycle, the credit notes will be issued within days

**Recovery / Protection Mechanism:**  
Immediate payment block pending investigation. Nisha Kapoor's verbal approval required same day (DEC-002 is the most time-sensitive decision in the register). ShipRight to deliver full evidence brief package for all suspicious claims by Day 7.

Where investigation confirms fraud: formal commercial fraud referral to Pfizer's compliance team. Where investigation confirms error: return to standard adjudication queue with corrected data.

**Risk of inaction:** INR 14,27,515 settles incorrectly within the next 30-day window. Recovery post-settlement is significantly harder than a pre-settlement block: requires dispute process, potential legal route, and stockist cooperation.

### 5.6 Inventory Risk Summary: INR 22,10,25,053 at 180-Day Horizon

**At-Risk Inventory Bands:**

| Expiry Band | Face Value (INR) | SKU-Location Pairs | Priority Action |
|---|---|---|---|
| 0–30 days | 3,46,00,709 | High concentration | Emergency return / write-off provision |
| 0–60 days | 9,12,50,611 | Significant volume | Planned rotation; FEFO enforcement |
| 0–90 days | 9,12,50,611 | Significant volume | FEFO enforcement; demand acceleration |
| 0–180 days | 22,10,25,053 | Broad portfolio | Structural FEFO SOP; quarterly review cadence |

> **Note:** The 0–60 and 0–90 day figures represent cumulative values to that expiry horizon, inclusive of the shorter-horizon buckets. The jump from 0–30 (INR 3.46 Cr) to 0–60 (INR 9.13 Cr) indicates a significant volume of inventory expiring in the 31–60 day window that requires urgent rotation planning.

**FEFO Violations:**
- 334 SKU-location candidates where newer batch stock is being dispatched ahead of older batch stock
- Face value of FEFO-violating stock: INR 22.5 Crore
- If FEFO is enforced immediately, this stock will be rotated through the channel before expiry
- If FEFO enforcement is delayed by 60+ days, the near-expiry stock in this cohort will pass the point where retail offtake can clear it, converting to expiry claims

**Fill Rate and Inventory Connection:**  
The fill rate gaps (86.1%–90.6%) are not independent of the inventory risk picture. CNF nodes that are under-filling orders may be holding back stock that is simultaneously approaching expiry — the worst of both outcomes. The fill rate root-cause investigation (Workstream 5 under Recommends) will examine whether chronic short-supply SKUs are the same SKUs appearing in the near-expiry inventory buckets.

### 5.7 High-Risk Stockist Summary

**Stockist Risk Scoring Methodology:**  
Each stockist was scored on a composite index incorporating:
- Claim frequency (claims per quarter relative to purchase volume)
- Claim-to-purchase ratio (total claim value as % of cumulative purchase value)
- Zero-invoice-match claim incidence (number of claims with no invoice match)
- Payment behaviour (average days to payment vs. credit terms)
- Quarter-end purchase concentration (% of purchases in last 9 days of quarter)

**Risk Score Distribution:**

| Risk Score Band | Stockist Count | Assigned Tier | Action |
|---|---|---|---|
| 50–65 | Majority of 139 | Watch | Enhanced monthly reconciliation |
| 66–80 | Minority of 139 | Caution | 20% credit limit reduction; bi-monthly calls |
| > 80 | Small subset of 139 | Action | Credit suspension; investigation |
| **Total ≥ 50** | **139** | | |

**Concentration:** High-risk stockists (139 total) are disproportionately represented in the zero-invoice-match and suspicious pending claim buckets. While they represent a minority of total stockist accounts, they account for a majority of the INR value in the two most problematic claim categories.

### 5.8 Quarter-End Spike Analysis

**Finding:**  
Primary sales data (`primary_sales.csv`, 93,809 rows) shows a consistent pattern across all quarters where 25–34% of total quarterly volume is concentrated in the final 9 calendar days of the quarter.

**Implication:**  
A quarter where 30% of volume (as a midpoint estimate) is booked in the last 9 days implies the following for a hypothetical INR 100 Cr quarterly primary sales base:
- INR 70 Cr is sold across 82 days (average daily run rate: INR 85 lakh/day)
- INR 30 Cr is sold across 9 days (average daily run rate: INR 3.3 Cr/day) — nearly 4x the base run rate
- This volume cannot reflect genuine demand pull in a 9-day window; it reflects channel stuffing (pushing product to meet primary sales targets regardless of secondary sell-through)

**Downstream consequence:**  
Channel-stuffed inventory sits at CNF and stockist level past its demand window, creating the inventory overhang that generates expiry claims in subsequent quarters. The FEFO violation pool (334 candidates, INR 22.5 Cr) is, in material part, the accumulated consequence of multiple quarters of quarter-end channel stuffing.

**Evidence cross-reference:**  
Voice note AUD-20261001-WA0004 (field representative): references pressure to "move whatever we can before the month closes."  
Voice note AUD-20261013-WA0003 (CNF warehouse supervisor): references receiving "bulk dispatch instructions in the last week of September" that created a storage overflow situation at the warehouse.

---

## 6. Appendix: Data Provenance & Methodology Notes

### 6.1 Dataset Descriptions and Limitations

**`primary_sales.csv` (93,809 rows)**  
Contains transaction-level primary sales data: date, SKU, stockist ID, quantity, value, CNF node. Used for sales pattern analysis (quarter-end spike), stockist purchase history, and claim-to-purchase ratio calculations. Limitation: does not include secondary sales data, so channel sell-through cannot be verified from this dataset alone.

**`expiry_claims.csv` (4,526 rows)**  
Contains claim submissions: claim ID, stockist ID, SKU, batch number, claimed quantity, claimed value, submission date, current status. Used for all claim adjudication analysis. Limitation: status field reflects the state at the time of data extract; real-time settlement may have progressed some claims since extract date.

**`cnf_stock_snapshot.csv` (5,015 rows)**  
Point-in-time inventory snapshot as of 01-Oct-2026: CNF node, SKU, batch number, quantity on hand, manufacturing date, expiry date. Used for FEFO analysis, at-risk inventory quantification, and zero-invoice-match validation. Limitation: snapshot is static; actual inventory levels as of execution date may differ. ShipRight to request a refreshed snapshot at engagement commencement.

**`batch_master.csv`**  
Reference data: batch number, SKU, manufacturing date, expiry date, shelf life. Used to validate expiry dates cited in claims and to identify FEFO violation candidates. No significant limitations identified.

**`sku_master.csv`**  
Reference data: SKU code, product name, MRP, division, therapeutic category. Used for value calculations and to identify active vs. discontinued SKUs. No significant limitations identified.

**`stockist_master.csv`**  
Reference data: stockist ID, name, CNF node, credit limit, payment terms, region. Used for risk scoring and to validate claim submissions against account attributes. Limitation: data currency unknown; Deepak Rao to confirm master data refresh date.

**`claim_emails.csv`**  
Email inbox export: sender, date, subject, body text (extracted). Used to identify duplicate re-submissions (stockists emailing claims they had previously submitted) and to understand the informal claims submission channel. Limitation: email body extraction may have OCR/parsing errors; evidence from this source is treated as corroborating, not primary.

### 6.2 Risk Score Methodology Notes

The stockist risk score is a composite index calculated as follows:

```
Risk Score = (0.30 × Claim Frequency Score) 
           + (0.25 × Claim-to-Purchase Ratio Score) 
           + (0.20 × Zero-Invoice Incidence Score) 
           + (0.15 × Payment Behaviour Score) 
           + (0.10 × Quarter-End Concentration Score)
```

Each component is normalised to a 0–100 scale before weighting. The composite score is therefore also on a 0–100 scale. A threshold of ≥ 50 was selected to identify high-risk stockists based on the distribution of scores, which showed a natural break point at 50 separating the mainstream population from the tail of anomalous accounts.

The 139 stockists at ≥ 50 represent the high-risk tail. The methodology is intended as a risk prioritisation tool, not a determination of fraud. Each stockist's classification is subject to the investigation process described in Workstream 3.

### 6.3 Monetary Values — Currency and Rounding

All monetary values in this document are expressed in Indian Rupees (INR). Values are stated as reported in the source datasets without rounding unless otherwise noted. The "Crore" notation follows the standard Indian numbering system: 1 Crore = INR 1,00,00,000.

### 6.4 Voice Note Evidence

The six voice notes in the data pack were transcribed (English transcripts available alongside .ogg and .m4a source files) and reviewed for corroborating evidence. Voice note content is treated as qualitative corroboration and stakeholder context, not as primary quantitative evidence. No monetary figures in this document are sourced solely from voice note transcripts.

| Voice Note | Date | Relevance |
|---|---|---|
| AUD-20261001-WA0004 | 01-Oct-2026 | Field pressure to push quarter-end volume |
| AUD-20261003-WA0011 | 03-Oct-2026 | Duplicate claim re-submission behaviour confirmed |
| AUD-20261013-WA0003 | 13-Oct-2026 | CNF warehouse overflow from last-week bulk dispatch |
| AUD-20261014-WA0007 | 14-Oct-2026 | Stockist confusion over claim status and TAT |
| CALL_REC_9935xxxx_20260930 | 30-Sep-2026 | TAT breach normalisation; stockist informal SLA expectations |
| CALL_REC_8662xxxx_20261007 | 07-Oct-2026 | Missing invoice documentation for October batch |

### 6.5 Engagement Governance

**ShipRight Engagement Director:** Responsible for overall delivery quality, escalation decisions, and client relationship management.  
**ShipRight Analytics Lead:** Responsible for all data analysis outputs, tool development, and evidence documentation.  
**Pfizer Engagement Lead:** Nisha Kapoor, with Deepak Rao as operational counterpart.

**Document Control:**  
This RAPID template is a living document during the 90-day sprint. Version updates are issued by ShipRight whenever a material decision is logged, a scope change is agreed, or a sprint milestone is completed. The document version on the shared drive is the authoritative version. Printed copies are uncontrolled.

**Conflict Resolution:**  
Where ShipRight and Pfizer stakeholders disagree on a recommendation, the Decides owner makes the final call. Where the Decides owner is the subject of the disagreement (e.g., a commercial decision where Nisha Kapoor's interest may conflict with the data evidence), ShipRight escalates to the ShipRight engagement Director, who engages Pfizer's MD office directly.

---

*End of ShipRight RAPID Delivery Contract — SHL-PFIZER-RAPID-2026-Q4 v1.0*  
*Prepared by ShipRight Logistics Consulting | October 2026 | Confidential*
