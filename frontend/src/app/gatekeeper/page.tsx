"use client";

import { useState } from "react";
import { apiPost } from "@/lib/api";
import Card from "@/components/Card";
import Markdown from "@/components/Markdown";
import { inr } from "@/lib/format";

function prettyJson(s: string): string {
  try {
    return JSON.stringify(JSON.parse(s), null, 2).slice(0, 1800);
  } catch {
    return s.slice(0, 1800);
  }
}

// ── Types ──────────────────────────────────────────────────────────────────
interface AuditEvidence {
  records?: string[];
  batch: Record<string, unknown>;
  stockist: Record<string, unknown>;
  billed_history: Record<string, unknown>;
  prior_claims: Record<string, unknown>;
}
interface AskEvidence { tool: string; content: string }
interface AuditResult {
  verdict?: {
    decision: string;
    rule_id: string;
    policy_clause: string;
    owner: string;
    reason: string;
    rupee_impact: number;
    checks_passed: string[];
    checks_failed: string[];
    evidence?: string[];
    tier?: string;
  };
  // claim audit returns an object of records; /api/ask returns an array of tool evidence
  evidence?: AuditEvidence | AskEvidence[];
  // /api/ask response (LangGraph agent)
  answer?: string;
  model_calls?: number;
  latency_ms?: number;
  flags?: string[];
  blocked?: boolean;
  error?: string;
}

