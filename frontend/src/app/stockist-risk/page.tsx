"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import type { StockistRiskProfile, StockistRiskResponse } from "@/lib/types";
import Card from "@/components/Card";
import DataTable, { type Column } from "@/components/DataTable";
import KpiCard from "@/components/KpiCard";
import { Loader, PageMsg } from "@/components/Status";
import { inr, num, pct } from "@/lib/format";

const COLS: Column<StockistRiskProfile>[] = [
  { key: "stockist_code", header: "Code" },
  { key: "stockist_name", header: "Name", render: (r) => <span className="text-[12px]">{r.stockist_name ?? "—"}</span> },
  { key: "cnf_code", header: "CNF" },
  {
    key: "risk_score",
    header: "Score",
    render: (r) => (
      <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold border ${
        r.risk_score >= 50 ? "bg-danger/15 text-danger border-danger/30"
          : r.risk_score >= 25 ? "bg-warn/15 text-warn border-warn/30"
          : "bg-ok/15 text-ok border-ok/30"}`}>
        {r.risk_score}
      </span>
    ),
  },
  { key: "claim_rate_pct", header: "Claim rate", render: (r) => pct(r.claim_rate_pct) },
  { key: "total_claim_inr", header: "Total claims", render: (r) => inr(r.total_claim_inr, { compact: true }) },
  { key: "zero_inv_inr", header: "Zero-inv INR", render: (r) => inr(r.zero_inv_inr, { compact: true }) },
  { key: "dup_credit_inr", header: "Dup credits", render: (r) => inr(r.dup_credit_inr, { compact: true }) },
  {
    key: "signals",
    header: "Signals",
    render: (r) => (
      <div className="flex flex-wrap gap-1">
        {r.signals.map((s) => (
          <span key={s} className="px-1.5 py-0.5 rounded text-[10px] bg-danger/10 text-danger border border-danger/20">{s}</span>
        ))}
      </div>
    ),
  },
];

export default function StockistRiskPage() {
  const [data, setData] = useState<StockistRiskProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [minScore, setMinScore] = useState(25);
  const [runAt, setRunAt] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const r = await apiGet<StockistRiskResponse>("/api/analytics/stockist-risk", { min_score: minScore });
      setData(r.profiles);
      setRunAt(r.run_at ?? null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [minScore]); // eslint-disable-line

  const high = data.filter((p) => p.risk_score >= 50).length;
  const totalDup = data.reduce((s, p) => s + p.dup_credit_inr, 0);
  const totalZero = data.reduce((s, p) => s + p.zero_inv_inr, 0);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <select value={minScore} onChange={(e) => setMinScore(Number(e.target.value))}
          className="bg-raised border border-line text-ink text-[13px] rounded-sm px-2.5 py-1.5 outline-none focus:border-brand">
          <option value={0}>All stockists</option>
          <option value={25}>Medium risk (≥ 25)</option>
          <option value={50}>High risk (≥ 50)</option>
        </select>
        <button onClick={load} className="px-3.5 py-1.5 bg-brand text-white text-[13px] rounded-sm font-medium hover:opacity-85">
          Refresh
        </button>
        {runAt && <span className="text-[11px] text-ink3">Last batch: {new Date(runAt).toLocaleDateString()}</span>}
      </div>

      <div className="grid gap-3 grid-cols-2 sm:grid-cols-4">
        <KpiCard label="Profiles shown" value={num(data.length)} tone="warn" />
        <KpiCard label="High risk (≥50)" value={num(high)} tone="danger" />
        <KpiCard label="Dup credits total" value={inr(totalDup, { compact: true })} tone="danger" />
        <KpiCard label="Zero-inv total" value={inr(totalZero, { compact: true })} tone="warn" />
      </div>

      <Card title="Stockist risk profiles — from batch ML analysis">
        {loading ? <Loader label="Loading profiles…" />
          : error ? <PageMsg tone="danger">{error}</PageMsg>
          : <DataTable
              columns={COLS}
              data={data}
              maxHeight={560}
              empty="No stockists match this filter."
              rowKey={(_, i) => i}
            />}
      </Card>
    </div>
  );
}
