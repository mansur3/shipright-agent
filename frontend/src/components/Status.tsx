import clsx from "clsx";
import type { ReactNode } from "react";

export function Loader({ label = "Loading…" }: { label?: string }) {
  return <div className="text-ink3 text-[13px] py-4">{label}</div>;
}

export function PageMsg({
  title,
  children,
  tone = "default",
}: {
  title?: string;
  children?: ReactNode;
  tone?: "default" | "danger" | "ok";
}) {
  return (
    <div
      className={clsx(
        "rounded-[10px] border p-4 text-[13px] fade-in",
        tone === "danger" && "border-danger/40 bg-danger/10 text-danger",
        tone === "ok" && "border-ok/40 bg-ok/10 text-ok",
        tone === "default" && "border-line bg-panel text-ink2"
      )}
    >
      {title && <div className="font-semibold mb-1">{title}</div>}
      <div>{children ?? "Nothing to show."}</div>
    </div>
  );
}

/** Coloured pill for a claim/risk status string. */
export function StatusPill({ status }: { status: string }) {
  const s = (status || "").toLowerCase();
  const cls = clsx(
    "inline-block text-[11px] font-semibold px-2 py-0.5 rounded-full",
    s.includes("approv") && "bg-ok/15 text-ok",
    s.includes("reject") && "bg-danger/15 text-danger",
    s.includes("credit") && "bg-ok/15 text-ok",
    s.includes("review") && "bg-warn/15 text-warn",
    s.includes("submit") && "bg-brand/15 text-brand",
    s.includes("pending") && "bg-warn/15 text-warn",
    !s.match(/approv|reject|credit|review|submit|pending/) && "bg-raised text-ink2 border border-line"
  );
  return <span className={cls}>{status || "—"}</span>;
}

export function RiskPill({ level }: { level: string }) {
  const l = (level || "").toUpperCase();
  const cls = clsx(
    "inline-block text-[11px] font-semibold px-2 py-0.5 rounded-full",
    l === "HIGH" && "bg-danger/15 text-danger",
    l === "MEDIUM" && "bg-warn/15 text-warn",
    l === "LOW" && "bg-ok/15 text-ok",
    !["HIGH", "MEDIUM", "LOW"].includes(l) && "bg-raised text-ink2 border border-line"
  );
  return <span className={cls}>{l || "—"}</span>;
}
