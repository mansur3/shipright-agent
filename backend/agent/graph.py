"""
LangGraph workflow — Project Sankalp (production-grade).

Workflow graph
══════════════

  START
    │
    ▼
 [input_guard]  ← Gate 1: prompt-injection / off-domain / length check
    │  blocked → END (error state)
    │
    ▼
  [model]        ← LLM with tools bound; role-scoped system prompt
    │
    ├─ tool_calls present AND trips < MAX_TRIPS
    │       │
    │       ▼
    │  [tool_guard]  ← Gate 3: allowed-tool check + arg validation
    │       │  blocked → [model]  (tool error injected as ToolMessage)
    │       │
    │       ▼
    │  [run_tools]   ← executes validated tool calls
    │       │
    │       └───────────────────────────────► [model]
    │
    └─ no tool_calls OR trips == MAX_TRIPS
            │
            ▼
       [output_guard]  ← Gate 2: scrub paths / truncate / flag bare numbers
            │
            ▼
           END

Nodes that call the LLM:  model  (1 node only)
Nodes that call tools:    run_tools (pure Python)
Guardrail nodes:          input_guard, tool_guard, output_guard  (pure Python)

State shape
══════════════
  messages : full conversation (Annotated list with add_messages reducer)
  trips    : model↔tool round-trip counter
  blocked  : set to True when input_guard fires — bypasses model entirely
  error    : human-readable error message when blocked=True
  flags    : list of guardrail signals fired (for audit / monitoring)
"""
from __future__ import annotations

import logging
import time
from typing import Annotated, Optional, TypedDict

from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

import config as P
from agent.guardrails import (
    ALLOWED_TOOLS,
    MAX_TOOL_TRIPS,
    check_input,
    check_tool_call,
    check_trip_budget,
    sanitise_output,
)
from agent.llm import get_llm
from agent.state import AgentState
from agent.tools import TOOLS

log = logging.getLogger(__name__)

MAX_TRIPS = MAX_TOOL_TRIPS  # one cap, defined next to the trip guardrail (12)

