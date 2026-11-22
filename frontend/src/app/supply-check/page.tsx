"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import Card from "@/components/Card";
import KpiCard from "@/components/KpiCard";
import { Loader, PageMsg } from "@/components/Status";
import { inr, num, pct } from "@/lib/format";

interface CoverRow {
  cnf_code: string; cnf_city: string; stock_inr: number; cover_months: number | null;
  share_of_stock_pct: number; share_of_outward_pct: number; skus_with_no_stock: number;
}
interface CoverResp {
  as_of: string; network_cover_months: number; by_cnf: CoverRow[];
  stock_above_network_cover_inr: number; stock_below_network_cover_inr: number;
  cnfs_lacking_skus_that_other_cnfs_hold_spare: Record<string, { skus_lacking: number; spare_stock_elsewhere_inr: number; spare_covers_months_of_this_cnfs_own_outward: number }>;
  shortage_split_last_6_month_ends: { shortfall_inr: number; allocation_fixable_inr: number; not_coverable_inr: number; allocation_fixable_pct: number };
  note: string;
}
interface FefoRow { cnf_code: string; cnf_city: string; quarter: string; lines: number; breach_lines: number; breach_pct: number; shipped_out_of_order_inr: number }
interface DispatchResp {
  fefo_breaches_by_quarter: FefoRow[];
  short_dated_dispatch: { rows: number; rows_under_60pct: number; share_pct: number; value_inr: number; clause: string };
}
interface CapRow { quarter: string; primary_inr: number; free_inr: number; foc_pct: number; cap_pct: number; over_cap: boolean; over_cap_inr: number }
interface CapResp {
  free_goods_by_quarter: CapRow[];
  scheme_pack_claim_rates: { scheme_pack_rate_pct: number; other_pack_rate_pct: number; multiple: number; tier_a_scheme_pack_rate_pct: number; tier_a_other_pack_rate_pct: number; tier_a_multiple: number; cohort_low_pct: number; cohort_high_pct: number };
}

const CNFS = ["CF-N01", "CF-N02", "CF-E01", "CF-W01", "CF-S01", "CF-S02"];

