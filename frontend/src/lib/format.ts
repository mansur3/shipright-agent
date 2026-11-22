/** Formatting helpers — INR uses the Indian numbering system. */

export function inr(
  n: number | null | undefined,
  opts: { compact?: boolean } = {}
): string {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "₹0";
  const v = Number(n);
  if (opts.compact) {
    const abs = Math.abs(v);
    if (abs >= 1e7) return `₹${(v / 1e7).toFixed(2)} Cr`;
    if (abs >= 1e5) return `₹${(v / 1e5).toFixed(2)} L`;
    if (abs >= 1e3) return `₹${(v / 1e3).toFixed(1)}K`;
    return `₹${v.toFixed(0)}`;
  }
  return `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

export function pct(n: number | null | undefined, digits = 1): string {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  return `${Number(n).toFixed(digits)}%`;
}

export function num(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  return Number(n).toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

export function shortDate(s: string | null | undefined): string {
  if (!s) return "—";
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return s;
  return d.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function dateTime(s: string | null | undefined): string {
  if (!s) return "—";
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return s;
  return d.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}
