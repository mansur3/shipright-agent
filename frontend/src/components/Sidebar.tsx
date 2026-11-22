"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import clsx from "clsx";
import { useAuth } from "./AuthProvider";
import { navForRole } from "@/lib/nav";
import { apiGet } from "@/lib/api";
import type { HealthResponse } from "@/lib/types";

export default function Sidebar({ open = false, onClose = () => {} }: { open?: boolean; onClose?: () => void }) {
  const pathname = usePathname();
  const { user } = useAuth();
  const [health, setHealth] = useState<"loading" | "ok" | "err">("loading");

  useEffect(() => {
    let active = true;
    apiGet<HealthResponse>("/api/health")
      .then((d) => active && setHealth(d.ok ? "ok" : "err"))
      .catch(() => active && setHealth("err"));
    return () => {
      active = false;
    };
  }, []);

  const items = navForRole(user?.role);

  return (
    <>
      {open && <div className="fixed inset-0 z-30 bg-black/50 md:hidden" onClick={onClose} aria-hidden="true" />}
    <aside className={clsx("w-[220px] shrink-0 bg-panel border-r border-line flex flex-col h-screen z-40 fixed inset-y-0 left-0 transition-transform md:sticky md:top-0 md:translate-x-0 md:z-20", open ? "translate-x-0" : "-translate-x-full")}>
      <div className="flex items-center gap-2.5 px-4 py-[18px] border-b border-line">
        <div className="w-8 h-8 grid place-items-center rounded-sm bg-brand text-white font-bold text-base shadow-glow">
          S
        </div>
        <div className="font-bold text-[15px] tracking-tight">Sankalp AI</div>
      </div>

      <nav className="flex-1 px-2 py-2.5 flex flex-col gap-0.5 overflow-y-auto">
        {items.map((it) => {
          const Icon = it.icon;
          const active =
            pathname === it.href || pathname.startsWith(it.href + "/");
          return (
            <Link
              key={it.href}
              href={it.href}
              className={clsx(
                "flex items-center gap-2.5 px-3 py-2 rounded-sm text-[13px] transition-colors",
                active
                  ? "bg-[#2563eb22] text-brand font-semibold"
                  : "text-ink2 hover:bg-raised hover:text-ink"
              )}
            >
              <Icon size={15} className="shrink-0" />
              <span className="truncate">{it.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="px-4 py-3.5 border-t border-line flex items-center gap-2 text-xs text-ink3">
        <span
          className={clsx(
            "w-2 h-2 rounded-full shrink-0",
            health === "loading" && "bg-ink3",
            health === "ok" && "bg-ok shadow-[0_0_6px_#10b981]",
            health === "err" && "bg-danger"
          )}
        />
        {health === "loading"
          ? "Checking…"
          : health === "ok"
            ? "System healthy"
            : "Backend offline"}
      </div>
    </aside>
    </>
  );
}