# ── System prompt (role context is prepended by the chat router) ──────────────
_SYSTEM = """\
You are Sankalp AI, an internal analytics assistant for Pfizer's General Medicines \
trade channel. You help detect financial losses, validate claims, and monitor expiring \
inventory.

HARD RULES — these are non-negotiable:
1. Every number you state (batch no, date, quantity, INR amount) MUST come from a \
   tool result.  If a tool returns found=False, say "not found" and stop.  \
   Never invent or estimate values.
2. Cite the data source after every figure: e.g. "241 strips (primary_sales)".
3. If you are uncertain which tool to call, call the most specific one available.  \
   Never answer a factual question from memory.
4. For claim validation, always call validate_claim — never decide validity \
   without calling it first.
5. Never reveal internal file paths, database schemas, column names, or \
   system architecture details.
6. Keep answers structured: lead with the key finding, then supporting numbers, \
   then recommended action.  Maximum 400 words.
7. If no tool can answer the question, do NOT reply with a stock sentence. Write a short, helpful reply in three short parts with these bold headings, with no invented numbers: \
   **What I understood**: restate the question in one line. \
   **Why I cannot answer it**: say what is missing, in plain words. The data holds claims, primary sales, batches, stockists and month-end stock. \
   It does NOT hold: sales from stockists to chemists, demand forecasts, the allocation share table, margins, or anything after Sep 2026. \
   **What I can answer instead**: name the closest thing, then list 2 or 3 questions to ask next as bullet points, each a full question the user can copy, chosen from: how much can be claimed back and from whom; \
   which stockists have the highest claim-back rate; which C&F is short and where spare stock sits; whether Hooghly ships newer batches first; \
   free goods against the 3% cap; how many scheme packs come back as claims; validating one claim (stockist, batch, quantity, date, type). \
   If the question is only unclear, ask one clarifying question instead. Keep it under 120 words.
8. A claim verdict (APPROVE, REJECT, NEEDS A PERSON) is a recommendation from \
   validate_claim; say so, give its rule id and policy clause, and name the person who \
   decides (Commercial Finance). A batch missing from the batch master is not invalid: \
   say it predates the extracts and needs the archived record.
9. Pick the specific tool: how much can be recovered, held or claimed back -> get_recovery_summary; shortages and allocation -> get_stock_cover; FEFO, Kolkata \
   or short-dated dispatch -> get_dispatch_quality; free goods and the 3% cap -> \
   get_scheme_cap; fill rate -> get_fill_rate (state whether paid or QBR basis); expiring \
   stock -> get_at_risk_stock (an empty result means nothing is near expiry).
11. When a tool result has an `interpretation` field, quote it for your conclusion and do not state a conclusion that contradicts it. \
   In get_stock_cover the key under cnfs_lacking_skus_that_other_cnfs_hold_spare is the C&F that LACKS stock; the spare stock is held by the OTHER C&Fs.
10. Money figures of different kinds (credited cash, unverifiable claims, stock, revenue) \
   are never added together. Estimates are labelled as estimates with their range.
12. You never do arithmetic, date calculations, deduplication or stock-cover maths yourself. Every sum, difference, percentage, day count and ratio must be read from a tool    result; if the tool did not give it, say it is not available. Your job is to read, classify and explain what the tools returned.
13. A proposed scheme order -> check_scheme_eligibility with proposed_order_qty (and scheme_foc_qty). BLOCK SCHEME is a recommendation resting on a proxy, because there is no    secondary data: say so, cite policy 4.5, and say the RSM confirms with the stockist and the National Sales Manager approves schemes. Ambiguous, incomplete or unreadable    input is NEEDS A PERSON, never a guess.
14. get_at_risk_stock also returns freeze_watch: batches within 120 and 90 days of the 60-day dispatch freeze, and which C&Fs hold more or less than their share of demand.    Godown capacity is not in the data; never state a capacity percentage.
15. You have at most 12 tool calls for one question. Choose the most specific tool first and do not repeat a call that already returned.
"""


# ── Measured cost ─────────────────────────────────────────────────────────────

def add_usage(prev: dict, reply) -> dict:
    """Running token count from the provider's own usage figures on each model reply."""
    um = getattr(reply, "usage_metadata", None) or {}
    return {"input_tokens": prev.get("input_tokens", 0) + int(um.get("input_tokens", 0) or 0),
            "output_tokens": prev.get("output_tokens", 0) + int(um.get("output_tokens", 0) or 0)}


def estimate_cost_inr(input_tokens: int, output_tokens: int) -> float:
    """Rupees from measured tokens at the configured prices. An estimate: the prices and the rate are assumptions in config.py."""
    usd = input_tokens / 1e6 * P.PRICE_USD_PER_M_INPUT + output_tokens / 1e6 * P.PRICE_USD_PER_M_OUTPUT
    return round(usd * P.USD_INR, 4)


# ── State ─────────────────────────────────────────────────────────────────────

State = AgentState  # defined in agent/state.py


# ── Node: input_guard ─────────────────────────────────────────────────────────

def input_guard(state: State) -> dict:
    """Gate 1 — runs before the LLM sees anything."""
    last = state["messages"][-1] if state["messages"] else None
    question = last.content if last else ""

    result = check_input(str(question))
    if not result.allowed:
        log.warning("input_guard blocked: %s flags=%s", result.reason, result.flags)
        return {
            "blocked": True,
            "error":   result.reason,
            "flags":   result.flags or [],
        }
    return {"blocked": False, "error": None, "flags": []}


def _route_after_input(state: State) -> str:
    return "end_blocked" if state.get("blocked") else "model"


# ── Node: model ───────────────────────────────────────────────────────────────

