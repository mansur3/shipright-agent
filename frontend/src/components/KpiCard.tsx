import clsx from "clsx";
import type { ReactNode } from "react";

type Tone = "brand" | "ok" | "warn" | "danger" | "default";

const BAR: Record<Tone, string> = {
  brand: "bg-brand",
  ok: "bg-ok",
  warn: "bg-warn",
  danger: "bg-danger",
  default: "bg-brand",
};

export default function KpiCard({
  label,
  value,
  sub,
  tone = "brand",
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  tone?: Tone;
}) {
  return (
    <div className="relative bg-panel border border-line rounded-[10px] px-[18px] py-4 overflow-hidden">
      <span className={clsx("absolute top-0 left-0 right-0 h-0.5", BAR[tone])} />
      <div className="text-[11px] uppercase tracking-wide text-ink2">{label}</div>
      <div className="text-[26px] font-bold leading-none mt-1.5 mb-0.5">{value}</div>
      {sub && <div className="text-[11px] text-ink3">{sub}</div>}
    </div>
  );
}
