"use client";

import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";
import {
  apiPost,
  setToken,
  setUser as setApiUser,
  clearToken,
  clearUser,
  getUser,
} from "@/lib/api";
import type { AuthUser, LoginResponse } from "@/lib/types";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<AuthUser>;
  demoLogin: (role: string) => Promise<AuthUser>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<AuthUser | null>(() => getUser());
  const [loading, setLoading] = useState(false);

  const login = useCallback(async (username: string, password: string) => {
    setLoading(true);
    try {
      const res = await apiPost<LoginResponse>("/api/auth/login", {
        username,
        password,
      });
      setToken(res.access_token);
      const u: AuthUser = { username: res.username, role: res.role };
      setApiUser(u);
      setUserState(u);
      return u;
    } finally {
      setLoading(false);
    }
  }, []);

  const demoLogin = useCallback(async (role: string) => {
    setLoading(true);
    try {
      const res = await apiPost<LoginResponse>("/api/auth/demo-login", { role });
      setToken(res.access_token);
      const u: AuthUser = { username: res.username, role: res.role };
      setApiUser(u);
      setUserState(u);
      return u;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    clearToken();
    clearUser();
    setUserState(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, demoLogin, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
