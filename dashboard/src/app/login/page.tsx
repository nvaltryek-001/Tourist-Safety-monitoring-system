"use client";

import { ShieldAlert } from "lucide-react";
import { useRouter } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Button, Field } from "@/components/ui";
import { API_URL } from "@/lib/api";
import { isAdminRole, useAuth } from "@/lib/auth";

function LoginForm() {
  const { login, session, ready } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(params.get("expired") ? "Your session expired. Please sign in again." : null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (ready && session) router.replace(isAdminRole(session.user.role) ? "/" : "/police");
  }, [ready, session, router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const s = await login(email.trim(), password);
      router.replace(isAdminRole(s.user.role) ? "/" : "/police");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      <section className="relative hidden overflow-hidden bg-ink-950 p-12 text-slate-200 lg:flex lg:flex-col lg:justify-between">
        <div
          className="absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage:
              "linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)",
            backgroundSize: "48px 48px",
          }}
        />
        <div className="relative flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded bg-brand-600 text-white">
            <ShieldAlert className="h-5 w-5" />
          </div>
          <div>
            <p className="font-semibold text-white">SafeTrail</p>
            <p className="text-xs text-slate-400">Tourist Safety Command</p>
          </div>
        </div>
        <div className="relative max-w-md">
          <h1 className="text-3xl font-semibold leading-tight text-white">
            Live tourist safety, geofencing and SOS response in one console.
          </h1>
          <p className="mt-4 text-sm leading-relaxed text-slate-400">
            Locations are shared only with the tourist&apos;s consent. Officers see contact details only while they handle an
            active emergency. Every access is audit-logged.
          </p>
        </div>
        <p className="relative font-mono text-[11px] text-slate-500">API · {API_URL}</p>
      </section>

      <section className="flex items-center justify-center p-6">
        <form onSubmit={submit} className="w-full max-w-sm space-y-5">
          <div>
            <h2 className="text-xl font-semibold">Staff sign-in</h2>
            <p className="mt-1 text-sm muted">Administrators and police officers. Tourists use the mobile app.</p>
          </div>
          <Field label="Email">
            <input className="field" type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <Field label="Password">
            <input
              className="field"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </Field>
          {error && (
            <p role="alert" className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
              {error}
            </p>
          )}
          <Button variant="primary" type="submit" loading={busy} className="w-full">
            Sign in
          </Button>
          <p className="text-xs muted">Accounts lock for 15 minutes after 5 failed attempts.</p>
        </form>
      </section>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
