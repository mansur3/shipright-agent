"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";
import type { AllClaimsResponse, ReviewResponse, UserClaim } from "@/lib/types";
import Card from "@/components/Card";
import DataTable, { type Column } from "@/components/DataTable";
import { Loader, PageMsg } from "@/components/Status";
import { inr, num, shortDate } from "@/lib/format";

function StatusBadge({ s }: { s: string }) {
  const cls = s === "Credited" || s === "Approved" ? "bg-ok/15 text-ok border-ok/30"
    : s === "Submitted" || s === "Under Review" ? "bg-warn/15 text-warn border-warn/30"
    : "bg-danger/15 text-danger border-danger/30";
  return <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium border ${cls}`}>{s}</span>;
}

export default function AuditorPage() {
  const [data, setData] = useState<UserClaim[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [userFilter, setUserFilter] = useState("");
  const [minRisk, setMinRisk] = useState(0);
  const [reviewing, setReviewing] = useState<number | null>(null);
  const [notes, setNotes] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const r = await apiGet<AllClaimsResponse>("/api/claims/all", {
        status_filter: statusFilter,
        submitted_by: userFilter,
        min_risk: minRisk,
        limit: 200,
      });
      setData(r.claims);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally { setLoading(false); }
  }

  useEffect(() => { load(); }, [statusFilter, userFilter, minRisk]); // eslint-disable-line

  async function review(id: number, decision: string) {
    try {
      const r = await apiPost<ReviewResponse>(`/api/claims/${id}/review`, { decision, notes });
      setData((d) => d.map((c) => c.id === id ? { ...c, status: r.status } : c));
      setReviewing(null);
      setNotes("");
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  }

  const COLS: Column<UserClaim>[] = [
    { key: "claim_no", header: "Claim No", render: (r) => <span className="font-mono text-[11px]">{r.claim_no}</span> },
    { key: "submitted_by", header: "User" },
    { key: "status", header: "Status", render: (r) => <StatusBadge s={r.status} /> },
    { key: "stockist_code", header: "Stockist" },
    { key: "batch_no", header: "Batch", render: (r) => <span className="font-mono text-[11px]">{r.batch_no}</span> },
    { key: "sku_code", header: "SKU" },
    { key: "claim_type", header: "Type", render: (r) => <span className="text-[11px]">{r.claim_type}</span> },
    { key: "qty_claimed", header: "Qty", render: (r) => num(r.qty_claimed) },
    { key: "claim_value_inr", header: "Value", render: (r) => inr(r.claim_value_inr) },
    { key: "recovery_amount_inr", header: "Recovery", render: (r) => inr(r.recovery_amount_inr) },
    {
      key: "risk_score",
      header: "Risk",
      render: (r) => (
        <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold border ${
          r.risk_score >= 50 ? "bg-danger/15 text-danger border-danger/30"
            : r.risk_score >= 25 ? "bg-warn/15 text-warn border-warn/30"
            : "bg-ok/15 text-ok border-ok/30"}`}>
          {r.risk_score}
        </span>
      ),
    },
    {
      key: "risk_flags",
      header: "Flags",
      render: (r) => (
        <div className="flex flex-wrap gap-1">
          {r.risk_flags.filter(Boolean).map((f) => (
            <span key={f} className="px-1.5 py-0.5 rounded text-[10px] bg-danger/10 text-danger border border-danger/20">{f}</span>
          ))}
        </div>
      ),
    },
    { key: "created_at", header: "Filed", render: (r) => <span className="text-[11px]">{shortDate(r.created_at)}</span> },
    {
      key: "id",
      header: "Action",
      render: (r) => (
        r.status === "Submitted" || r.status === "Under Review" ? (
          <div className="flex gap-1.5">
            <button onClick={() => review(r.id, "Approved")}
              className="px-2 py-0.5 text-[11px] bg-ok/15 text-ok border border-ok/30 rounded hover:bg-ok/25 whitespace-nowrap">
              Approve
            </button>
            <button onClick={() => review(r.id, "Rejected")}
              className="px-2 py-0.5 text-[11px] bg-danger/15 text-danger border border-danger/30 rounded hover:bg-danger/25 whitespace-nowrap">
              Reject
            </button>
          </div>
        ) : <span className="text-ink3 text-[11px]">—</span>
      ),
    },
  ];

  const totalValue = data.reduce((s, c) => s + c.claim_value_inr, 0);
  const highRisk = data.filter((c) => c.risk_score >= 50).length;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-raised border border-line text-ink text-[13px] rounded-sm px-2.5 py-1.5 outline-none focus:border-brand">
          {["", "Submitted", "Under Review", "Approved", "Rejected", "Credited"].map((s) => (
            <option key={s} value={s}>{s || "All Statuses"}</option>
          ))}
        </select>
        <input value={userFilter} onChange={(e) => setUserFilter(e.target.value)}
          placeholder="Filter by username"
          className="bg-raised border border-line text-ink text-[13px] rounded-sm px-2.5 py-1.5 outline-none focus:border-brand w-36" />
        <select value={minRisk} onChange={(e) => setMinRisk(Number(e.target.value))}
          className="bg-raised border border-line text-ink text-[13px] rounded-sm px-2.5 py-1.5 outline-none focus:border-brand">
          <option value={0}>Any risk</option>
          <option value={25}>≥ 25 (Medium+)</option>
          <option value={50}>≥ 50 (High)</option>
        </select>
        <button onClick={load} className="px-3.5 py-1.5 bg-brand text-white text-[13px] rounded-sm font-medium hover:opacity-85">
          Load
        </button>
      </div>

      <div className="flex gap-2 text-[12px] flex-wrap">
        <span className="px-3 py-1 bg-raised border border-line rounded-full text-ink2">
          {num(data.length)} claims · <strong className="text-ink">{inr(totalValue, { compact: true })}</strong>
        </span>
        <span className="px-3 py-1 bg-raised border border-line rounded-full text-ink2">
          High risk: <strong className="text-danger">{num(highRisk)}</strong>
        </span>
      </div>

      <Card title="All user-submitted claims — auditor review">
        {loading ? <Loader label="Loading claims…" />
          : error ? <PageMsg tone="danger">{error}</PageMsg>
          : <DataTable
              columns={COLS}
              data={data}
              maxHeight={560}
              empty="No claims match the selected filters."
              rowKey={(_, i) => i}
            />}
      </Card>
    </div>
  );
}