export default function SupplyCheckPage() {
  const [cover, setCover] = useState<CoverResp | null>(null);
  const [disp, setDisp] = useState<DispatchResp | null>(null);
  const [cap, setCap] = useState<CapResp | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      apiGet<CoverResp>("/api/stock-cover"),
      apiGet<DispatchResp>("/api/dispatch-quality"),
      apiGet<CapResp>("/api/scheme-cap"),
    ])
      .then(([c, d, k]) => { setCover(c); setDisp(d); setCap(k); })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader label="Loading allocation, dispatch and scheme checks…" />;
  if (error) return <PageMsg tone="danger">{error}</PageMsg>;
  if (!cover || !disp || !cap) return <PageMsg>No data available.</PageMsg>;

  const quarters = Array.from(new Set(disp.fefo_breaches_by_quarter.map((r) => r.quarter))).sort().slice(-6);
  const breach = (c: string, q: string) => disp.fefo_breaches_by_quarter.find((r) => r.cnf_code === c && r.quarter === q);
  const n02 = cover.by_cnf.find((r) => r.cnf_code === "CF-N02");
  const e01 = cover.by_cnf.find((r) => r.cnf_code === "CF-E01");
  const lastQ = quarters[quarters.length - 1];
  const e01Last = breach("CF-E01", lastQ);
  const split = cover.shortage_split_last_6_month_ends;
  const sp = cap.scheme_pack_claim_rates;
  const capRows = cap.free_goods_by_quarter.slice(-8);

  return (
    <div className="space-y-4">
      <PageMsg title="Where the shortage and the expiry returns come from">
        Recommendations for the owners, from the extracts. Every figure names its file; nothing here changes any record.
      </PageMsg>

      <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Lucknow share of stock" value={n02 ? pct(n02.share_of_stock_pct) : "—"} sub={n02 ? `vs ${pct(n02.share_of_outward_pct)} of outward volume` : ""} tone="danger" />
        <KpiCard label="Kolkata cover" value={e01?.cover_months ? `${e01.cover_months} months` : "—"} sub={`network ${cover.network_cover_months} months`} tone="warn" />
        <KpiCard label="Shortage fixable by allocation" value={pct(split.allocation_fixable_pct, 0)} sub={`INR ${(split.shortfall_inr / 1e7).toFixed(1)} Cr short, last 6 month-ends`} tone="ok" />
        <KpiCard label={`Kolkata FEFO breaches ${lastQ}`} value={e01Last ? pct(e01Last.breach_pct, 0) : "—"} sub="other five C&Fs: 0%" tone="danger" />
      </div>

      <Card title={`Stock cover by C&F at ${cover.as_of} (stock on hand / extract's average monthly outward)`}>
        <div className="dt-scroll"><table className="dt-table">
          <thead><tr><th>C&F</th><th>Stock (₹)</th><th>Cover (months)</th><th>Share of stock</th><th>Share of outward</th><th>SKUs with no stock</th></tr></thead>
          <tbody>
            {cover.by_cnf.map((r) => (
              <tr key={r.cnf_code}>
                <td>{r.cnf_city} ({r.cnf_code})</td><td>{inr(r.stock_inr, { compact: true })}</td><td>{r.cover_months ?? "—"}</td>
                <td>{pct(r.share_of_stock_pct)}</td><td>{pct(r.share_of_outward_pct)}</td><td>{num(r.skus_with_no_stock)}</td>
              </tr>
            ))}
          </tbody>
        </table></div>
        <p className="text-[12px] text-ink2 mt-2">
          Stock above network-average cover: {inr(cover.stock_above_network_cover_inr, { compact: true })}. Lucknow has none of {cover.cnfs_lacking_skus_that_other_cnfs_hold_spare["CF-N02"]?.skus_lacking ?? 0} SKUs
          that the other C&Fs hold ({inr(cover.cnfs_lacking_skus_that_other_cnfs_hold_spare["CF-N02"]?.spare_stock_elsewhere_inr ?? 0, { compact: true })} spare, about {cover.cnfs_lacking_skus_that_other_cnfs_hold_spare["CF-N02"]?.spare_covers_months_of_this_cnfs_own_outward ?? "—"} months of Lucknow's own demand).
          Recommendation: change the next monthly allocation split (owners: Head, Supply Chain; Demand Planning). {cover.note}.
        </p>
      </Card>

      <Card title="First-expiry-first-out breaches by C&F and quarter (policy: pick oldest batch first)">
        <div className="dt-scroll"><table className="dt-table">
          <thead><tr><th>Quarter</th>{CNFS.map((c) => <th key={c}>{c}</th>)}</tr></thead>
          <tbody>
            {quarters.map((q) => (
              <tr key={q}><td>{q}</td>{CNFS.map((c) => { const b = breach(c, q); return <td key={c} className={b && b.breach_pct > 10 ? "text-danger font-semibold" : ""}>{b ? pct(b.breach_pct, 0) : "—"}</td>; })}</tr>
            ))}
          </tbody>
        </table></div>
        <p className="text-[12px] text-ink2 mt-2">
          A breach is a later-expiry batch shipped while an older batch of the same SKU was on hand at the same C&F at both neighbouring month-ends. Kolkata moved to a new WMS in February 2026.
          Dispatched with under 60% of shelf life left ({disp.short_dated_dispatch.clause}): {num(disp.short_dated_dispatch.rows_under_60pct)} of {num(disp.short_dated_dispatch.rows)} invoice rows ({pct(disp.short_dated_dispatch.share_pct)}).
        </p>
      </Card>

      <Card title="Free goods against the 3% cap, and scheme packs that come back as claims">
        <div className="dt-scroll"><table className="dt-table">
          <thead><tr><th>Quarter</th><th>Primary (₹)</th><th>Free goods (₹)</th><th>Free %</th><th>Cap</th><th>Above cap (₹)</th></tr></thead>
          <tbody>
            {capRows.map((r) => (
              <tr key={r.quarter}><td>{r.quarter}</td><td>{inr(r.primary_inr, { compact: true })}</td><td>{inr(r.free_inr, { compact: true })}</td>
                <td className={r.over_cap ? "text-danger font-semibold" : ""}>{r.foc_pct}%</td><td>{r.cap_pct}%</td><td>{r.over_cap ? inr(r.over_cap_inr, { compact: true }) : "—"}</td></tr>
            ))}
          </tbody>
        </table></div>
        <p className="text-[12px] text-ink2 mt-2">
          Packs supplied under a quarter-end scheme came back as claims at {sp.scheme_pack_rate_pct}% against {sp.other_pack_rate_pct}% for other packs ({sp.multiple}x); inside the ten tier-A SKUs alone
          {" "}{sp.tier_a_scheme_pack_rate_pct}% vs {sp.tier_a_other_pack_rate_pct}% ({sp.tier_a_multiple}x). By scheme quarter the rate ran {sp.cohort_low_pct}% to {sp.cohort_high_pct}%.
          This is a measured association, not an experiment. Owners: National Sales Manager (schemes), CFO (cap exceptions).
        </p>
      </Card>
    </div>
  );
}
