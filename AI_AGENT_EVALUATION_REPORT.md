# AI agent evaluation report

Principle: an output is judged against the data, not by whether it sounds plausible. Where a result was not measured, this report says so.

## 1. What was measured

| Dimension | Agent(s) | Method | Result |
|---|---|---|---|
| Correctness (claim verdicts) | Claim Gatekeeper | 20 hand-agreed records, `python -m checks.run_checks` | 20 of 20 right |
| Correctness (totals) | Gatekeeper, Recovery Analyst | independent stdlib recomputation of late claims, counts, values, sums | 23 of 23 reconciliations agree |
| Financial accuracy | register | opportunity amounts equal recovery buckets and ledger figures (`test_opportunities.py`, 7 tests) | pass |
| Groundedness (model) | Ask Analyst | `ungrounded_figures` unit tests: grounded lakh/crore/percent pass; invented amounts, counts, percents are flagged; dates exempt (6 tests) | pass |
| Hallucination resistance, wording | Intake Assistant | model changes or adds a figure -> draft is used (`test_claims_agent_flow.py`) | pass (3 cases incl. new one) |
| Hallucination resistance, prompt injection | Ask Analyst | input guard tests (`test_guardrails.py`) | pass |
| Tool-use accuracy | Ask Analyst | allow-list and argument checks, tools return documented keys (`test_tools.py`) | pass; model routing to the right tool **not** measured (needs live calls) |
| Orchestration | Ask, Intake graphs | trip cap, blocked-input path, claim creation flow (`test_guardrails.py`, `test_claims_agent_flow.py`) | pass |
| Schema compliance | all API outputs | API tests, Pydantic models | pass |
| Consistency | all | rule defined once, enforced by `test_rules.py` | pass |
| Business relevance | register | every opportunity has owner, action, class, evidence | validated flag true for 10 of 10 |
| Failure recovery | Intake, Ask | model unavailable -> deterministic draft; tool error -> message; trip cap -> plain stop text | tested with fakes |

## 2. What was not measured

- Live model behaviour: no run against the paid API in this audit, so tool-selection accuracy, answer quality and the real rate at which `ungrounded_figures` fires are unknown.
- Token cost: the app shows a per-request rupee estimate from assumed prices in `config.py`; the prices are unconfirmed.
- The grounding check is numeric. It does not detect a wrong conclusion drawn from correct numbers.
- Check-set answers are a draft until the claim owner signs them (stated in the repo README).

## 3. Per-agent scorecard

| Agent | Correctness | Grounded | Structured output | Failure handling | Comment |
|---|---|---|---|---|---|
| Claim Gatekeeper | 20/20, ledger-tied | yes (code) | yes | T4 for unknown batch | strongest component |
| Mailbox Triage | tested, text cannot change verdict | yes | yes | NEEDS A PERSON | ok |
| Recovery Analyst | ties to ledger and independent recompute | yes | yes | n/a | ok |
| Intake Assistant | flow tested with a fake model | draft figures guarded | yes | falls back to draft | wording guard tightened |
| Ask Analyst | tools tested; routing unmeasured | now checked per answer | yes | caps and fallbacks | needs a live evaluation set |
| Supply and FEFO Watcher | ledger-pinned | yes (code) | yes | explained empties | shortage text corrected |
| Scheme Order Gate | ledger-pinned | yes (code) | yes | "no baseline" | proxy labelled |

## 4. Recommended next evaluation

Build 30 to 40 labelled questions with expected tool and expected figures; run weekly against the live model; track tool-selection accuracy, `ungrounded_figures` rate and cost per answer.
