"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, readSession, writeSession } from "./api";
import type { Role, Session } from "./types";

interface AuthState {
  session: Session | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<Session>;
  logout: () => Promise<void>;
  hasRole: (...roles: Role[]) => boolean;
}

const AuthContext = createContext<AuthState | null>(null);

interface LoginResponse {
  access_token: string;
  expires_at: string;
  user: Session["user"];
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setSession(readSession());
    setReady(true);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await api<LoginResponse>("/api/v1/auth/staff/login", { method: "POST", body: { email, password } });
    const next: Session = { token: res.access_token, expiresAt: res.expires_at, user: res.user };
    writeSession(next);
    setSession(next);
    return next;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api("/api/v1/auth/logout", { method: "POST" });
    } catch {
      /* token may already be invalid */
    }
    writeSession(null);
    setSession(null);
  }, []);

  const hasRole = useCallback((...roles: Role[]) => !!session && roles.includes(session.user.role), [session]);

  const value = useMemo(() => ({ session, ready, login, logout, hasRole }), [session, ready, login, logout, hasRole]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

export const isAdminRole = (role?: Role) => role === "ADMIN" || role === "SUPER_ADMIN";
