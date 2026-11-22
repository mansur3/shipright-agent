"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { ApiError, apiGet, getUser } from "@/lib/api";
import { homeFor } from "@/lib/nav";
import type { Role } from "@/lib/types";

const DEMO_LABELS: Record<string, string> = {
  claims_finance: "Claims Finance (Controller's team): check a claim",
  supply_chain: "Supply Chain: allocation, FEFO, stock",
  cfo: "CFO: money to recover, scheme cap, returns",
};

export default function LoginPage() {
  const router = useRouter();
  const { login, demoLogin, loading } = useAuth();
  const [demoRoles, setDemoRoles] = useState<string[]>([]);

  useEffect(() => {
    apiGet<{ enabled: boolean; roles: string[] }>("/api/auth/demo-status").then((d) => setDemoRoles(d.enabled ? d.roles : [])).catch(() => setDemoRoles([]));
  }, []);

  async function enterDemo(role: string) {
    setError("");
    setBusy(true);
    try {
      await demoLogin(role);
      router.replace(homeFor(role as Role));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Demo entry failed.");
    } finally {
      setBusy(false);
    }
  }
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(username.trim(), password);
      router.replace(homeFor(getUser()?.role));
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Login failed. Is the backend running on http://localhost:8000?"
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen grid place-items-center px-4 bg-canvas">
      <div className="w-[380px] max-w-[95vw] bg-panel border border-line rounded-[14px] px-9 py-8 fade-in">
        <div className="flex items-center gap-2.5 text-xl font-bold mb-1">
          <span className="w-9 h-9 grid place-items-center rounded-sm bg-brand text-white shadow-glow">
            S
          </span>
          Sankalp AI
        </div>
        <p className="text-xs text-ink3 mb-7">
          Pfizer Channel Intelligence Platform
        </p>

        <form onSubmit={submit} className="flex flex-col gap-3.5">
          <label className="flex flex-col gap-1.5 text-xs text-ink2">
            Username
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              autoComplete="username"
              className="bg-raised border border-line rounded-sm px-2.5 py-2 text-[13px] text-ink outline-none focus:border-brand transition-colors"
            />
          </label>
          <label className="flex flex-col gap-1.5 text-xs text-ink2">
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              className="bg-raised border border-line rounded-sm px-2.5 py-2 text-[13px] text-ink outline-none focus:border-brand transition-colors"
            />
          </label>

          {error && (
            <div className="text-danger text-xs bg-danger/10 border border-danger/30 rounded-sm px-2.5 py-2">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={busy || loading}
            className="bg-brand text-white rounded-sm py-2.5 text-[13px] font-semibold hover:opacity-85 disabled:opacity-50 transition-opacity"
          >
            {busy || loading ? "Signing in…" : "Sign in"}
          </button>
        </form>

        {demoRoles.length > 0 && (
          <div className="mt-5 pt-3 border-t border-line text-[11px] text-ink3 leading-relaxed">
            <div className="font-semibold text-ink2 mb-1.5">Panel demo, no password (fictional data, read-only roles):</div>
            <div className="flex flex-col gap-1.5">
              {demoRoles.map((r) => (
                <button key={r} type="button" disabled={busy || loading} onClick={() => enterDemo(r)}
                  className="text-left border border-line rounded-sm px-2.5 py-2 text-[12px] text-ink2 hover:border-brand hover:text-brand disabled:opacity-50 transition-colors">
                  {DEMO_LABELS[r] ?? r}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
