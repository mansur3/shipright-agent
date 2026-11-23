# QA and validation report

Everything below was run in this session on Windows with Python 3.14 and Node 22. Items not run are listed at the end.

## 1. Executed checks

| Check | Command | Result |
|---|---|---|
| Baseline backend suite (before changes) | `python -m pytest -q` in `backend` | 281 passed |
| Backend suite (final) | same | **298 passed**, 0 failed (+17: 7 register, 2 API, 6 grounding, 1 wording guard, 1 source reconciliation) |
| Claim check set | `python -m checks.run_checks` | 20 of 20 right; 4,503 claims replayed (2,081 approve, 575 reject, 1,847 needs a person) |
| Source reconciliation | `python -m checks.reconcile_source` | 23 of 23 agree |
| Type check | `npx tsc --noEmit` in `frontend` | exit 0 (after clearing stale generated type folders) |
| Lint | `npx next lint` | no warnings or errors |
| Production build | `python build_frontend.py` | success; 13 routes exported to `backend/public` |
| Application smoke | started the app (uvicorn, demo mode), health 200, demo CFO login, visited Recovery, Recovery Register, Allocation FEFO Cap, Agents, Scheme Returns, Ask AI, Check a Claim in a browser and captured screenshots | pages render with data; register shows 10 opportunities |
| Diagram import | each `.excalidraw` loaded and rendered by Excalidraw's own library (gstack diagram bundle) | 5 of 5 render to SVG and PNG |
| Deck | built with python-pptx from the template, converted with LibreOffice, every slide inspected | 14 slides, no overflow after fixes |

## 2. Test coverage by area

- API and auth: `test_api.py` (64 tests incl. opportunities auth and tie-out).
- Data: `test_clean.py`, `test_analysis.py`, `test_reconcile_source.py`.
- Claims: `test_claim_checks.py`, `test_claims.py`, `test_rules.py`, `test_email_intake.py`, `test_recovery.py`.
- Agents: `test_guardrails.py`, `test_tools.py`, `test_claims_agent_flow.py`, `test_cost_and_checks.py`.
- Financial: `test_opportunities.py` (class, tie to buckets, no cross-class total, overlap flags, latest-month rule).

## 3. Defects found while testing

| Defect | Where | Resolution |
|---|---|---|
| Reconciliation disagreed on 1 sales row and 3 derived figures | my own script, not normalising codes and scheme-code variants | script fixed; shows the application's cleaning is correct |
| Stale generated types made `tsc` fail after deleting a page | `.next` / `.next-qa` caches | caches cleared |
| Late-claim reconciliation first restricted to type "Expired" | my script | removed restriction; matches 64 claims exactly |

## 4. Not run, and why

- No browser end-to-end test suite exists and none was written; UI was checked by hand.
- No live model calls were made, so Ask Analyst and Intake Assistant were tested with fakes only.
- Excalidraw files were not manually opened at excalidraw.com; they were rendered by the Excalidraw library itself, which parses the same format.
- Deployment (Vercel) was not exercised.
- `postman`, `gstack qa`, `review`, `cso` skills were not run. Skills actually used: gstack `diagram` renderer and `browse`.
- rea.tools (reverse-engineering MCP) has no documented capability relevant to this assignment and was not used.

## 5. Known limits carried forward

Allocation inferred from stock and outward; returns estimate depends on the 1% target; admin batch has no run lock; no frontend tests.
