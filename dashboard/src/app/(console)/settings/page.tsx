"use client";

import { useState } from "react";
import { Badge, Button, Field, PageHeader, Panel, useToast } from "@/components/ui";
import { API_URL, api } from "@/lib/api";
import { isAdminRole, useAuth } from "@/lib/auth";
import { dateTime } from "@/lib/format";
import { useApi } from "@/lib/hooks";

interface Info {
  environment: string;
  database_dialect: string;
  schema_version: number;
  email_provider: string;
  push_notifications: string;
  otp_dev_echo: boolean;
  location_retention_days: number;
  websocket: { connections: number; staff: number; tourists: number };
  allowed_origins: string[];
}

interface SessionRow {
  id: number;
  created_at: string;
  expires_at: string;
  user_agent: string | null;
  current: boolean;
}

export default function SettingsPage() {
  const { session } = useAuth();
  const admin = isAdminRole(session?.user.role);
  const toast = useToast();
  const info = useApi<Info>(admin ? "/api/v1/system/info" : null);
  const sessions = useApi<SessionRow[]>("/api/v1/auth/sessions");
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [busy, setBusy] = useState(false);

  async function changePassword(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api("/api/v1/auth/staff/change-password", { method: "POST", body: { current_password: current, new_password: next } });
      toast("Password changed. Other sessions were signed out.");
      setCurrent("");
      setNext("");
      void sessions.reload();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed", "error");
    } finally {
      setBusy(false);
    }
  }

  async function purge() {
    try {
      const r = await api<{ deleted: number; retention_days: number }>("/api/v1/admin/retention/purge", { method: "POST" });
      toast(`Removed ${r.deleted} location points older than ${r.retention_days} days`);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed", "error");
    }
  }

  return (
    <>
      <PageHeader title="Settings" subtitle="Your account security and system configuration status." />
      <div className="grid gap-6 xl:grid-cols-2">
        <Panel title="Change password">
          <form onSubmit={changePassword} className="space-y-3">
            <Field label="Current password"><input className="field" type="password" autoComplete="current-password" required value={current} onChange={(e) => setCurrent(e.target.value)} /></Field>
            <Field label="New password" hint="At least 10 characters with upper case, lower case and a digit."><input className="field" type="password" autoComplete="new-password" minLength={10} required value={next} onChange={(e) => setNext(e.target.value)} /></Field>
            <Button variant="primary" type="submit" loading={busy}>Update password</Button>
          </form>
        </Panel>

        <Panel title="Active sessions" action={<Button size="sm" onClick={async () => { await api("/api/v1/auth/sessions/revoke-others", { method: "POST" }); toast("Other sessions signed out"); void sessions.reload(); }}>Sign out other sessions</Button>}>
          <ul className="space-y-2 text-sm">
            {(sessions.data ?? []).map((s) => (
              <li key={s.id} className="flex items-start justify-between gap-3 rounded border hairline px-3 py-2">
                <span>
                  <span className="block text-xs">{s.user_agent?.slice(0, 80) || "Unknown device"}</span>
                  <span className="text-[11px] muted">Signed in {dateTime(s.created_at)} · expires {dateTime(s.expires_at)}</span>
                </span>
                {s.current ? <Badge tone="safe">This device</Badge> : (
                  <Button size="sm" variant="ghost" onClick={async () => { await api(`/api/v1/auth/sessions/${s.id}/revoke`, { method: "POST" }); void sessions.reload(); }}>Revoke</Button>
                )}
              </li>
            ))}
          </ul>
        </Panel>

        {admin && (
          <Panel title="System status">
            {info.error ? <p className="text-sm text-orange-700">{info.error}</p> : !info.data ? <p className="text-sm muted">Loading…</p> : (
              <dl className="space-y-2 text-sm">
                <Row k="API" v={<span className="font-mono text-xs">{API_URL}</span>} />
                <Row k="Environment" v={info.data.environment} />
                <Row k="Database" v={`${info.data.database_dialect} · schema v${info.data.schema_version}`} />
                <Row k="Email provider" v={<Badge tone={info.data.email_provider === "not configured" ? "caution" : "safe"}>{info.data.email_provider}</Badge>} />
                <Row k="Push notifications" v={<Badge tone={info.data.push_notifications === "enabled" ? "safe" : "caution"}>{info.data.push_notifications}</Badge>} />
                <Row k="OTP demo echo" v={info.data.otp_dev_echo ? <Badge tone="caution">ON — codes shown in app</Badge> : <Badge tone="safe">Off</Badge>} />
                <Row k="Live connections" v={`${info.data.websocket.staff} staff · ${info.data.websocket.tourists} tourists`} />
                <Row k="Location retention" v={`${info.data.location_retention_days} days`} />
              </dl>
            )}
          </Panel>
        )}
        {admin && (
          <Panel title="Privacy & retention">
            <p className="text-sm muted">Location history older than the retention period can be removed permanently. Tourists can also delete their own history from the app.</p>
            <Button className="mt-3" variant="danger" onClick={purge}>Purge expired location history</Button>
          </Panel>
        )}
      </div>
    </>
  );
}

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return <div className="flex items-center justify-between gap-3"><dt className="muted">{k}</dt><dd className="text-right">{v}</dd></div>;
}
