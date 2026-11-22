"use client";

import { Fragment, useEffect, useMemo, useState } from "react";
import { Download } from "lucide-react";
import { apiGet } from "@/lib/api";
import Card from "@/components/Card";
import { Loader, PageMsg } from "@/components/Status";
import { inr, num, shortDate } from "@/lib/format";

interface Row {
  claim_no: string; stockist_code: string; stockist_name: string; batch_no: string; sku_code: string; claim_type: string;
  claim_date: string | null; status: string; credited_inr: number; amount_inr: number; bucket: string; tier: string;
  rule_id: string; clause: string; reason: string; decision: string;
}

const BUCKETS: { key: string; label: string; hint: string }[] = [
  { key: "", label: "All", hint: "Everything on this list" },
  { key: "hold", label: "Hold: pending", hint: "Not credited yet, fails a rule" },
  { key: "recover_t1", label: "Recover: T1", hint: "Credited, policy text breached" },
  { key: "recover_t2", label: "Recover: T2", hint: "Credited, probable breach" },
];

function csv(rows: Row[]): string {
  const head = ["claim_no", "stockist_code", "stockist_name", "batch_no", "sku_code", "claim_type", "claim_date", "status", "credited_inr", "amount_inr", "bucket", "tier", "rule_id", "policy_clause", "reason"];
  const esc = (v: unknown) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  return [head.join(","), ...rows.map((r) => [r.claim_no, r.stockist_code, r.stockist_name, r.batch_no, r.sku_code, r.claim_type, r.claim_date, r.status, r.credited_inr, r.amount_inr, r.bucket, r.tier, r.rule_id, r.clause, r.reason].map(esc).join(","))].join("\n");
}

export default function RecoveryListPage() {
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [bucket, setBucket] = useState("");
  const [q, setQ] = useState("");
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    apiGet<{ claims: Row[] }>("/api/analytics/recovery/claims")
      .then((r) => setRows(r.claims))
      .catch((e: Error) => setErr(e.message))
      .finally(() => setLoading(false));
  }, []);

  const shown = useMemo(() => {
    const s = q.trim().toLowerCase();
    return rows.filter((r) => (!bucket || r.bucket === bucket) && (!s || `${r.claim_no} ${r.stockist_code} ${r.stockist_name} ${r.batch_no}`.toLowerCase().includes(s)));
  }, [rows, bucket, q]);
  const total = shown.reduce((s, r) => s + r.amount_inr, 0);

  function download() {
    const url = URL.createObjectURL(new Blob([csv(shown)], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "recovery_list.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  if (loading) return <Loader label="Loading the recovery list…" />;
  if (err) return <PageMsg tone="danger">{err}</PageMsg>;

  return (
    <div className="space-y-4">
      <Card
        title={<span>Recovery list <span className="ml-2 text-[11px] font-normal text-ink3">claims that broke a clear rule, with the clause and the reason</span></span>}
        right={
          <button onClick={download} className="inline-flex items-center gap-1.5 text-[12px] px-3 py-1.5 rounded-sm border border-line text-ink2 hover:border-brand hover:text-brand">
            <Download size={13} /> Download CSV
          </button>
        }
      >
        <div className="flex flex-wrap items-center gap-2 mb-3">
          {BUCKETS.map((b) => (
            <button key={b.key} onClick={() => setBucket(b.key)} title={b.hint}
              className={`text-[12px] px-3 py-1.5 rounded-full border transition-colors ${bucket === b.key ? "bg-brand text-white border-brand" : "bg-raised border-line text-ink2 hover:border-brand"}`}>
              {b.label}
            </button>
          ))}
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search claim, stockist or batch"
            className="ml-auto bg-raised border border-line rounded-sm px-3 py-1.5 text-[13px] outline-none focus:border-brand w-60" />
        </div>
        <p className="text-[12px] text-ink2 mb-2">
          <strong className="text-ink">{num(shown.length)}</strong> claims, <strong className="text-danger">{inr(total, { compact: true })}</strong> shown.
          Hold and recover are different kinds of money; filter to one before reading the total.
        </p>
        <div className="overflow-auto max-h-[62vh] rounded border border-line">
          <table className="w-full text-[12.5px] border-collapse min-w-[900px]">
            <thead className="sticky top-0 bg-panel z-10">
              <tr className="border-b border-line text-ink2 text-left">
                {["Claim", "Stockist", "Batch", "Type", "Date", "Amount", "Tier", "Why"].map((h, i) => (
                  <th key={h} className={`px-3 py-2 font-medium whitespace-nowrap ${i === 5 ? "text-right" : ""}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {shown.slice(0, 300).map((r) => (
                <Fragment key={r.claim_no}>
                  <tr onClick={() => setOpen(open === r.claim_no ? null : r.claim_no)} className="border-b border-line hover:bg-raised cursor-pointer align-top">
                    <td className="px-3 py-2 font-mono text-[11.5px] whitespace-nowrap">{r.claim_no}</td>
                    <td className="px-3 py-2">{r.stockist_name} <span className="text-ink3 font-mono text-[11px]">{r.stockist_code}</span></td>
                    <td className="px-3 py-2 font-mono text-[11.5px]">{r.batch_no}</td>
                    <td className="px-3 py-2 text-ink2 whitespace-nowrap">{r.claim_type}</td>
                    <td className="px-3 py-2 text-ink2 whitespace-nowrap">{shortDate(r.claim_date)}</td>
                    <td className="px-3 py-2 text-right font-semibold whitespace-nowrap">{inr(r.amount_inr)}</td>
                    <td className="px-3 py-2">
                      <span className={`px-2 py-0.5 rounded-full text-[11px] border ${r.bucket === "hold" ? "bg-warn/15 text-warn border-warn/30" : r.tier === "T1" ? "bg-danger/15 text-danger border-danger/30" : "bg-raised text-ink2 border-line"}`}>
                        {r.bucket === "hold" ? `Hold ${r.tier}` : r.tier}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-ink2 max-w-[340px] truncate">{r.reason}</td>
                  </tr>
                  {open === r.claim_no && (
                    <tr className="border-b border-line bg-canvas">
                      <td colSpan={8} className="px-4 py-3 text-[12.5px] text-ink2 leading-relaxed">
                        <div><strong className="text-ink">Rule:</strong> {r.rule_id} {r.clause && <span>(policy clause {r.clause})</span>}</div>
                        <div><strong className="text-ink">Reason:</strong> {r.reason}</div>
                        <div><strong className="text-ink">Credited:</strong> {inr(r.credited_inr)} · <strong className="text-ink">Amount to {r.bucket === "hold" ? "hold" : "recover"}:</strong> {inr(r.amount_inr)} · <strong className="text-ink">Status:</strong> {r.status}</div>
                        <div className="text-ink3 mt-1">A recommendation only. Commercial Finance decides what to recover.</div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
        {shown.length > 300 && <p className="text-[11px] text-ink3 mt-2">Showing the first 300 by amount. The CSV has all {num(shown.length)}.</p>}
      </Card>
    </div>
  );
}
