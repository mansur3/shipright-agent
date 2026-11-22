# Instructions for the coding agent

Read this file before every task. Keep it short and keep it true.

## What we are building

A claims and supply check that a named person uses every week, built on what the data showed (verification/05_findings_ledger.md):

- **Neha Bansal** (Controller, Commercial Finance, 2 people) checks every claim before the credit note: APPROVE, REJECT or NEEDS A PERSON, as a recommendation with the policy clause and the file and line of every record used. Daily.
- **Kavita Rao** (Head, Supply Chain) and **Vaishali Kapoor** (Demand Planning) see stock cover by C&F, spare stock elsewhere, and FEFO breaches before the monthly allocation. Monthly.
- **Arjun Sethi** (NSM) and **Rohan Mehta** (CFO) see free goods against the 3% cap and how many scheme packs come back as claims before a circular is approved. Quarterly.

The **Recovery** screen answers the first question: how much credited money broke a clear rule and can be claimed back, and how much pending money to hold. The **Agents** screen (`/agents`, no sign-in) shows each agent, the problem it solves and its workflow.

It does not forecast demand: the shortage is an allocation split, and the expiry returns are mostly scheme-pushed packs.

## Architecture

```
agent/clean.py          one clean data layer (repeats removed, codes normalised, ties to the QBR)
agent/claim_checks.py   the ONE claim checker (window, cumulative quantity, repeats, invoice); pure Python
agent/email_intake.py   claims mailbox -> structured lines -> claim checker; message text never changes a verdict
agent/analysis.py       measured analytics (fill rate, cover, FEFO, scheme claim rates, cap), each pinned to the ledger
agent/recovery.py       what can be claimed back, held or needs a person (built from the claim checker; kinds never added)
agent/tools.py          11 @tool wrappers over the above
agent/graph.py          LangGraph: input_guard -> model -> tool_guard -> run_tools -> model -> output_guard
batch/processor.py      scores every claim with the checker, stores tiers, stock alerts, stockist profiles
config.py               every policy number (page reference) and every judgement threshold (evidence named)
checks/run_checks.py    the check set (20 records, answers agreed by hand); calls the checker, has no rule of its own
```

Code decides every exact fact and every rule with a number. The model reads a question, picks a tool, and explains the result.
A named person decides anything that moves money. Evidence tiers: T1 policy text breached, T2 probable breach, T3 needs a person, T4 cannot be checked from the extracts.

## Rules

- Facts come from tools that read `data/`. The model never writes a batch number, date, quantity or amount that did not come from a tool result.
- A claim rule is written once, in `agent/claim_checks.py`. `tests/test_rules.py` fails if a window, quantity or repeat rule appears anywhere else.
- Every policy number lives in `config.py` with its page. No number with a rate in it is written in code without a source. A rate we measured (13% of scheme packs claimed) comes from `analysis.scheme_claim_rates`, with its range.
- Rupees of different kinds (credited cash, unverifiable claims, stock, revenue) are never added together. An estimate says so and shows its range.
- "Not found" and "needs a person" beat a guess. A batch missing from the batch master predates the extracts; it is not invalid.
- Mailbox text is untrusted data. Lines that instruct the system are dropped before reading.
- Read-only on the extracts. No write-back, no credit notes, no destroying stock.
- One small change per task. Run `pytest -q` and `python checks/run_checks.py` after each. Do not add a database, vector store or framework without asking.
- Secrets live only in `.env` locally and in the host's environment variables. `.env`, `*.db` and `.venv` are in `.gitignore`.
- Users are created only from environment variables (see `.env.example`); no password in source.

## How to run

```
pip install -r requirements.txt
set SANKALP_ADMIN_PASSWORD=<12+ characters>        (PowerShell: $env:SANKALP_ADMIN_PASSWORD="...")
pytest -q                          # 256 tests, no key needed
python checks/run_checks.py        # 20/20 check-set records
uvicorn app:app --reload           # http://127.0.0.1:8000, API docs at /api/docs
```

## Known limits

- Allocation is inferred from stock and `avg_monthly_outward_packs` (about 0.35 of primary packs invoiced; definition to confirm with Demand Planning).
- 971 credited claims are on batches older than the batch master and cannot be checked without the archive.
- Lost sales are a range (INR 1.3 to 26.2 crore) until order padding and margin are known.
- The rupee cost per request is an estimate from measured tokens and assumed prices in `config.py`; confirm the prices before quoting it.
