"use client";

import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "./AuthProvider";
import { PAGE_TITLES } from "@/lib/nav";

export default function TopBar({ onMenu = () => {} }: { onMenu?: () => void }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const path = pathname.length > 1 ? pathname.replace(/\/$/, "") : pathname;
  const title = PAGE_TITLES[path] ?? "Sankalp AI";

  return (
    <header className="h-14 bg-panel border-b border-line flex items-center justify-between px-3 sm:px-6 shrink-0 gap-2">
      <div className="flex items-center gap-2 min-w-0">
        <button type="button" onClick={onMenu} aria-label="Open menu" className="md:hidden border border-line rounded-sm px-2.5 py-1.5 bg-raised text-ink2">☰</button>
        <div className="text-base font-semibold truncate">{title}</div>
      </div>
      <div className="flex items-center gap-2">
        <span className="hidden sm:flex text-[11px] font-semibold px-2.5 py-[3px] rounded-full bg-[#10b9811a] text-ok items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-ok animate-pulse" />
          LIVE
        </span>
        <span className="text-[11px] font-semibold px-2.5 py-[3px] rounded-full bg-raised border border-line text-ink2">
          {user?.role}
        </span>
        <span className="text-[11px] text-ink2 hidden sm:inline">
          {user?.username}
        </span>
        <button
          onClick={() => {
            logout();
            router.replace("/");
          }}
          className="text-xs text-ink2 hover:text-danger border border-line rounded-sm px-3 py-1.5 bg-raised transition-colors"
        >
          Sign out
        </button>
      </div>
    </header>
  );
}
