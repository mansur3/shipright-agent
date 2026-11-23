"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, Cell } from "recharts";
import { apiGet, ApiError } from "@/lib/api";
import KpiCard from "@/components/KpiCard";
import Card from "@/components/Card";
import { Loader, PageMsg } from "@/components/Status";
import { inr, num } from "@/lib/format";

interface Bucket { claims: number; inr: number }
interface StockistRow { stockist_code: string; stockist_name: string; cnf: string; claims: number; recover_inr: number; credited_inr: number }
interface Recovery {
  buckets: { recover_t1: Bucket; recover_t2: Bucket; hold: Bucket; review: Bucket; unverifiable: Bucket };
  recover_inr: number;
  recover_claims: number;
  recover_per_year_inr: number;
  window: string;
  basis: string;
  by_stockist: StockistRow[];
}
interface Register { headline: { annual_cost_saving_inr: { returns_above_1pct_target_last_4_quarters: number } } }

const AXIS = { fill: "#94a3b8", fontSize: 11 };

export default function RecoveryPage() {
  const [d, setD] = useState<Recovery | null>(null);
  const [reg, setReg] = useState<Register | null>(null);
  const [denied, setDenied] = useState(false);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiGet<Register>("/api/analytics/opportunities").then(setReg).catch(() => setReg(null));
    apiGet<Recovery>("/api/analytics/recovery")
      .then(setD)
      .catch((e: unknown) => {
        if (e instanceof ApiError && e.status === 403) setDenied(true);
        else setErr(e instanceof Error ? e.message : "Could not load");
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader label="Working out what can be claimed back…" />;
  if (denied)
    return (
      <PageMsg>
        The recovery view is for Finance, Supply Chain and the CFO. Use <Link href="/gatekeeper" className="text-brand underline">Check a Claim</Link> or{" "}
        <Link href="/my-claims" className="text-brand underline">File a Claim</Link>.
      </PageMsg>
    );
  if (err) return <PageMsg tone="danger">{err}</PageMsg>;
  if (!d) return <PageMsg>No data yet. An admin can run the batch.</PageMsg>;

  const b = d.buckets;
  const top = d.by_stockist.slice(0, 10).map((s) => ({ label: s.stockist_code, name: s.stockist_name, value: s.recover_inr }));

  return (
    <div className="space-y-4">
      {/* The headline: money to claim back */}
      <div className="rounded-[10px] border border-line bg-panel p-5 grid gap-5 md:grid-cols-[1.2fr_1fr]">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-ink3">Credited against a policy rule: potentially recoverable</div>
          <div className="mt-1 text-[40px] leading-none font-bold text-danger">{inr(d.recover_inr, { compact: true })}</div>
          <p className="mt-2 text-[13px] text-ink2 leading-relaxed">
            {num(d.recover_claims)} claims credited over {d.window}, about <strong className="text-ink">{inr(d.recover_per_year_inr, { compact: true })} a year</strong>.
            T1 claims broke the written policy text; T2 claims probably did and need the owner to confirm. Commercial Finance decides whether to recover; nothing moves automatically.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-3 content-center">
          <div className="rounded-lg bg-raised border border-line p-3">
            <div className="text-[11px] text-ink3">Policy text breached (T1)</div>
            <div className="text-xl font-bold mt-0.5">{inr(b.recover_t1.inr, { compact: true })}</div>
            <div className="text-[11px] text-ink3">{num(b.recover_t1.claims)} claims, strongest case</div>
          </div>
          <div className="rounded-lg bg-raised border border-line p-3">
            <div className="text-[11px] text-ink3">Probable breach (T2)</div>
            <div className="text-xl font-bold mt-0.5">{inr(b.recover_t2.inr, { compact: true })}</div>
            <div className="text-[11px] text-ink3">{num(b.recover_t2.claims)} claims, repeats and out of window</div>
          </div>
        </div>
      </div>

      {/* Other kinds of money, never added to the above */}
      <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Hold now: pending claims that fail a rule" value={inr(b.hold.inr, { compact: true })} sub={`${num(b.hold.claims)} claims, stop before credit`} tone="warn" />
        <KpiCard label="Needs a person (already credited)" value={inr(b.review.inr, { compact: true })} sub={`${num(b.review.claims)} claims, partial repeats or no invoice`} tone="warn" />
        <KpiCard label="Cannot be checked" value={inr(b.unverifiable.inr, { compact: true })} sub={`${num(b.unverifiable.claims)} claims, batch older than the data`} />
        <KpiCard label="Scheme-pushed returns above target" value={reg ? inr(reg.headline.annual_cost_saving_inr.returns_above_1pct_target_last_4_quarters, { compact: true }) : "…"} sub="last 4 quarters; a cost, not recoverable cash. See Recovery Register" tone="danger" />
      </div>
      <p className="text-[11px] text-ink3 -mt-2">These are different kinds of rupee and are never added together. {d.basis}</p>

      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <Card title="Where to recover from: top 10 stockists by amount" bodyClassName="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={top} layout="vertical" margin={{ left: 8, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2535" horizontal={false} />
              <XAxis type="number" tick={AXIS} tickFormatter={(v) => inr(v, { compact: true })} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="label" tick={AXIS} width={64} axisLine={false} tickLine={false} />
              <Tooltip cursor={{ fill: "#ffffff08" }} formatter={(v: number) => [inr(v, { compact: true }), "To claim back"]} labelFormatter={(l, p) => `${l} ${p?.[0]?.payload?.name ?? ""}`} />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {top.map((t) => <Cell key={t.label} fill="#ef4444" />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="What to do next">
          <ol className="space-y-3 text-[13px] leading-relaxed">
            <li>
              <strong className="text-ink">1. Hold the {num(b.hold.claims)} pending claims</strong> that fail a rule ({inr(b.hold.inr, { compact: true })}). Cheapest money to save: it has not been credited yet.{" "}
              <Link href="/claims-findings" className="text-brand hover:underline">Open the list</Link>
            </li>
            <li>
              <strong className="text-ink">2. Raise recovery on the {num(b.recover_t1.claims)} T1 claims</strong> ({inr(b.recover_t1.inr, { compact: true })}). The policy text was breached, so the case is the strongest.
            </li>
            <li>
              <strong className="text-ink">3. Review the {num(b.recover_t2.claims)} T2 claims</strong> ({inr(b.recover_t2.inr, { compact: true })}) with the stockist: repeats and late claims are probable, not certain.
            </li>
            <li>
              <strong className="text-ink">4. Check new claims first.</strong> Run each one through <Link href="/gatekeeper" className="text-brand hover:underline">Check a Claim</Link> before the credit note.
            </li>
          </ol>
        </Card>
      </div>

      <Card title="Stockists, ranked by amount to claim back">
        <div className="overflow-auto max-h-[420px]">
          <table className="w-full text-[13px] border-collapse min-w-[640px]">
            <thead className="sticky top-0 bg-panel">
              <tr className="border-b border-line text-ink2 text-left">
                {["Stockist", "C&F", "Claims", "Credited in total", "To claim back"].map((h, i) => (
                  <th key={h} className={`px-3 py-2 font-medium ${i >= 2 ? "text-right" : ""}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {d.by_stockist.map((s) => (
                <tr key={s.stockist_code} className="border-b border-line hover:bg-raised">
                  <td className="px-3 py-2">{s.stockist_name} <span className="text-ink3 font-mono text-[11px]">{s.stockist_code}</span></td>
                  <td className="px-3 py-2 text-ink2">{s.cnf}</td>
                  <td className="px-3 py-2 text-right">{num(s.claims)}</td>
                  <td className="px-3 py-2 text-right text-ink2">{inr(s.credited_inr, { compact: true })}</td>
                  <td className="px-3 py-2 text-right font-semibold text-danger">{inr(s.recover_inr, { compact: true })}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
