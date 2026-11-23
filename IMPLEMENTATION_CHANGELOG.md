# Implementation changelog

Principle: preserve the existing, sound multi-agent implementation; change only what an audit finding justified.

## Added

| Item | Files | Why |
|---|---|---|
| Opportunity Register (deterministic) | `backend/agent/opportunities.py`, `GET /api/analytics/opportunities` in `routers/analytics.py` | one list of every money finding with class, formula, evidence, owner, finding agent, validated flag; no cross-class totals |
| Recovery Register page | `frontend/src/app/opportunities/page.tsx`, nav entry | executives can see evidence and owner per opportunity |
| Numeric grounding check | `agent/guardrails.py` (`ungrounded_figures`, used by `sanitise_output`) | flags any figure in an Ask answer that no tool returned |
| Independent source reconciliation | `backend/checks/reconcile_source.py`, `tests/test_reconcile_source.py` | recompute from the raw CSVs without the application's cleaning |
| Tests | `test_opportunities.py`, additions to `test_api.py`, `test_guardrails.py`, `test_claims_agent_flow.py` | 17 new tests |
| Diagrams | `deliverables/excalidraw/01..05_*.excalidraw`, `build_diagrams.py`, `xl.py`, `render_all.py`, `exports/*.png|svg` | editable architecture and workflow diagrams |
| Deck and screenshots | `ShipRight_Final_Executive_Presentation.pptx`, `deliverables/build_deck.py`, `deliverables/figures.json`, `deliverables/screenshots/` | executive presentation |
| Reports | seven `*_REPORT/ANALYSIS/AUDIT/CHANGELOG.md` files at the repo root | audit record |

## Changed

| Item | Change | Reason |
|---|---|---|
| `frontend/src/app/dashboard/page.tsx` | hardcoded "₹2.7-3.4 cr a year" replaced with the computed value; headline reworded (T1 broke policy text, T2 probable) | unsourced literal; T2 overstated |
| `agent/tools.get_stock_cover` | adds latest month-end shortage split; interpretation states the six-month total counts a gap once per month | the six-month sum was read as one amount |
| `frontend/src/lib/agents.ts` | shortage evidence strings corrected | consistency with the tool |
| `agent/claims_graph._polish` | rejects a wording reply that adds a figure of two or more digits | model could add facts |
| `agent/llm.get_llm` | 30 s timeout, one retry | no timeout existed |

## Removed

| Item | Reason |
|---|---|
| Stockists page (`/stockist-risk`), nav entry, `StockistRisk*` types | showed whole-claim "zero invoice" and "duplicate" totals that the findings ledger shows are overstated; Recovery by-stockist table replaces it |

## Not changed (deliberately)

All seven agents, both LangGraph graphs, the claim rules, the cleaning rules, role-based access, the check set, `/api/analytics/stockist-risk` and `/summary` endpoints (admin use; no UI), the "Sankalp AI" brand in the UI.

## Verification

298 backend tests, 20 of 20 check set, 23 of 23 reconciliations, `tsc` and lint clean, production export built. Details in QA_AND_VALIDATION_REPORT.md.

## How to rebuild the deliverables

```
cd ShipRight_Agent
backend\.venv\Scripts\python.exe deliverables\excalidraw\build_diagrams.py
python deliverables\excalidraw\render_all.py          # needs bun and gstack's diagram-render bundle
python build_frontend.py                               # static export into backend/public
python deliverables\build_deck.py ..\Project1_Presentation_Template.pptx   # needs python-pptx, pillow
```
