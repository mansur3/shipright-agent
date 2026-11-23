# Sankalp: claim check and supply view for the Pfizer channel

Fictional case (FDE Academy, Project 1). Checks every stockist expiry or damage claim against policy and the records, and shows Supply Chain where stock sits in the wrong place. A named person (Commercial Finance) decides every credit; the tool only recommends.

- **Claims:** one checker, `backend/agent/claim_checks.py`, returns APPROVE, REJECT or NEEDS A PERSON with the clause and the file lines. No model is called on this path.
- **Ask:** a LangGraph graph (`backend/agent/graph.py`): input guard, model picks one of 11 read-only tools, tool guard, output guard, at most 4 trips.
- **Data:** the seven CSVs of the pack are read once and cleaned by `backend/agent/clean.py`. Policy numbers live in `backend/config.py`.
- Agent rules for this repo are in `backend/AGENTS.md`. Why each choice was made is in the discovery and architecture notes.

## Run locally (Windows)

```
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt -r requirements-dev.txt
copy .env.example .env      # then fill it in; never commit .env
cd ..
run_local.cmd               # http://127.0.0.1:8000, public demo on, throwaway database
```

## Test

```
cd backend
python -m pytest -q                 # 298 tests
python -m checks.run_checks         # 20-record check set`r`npython -m checks.reconcile_source   # independent recompute from the CSVs, 23 checks
```

## Frontend

`frontend/` is Next.js 15, built as a static export into `backend/public/` by `python build_frontend.py`. The API serves it, so deploy is one unit.

## Deploy (Vercel Hobby)

Root Directory `backend`, FastAPI preset, region `bom1`. Environment variables are listed in `backend/.env.example`; set `SANKALP_PUBLIC_DEMO=1` for the panel demo (read roles only, never admin). Full steps: the Step 9 section of `verification/11_qa_and_deploy.md` in the working pack.

## Limits

The check-set answers are a draft until the claim owner signs them. Cost per question is estimated from assumed prices in `config.py`. Allocation is inferred from stock and outward because the share table is not in the pack.

