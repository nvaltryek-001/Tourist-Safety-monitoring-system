import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, loadToken, saveToken, setUnauthorizedHandler } from "./api";

export interface Profile {
  tourist_code: string;
  name: string;
  phone: string | null;
  college_email: string | null;
  enrollment_number: string | null;
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  emergency_contact_email: string | null;
  safety_status: string;
  latitude: number | null;
  longitude: number | null;
  location_accuracy: number | null;
  last_location_update: string | null;
  location_consent_at: string | null;
  notify_push: boolean;
  notify_email: boolean;
  push_registered: boolean;
}

interface AuthState {
  ready: boolean;
  signedIn: boolean;
  profile: Profile | null;
  sessionExpired: boolean;
  refreshProfile: () => Promise<Profile | null>;
  completeLogin: (token: string) => Promise<Profile | null>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [signedIn, setSignedIn] = useState(false);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);

  const refreshProfile = useCallback(async () => {
    try {
      const p = await api<Profile>("/api/v1/me");
      setProfile(p);
      return p;
    } catch {
      return null;
    }
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setSignedIn(false);
      setProfile(null);
      setSessionExpired(true);
    });
    (async () => {
      const token = await loadToken();
      if (token) {
        setSignedIn(true);
        await refreshProfile();
      }
      setReady(true);
    })();
    return () => setUnauthorizedHandler(null);
  }, [refreshProfile]);

  const completeLogin = useCallback(
    async (token: string) => {
      await saveToken(token);
      setSessionExpired(false);
      setSignedIn(true);
      return refreshProfile();
    },
    [refreshProfile],
  );

  const logout = useCallback(async () => {
    try {
      await api("/api/v1/auth/logout", { method: "POST" });
    } catch {
      /* already invalid */
    }
    await saveToken(null);
    setSignedIn(false);
    setProfile(null);
  }, []);

  const value = useMemo(
    () => ({ ready, signedIn, profile, sessionExpired, refreshProfile, completeLogin, logout }),
    [ready, signedIn, profile, sessionExpired, refreshProfile, completeLogin, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}
