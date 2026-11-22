"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "./AuthProvider";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";
import { homeFor } from "@/lib/nav";

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user } = useAuth();
  const isLogin = pathname === "/";
  // The agent catalogue is documentation with no data in it, so it opens without signing in.
  const isPublic = pathname.startsWith("/agents");
  const [menuOpen, setMenuOpen] = useState(false);

  // close the phone drawer whenever the page changes
  useEffect(() => { setMenuOpen(false); }, [pathname]);

  // Guard routes: bounce unauthenticated users to the login screen, and
  // send already-authenticated users away from the login screen.
  useEffect(() => {
    if (!isLogin && !isPublic && !user) router.replace("/");
    if (isLogin && user) router.replace(homeFor(user.role));
  }, [isLogin, isPublic, user, router]);

  if (isLogin) {
    return <main className="min-h-screen">{children}</main>;
  }

  if (!user && isPublic) {
    return <main className="min-h-screen p-4 sm:p-6 bg-canvas">{children}</main>;
  }

  if (!user) {
    return (
      <div className="min-h-screen grid place-items-center text-ink2 text-sm">
        Redirecting to sign in…
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
      <div className="flex-1 min-w-0 flex flex-col">
        <TopBar onMenu={() => setMenuOpen((o) => !o)} />
        <main className="flex-1 min-h-0 overflow-y-auto p-3 sm:p-5 md:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