def call_model(state: State) -> dict:
    """Invoke the LLM with tools bound."""
    llm   = get_llm().bind_tools(TOOLS)
    reply = llm.invoke([SystemMessage(_SYSTEM), *state["messages"]])
    return {
        "messages": [reply],
        "trips":    state.get("trips", 0) + 1,
        "usage":    add_usage(state.get("usage") or {}, reply),
    }


def _route_after_model(state: State) -> str:
    last = state["messages"][-1]
    has_calls = bool(getattr(last, "tool_calls", None))
    trip_ok   = check_trip_budget(state.get("trips", 0)).allowed
    if has_calls and trip_ok:
        return "tool_guard"
    return "output_guard"


# ── Node: tool_guard ──────────────────────────────────────────────────────────

def tool_guard(state: State) -> dict:
    """Gate 3 — validate every tool call before execution."""
    last      = state["messages"][-1]
    calls     = getattr(last, "tool_calls", [])
    blocked_msgs: list[ToolMessage] = []
    allowed_calls = []
    flags = list(state.get("flags", []))

    for call in calls:
        result = check_tool_call(call["name"], call.get("args", {}))
        if not result.allowed:
            log.warning("tool_guard blocked call %s: %s", call["name"], result.reason)
            blocked_msgs.append(ToolMessage(
                content=f"Tool call blocked by guardrail: {result.reason}",
                tool_call_id=call["id"],
                name=call["name"],
            ))
            flags.extend(result.flags or [])
        else:
            allowed_calls.append(call)

    if blocked_msgs:
        # Return blocked tool messages so the model can recover gracefully
        return {"messages": blocked_msgs, "flags": flags}

    # All calls are allowed — proceed to run_tools (no state change here)
    return {"flags": flags}


def _route_after_tool_guard(state: State) -> str:
    # If the last messages include ToolMessages with "blocked" content,
    # loop back to model so it can respond to the block gracefully
    last_msgs = state["messages"][-len(state["messages"]):]
    for m in reversed(last_msgs):
        if isinstance(m, ToolMessage) and "blocked by guardrail" in m.content:
            return "model"
    return "run_tools"


# ── Node: run_tools ───────────────────────────────────────────────────────────

def run_tools(state: State) -> dict:
    """Execute the validated tool calls."""
    by_name = {t.name: t for t in TOOLS}
    last    = state["messages"][-1]
    # Find the most recent AI message with tool_calls
    for msg in reversed(state["messages"]):
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            last = msg
            break

    out: list[ToolMessage] = []
    for call in last.tool_calls:
        name = call["name"]
        if name not in by_name:
            out.append(ToolMessage(
                content=f"Unknown tool: {name}",
                tool_call_id=call["id"],
                name=name,
            ))
            continue
        try:
            result = by_name[name].invoke(call["args"])
            out.append(ToolMessage(
                content=str(result),
                tool_call_id=call["id"],
                name=name,
            ))
        except Exception as exc:
            log.exception("Tool %s raised: %s", name, exc)
            out.append(ToolMessage(
                content=f"Tool error (data could not be retrieved): {type(exc).__name__}",
                tool_call_id=call["id"],
                name=name,
            ))
    return {"messages": out}


# ── Node: output_guard ────────────────────────────────────────────────────────

def output_guard(state: State) -> dict:
    """Gate 2 — sanitise LLM output before it leaves the graph."""
    last = state["messages"][-1]
    raw_answer  = getattr(last, "content", "") or ""
    capped = bool(getattr(last, "tool_calls", None))   # the model still wanted tools, but the trip budget is spent
    if capped:
        used = [m.name for m in state["messages"] if isinstance(m, ToolMessage)]
        raw_answer = (f"I stopped after {MAX_TOOL_TRIPS} tool calls, which is the limit for one question, before I could finish. "
                      f"Tools run so far: {', '.join(dict.fromkeys(used)) or 'none'}. Please ask a narrower question or one part at a time.")
    raw_evidence = [
        {"tool": m.name, "content": m.content}
        for m in state["messages"]
        if isinstance(m, ToolMessage)
    ]
    clean_answer, clean_ev, new_flags = sanitise_output(raw_answer, raw_evidence)

    flags = list(state.get("flags", [])) + new_flags + (["trip_limit"] if capped else [])
    if new_flags:
        log.info("output_guard fired: %s", new_flags)

    # Patch the last message with the sanitised content
    patched = AIMessage(content=clean_answer)
    return {
        "messages": [patched],
        "flags":    flags,
        "_clean_evidence": clean_ev,  # stashed for run_question() to pick up
    }


