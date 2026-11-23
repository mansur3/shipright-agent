"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiGet, ApiError } from "@/lib/api";
import Card from "@/components/Card";
import KpiCard from "@/components/KpiCard";
import { Loader, PageMsg } from "@/components/Status";
import { inr, num } from "@/lib/format";

interface Opp {
  id: string;
  name: string;
  class: string;
  class_label: string;
  kind: string;
  problem: string;
  evidence: string;
  scope: string;
  formula: string;
  amount_inr: number | null;
  reference_inr?: number;
  claims: number | null;
  range?: { low_inr: number; high_inr: number; note: string };
  confidence: string;
  feasibility: string;
  action: string;
  owner: string;
  agent: string;
  priority: number;
  validated: boolean;
  validation: string;
  overlap?: string;
}
interface Register {
  opportunities: Opp[];
  headline: {
    confirmed_leakage_inr: number;
    potentially_recoverable_inr: number;
    credited_cash_to_review_inr: number;
    cash_to_hold_inr: number;
    annual_cost_saving_inr: { free_goods_over_cap_last_4_quarters: number; returns_above_1pct_target_last_4_quarters: number };
    revenue_opportunity_at_pts_inr: number;
  };
  rules: string[];
  window: string;
}

const TONE: Record<string, string> = {
  confirmed_leakage: "bg-danger/15 text-danger border-danger/30",
  potentially_recoverable: "bg-warn/15 text-warn border-warn/30",
  cost_avoidance: "bg-ok/15 text-ok border-ok/30",
  cost_saving: "bg-brand/15 text-brand border-brand/30",
  revenue_opportunity: "bg-brand/15 text-brand border-brand/30",
  operational_risk: "bg-warn/15 text-warn border-warn/30",
  exposure: "bg-raised text-ink2 border-line",
};

export default function OpportunitiesPage() {
  const [d, setD] = useState<Register | null>(null);
  const [denied, setDenied] = useState(false);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState<string | null>("OPP-01");
  const [cls, setCls] = useState("all");

  useEffect(() => {
    apiGet<Register>("/api/analytics/opportunities")
      .then(setD)
      .catch((e: unknown) => {
        if (e instanceof ApiError && e.status === 403) setDenied(true);
        else setErr(e instanceof Error ? e.message : "Could not load");
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader label="Building the recovery register…" />;
  if (denied) return <PageMsg>The recovery register is for Finance, Supply Chain and the CFO. Use <Link href="/gatekeeper" className="text-brand underline">Check a Claim</Link>.</PageMsg>;
  if (err) return <PageMsg tone="danger">{err}</PageMsg>;
  if (!d) return <PageMsg>No data.</PageMsg>;

  const h = d.headline;
  const rows = d.opportunities.filter((o) => cls === "all" || o.class === cls);
  const classes = Array.from(new Set(d.opportunities.map((o) => o.class)));

  return (
    <div className="space-y-4">
      <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
        <KpiCard tone="danger" label="Confirmed leakage (T1)" value={inr(h.confirmed_leakage_inr, { compact: true })} sub="credited, policy text breached" />
        <KpiCard tone="warn" label="Potentially recoverable (T2)" value={inr(h.potentially_recoverable_inr, { compact: true })} sub="credited, probable breach; owner confirms" />
        <KpiCard tone="ok" label="Cash to hold now" value={inr(h.cash_to_hold_inr, { compact: true })} sub="pending claims that fail a rule" />
        <KpiCard label="Revenue opportunity (at PTS)" value={inr(h.revenue_opportunity_at_pts_inr, { compact: true })} sub="latest month-end; not cash, not margin" />
      </div>
      <p className="text-[11px] text-ink3 -mt-2">{d.rules.join(" ")}</p>

      <div className="flex flex-wrap gap-2">
        {["all", ...classes].map((c) => (
          <button key={c} onClick={() => setCls(c)} className={`px-3 py-1 rounded-full text-[12px] border ${cls === c ? "bg-brand text-white border-brand" : "bg-panel text-ink2 border-line hover:bg-raised"}`}>
            {c === "all" ? "All" : d.opportunities.find((o) => o.class === c)?.class_label}
          </button>
        ))}
      </div>

      <div className="space-y-2">
        {rows.map((o) => (
          <Card key={o.id} bodyClassName="p-0">
            <button className="w-full text-left px-[18px] py-3 flex flex-wrap items-center gap-3" onClick={() => setOpen(open === o.id ? null : o.id)} aria-expanded={open === o.id}>
              <span className="font-mono text-[11px] text-ink3">{o.id}</span>
              <span className="font-semibold text-[13px] flex-1 min-w-[220px]">{o.name}</span>
              <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold border ${TONE[o.class]}`}>{o.class_label}</span>
              <span className="text-[13px] font-bold w-[120px] text-right">
                {o.amount_inr !== null ? inr(o.amount_inr, { compact: true }) : o.reference_inr !== undefined ? <span className="text-ink3 font-normal">{inr(o.reference_inr, { compact: true })} ref.</span> : "—"}
              </span>
            </button>
            {open === o.id && (
              <div className="px-[18px] pb-4 pt-1 grid gap-3 md:grid-cols-2 text-[12px] leading-relaxed text-ink2 border-t border-line">
                <div><b className="text-ink">Problem.</b> {o.problem}</div>
                <div><b className="text-ink">Scope.</b> {o.scope}{o.claims ? ` (${num(o.claims)} claims)` : ""}</div>
                <div><b className="text-ink">Evidence.</b> {o.evidence}</div>
                <div><b className="text-ink">Formula.</b> {o.formula}</div>
                {o.range && <div><b className="text-ink">Forward range.</b> {inr(o.range.low_inr, { compact: true })} to {inr(o.range.high_inr, { compact: true })}. {o.range.note}</div>}
                <div><b className="text-ink">Kind of money.</b> {o.kind}. <b className="text-ink">Confidence.</b> {o.confidence}. <b className="text-ink">Feasibility.</b> {o.feasibility}</div>
                <div><b className="text-ink">Next action.</b> {o.action}</div>
                <div><b className="text-ink">Owner.</b> {o.owner}. <b className="text-ink">Found by.</b> {o.agent}.</div>
                {o.overlap && <div className="text-warn"><b>Overlap.</b> {o.overlap}</div>}
                <div className={o.validated ? "text-ok" : "text-danger"}>{o.validated ? "Validated: " : ""}{o.validation}</div>
              </div>
            )}
          </Card>
        ))}
      </div>
      <p className="text-[11px] text-ink3">Window: {d.window}. Sizes are computed in code from the source files; the model never writes a figure. Commercial Finance decides every recovery.</p>
    </div>
  );
}
