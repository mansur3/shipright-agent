# Multi-agent architecture audit

Method: read every module under `backend/agent`, `backend/batch`, `backend/routers`, the tests, the agent catalogue (`deliverables/Agent_Catalogue.md`) and `frontend/src/lib/agents.ts`; ran the suite. Diagrams: `deliverables/excalidraw/01` to `05`.

## 1. Agents discovered (7) and verdict

| # | Agent | Type | File | Input | Output | Tools / data | Upstream | Downstream | Validation | Failure handling | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Claim Gatekeeper | code | `agent/claim_checks.py` | stockist, batch, qty, date, type | verdict, tier T1 to T4, rule id, clause, evidence rows | clean layer (all CSVs); no model | Mailbox Triage, Intake, Recovery, Ask (validate_claim) | Controller | 20-record check set 20/20; `test_rules.py` forbids rule duplication | missing batch is T4, not invalid | retained |
| 2 | Claims Mailbox Triage | code | `agent/email_intake.py` | claim_emails | structured lines + verdicts | Gatekeeper | mailbox | claims desk | message text cannot change a verdict (tested) | unparseable email goes to NEEDS A PERSON | retained |
| 3 | Recovery Analyst | code | `batch/processor.py`, `agent/recovery.py` | all claims | five buckets, by stockist; SQLite rows | Gatekeeper | Gatekeeper | Recovery page, register | ties to ledger (tests) | kinds never added | retained |
| 4 | Claims Intake Assistant | code + model | `agent/claims_graph.py` (LangGraph, 14 nodes) | chat message | claim or status or benchmark reply | Gatekeeper, SQLite; model for intent fallback and wording | user | SQLite, Review Queue | Pydantic field validation, guardrails, number guard on wording | falls back to the draft when the model fails | **modified** |
| 5 | Ask Analyst | model + 11 tools | `agent/graph.py` (LangGraph) | question | answer, evidence, flags, usage | 11 read-only tools | user | analysis engines, gpt-4o-mini via OpenRouter, temperature 0 | input, tool and output guards; 12-trip cap | refusal text, trip-limit message, tool error text | **modified** |
| 6 | Supply and FEFO Watcher | code | `agent/analysis.py` | snapshots, sales, batches | cover, shortage, FEFO, freeze watch | clean layer | none | Supply page, register, Ask tools | tests pin each figure to the ledger | empty results explained | retained (text corrected) |
| 7 | Scheme Order Gate | code | `agent/analysis.py` | quarter, SKU, proposed order | cap status, claim rates, BLOCK SCHEME | clean layer | none | Scheme page, register, Ask tools | tests; proxy labelled | no baseline returns "no baseline" | retained |

New component, not an agent: `agent/opportunities.py` (deterministic register, no model). Counts: 7 discovered, 7 retained, 2 modified (Ask Analyst, Intake Assistant) plus one text correction (Supply and FEFO Watcher), 0 removed, 0 agents added.

## 2. Architecture dimensions

**A. Orchestration.** There is no central orchestrator and no cross-agent LLM handoff. "Multi-agent" here means seven narrowly scoped agents that share one deterministic code layer. Two LangGraph graphs hold the only model loops: Ask Analyst (input_guard, model, tool_guard, run_tools, output_guard) and Intake Assistant (classify_intent to create, status or recovery branches). Execution is sequential; retries are capped (`MAX_TOOL_TRIPS` = 12, one source for the cap), so no infinite loop exists. Tool calls inside one model reply run in a plain loop. Duplicate execution: `recovery.build` and `opportunities.build` are `lru_cache`d. No unnecessary agent calls: the Intake Assistant tries keywords before it uses the model; claim checks, scheme gates and the register call no model.

**B. Collaboration.** Agents cannot disagree on a rule because each rule is written once in `claim_checks.py` and `tests/test_rules.py` fails if a window, quantity or repeat rule appears elsewhere. Downstream agents receive the checker's structured result, not text.

**C. Data grounding.** Every figure comes from code reading `data/`. The model is told (rules 1 and 12 of its system prompt) never to compute or invent, but a prompt is not enforcement. Before this audit nothing deterministically checked an answer's figures; see section 4.

**D. Reliability and safety.** Present: Pydantic and guardrails on input, allow-listed tools with argument checks, trip cap, output scrubbing, audit log, JWT with six roles, rate limiting, throwaway-demo mode that never grants admin, human decision for every credit. Gaps: no run lock around the admin batch (`routers/admin.py` run-batch; a second click would re-run it, admin-only, left as is). The model call had no timeout; it now has 30 s and one retry.

**E. Evaluation.** See AI_AGENT_EVALUATION_REPORT.md.

## 3. Findings

| Finding | Severity | Action |
|---|---|---|
| Duplicate agent responsibilities | none found | claim rule exists once (enforced by test) |
| Unused agents | none; all seven are exposed on screens and in `/agents` | none |
| Overlapping capability | Supply and FEFO Watcher and Scheme Order Gate share `analysis.py`; they are separate roles, one file | kept: shared helpers, distinct users |
| Hardcoded outputs | dashboard KPI "₹2.7-3.4 cr a year" was a literal in `dashboard/page.tsx` | replaced with the computed value from the register |
| Unsupported financial claims | Stockists page showed whole-claim "zero invoice" and "duplicate" totals the ledger shows are overstated (INR 79.2 L and 82.7 L against INR 51.5 L clear breaches) | page and nav entry removed; API endpoint kept for admin (tests) |
| Unsupported figure in Ask answers | output guard only regex-flagged bare INR amounts | numeric grounding validator added |
| Reply-wording guard let the model add new figures | `_polish` required old figures present, not that no new ones appear | tightened |
| Misleading shortage headline | six-month sum presented as the measured shortfall | latest month-end added to tool and register; text corrected |
| Mock responses | none found in production paths; the model-unavailable path returns the deterministic draft | none |
| Model-call concentration | Ask Analyst up to 4 model calls per question; Intake Assistant up to 2 | acceptable; cost shown per request |
| Missing validation step | no independent check of totals against the CSVs | `checks/reconcile_source.py` added |
| Missing agent | none justified; the register is code, not an agent | none |

## 4. Changes made to the agent layer

1. `guardrails.ungrounded_figures` and its use in `sanitise_output`: every number in an answer must match a number in some tool result (after lakh, crore and percent conversion, to the precision stated; dates and list numbers exempt). A miss adds the flag `ungrounded_figures` and a visible caveat; it does not block.
2. `claims_graph._polish`: rejects wording that adds any figure of two or more digits.
3. `tools.get_stock_cover`: returns the latest month-end split next to the six-month split and says the latter counts a gap once per month.
4. `agents.ts` evidence strings corrected to match.
5. `llm.get_llm`: 30 s timeout and one retry on every model call.

## 5. Residual risk

The grounding check is a numeric match, not semantic: a wrong claim built from correct numbers passes. Live model answers were not re-run in this audit. Branding differs (UI "Sankalp AI", repo "ShipRight_Agent").