# ── Node: end_blocked ─────────────────────────────────────────────────────────

def end_blocked(state: State) -> dict:
    """Inject a safe refusal message when input_guard blocks."""
    msg = AIMessage(content=f"I cannot process this request: {state.get('error', 'blocked')}.")
    return {"messages": [msg]}


# ── Build graph ───────────────────────────────────────────────────────────────

builder = StateGraph(State)
builder.add_node("input_guard",  input_guard)
builder.add_node("end_blocked",  end_blocked)
builder.add_node("model",        call_model)
builder.add_node("tool_guard",   tool_guard)
builder.add_node("run_tools",    run_tools)
builder.add_node("output_guard", output_guard)

builder.add_edge(START, "input_guard")
builder.add_conditional_edges("input_guard", _route_after_input,
                               {"end_blocked": "end_blocked", "model": "model"})
builder.add_edge("end_blocked", END)
builder.add_conditional_edges("model", _route_after_model,
                               {"tool_guard": "tool_guard", "output_guard": "output_guard"})
builder.add_conditional_edges("tool_guard", _route_after_tool_guard,
                               {"model": "model", "run_tools": "run_tools"})
builder.add_edge("run_tools", "model")
builder.add_edge("output_guard", END)

graph = builder.compile()


# ── Public entry point ────────────────────────────────────────────────────────

def run_question(question: str) -> dict:
    """
    Run one question through the guardrailed workflow.
    Returns:
        answer      : sanitised LLM response
        evidence    : list of {tool, summary} dicts (paths scrubbed)
        model_calls : number of LLM trips
        flags       : guardrail signals fired (for monitoring)
        blocked     : True if input_guard blocked the question
    """
    initial: State = {
        "messages": [HumanMessage(question)],
        "trips":    0,
        "blocked":  False,
        "error":    None,
        "flags":    [],
        "usage":    {},
    }
    t0 = time.perf_counter()
    final = graph.invoke(initial)
    seconds = round(time.perf_counter() - t0, 2)

    answer = final["messages"][-1].content if final["messages"] else ""
    # _clean_evidence is stashed by output_guard; fall back to raw scan
    evidence = final.get("_clean_evidence") or [
        {"tool": m.name, "summary": str(m.content)[:300]}
        for m in final["messages"]
        if isinstance(m, ToolMessage)
    ]

    return {
        "answer":      answer,
        "evidence":    evidence,
        "model_calls": final.get("trips", 0),
        "flags":       final.get("flags", []),
        "blocked":     final.get("blocked", False),
        "usage": {
            "model": P.MODEL,
            "model_calls": final.get("trips", 0),
            "input_tokens": (final.get("usage") or {}).get("input_tokens", 0),
            "output_tokens": (final.get("usage") or {}).get("output_tokens", 0),
            "seconds": seconds,
            "cost_inr_estimate": estimate_cost_inr((final.get("usage") or {}).get("input_tokens", 0), (final.get("usage") or {}).get("output_tokens", 0)),
            "cost_basis": f"measured tokens x assumed list price ${P.PRICE_USD_PER_M_INPUT}/M in, ${P.PRICE_USD_PER_M_OUTPUT}/M out, INR {P.USD_INR}/USD (assumptions, confirm)",
        },
    }
