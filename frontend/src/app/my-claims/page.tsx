"use client";

import { useEffect, useRef, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";
import type { ClaimsChatResponse, MyClaimsResponse, UserClaim } from "@/lib/types";
import Card from "@/components/Card";
import Markdown from "@/components/Markdown";
import { inr, num, shortDate } from "@/lib/format";

interface ChatMsg { role: "user" | "ai" | "thinking"; text: string; }

function StatusBadge({ s }: { s: string }) {
  const cls = s === "Credited" ? "bg-ok/15 text-ok border-ok/30"
    : s === "Submitted" || s === "Under Review" ? "bg-warn/15 text-warn border-warn/30"
    : "bg-danger/15 text-danger border-danger/30";
  return <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium border ${cls}`}>{s}</span>;
}

export default function MyClaimsPage() {
  const [msgs, setMsgs] = useState<ChatMsg[]>([
    { role: "ai", text: "Hello! I can help you create a new claim or check the status of your existing ones. What would you like to do?" },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [sessionId, setSessionId] = useState("");
  const [claims, setClaims] = useState<UserClaim[]>([]);
  const [claimsLoading, setClaimsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  async function loadClaims() {
    setClaimsLoading(true);
    try {
      const r = await apiGet<MyClaimsResponse>("/api/claims/my", { status_filter: statusFilter });
      setClaims(r.claims);
    } catch { /* user may not have claims yet */ }
    finally { setClaimsLoading(false); }
  }

  useEffect(() => { loadClaims(); }, [statusFilter]); // eslint-disable-line

  async function send(q: string) {
    if (!q.trim() || busy) return;
    setInput("");
    setBusy(true);
    setMsgs((m) => [...m, { role: "user", text: q }, { role: "thinking", text: "Processing…" }]);
    try {
      const r = await apiPost<ClaimsChatResponse>("/api/claims/chat", { message: q, session_id: sessionId });
      setSessionId(r.session_id);
      setMsgs((m) => [...m.slice(0, -1), { role: "ai", text: r.answer }]);
      if (r.claim_no) loadClaims();
    } catch (e: unknown) {
      setMsgs((m) => [...m.slice(0, -1), { role: "ai", text: `Error: ${e instanceof Error ? e.message : "Failed"}` }]);
    } finally {
      setBusy(false);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  }

  const totalValue = claims.reduce((s, c) => s + c.claim_value_inr, 0);
  const totalRecovery = claims.reduce((s, c) => s + c.recovery_amount_inr, 0);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Chat agent */}
      <Card title="Claims AI Assistant">
        <div className="min-h-[280px] max-h-[380px] overflow-y-auto space-y-3 pb-3">
          {msgs.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[88%] rounded-[10px] px-3.5 py-2.5 text-[13px] leading-relaxed ${
                m.role === "user" ? "bg-brand text-white"
                  : m.role === "thinking" ? "bg-raised border border-line text-ink3 italic opacity-70"
                  : "bg-raised border border-line text-ink"}`}>
                {m.role === "ai" ? <Markdown text={m.text} /> : <span className="whitespace-pre-wrap">{m.text}</span>}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
        <form onSubmit={(e) => { e.preventDefault(); send(input); }}
          className="flex gap-2 mt-3 pt-3 border-t border-line">
          <input value={input} onChange={(e) => setInput(e.target.value)}
            disabled={busy}
            placeholder="e.g. 'I want to file a near expiry claim'"
            className="flex-1 bg-raised border border-line rounded-sm px-3 py-2 text-[13px] text-ink outline-none focus:border-brand transition-colors disabled:opacity-50" />
          <button type="submit" disabled={busy || !input.trim()}
            className="px-4 py-2 bg-brand text-white text-[13px] font-semibold rounded-sm hover:opacity-85 disabled:opacity-50 whitespace-nowrap">
            Send
          </button>
        </form>
        <div className="flex flex-wrap gap-1.5 mt-2.5">
          {["I want to file a near expiry claim", "Check my claim status", "How much can I recover?"].map((s) => (
            <button key={s} onClick={() => send(s)} disabled={busy}
              className="text-[11px] px-2.5 py-1 bg-raised border border-line rounded-full text-ink2 hover:border-brand hover:text-brand transition-colors">
              {s}
            </button>
          ))}
        </div>
      </Card>

      {/* Claims list */}
      <Card title="My Claims">
        <div className="flex items-center gap-2 mb-3">
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-raised border border-line text-ink text-[13px] rounded-sm px-2.5 py-1.5 outline-none focus:border-brand flex-1">
            {["", "Submitted", "Under Review", "Approved", "Rejected", "Credited"].map((s) => (
              <option key={s} value={s}>{s || "All Statuses"}</option>
            ))}
          </select>
          <button onClick={loadClaims} className="px-3 py-1.5 text-[13px] bg-raised border border-line rounded-sm hover:border-brand">↻</button>
        </div>

        {claims.length > 0 && (
          <div className="flex gap-2 mb-3 text-[12px] flex-wrap">
            <span className="px-2.5 py-1 bg-raised border border-line rounded-full text-ink2">
              {num(claims.length)} claims · <strong className="text-ink">{inr(totalValue, { compact: true })}</strong>
            </span>
            {totalRecovery > 0 && (
              <span className="px-2.5 py-1 bg-raised border border-line rounded-full text-ink2">
                Recovery: <strong className="text-ok">{inr(totalRecovery, { compact: true })}</strong>
              </span>
            )}
          </div>
        )}

        <div className="overflow-y-auto max-h-[360px] space-y-2">
          {claimsLoading ? (
            <p className="text-ink3 text-[13px] text-center py-6">Loading…</p>
          ) : claims.length === 0 ? (
            <p className="text-ink3 text-[13px] text-center py-6">
              No claims yet. Use the chat to create one.
            </p>
          ) : (
            claims.map((c) => (
              <div key={c.claim_no} className="border border-line rounded-[8px] p-3 bg-raised space-y-1.5">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <span className="font-mono text-[11px] text-ink2">{c.claim_no}</span>
                  <StatusBadge s={c.status} />
                </div>
                <div className="grid grid-cols-2 gap-x-4 text-[12px] text-ink2">
                  <span>Batch: <strong className="text-ink font-mono">{c.batch_no}</strong></span>
                  <span>SKU: <strong className="text-ink">{c.sku_code}</strong></span>
                  <span>Type: <strong className="text-ink">{c.claim_type}</strong></span>
                  <span>Qty: <strong className="text-ink">{num(c.qty_claimed)}</strong></span>
                  <span>Value: <strong className="text-ink">{inr(c.claim_value_inr)}</strong></span>
                  <span>Recovery: <strong className={c.recovery_amount_inr > 0 ? "text-ok" : "text-ink"}>{inr(c.recovery_amount_inr)}</strong></span>
                </div>
                <div className="flex items-center gap-2 flex-wrap text-[11px]">
                  <span className={`px-2 py-0.5 rounded-full border ${c.risk_score >= 50 ? "bg-danger/15 text-danger border-danger/30" : c.risk_score >= 25 ? "bg-warn/15 text-warn border-warn/30" : "bg-ok/15 text-ok border-ok/30"}`}>
                    Risk {c.risk_score}/100
                  </span>
                  {c.risk_flags.filter(Boolean).map((f) => (
                    <span key={f} className="px-1.5 py-0.5 bg-danger/10 text-danger border border-danger/20 rounded text-[10px]">{f}</span>
                  ))}
                  <span className="text-ink3 ml-auto">{shortDate(c.created_at)}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}