// ── Tab 1: Claims Gatekeeper (deterministic, no LLM) ──────────────────────
function ClaimsGatekeeper() {
  const [stockist, setStockist] = useState("STK0054");
  const [batch, setBatch] = useState("K2310267");
  const [qty, setQty] = useState(50);
  const [claimDate, setClaimDate] = useState("15-09-2025");
  const [invoiceRef, setInvoiceRef] = useState("INV/E01/2404/000881");
  const [claimType, setClaimType] = useState("Near expiry");
  const [result, setResult] = useState<AuditResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function runAudit() {
    setLoading(true);
    setResult(null);
    try {
      const r = await apiPost<AuditResult>("/api/audit-claim", {
        stockist_code: stockist,
        batch_no: batch,
        qty_claimed: Number(qty),
        claim_date: claimDate,
        claim_type: claimType,
        original_invoice_ref: invoiceRef || null,
      });
      setResult(r);
    } catch (e: unknown) {
      setResult({ error: e instanceof Error ? e.message : "Failed" });
    } finally {
      setLoading(false);
    }
  }

  const v = result?.verdict;
  const decisionColor =
    v?.decision === "APPROVE"
      ? "text-ok"
      : v?.decision === "REJECT"
        ? "text-danger"
        : "text-warn";

  return (
    <div className="space-y-4">
      <Card title="Claims Gatekeeper — deterministic CO-POL-014 v4.2 checks (no LLM)">
        <p className="text-[13px] text-ink2 mb-3">
          Every check runs in pure Python against the CSV data — the model is
          never involved. This is the &quot;real-time call&quot; for claims that
          move money.
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-3">
          <Field
            label="Stockist Code"
            value={stockist}
            onChange={setStockist}
          />
          <Field label="Batch No" value={batch} onChange={setBatch} />
          <Field
            label="Qty Claimed"
            value={String(qty)}
            onChange={(v) => setQty(Number(v))}
            type="number"
          />
          <Field
            label="Claim Date (dd-mm-yyyy)"
            value={claimDate}
            onChange={setClaimDate}
          />
          <div>
            <label className="text-[11px] text-ink3 block mb-1">
              Claim Type
            </label>
            <select
              value={claimType}
              onChange={(e) => setClaimType(e.target.value)}
              className="w-full bg-raised border border-line rounded-sm px-2.5 py-1.5 text-[13px] text-ink outline-none focus:border-brand"
            >
              {[
                "Near expiry",
                "Expired",
                "Breakage in transit",
                "Short supply",
              ].map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
          </div>
          <Field
            label="Invoice Ref (blank = v4.2 route)"
            value={invoiceRef}
            onChange={setInvoiceRef}
          />
        </div>
        <button
          onClick={runAudit}
          disabled={loading}
          className="px-4 py-2 bg-brand text-white text-[13px] font-semibold rounded-sm hover:opacity-85 disabled:opacity-50"
        >
          {loading ? "Running checks…" : "Evaluate Claim"}
        </button>
      </Card>

      {result && !result.error && v && (
        <Card title="Verdict">
          <div className="space-y-3">
            <div className="flex items-center gap-3 flex-wrap">
              <span className={`text-[20px] font-bold ${decisionColor}`}>
                {v.decision}
              </span>
              <span className="px-2 py-0.5 rounded-full text-[11px] bg-raised border border-line text-ink2">
                {v.rule_id}
              </span>
              <span className="text-[12px] text-ink2">{v.policy_clause}</span>
            </div>
            <p className="text-[13px] text-ink2">{v.reason}</p>
            {v.rupee_impact > 0 && (
              <p className="text-[14px] font-semibold text-ink">
                Rupee impact: {inr(v.rupee_impact)}
              </p>
            )}
            {v.checks_passed.length > 0 && (
              <div>
                <p className="text-[11px] font-semibold text-ok uppercase mb-1">
                  Checks passed ({v.checks_passed.length})
                </p>
                <ul className="space-y-1">
                  {v.checks_passed.map((c, i) => (
                    <li key={i} className="text-[12px] text-ink2 flex gap-2">
                      <span className="text-ok">✓</span> {c}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {v.evidence && v.evidence.length > 0 && (
              <div>
                <p className="text-[11px] font-semibold text-ink3 uppercase mb-1.5">Records used ({v.evidence.length})</p>
                <ul className="text-[11px] text-ink2 space-y-0.5">
                  {v.evidence.map((e, i) => (<li key={i}>{e}</li>))}
                </ul>
              </div>
            )}
            {v.checks_failed.length > 0 && (
              <div>
                <p className="text-[11px] font-semibold text-danger uppercase mb-1">
                  Checks failed ({v.checks_failed.length})
                </p>
                <ul className="space-y-1">
                  {v.checks_failed.map((c, i) => (
                    <li key={i} className="text-[12px] text-ink2 flex gap-2">
                      <span className="text-danger">✗</span> {c}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <p className="text-[11px] text-ink3">Owner: {v.owner}</p>
          </div>
        </Card>
      )}

      {result?.error && (
        <Card title="Error">
          <p className="text-danger text-[13px]">{result.error}</p>
        </Card>
      )}
    </div>
  );
}

// ── Tab 2: LangGraph Agent (natural language, with guardrails) ─────────────
function AgentTab() {
  const [question, setQuestion] = useState(
    "Audit claim from STK0054 for batch K2310267, 50 strips, near expiry, dated 15-09-2025, invoice INV/E01/2404/000881",
  );
  const [result, setResult] = useState<AuditResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function runAgent() {
    setLoading(true);
    setResult(null);
    try {
      const r = await apiPost<AuditResult>("/api/ask", { question });
      setResult(r);
    } catch (e: unknown) {
      setResult({ error: e instanceof Error ? e.message : "Failed" });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <Card title="LangGraph Agent — natural-language audit with guardrails">
        <p className="text-[13px] text-ink2 mb-3">
          The LLM decides which tools to call and formats the answer. All
          numbers come from tool calls against the CSV data — the model never
          writes a batch number, date, or INR amount from memory. 3 guardrail
          gates: input (blocks injection), tool (validates calls), output
          (scrubs paths).
        </p>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={3}
          className="w-full bg-raised border border-line rounded-sm px-3 py-2 text-[13px] text-ink outline-none focus:border-brand mb-3"
          placeholder="Describe a claim to audit in natural language…"
        />
        <button
          onClick={runAgent}
          disabled={loading || !question.trim()}
          className="px-4 py-2 bg-brand text-white text-[13px] font-semibold rounded-sm hover:opacity-85 disabled:opacity-50"
        >
          {loading ? "Running LangGraph…" : "Run LangGraph Workflow"}
        </button>
        <div className="flex flex-wrap gap-1.5 mt-2">
          {[
            "Audit claim STK0054 K2310267 50 strips near expiry 15-09-2025 INV/E01/2404/000881",
            "Check scheme eligibility for STK0120 on PFL1301 ordering 1000 packs",
            "What batches at CF-N01 expire in 60 days?",
          ].map((q) => (
            <button
              key={q}
              onClick={() => setQuestion(q)}
              disabled={loading}
              className="text-[11px] px-2.5 py-1 bg-raised border border-line rounded-full text-ink2 hover:border-brand hover:text-brand transition-colors"
            >
              {q.slice(0, 50)}…
            </button>
          ))}
        </div>
      </Card>

      {result && !result.error && (
        <Card title="Agent Response">
          <div className="space-y-3">
            {result.blocked && (
              <p className="text-danger text-[13px] bg-danger/10 rounded-sm px-3 py-1.5">
                ⛔ Request blocked by input guardrail
              </p>
            )}
            {result.answer && (
              <div className="rounded-lg bg-raised border border-line px-4 py-3">
                <Markdown text={result.answer} />
              </div>
            )}
            {result.flags && result.flags.length > 0 && (
              <p className="text-[11px] text-warn">
                {result.flags.includes("unverified_number_risk")
                  ? "Some figures were reworded by the model. Open the evidence below and check them against the tool result."
                  : `Guardrail note: ${result.flags.join(", ")}`}
              </p>
            )}
            {Array.isArray(result.evidence) && result.evidence.length > 0 && (
              <details className="text-[11px] text-ink3">
                <summary className="cursor-pointer select-none hover:text-ink2">
                  Evidence: {result.evidence.length} tool result{result.evidence.length !== 1 ? "s" : ""}, read from the data files
                </summary>
                <div className="mt-2 space-y-2 max-h-72 overflow-y-auto">
                  {result.evidence.map((e, i) => (
                    <div key={i} className="bg-raised border border-line rounded-sm px-3 py-2">
                      <div className="font-mono text-ink2 mb-1">{e.tool}</div>
                      <pre className="whitespace-pre-wrap break-words text-ink3 font-mono text-[10.5px]">{prettyJson(e.content)}</pre>
                    </div>
                  ))}
                </div>
              </details>
            )}
            {result.model_calls !== undefined && (
              <div className="flex gap-3 text-[11px] text-ink3">
                <span>LLM calls: {result.model_calls}</span>
                {result.latency_ms && (
                  <span>Latency: {result.latency_ms}ms</span>
                )}
              </div>
            )}
          </div>
        </Card>
      )}

      {result?.error && (
        <Card title="Error">
          <p className="text-danger text-[13px]">{result.error}</p>
        </Card>
      )}
    </div>
  );
}

// ── Helper ─────────────────────────────────────────────────────────────────
function Field({
  label,
  value,
  onChange,
  type,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
}) {
  return (
    <div>
      <label className="text-[11px] text-ink3 block mb-1">{label}</label>
      <input
        type={type ?? "text"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-raised border border-line rounded-sm px-2.5 py-1.5 text-[13px] text-ink outline-none focus:border-brand"
      />
    </div>
  );
}

// ── Page: two tabs ─────────────────────────────────────────────────────────
export default function GatekeeperPage() {
  const [tab, setTab] = useState<"claims" | "agent">("claims");

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <div className="flex gap-2">
        <button
          onClick={() => {
            setTab("claims");
          }}
          className={`px-4 py-2 text-[13px] font-semibold rounded-sm transition-colors ${
            tab === "claims"
              ? "bg-brand text-white"
              : "bg-raised border border-line text-ink2 hover:border-brand"
          }`}
        >
          1. Claims Gatekeeper (CO-POL-014)
        </button>
        <button
          onClick={() => {
            setTab("agent");
          }}
          className={`px-4 py-2 text-[13px] font-semibold rounded-sm transition-colors ${
            tab === "agent"
              ? "bg-brand text-white"
              : "bg-raised border border-line text-ink2 hover:border-brand"
          }`}
        >
          2. LangGraph Agent (Natural Language)
        </button>
      </div>

      {tab === "claims" ? <ClaimsGatekeeper /> : <AgentTab />}
    </div>
  );
}
