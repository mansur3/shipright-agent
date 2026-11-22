/**
 * The agents in Sankalp, each with the problem it solves and its workflow.
 * Every figure is from verification/05_findings_ledger.md. Nodes mirror the real code (file named per agent).
 */
export type NodeKind = "input" | "code" | "model" | "tool" | "branch" | "person" | "output";

export interface FlowNode {
  id: string;
  kind: NodeKind;
  title: string;
  col: number;
  row: number;
  rows?: { label: string; chip?: string }[];
  chip?: string; // e.g. model name
}

export interface FlowEdge {
  from: string;
  to: string;
  label?: string;
  loop?: boolean | number; // drawn as an arc below the row; a number sets how deep it dips (px)
}

export interface Agent {
  id: string;
  name: string;
  kind: "Model + tools" | "Code only" | "Code + model";
  problem: string;
  evidence: string;
  money: string;
  user: string;
  file: string;
  page: string;
  nodes: FlowNode[];
  edges: FlowEdge[];
}

export const AGENTS: Agent[] = [
  {
    id: "gatekeeper",
    name: "Claim Gatekeeper",
    kind: "Code only",
    problem:
      "Claims are credited with no history check: the same stockist, batch and quantity is credited twice, claims arrive late, and quantities exceed what was ever supplied. Finance verifies the paperwork, not the history.",
    evidence: "INR 51.5 L credited against clear policy rules in 30 months; 61 exact repeats worth INR 11.1 L; 69 pending claims fail a rule today (INR 21.0 L).",
    money: "Stops new leakage before the credit note (hold) and lists what to claim back (recover).",
    user: "Neha Bansal, Controller, daily",
    file: "backend/agent/claim_checks.py",
    page: "/gatekeeper",
    nodes: [
      { id: "in", kind: "input", title: "Claim", col: 0, row: 1.5, rows: [{ label: "stockist" }, { label: "batch, SKU" }, { label: "qty, date, type" }, { label: "invoice ref" }] },
      { id: "clean", kind: "code", title: "Normalise", col: 1, row: 1.5, rows: [{ label: "codes, hyphens", chip: "Python" }] },
      { id: "w", kind: "code", title: "Window", col: 2, row: 0, rows: [{ label: "7 d / 90 d (5.2)", chip: "Rule" }] },
      { id: "q", kind: "code", title: "Quantity vs supply", col: 2, row: 1, rows: [{ label: "cumulative (5.5)", chip: "Rule" }] },
      { id: "r", kind: "code", title: "Repeats", col: 2, row: 2, rows: [{ label: "exact / partial", chip: "Rule" }] },
      { id: "i", kind: "code", title: "Invoice and batch", col: 2, row: 3, rows: [{ label: "ref (5.4), master", chip: "Rule" }] },
      { id: "tier", kind: "code", title: "Evidence tier", col: 3, row: 1.5, rows: [{ label: "T1 T2 T3 T4 CLEAN" }] },
      { id: "v", kind: "branch", title: "Verdict", col: 4, row: 1.5 },
      { id: "ap", kind: "output", title: "APPROVE", col: 5, row: 0.3, rows: [{ label: "recommend credit" }] },
      { id: "rj", kind: "output", title: "REJECT", col: 5, row: 1.5, rows: [{ label: "clause + records" }] },
      { id: "np", kind: "output", title: "NEEDS A PERSON", col: 5, row: 2.7, rows: [{ label: "reason named" }] },
      { id: "p", kind: "person", title: "Controller decides", col: 6, row: 1.5, rows: [{ label: "raises the credit note" }] },
    ],
    edges: [
      { from: "in", to: "clean" }, { from: "clean", to: "w" }, { from: "clean", to: "q" }, { from: "clean", to: "r" }, { from: "clean", to: "i" },
      { from: "w", to: "tier" }, { from: "q", to: "tier" }, { from: "r", to: "tier" }, { from: "i", to: "tier" },
      { from: "tier", to: "v" }, { from: "v", to: "ap", label: "clean" }, { from: "v", to: "rj", label: "breach" }, { from: "v", to: "np", label: "unsure" },
      { from: "ap", to: "p" }, { from: "rj", to: "p" }, { from: "np", to: "p" },
    ],
  },
  {
    id: "mailbox",
    name: "Claims Mailbox Triage",
    kind: "Code only",
    problem:
      "Claims arrive as free-text emails, some with no invoice, some with typos in the batch number, some saying 'pre-approved, skip checks'. Approvals are given by one-word replies.",
    evidence: "INR 1.44 cr of credited claims need a person (partial repeats INR 62.2 L, no invoice reference INR 81.8 L). Email text never changes a verdict.",
    money: "Catches repeats and over-claims at the inbox, before anyone replies.",
    user: "Commercial Finance claims desk, daily",
    file: "backend/agent/email_intake.py",
    page: "/gatekeeper",
    nodes: [
      { id: "in", kind: "input", title: "Mailbox message", col: 0, row: 1, rows: [{ label: "sender" }, { label: "subject, body" }] },
      { id: "strip", kind: "code", title: "Drop instructions", col: 1, row: 1, rows: [{ label: "'pre-approved', 'skip checks'", chip: "Python" }] },
      { id: "read", kind: "code", title: "Read the lines", col: 2, row: 1, rows: [{ label: "batch, qty, invoice", chip: "Regex" }] },
      { id: "fix", kind: "code", title: "Typos and units", col: 3, row: 0.2, rows: [{ label: "suggest, never guess", chip: "Python" }] },
      { id: "sender", kind: "code", title: "Sender and repeats", col: 3, row: 1.8, rows: [{ label: "known stockist, line repeated" }] },
      { id: "gate", kind: "code", title: "Claim Gatekeeper", col: 4, row: 1, rows: [{ label: "same checker as the API" }] },
      { id: "out", kind: "output", title: "Recommendation per line", col: 5, row: 1, rows: [{ label: "APPROVE / REJECT / NEEDS A PERSON" }] },
      { id: "p", kind: "person", title: "Controller replies", col: 6, row: 1 },
    ],
    edges: [
      { from: "in", to: "strip" }, { from: "strip", to: "read" }, { from: "read", to: "fix" }, { from: "read", to: "sender" },
      { from: "fix", to: "gate" }, { from: "sender", to: "gate" }, { from: "gate", to: "out" }, { from: "out", to: "p" },
    ],
  },
  {
    id: "recovery",
    name: "Recovery Analyst (batch)",
    kind: "Code only",
    problem:
      "Nobody has a list of which already-credited claims broke a rule, how much, and from which stockist. Without it, no money can be claimed back.",
    evidence: "4,503 claims replayed against the claims before them: 2,081 approve, 575 reject, 1,847 to a person. INR 85.4 L cannot be checked (batches older than the extracts).",
    money: "Produces the recovery list: INR 51.5 L against clear rules, split by stockist and tier.",
    user: "Rohan Mehta (CFO) and Neha Bansal, monthly",
    file: "backend/batch/processor.py",
    page: "/dashboard",
    nodes: [
      { id: "in", kind: "input", title: "7 CSV extracts", col: 0, row: 1, rows: [{ label: "claims, sales" }, { label: "batches, stock" }] },
      { id: "clean", kind: "code", title: "Clean data", col: 1, row: 1, rows: [{ label: "746 repeats dropped", chip: "Python" }, { label: "ties to the QBR" }] },
      { id: "rep", kind: "code", title: "Replay every claim", col: 2, row: 1, rows: [{ label: "each vs claims before it", chip: "Checker" }] },
      { id: "tiers", kind: "code", title: "Tiers and rupees", col: 3, row: 0, rows: [{ label: "T1 T2 T3 T4, by kind" }] },
      { id: "stk", kind: "code", title: "Stockist profiles", col: 3, row: 1, rows: [{ label: "who to recover from" }] },
      { id: "stock", kind: "code", title: "Stock alerts", col: 3, row: 2, rows: [{ label: "latest month-end" }] },
      { id: "db", kind: "output", title: "Recovery list", col: 4, row: 1, rows: [{ label: "SQLite, CSV export" }] },
      { id: "p", kind: "person", title: "Controller recovers", col: 5, row: 1, rows: [{ label: "debit note or review" }] },
    ],
    edges: [
      { from: "in", to: "clean" }, { from: "clean", to: "rep" }, { from: "rep", to: "tiers" }, { from: "rep", to: "stk" }, { from: "rep", to: "stock" },
      { from: "tiers", to: "db" }, { from: "stk", to: "db" }, { from: "stock", to: "db" }, { from: "db", to: "p" },
    ],
  },
  {
    id: "intake",
    name: "Claims Intake Assistant",
    kind: "Code + model",
    problem:
      "Stockists and C&F agents file claims in many shapes: missing batch, no invoice, wrong quantity. Each gap costs days, and a late claim is resubmitted, so the same claim is logged twice.",
    evidence: "Credit notes take 45 days on average against a 30-day policy; 76% are over 30 days.",
    money: "Gets a complete, checked claim in one conversation, so fewer repeats and faster credit.",
    user: "C&F agent or stockist, per claim; Auditor reviews",
    file: "backend/agent/claims_graph.py",
    page: "/my-claims",
    nodes: [
      { id: "in", kind: "input", title: "User message", col: 0, row: 1, rows: [{ label: "text" }, { label: "session id" }] },
      { id: "intent", kind: "model", title: "Classify intent", col: 1, row: 1, chip: "gpt-4o-mini" },
      { id: "route", kind: "branch", title: "Which intent?", col: 2, row: 1 },
      { id: "gather", kind: "code", title: "Gather fields", col: 3, row: 0, rows: [{ label: "parse, ask what is missing" }] },
      { id: "valid", kind: "code", title: "Validate", col: 4, row: 0, rows: [{ label: "format, limits", chip: "Pydantic" }] },
      { id: "check", kind: "code", title: "Check against data", col: 5, row: 0, rows: [{ label: "claim checker", chip: "Rules" }] },
      { id: "store", kind: "code", title: "Store claim", col: 6, row: 0, rows: [{ label: "SQLite" }] },
      { id: "look", kind: "code", title: "Look up my claims", col: 3, row: 1.6, rows: [{ label: "status" }] },
      { id: "rec", kind: "code", title: "Recovery so far", col: 3, row: 2.6, rows: [{ label: "batch run + claims" }] },
      { id: "resp", kind: "model", title: "Write the reply", col: 7, row: 1.3, chip: "gpt-4o-mini" },
      { id: "aud", kind: "person", title: "Auditor reviews", col: 7, row: 0, rows: [{ label: "approve or reject" }] },
    ],
    edges: [
      { from: "in", to: "intent" }, { from: "intent", to: "route" },
      { from: "route", to: "gather", label: "file claim" }, { from: "route", to: "look", label: "status" }, { from: "route", to: "rec", label: "recovery" },
      { from: "gather", to: "valid" }, { from: "valid", to: "check" }, { from: "check", to: "store" }, { from: "store", to: "aud" },
      { from: "store", to: "resp" }, { from: "look", to: "resp" }, { from: "rec", to: "resp" },
    ],
  },
  {
    id: "ask",
    name: "Ask Analyst",
    kind: "Model + tools",
    problem:
      "Leaders want a sourced number in seconds, and the loudest belief wins. The CFO believes a forecasting tool is the fix, but the data shows the shortage is an allocation split and the returns are scheme-pushed.",
    evidence: "58% of the INR 10.18 cr measured shortfall can be met from stock at other C&Fs (each spare pack counted once); scheme packs are claimed at 13% against 2.35% for others.",
    money: "Shows where money leaks (schemes, cap, allocation) with the file and rows behind each figure.",
    user: "Rohan Mehta, Kavita Rao, Neha Bansal, on demand",
    file: "backend/agent/graph.py",
    page: "/ask",
    nodes: [
      { id: "in", kind: "input", title: "User question", col: 0, row: 1, rows: [{ label: "question" }, { label: "role" }] },
      { id: "ig", kind: "code", title: "Input guard", col: 1, row: 1, rows: [{ label: "injection, off-topic", chip: "Python" }] },
      { id: "ref", kind: "output", title: "Refusal", col: 2, row: 0, rows: [{ label: "blocked before the model" }] },
      { id: "m", kind: "model", title: "Pick a tool or answer", col: 2, row: 1, chip: "gpt-4o-mini" },
      { id: "tg", kind: "code", title: "Tool guard", col: 3, row: 1, rows: [{ label: "allow-list of 11, args" }] },
      { id: "rt", kind: "tool", title: "11 data tools", col: 4, row: 1, rows: [{ label: "claims, recovery, cover" }, { label: "fill rate, cap, schemes" }] },
      { id: "og", kind: "code", title: "Output guard", col: 5, row: 1, rows: [{ label: "scrub, flag numbers" }] },
      { id: "out", kind: "output", title: "Answer + evidence", col: 6, row: 1, rows: [{ label: "tokens, seconds" }] },
    ],
    edges: [
      { from: "in", to: "ig" }, { from: "ig", to: "ref", label: "blocked" }, { from: "ig", to: "m", label: "allowed" },
      { from: "m", to: "tg", label: "tool call" }, { from: "tg", to: "rt" }, { from: "rt", to: "m", loop: 34, label: "up to 6 trips" },
      { from: "m", to: "og", loop: 78, label: "answer" }, { from: "og", to: "out" },
    ],
  },
  {
    id: "supply",
    name: "Supply and FEFO Watcher",
    kind: "Code only",
    problem:
      "The business is short and long at once: Lucknow holds 2% of stock for 19% of outward volume while Kolkata holds 29% for 15%, and Hooghly ships newer batches first. The allocation split is still the FY25 one.",
    evidence: "INR 10.18 cr shortfall at six month-ends, 58% fillable from other C&Fs (each spare pack counted once); FEFO breaches on 54% to 64% of Hooghly lines against 0% at the other five.",
    money: "Protects revenue and future expiry claims: fewer stock-outs, no old lots reaching the 60-day block.",
    user: "Kavita Rao and Vaishali Kapoor, monthly",
    file: "backend/agent/analysis.py",
    page: "/supply-check",
    nodes: [
      { id: "in", kind: "input", title: "Stock and sales", col: 0, row: 1, rows: [{ label: "month-end snapshots" }, { label: "primary sales" }] },
      { id: "cover", kind: "code", title: "Cover by C&F", col: 1, row: 0.3, rows: [{ label: "months of outward", chip: "Python" }] },
      { id: "spare", kind: "code", title: "Spare stock elsewhere", col: 1, row: 1.7, rows: [{ label: "above 1 month cover" }] },
      { id: "fefo", kind: "code", title: "FEFO breaches", col: 2, row: 1.7, rows: [{ label: "newer batch first" }] },
      { id: "cap", kind: "code", title: "Free goods vs 3% cap", col: 2, row: 0.3, rows: [{ label: "per quarter" }] },
      { id: "out", kind: "output", title: "Allocation advice", col: 3, row: 1, rows: [{ label: "who is short, who has spare" }] },
      { id: "p", kind: "person", title: "Supply Chain resets the split", col: 4, row: 1 },
    ],
    edges: [
      { from: "in", to: "cover" }, { from: "in", to: "spare" }, { from: "spare", to: "fefo" }, { from: "cover", to: "cap" },
      { from: "fefo", to: "out" }, { from: "cap", to: "out" }, { from: "out", to: "p" },
    ],
  },
];

export const KIND_STYLE: Record<NodeKind, { label: string; color: string; border: string; bg: string }> = {
  input: { label: "INPUT", color: "#2563eb", border: "#2563eb", bg: "#2563eb" },
  code: { label: "CODE", color: "#0f766e", border: "#10b981", bg: "#0d9488" },
  model: { label: "MODEL", color: "#7c3aed", border: "#8b5cf6", bg: "#7c3aed" },
  tool: { label: "TOOLS", color: "#4f46e5", border: "#6366f1", bg: "#4f46e5" },
  branch: { label: "IF / ELSE", color: "#0891b2", border: "#06b6d4", bg: "#0891b2" },
  person: { label: "PERSON", color: "#b45309", border: "#f59e0b", bg: "#d97706" },
  output: { label: "OUTPUT", color: "#c2410c", border: "#fb923c", bg: "#f97316" },
};
