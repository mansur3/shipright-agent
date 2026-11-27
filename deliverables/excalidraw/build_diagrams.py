"""Builds the five Sankalp Agent architecture diagrams as editable Excalidraw files.
Everything drawn here is read from the code as implemented (see MULTI_AGENT_ARCHITECTURE_AUDIT.md); figures come from the live
opportunity register so the diagrams, the app and the deck agree.

Run from ShipRight_Agent:  backend\\.venv\\Scripts\\python.exe deliverables\\excalidraw\\build_diagrams.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(APP / "backend"))
from xl import Scene  # noqa: E402
from agent import opportunities  # noqa: E402

REG = opportunities.build()
H = REG["headline"]
OPP = {o["id"]: o for o in REG["opportunities"]}


def inr(v):
    return f"INR {v / 1e7:.2f} cr" if v >= 1e7 else f"INR {v / 1e5:.2f} L"


# ───────────────────────────────────────────── 1. system architecture
def d1():
    s = Scene(1)
    s.title(40, 24, "1. Sankalp Agent: overall system architecture", "Original client data -> clean data layer -> 7 agents and code engines -> validation -> API -> dashboard -> named decision maker")
    # column 1: data
    s.box("d1", 40, 130, 300, 190, "data", "Client data pack (7 CSVs, read-only)",
          "primary_sales 93,809 rows\nexpiry_claims 4,526\nbatch_master 663\ncnf_stock_snapshot 5,015\nsku_master 36 · stockist_master 156\nclaim_emails 30", label="DATA SOURCE")
    s.box("d2", 40, 350, 300, 130, "data", "Policy and context PDFs",
          "CO-POL-014 trade terms and returns, C&F SOP, QBR pack, interviews. Policy numbers are copied into config.py with their page.", label="DATA SOURCE")
    # column 2: ingestion + storage
    s.box("i1", 400, 130, 290, 190, "orch", "Ingestion and cleaning (code)",
          "data_loader.py + clean.py. Drops 746 repeated sales rows and 23 repeated claims, normalises codes and dates, sums split stock rows. Ties to the QBR. Raw files are never edited.", label="ORCHESTRATION")
    s.box("i2", 400, 350, 290, 130, "data", "SQLite (SQLModel)",
          "users, claims filed, claim chat, batch run results, audit log", label="STORAGE")
    s.box("i3", 400, 510, 290, 120, "data", "config.py",
          "Every policy number with its page; every judgement threshold with the evidence named", label="STORAGE")
    # column 3: backend
    s.box("b1", 750, 130, 330, 230, "orch", "FastAPI backend (app.py)",
          "Routers: analytics, claims, chat, admin, auth. JWT and 6 roles, rate limits, audit log. Serves the static frontend from the same app. Returns latency, tools called and model calls on code-only endpoints.", label="ORCHESTRATION")
    s.box("b2", 750, 390, 330, 140, "orch", "Batch processor (admin run)",
          "batch/processor.py scores all 4,503 claims with the claim checker; stores tiers, stock alerts and stockist profiles", label="ORCHESTRATION")
    s.box("b3", 750, 560, 330, 150, "ok", "Opportunity Register (code, no model)",
          "agent/opportunities.py -> /api/analytics/opportunities. 10 opportunities in 7 classes; classes are never added together.", label="VALIDATED OUTPUT")
    # column 4: agents
    s.text(1140, 108, "Agent layer: 7 agents, no central LLM orchestrator", 14, "#6741d9")
    names = [("ag1", "Claim Gatekeeper", "CODE ONLY · claim_checks.py"), ("ag2", "Claims Mailbox Triage", "CODE ONLY · email_intake.py"),
             ("ag3", "Recovery Analyst (batch)", "CODE ONLY · recovery.py"), ("ag4", "Claims Intake Assistant", "CODE + MODEL · claims_graph.py"),
             ("ag5", "Ask Analyst", "MODEL + 11 TOOLS · graph.py"), ("ag6", "Supply and FEFO Watcher", "CODE ONLY · analysis.py"),
             ("ag7", "Scheme Order Gate", "CODE ONLY · analysis.py")]
    for i, (k, n, sub) in enumerate(names):
        s.box(k, 1140, 130 + i * 92, 380, 78, "agent", n, sub, tsize=15, bsize=11)
    s.box("v1", 1140, 790, 380, 200, "ok", "Validation layer (code)",
          "Input, tool and output guardrails · 12-trip cap · numeric grounding check on every Ask answer · reply-wording number guard · evidence tiers T1 to T4 · 20-record check set (20/20) · independent source reconciliation (23/23) · 298 backend tests", label="VALIDATION")
    s.box("x1", 1140, 1020, 380, 100, "ext", "OpenRouter LLM API", "gpt-4o-mini, temperature 0. Reads questions, picks tools, words replies. Never writes a figure.", label="EXTERNAL")
    # column 5: frontend + users
    s.box("f1", 1590, 130, 330, 430, "ok", "Executive dashboard (Next.js, static export)",
          "Recovery (headline)\nRecovery Register (evidence per opportunity)\nCheck a Claim\nRecovery List\nScheme Returns\nAllocation, FEFO, Cap\nAsk AI\nFile a Claim\nReview Queue (human decision)\nAgents (roles and workflows)\nAdmin", label="FRONTEND", bsize=13)
    s.box("u1", 1590, 600, 330, 170, "plain", "Business users",
          "Neha Bansal, Controller: claims, daily\nKavita Rao, Vaishali Kapoor: supply, monthly\nArjun Sethi, Rohan Mehta: schemes and cap, quarterly\nA named person decides every credit", label="BUSINESS USERS")
    # arrows
    s.arrow("d1", "i1", "reads")
    s.arrow("d2", "i3", "policy numbers", sa="right", sb="left", pts=[(340, 415), (370, 415), (370, 570), (400, 570)])
    s.arrow("i1", "b2", "clean data", sa="right", sb="left", pts=[(690, 225), (720, 225), (720, 460), (750, 460)])
    s.arrow("b2", "i2", None, sa="left", sb="right", pts=[(750, 440), (720, 440), (720, 415), (690, 415)])
    s.arrow("ag3", "b1", None, pts=[(1140, 360), (1125, 360), (1125, 230), (1080, 230)])
    s.arrow("b3", "b1", None, pts=[(1080, 635), (1095, 635), (1095, 300), (1080, 300)])
    s.arrow("b1", "f1", None, pts=[(1080, 150), (1100, 96), (1560, 96), (1560, 150), (1590, 150)])
    s.text(1566, 74, "JSON APIs", 11, "#495057")
    s.text(700, 100, "clean data is read by every agent", 11, "#495057")
    s.arrow("f1", "u1", "decisions", pts=[(1755, 560), (1755, 600)])
    s.arrow("ag5", "x1", None, dashed=True, pts=[(1520, 540), (1560, 540), (1560, 1070), (1520, 1070)])
    s.text(1565, 800, "question, reply", 11, "#495057")
    s.legend(40, 700)
    s.save(HERE / "01_system_architecture.excalidraw")


# ───────────────────────────────────────────── 2. multi-agent collaboration
def card(s, id, x, y, cls, name, kind, resp, inp, out, tools, up, down, w=450, h=250):
    body = f"Does: {resp}\nIn: {inp}\nOut: {out}\nTools: {tools}\nUpstream: {up}\nDownstream: {down}"
    s.box(id, x, y, w, h, cls, name, body, tsize=17, bsize=12, label=kind)


def d2():
    s = Scene(2)
    s.title(40, 24, "2. Multi-agent collaboration: the 7 implemented agents",
            "Collaboration is by plain function calls into shared, validated code. The only LLM agents are Ask Analyst and Claims Intake Assistant (two separate LangGraph graphs).")
    y1, y2 = 130, 500
    xs = [40, 530, 1020, 1510]
    card(s, "a1", xs[0], y1, "agent", "Claims Mailbox Triage", "CODE ONLY · backend/agent/email_intake.py",
         "turns free-text claim emails into structured lines and runs each through the checker; email text never changes a verdict",
         "claim_emails.csv (30 emails)", "claim lines + verdicts; INR 1.44 cr of credited claims that need a person",
         "none (pure Python)", "mailbox rule (stockist code)", "Claim Gatekeeper, then claims desk")
    card(s, "a2", xs[1], y1, "agent", "Claims Intake Assistant", "CODE + MODEL · backend/agent/claims_graph.py (LangGraph, 14 nodes)",
         "guides a claim filing: classify intent, collect fields, validate, check data, risk score, store",
         "chat message (create, status, recovery)", "claim_no + summary; reply wording by model, figures guarded",
         "claim checker, SQLite; model only for intent fallback and wording", "stockist or C&F user", "Claim Gatekeeper rules, SQLite, Review Queue (human)")
    card(s, "a3", xs[2], y1, "agent", "Recovery Analyst (batch)", "CODE ONLY · batch/processor.py, agent/recovery.py",
         "replays all 4,503 claims in date order and buckets credited and pending money",
         "cleaned claims and invoices", "T1, T2, hold, review, unverifiable buckets; by stockist; stored in SQLite",
         "claim checker", "Claim Gatekeeper rules", "Opportunity Register, Recovery page, Recovery List")
    card(s, "a4", xs[3], y1, "agent", "Ask Analyst", "MODEL + 11 TOOLS · backend/agent/graph.py (LangGraph)",
         "answers a leader's question with a sourced figure: input guard, model picks a tool, tool guard, tools, output guard (max 12 trips)",
         "question text (800 chars max)", "answer + evidence + flags + usage; ungrounded figures flagged",
         "11 read-only tools: lookup_batch, validate_claim, get_recovery_summary, get_stock_cover, get_dispatch_quality, get_scheme_cap, get_fill_rate, ...", "user, guardrails",
         "analysis and claim engines; OpenRouter gpt-4o-mini")
    card(s, "b1", xs[0], y2, "agent", "Claim Gatekeeper", "CODE ONLY · backend/agent/claim_checks.py (the one claim rule set)",
         "checks one claim: window, cumulative quantity, repeats, invoice; recommends APPROVE, REJECT or NEEDS A PERSON with clause and file lines",
         "stockist, batch, quantity, date, type", "verdict, tier T1 to T4, rule id, policy clause, evidence rows",
         "none (pure Python)", "Mailbox Triage, Intake Assistant, Recovery Analyst, Ask Analyst (validate_claim)", "Controller (Neha Bansal) decides")
    card(s, "b2", xs[1], y2, "ok", "Opportunity Register (new, not an agent)", "CODE ONLY · backend/agent/opportunities.py",
         f"lists every money finding with class, formula, evidence, owner, finding agent and a validated flag. Headline: {inr(H['credited_cash_to_review_inr'])} credited cash to review",
         "recovery.build, analysis functions", "10 opportunities, 7 classes, no cross-class total",
         "none", "Recovery Analyst, Supply and FEFO Watcher, Scheme Order Gate", "Recovery Register page, dashboard KPI")
    card(s, "b3", xs[2], y2, "agent", "Supply and FEFO Watcher", "CODE ONLY · backend/agent/analysis.py",
         "stock cover by C&F, spare stock elsewhere, FEFO breaches, short-dated dispatch, freeze watch",
         "cnf_stock_snapshot, primary_sales, batch_master", "cover months, shortage split, FEFO % per C&F",
         "none", "clean data layer", "Allocation, FEFO, Cap page; Ask tools; Opportunity Register")
    card(s, "b4", xs[3], y2, "agent", "Scheme Order Gate", "CODE ONLY · backend/agent/analysis.py",
         "tests free goods against the 3% cap, scheme claim rates, and a proposed scheme order against 2.5 months of stock",
         "quarter, SKU, proposed order", "cap status, claim rate, BLOCK SCHEME or not (proxy; RSM confirms)",
         "none", "clean data layer", "Scheme Returns page; Ask tools; Opportunity Register; RSM and NSM")
    s.arrow("a1", "b1", "calls checker")
    s.arrow("a2", "b1", "validates")
    s.arrow("a3", "b2", "buckets", pts=[(1245, 380), (1245, 440), (755, 440), (755, 500)])
    s.arrow("a4", "b3", "tool calls", pts=[(1735, 380), (1735, 440), (1245, 440), (1245, 500)], lx=-100)
    s.arrow("a4", "b4", None, pts=[(1850, 380), (1850, 500)])
    s.text(40, 780, "Reconciliation of disagreements: there is no agent-to-agent negotiation. Every rule is written once (claim_checks.py, enforced by tests/test_rules.py), so agents cannot disagree on a verdict.\n"
                    "No cross-agent LLM handoff exists. Cheapest-first routing: Intake Assistant tries keywords before it calls the model. Ask Analyst is capped at 12 tool trips.", 13, "#495057")
    s.legend(40, 850)
    s.save(HERE / "02_multi_agent_collaboration.excalidraw")


# ───────────────────────────────────────────── 3. end to end workflow
def d3():
    s = Scene(3)
    s.title(40, 24, "3. End-to-end business workflow: client data to business action",
            "Green = deterministic code. Purple = LLM-driven reasoning (words only; every figure comes from code).")
    s.text(40, 150, "DETERMINISTIC\nCODE", 14, "#2f9e44")
    s.text(40, 420, "LLM-DRIVEN\nREASONING", 14, "#6741d9")
    x0, w, g = 200, 215, 45
    top, bot = 140, 400
    steps = [
        ("w1", 0, "data", "1. Client data", "7 CSVs and policy PDFs. Read-only. Original files never changed.", top, "DATA"),
        ("w2", 1, "ok", "2. Analysis", "clean.py removes repeats, normalises codes, ties to QBR. analysis.py: fill rate, cover, FEFO, cap.", top, "CODE"),
        ("w3", 2, "agent", "3. Agent collaboration", "Gatekeeper, Mailbox Triage, Recovery Analyst, Supply and FEFO Watcher, Scheme Order Gate share one data layer. Ask Analyst and Intake Assistant add language.", bot, "AGENTS"),
        ("w4", 3, "ok", "4. Opportunity detection", "Claim tiers T1 to T4, 3% cap test, cover test, scheme claim rates.", top, "CODE"),
        ("w5", 4, "ok", "5. Financial validation", "Formulas in code. Independent reconciliation 23/23. Check set 20/20. Classes never added.", top, "CODE"),
        ("w6", 5, "ok", "6. Prioritisation", "Class, confidence, feasibility and priority 1 to 3 per opportunity.", top, "CODE"),
        ("w7", 6, "agent", "7. Recommendation", "Ask Analyst explains in plain words from tool results. Numeric grounding check flags unsupported figures.", bot, "LLM + GUARD"),
        ("w8", 7, "orch", "8. Business action", "A named person decides: Controller, Supply Chain, CFO or NSM. Review Queue records the decision.", top, "HUMAN"),
    ]
    for id_, i, cls, t, b, y, lab in steps:
        s.box(id_, x0 + i * (w + g), y, w, 210, cls, t, b, label=lab, tsize=16, bsize=12)
    for a, b in zip(("w1", "w2", "w3", "w4", "w5", "w6", "w7"), ("w2", "w3", "w4", "w5", "w6", "w7", "w8")):
        s.arrow(a, b)
    s.box("r1", 200, 700, 1000, 100, "risk", "Risks and limits stated on screen",
          "Allocation is inferred (share table not in the pack). 971 claims sit on batches older than the data and cannot be checked. Lost sales are a range, not a figure. Revenue opportunity is not cash.", label="RISK")
    s.box("o1", 1240, 700, 760, 100, "ok", "What the executive sees",
          f"{inr(H['credited_cash_to_review_inr'])} credited cash to review, {inr(H['cash_to_hold_inr'])} to hold, with the evidence and the owner of each.", label="BUSINESS OUTPUT")
    s.legend(40, 850)
    s.save(HERE / "03_end_to_end_workflow.excalidraw")


# ───────────────────────────────────────────── 4. financial recovery workflow
def d4():
    s = Scene(4)
    s.title(40, 24, "4. Financial recovery workflow", "How a suspected leak becomes a classified, validated, owned opportunity. Figures are live from the Opportunity Register.")
    w, g = 300, 40
    xs = [40 + i * (w + g) for i in range(5)]
    chain = [
        ("c1", "ag", "1. Identified leakage", "A credited claim, a pending claim, free goods over cap, stock in the wrong place", "agent"),
        ("c2", "ev", "2. Evidence collection", "Claim line, invoice line, batch expiry, supply to that stockist: file and line kept", "data"),
        ("c3", "fc", "3. Financial calculation", "Formula in code, e.g. credit INR if late; excess packs x PTS if over supply. No model-written figures.", "ok"),
        ("c4", "va", "4. Validation", "Evidence tier T1 to T4. Independent stdlib recomputation from the CSVs: 23 of 23 agree. Check set 20 of 20.", "ok"),
        ("c5", "cl", "5. Classification", "Confirmed leakage, potentially recoverable, cost avoidance, cost saving, revenue opportunity, risk, exposure", "orch"),
    ]
    for i, (id_, _, t, b, cls) in enumerate(chain):
        s.box(id_, xs[i], 130, w, 190, cls, t, b)
    for a, b in zip(("c1", "c2", "c3", "c4"), ("c2", "c3", "c4", "c5")):
        s.arrow(a, b)
    s.line([(xs[4] + w / 2, 320), (xs[4] + w / 2, 372), (xs[0] + w / 2, 372)], color="#495057", dashed=False, width=2)
    s.text(40, 335, "Classes are different kinds of money and are never added together.", 14, "#e03131")
    outs = [
        ("o1", "ok", "Confirmed leakage (T1)", f"{inr(H['confirmed_leakage_inr'])}\n{OPP['OPP-01']['claims']} credited claims broke policy text", "OPP-01"),
        ("o2", "ok", "Potentially recoverable (T2)", f"{inr(H['potentially_recoverable_inr'])}\n{OPP['OPP-02']['claims']} credited claims, probable breach; owner confirms", "OPP-02"),
        ("o3", "ok", "Cost avoidance: hold now", f"{inr(H['cash_to_hold_inr'])}\n{OPP['OPP-03']['claims']} pending claims that fail a rule", "OPP-03"),
        ("o4", "data", "Cost saving and revenue opportunity (not cash)", f"Free goods over cap {inr(OPP['OPP-04']['amount_inr'])}; scheme returns above target {inr(OPP['OPP-05']['amount_inr'])}; reallocation {inr(OPP['OPP-06']['amount_inr'])} at PTS", "OPP-04 to 06"),
        ("o5", "risk", "Risk and exposure (not sized as recovery)", f"Needs a person {inr(OPP['OPP-08']['reference_inr'])}; unverifiable {inr(OPP['OPP-09']['reference_inr'])}; FEFO and short-dated dispatch", "OPP-07 to 10"),
    ]
    for i, (id_, cls, t, b, lab) in enumerate(outs):
        s.box(id_, xs[i], 400, w, 190, cls, t, b, label=lab)
        s.free_arrow([(xs[i] + w / 2, 372), (xs[i] + w / 2, 400)])
    s.box("p1", 40, 650, 1660, 80, "orch", "6. Prioritisation",
          "Priority 1: claim control (OPP-01, OPP-03) and scheme-pushed returns (OPP-05). Priority 2: potentially recoverable, free goods cap, reallocation. Priority 3: FEFO, dispatch, review and data requests.")
    for i in range(5):
        s.free_arrow([(xs[i] + w / 2, 590), (xs[i] + w / 2, 650)])
    s.box("p2", 40, 780, 820, 130, "agent", "7. Recommended action (named owner)",
          "Controller: raise set-off on T1, confirm T2, hold pending. CFO and NSM: scheme circular within the 3% cap. Supply Chain: reallocate spare stock, raise Kolkata FEFO. The model explains; a person decides.")
    s.box("p3", 880, 780, 820, 130, "ok", "8. Expected outcome",
          f"Up to {inr(H['credited_cash_to_review_inr'])} of past credits reviewed for set-off (about {inr(H['credited_cash_to_review_inr'] / 2.5)} a year), {inr(H['cash_to_hold_inr'])} not paid out. Cost and revenue items are targets, not recovered cash.")
    s.arrow("p1", "p2", None, pts=[(450, 730), (450, 780)])
    s.arrow("p2", "p3")
    s.legend(40, 950)
    s.save(HERE / "04_financial_recovery_workflow.excalidraw")


# ───────────────────────────────────────────── 5. execution sequence
def d5():
    s = Scene(5)
    s.title(40, 24, "5. Agent execution sequence (as implemented)",
            "Strictly sequential. No agents run in parallel; tool calls inside one model reply run one after another. Human approval is only at the Review Queue.")
    lanes = [("User", 90, "plain"), ("Frontend", 330, "ok"), ("FastAPI", 570, "orch"), ("LangGraph agent", 810, "agent"), ("Guardrails", 1050, "ok"),
             ("Tools and claim checker", 1290, "ok"), ("LLM (OpenRouter)", 1530, "ext"), ("SQLite", 1770, "data"), ("Human decider", 2010, "orch")]
    X = {}
    for i, (n, x, cls) in enumerate(lanes):
        s.box(f"L{i}", x - 95, 130, 190, 50, cls, n, "", tsize=14)
        s.line([(x, 180), (x, 1560)])
        X[n] = x
    y = 215

    def sec(label, cls_color):
        nonlocal y
        s.text(20, y - 8, label, 15, cls_color)
        y += 26

    def msg(a, b, label, dashed=False, color="#495057"):
        nonlocal y
        xa, xb = X[a], X[b]
        s.free_arrow([(xa, y + 14), (xb, y + 14)], None, color=color, dashed=dashed)
        lo, hi = sorted((xa, xb))
        s.text((lo + hi) / 2 - (len(label) * 11 * 0.52) / 2, y - 6, label, 11, color, align="center", w=len(label) * 11 * 0.52 + 6)
        y += 38

    sec("A. Check a claim (no model call): POST /api/audit-claim", "#2f9e44")
    msg("User", "Frontend", "fill the claim form")
    msg("Frontend", "FastAPI", "POST /api/audit-claim (JWT)")
    msg("FastAPI", "Tools and claim checker", "claim_checks: window, quantity, repeats, invoice")
    msg("Tools and claim checker", "FastAPI", "verdict + tier + clause + file lines", dashed=True)
    msg("FastAPI", "Frontend", "recommendation (latency, tools, model_calls = 0)", dashed=True)
    msg("Frontend", "Human decider", "Commercial Finance decides the credit", color="#e8590c")
    y += 14
    sec("B. Ask Analyst: POST /api/chat/ask (sequential, at most 12 model trips)", "#6741d9")
    msg("User", "Frontend", "type a question")
    msg("Frontend", "FastAPI", "POST /api/chat/ask (role check, rate limit)")
    msg("FastAPI", "LangGraph agent", "run_question")
    msg("LangGraph agent", "Guardrails", "input_guard: injection, off-domain, length")
    msg("LangGraph agent", "LLM (OpenRouter)", "model call: pick one tool", color="#6741d9")
    msg("LangGraph agent", "Guardrails", "tool_guard: allow-list, args, trip budget")
    msg("LangGraph agent", "Tools and claim checker", "run_tools (one after another)")
    msg("Tools and claim checker", "LangGraph agent", "tool result (code-calculated)", dashed=True)
    s.text(830, y - 8, "repeat model <-> tools until an answer, max 12 trips", 11, "#e8590c")
    y += 26
    msg("LangGraph agent", "LLM (OpenRouter)", "model call: explain the result", color="#6741d9")
    msg("LangGraph agent", "Guardrails", "output_guard: scrub + numeric grounding check")
    msg("LangGraph agent", "FastAPI", "answer + evidence + flags + usage", dashed=True)
    msg("FastAPI", "SQLite", "audit log (question truncated)")
    msg("FastAPI", "Frontend", "answer shown with ungrounded-figure warning if any", dashed=True)
    y += 14
    sec("C. Recovery batch (admin only): POST /api/admin/run-batch", "#e8590c")
    msg("Frontend", "FastAPI", "run batch (admin)")
    msg("FastAPI", "Tools and claim checker", "score all 4,503 claims with the claim checker")
    msg("Tools and claim checker", "SQLite", "store tiers, stock alerts, stockist profiles")
    msg("FastAPI", "Frontend", "dashboard reads /recovery and /opportunities (computed by code)", dashed=True)
    y += 14
    sec("D. Human approval: Review Queue", "#e8590c")
    msg("Human decider", "Frontend", "approve or reject a filed claim", color="#e8590c")
    msg("Frontend", "FastAPI", "POST /api/claims/{id}/review")
    msg("FastAPI", "SQLite", "decision + reviewer + audit log")
    s.box("n1", 1400, 1380, 560, 130, "risk", "Not implemented (documented honestly)",
          "No parallel agent execution. No cross-agent LLM handoff. No automatic credit, recovery or set-off: every money decision waits for a named person.", label="LIMITS")
    s.legend(40, 1380)
    s.save(HERE / "05_agent_execution_sequence.excalidraw")


if __name__ == "__main__":
    for f in (d1, d2, d3, d4, d5):
        f()
        print("built", f.__name__)
