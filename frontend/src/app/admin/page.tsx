"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";
import type {
  AdminUser,
  AuditLogEntry,
  BatchHistoryEntry,
  RunBatchResponse,
} from "@/lib/types";
import Card from "@/components/Card";
import { Loader, PageMsg } from "@/components/Status";
import { inr, num, dateTime } from "@/lib/format";

export default function AdminPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [history, setHistory] = useState<BatchHistoryEntry[]>([]);
  const [audit, setAudit] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [batchRunning, setBatchRunning] = useState(false);
  const [batchMsg, setBatchMsg] = useState("");

  async function loadAll() {
    setLoading(true);
    const [u, h, a] = await Promise.allSettled([
      apiGet<AdminUser[]>("/api/admin/users"),
      apiGet<BatchHistoryEntry[]>("/api/admin/batch-history?limit=10"),
      apiGet<AuditLogEntry[]>("/api/admin/audit-log?limit=30"),
    ]);
    if (u.status === "fulfilled") setUsers(u.value);
    if (h.status === "fulfilled") setHistory(h.value);
    if (a.status === "fulfilled") setAudit(a.value ?? []);
    setLoading(false);
  }

  useEffect(() => {
    loadAll();
  }, []);

  async function runBatch() {
    setBatchRunning(true);
    setBatchMsg("");
    try {
      const r = await apiPost<RunBatchResponse>("/api/admin/run-batch", {});
      setBatchMsg(
        `✅ Batch complete — ${inr(r.total_addressable_inr, { compact: true })} addressable · ${r.findings} findings · ${r.stock_alerts} alerts`,
      );
      await loadAll();
    } catch (e: unknown) {
      setBatchMsg(`❌ ${e instanceof Error ? e.message : "Batch failed"}`);
    } finally {
      setBatchRunning(false);
    }
  }

  if (loading) return <Loader label="Loading admin panel…" />;

  return (
    <div className="space-y-5">
      {/* Batch control */}
      <Card title="Batch Processing — re-run the full data analysis">
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={runBatch}
            disabled={batchRunning}
            className="px-4 py-2 bg-brand text-white text-[13px] font-semibold rounded-sm hover:opacity-85 disabled:opacity-50 transition-opacity"
          >
            {batchRunning ? "Running…" : "Run Batch Now"}
          </button>
          {batchMsg && <p className="text-[13px] text-ink2">{batchMsg}</p>}
        </div>
        {history.length > 0 && (
          <div className="mt-4 space-y-2">
            <p className="text-[11px] text-ink3 font-medium uppercase tracking-wide">
              Recent runs
            </p>
            {history.map((r) => (
              <div
                key={r.id}
                className="flex flex-wrap items-center gap-3 text-[12px] border-b border-line pb-2"
              >
                <span className="text-ink2">{dateTime(r.run_at)}</span>
                <span className="text-ink font-semibold">
                  {inr(r.total_addressable_inr, { compact: true })} addressable
                </span>
                <span className="text-ink2">
                  {num(r.duplicate_groups)} dup groups
                </span>
                <span className="text-ink2">
                  {num(r.high_risk_stockists)} high-risk stockists
                </span>
              </div>
            ))}
          </div>
        )}
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Users */}
        <Card title={`Users (${users.length})`}>
          <div className="overflow-auto max-h-80">
            <table className="w-full text-[12px] border-collapse">
              <thead className="sticky top-0">
                <tr className="bg-canvas border-b border-line">
                  {["ID", "Username", "Email", "Role", "CNF", "Active"].map(
                    (h) => (
                      <th
                        key={h}
                        className="px-2.5 py-2 text-left text-ink2 font-medium whitespace-nowrap"
                      >
                        {h}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr
                    key={u.id}
                    className="border-b border-line hover:bg-raised"
                  >
                    <td className="px-2.5 py-2 text-ink3">{u.id}</td>
                    <td className="px-2.5 py-2 font-semibold">{u.username}</td>
                    <td className="px-2.5 py-2 text-ink2">{u.email}</td>
                    <td className="px-2.5 py-2">
                      <span className="px-1.5 py-0.5 bg-raised border border-line rounded text-ink2">
                        {u.role}
                      </span>
                    </td>
                    <td className="px-2.5 py-2 text-ink2">
                      {u.cnf_code ?? "—"}
                    </td>
                    <td className="px-2.5 py-2">
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${u.is_active ? "text-ok" : "text-danger"}`}
                      >
                        {u.is_active ? "Active" : "Disabled"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Audit log */}
        <Card title="Audit log (last 30)">
          <div className="overflow-auto max-h-80 space-y-1.5">
            {audit.length === 0 ? (
              <p className="text-ink3 text-[12px] py-4 text-center">
                No audit entries yet.
              </p>
            ) : (
              audit.map((l) => (
                <div
                  key={l.id}
                  className="text-[11px] border-b border-line pb-1.5 flex gap-2 items-start"
                >
                  <span
                    className={`font-semibold flex-shrink-0 ${l.success ? "text-ok" : "text-danger"}`}
                  >
                    {l.success ? "✓" : "✗"}
                  </span>
                  <div>
                    <span className="text-ink font-medium">{l.username}</span>
                    {" · "}
                    <span className="text-ink2">{l.action}</span>
                    {l.detail && (
                      <span className="text-ink3"> — {l.detail}</span>
                    )}
                    <span className="text-ink3 block">
                      {dateTime(l.created_at)}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
