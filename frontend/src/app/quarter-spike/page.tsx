"use client";

import { useEffect, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { apiGet } from "@/lib/api";
import type { QuarterSpikeResponse } from "@/lib/types";
import Card from "@/components/Card";
import KpiCard from "@/components/KpiCard";
import { Loader, PageMsg } from "@/components/Status";
import { inr, pct } from "@/lib/format";

// Real SKUs from sku_master.csv — drive the analysis
const SKU_OPTIONS = [
  { value: "", label: "All SKUs" },
  { value: "PFL1001", label: "PFL1001 — Azithromycin 500 mg" },
  { value: "PFL1002", label: "PFL1002 — Amoxicillin+Clavulanic" },
  { value: "PFL1003", label: "PFL1003 — Cefixime 200 mg" },
  { value: "PFL1101", label: "PFL1101 — Vit B-complex+Zinc" },
  { value: "PFL1102", label: "PFL1102 — Calcium+Vit D3" },
  { value: "PFL1103", label: "PFL1103 — Methylcobalamin" },
  { value: "PFL1105", label: "PFL1105 — Multivitamin syrup" },
  { value: "PFL1301", label: "PFL1301 — Montelukast+Levocetir" },
  { value: "PFL1303", label: "PFL1303 — Ambroxol+Guaifenesin" },
  { value: "PFL1401", label: "PFL1401 — Pantoprazole 40 mg" },
];

const AXIS = { fill: "#94a3b8", fontSize: 11 };
const GRID = "#1e2535";

function barColor(pct: number) {
  return pct >= 30 ? "#ef4444" : pct >= 20 ? "#f59e0b" : "#10b981";
}

export default function QuarterSpikePage() {
  const [sku, setSku] = useState("");
  const [data, setData] = useState<QuarterSpikeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const r = await apiGet<QuarterSpikeResponse>("/api/quarter-spike", { sku_code: sku });
      setData(r);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [sku]); // eslint-disable-line

  const phases = data?.phasing_by_quarter ?? [];

  return (
    <div className="space-y-4">
      {/* SKU selector */}
      <div className="flex items-center gap-3">
        <select value={sku} onChange={(e) => setSku(e.target.value)}
          className="bg-raised border border-line text-ink text-[13px] rounded-sm px-2.5 py-1.5 outline-none focus:border-brand">
          {SKU_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <button onClick={load} className="px-3.5 py-1.5 bg-brand text-white text-[13px] rounded-sm font-medium hover:opacity-85">
          Analyse
        </button>
      </div>

      {/* KPIs */}
      {data && !loading && (
        <div className="grid gap-3 grid-cols-2 sm:grid-cols-4">
          <KpiCard label="Avg spike (last 4Q)" value={pct(data.avg_spike_pct_last4q)}
            tone={data.risk_level === "HIGH" ? "danger" : "warn"} />
          <KpiCard label="Risk level" value={data.risk_level ?? "—"}
            tone={data.risk_level === "HIGH" ? "danger" : data.risk_level === "MEDIUM" ? "warn" : "ok"} />
          <KpiCard label="Latest spike" value={pct(data.latest_spike_pct)}
            sub={data.latest_quarter} tone="warn" />
          <KpiCard label="Projected return" value={inr(data.projected_expiry_return_inr, { compact: true })}
            sub="From latest spike" tone="danger" />
        </div>
      )}

      {/* Root-cause explanation */}
      <Card title="Why end-of-quarter spikes drive expiry returns">
        <div className="text-[13px] text-ink2 leading-relaxed space-y-2">
          <p>
            The sales incentive plan (introduced Q3 FY25) ties field-force payout <strong className="text-ink">100% to quarterly primary sales</strong>.
            This makes it rational to push volume into the last 9 days via the quarter-end "10+2" (tier A) and "10+1" (tier B) schemes in Annex B of CO-POL-014.
          </p>
          <p>
            Stock pushed above a stockist's consumption capacity sits unsold and returns as expiry claims
            <strong className="text-ink"> many months later</strong>. The data shows the last 9 days carried about{" "}
            <strong className="text-danger">20%</strong> of a quarter's sales before the December 2024 quarter and{" "}
            <strong className="text-danger">25–34%</strong> since, while packs supplied under those schemes were claimed back at about 13% against 2.4% for other packs (measured, with a range).
          </p>
          <p>
            <strong className="text-warn">Policy §4.5</strong> requires RSMs to check closing stock before accepting
            scheme orders — but the DMS that supplied that data was discontinued in 2023.
            This tool proxies §4.5 using the billing history.
          </p>
        </div>
      </Card>

      {/* Spike chart */}
      <Card title={`Last-9-day % of quarterly sales${data?.product ? ` — ${data.product}` : ""}`}>
        {loading ? (
          <Loader label="Loading spike data…" />
        ) : error ? (
          <PageMsg tone="danger">{error}</PageMsg>
        ) : phases.length === 0 ? (
          <PageMsg>No data for this SKU.</PageMsg>
        ) : (
          <>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={phases} margin={{ top: 4, right: 8, left: 8, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
                  <XAxis dataKey="quarter" tick={AXIS} tickLine={false} axisLine={{ stroke: GRID }} />
                  <YAxis tick={AXIS} tickLine={false} axisLine={false} domain={[0, "auto"]}
                    tickFormatter={(v) => `${v}%`} width={40} />
                  <Tooltip
                    cursor={{ fill: "#ffffff08" }}
                    content={({ active, payload, label }) => {
                      if (!active || !payload?.length) return null;
                      const p = payload[0].payload;
                      return (
                        <div className="bg-panel border border-line rounded-sm p-2.5 text-[12px] text-ink space-y-1">
                          <p className="font-semibold">{label}</p>
                          <p>Spike: <span className="font-mono">{p.spike_pct}%</span></p>
                          <p>Scheme: <span className="font-mono">{p.scheme_pct}%</span></p>
                          <p>Total: <span className="font-mono">{inr(p.total_inr, { compact: true })}</span></p>
                          <p>Last 9d: <span className="font-mono">{inr(p.last9d_inr, { compact: true })}</span></p>
                        </div>
                      );
                    }}
                  />
                  <Bar dataKey="spike_pct" radius={[4, 4, 0, 0]}>
                    {phases.map((p) => (
                      <Cell key={p.quarter} fill={barColor(p.spike_pct)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="flex gap-3 mt-3 text-[11px] flex-wrap">
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-danger inline-block" /> ≥30% — HIGH risk</span>
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-warn inline-block" /> 20–29% — MEDIUM</span>
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-ok inline-block" /> &lt;20% — LOW</span>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
