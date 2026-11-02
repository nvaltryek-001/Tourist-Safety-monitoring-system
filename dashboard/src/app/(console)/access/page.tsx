"use client";

import { useState } from "react";
import { Badge, Button, EmptyState, ErrorState, Field, PageHeader, Panel, SkeletonRows, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import type { Paged, Tourist } from "@/lib/types";

interface Access {
  id: number;
  email: string;
  tourist_code: string;
  active: boolean;
  tourist_name: string | null;
  tourist_exists: boolean;
}

export default function AccessPage() {
  const toast = useToast();
  const access = useApi<Access[]>("/api/v1/admin/tourist-access");
  const tourists = useApi<Paged<Tourist>>("/api/v1/admin/tourists?page_size=200&sort=code&order=asc");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const linked = new Set((access.data ?? []).map((a) => a.tourist_code));

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api("/api/v1/admin/tourist-access", { method: "POST", body: { email: email.trim(), tourist_code: code } });
      toast("Gmail login granted");
      setEmail("");
      setCode("");
      void access.reload();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed", "error");
    } finally {
      setBusy(false);
    }
  }

  async function toggle(a: Access) {
    try {
      await api(`/api/v1/admin/tourist-access/${a.id}`, { method: "PATCH", body: { active: !a.active } });
      toast(a.active ? "Login disabled — existing sessions stop at expiry" : "Login enabled");
      void access.reload();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed", "error");
    }
  }

  return (
    <>
      <PageHeader title="Tourist login access" subtitle="Only Gmail addresses on this list can receive a one-time login code in the mobile app. No passwords are used." />
      <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <Panel bodyClass="p-0">
          {access.loading ? <SkeletonRows /> : access.error ? <ErrorState message={access.error} onRetry={access.reload} /> : !access.data?.length ? (
            <EmptyState title="No approved tourist logins yet" hint="Link a registered tourist to their Gmail address on the right." />
          ) : (
            <table className="w-full">
              <thead className="border-b hairline"><tr><th className="th">Gmail</th><th className="th">Tourist</th><th className="th">Status</th><th className="th" /></tr></thead>
              <tbody className="divide-y hairline">
                {access.data.map((a) => (
                  <tr key={a.id}>
                    <td className="td font-mono text-xs">{a.email}</td>
                    <td className="td">{a.tourist_name ?? <span className="text-orange-700">missing tourist</span>}<p className="text-xs muted">{a.tourist_code}</p></td>
                    <td className="td">{a.active ? <Badge tone="safe">Can sign in</Badge> : <Badge tone="neutral">Disabled</Badge>}</td>
                    <td className="td whitespace-nowrap text-right">
                      <Button size="sm" onClick={() => toggle(a)}>{a.active ? "Disable" : "Enable"}</Button>
                      <Button size="sm" variant="ghost" className="text-red-700" onClick={async () => {
                        if (!window.confirm(`Remove Gmail login ${a.email}? The tourist record stays.`)) return;
                        try {
                          await api(`/api/v1/admin/tourist-access/${a.id}`, { method: "DELETE" });
                          toast("Login access removed");
                          void access.reload();
                        } catch (err) {
                          toast(err instanceof Error ? err.message : "Failed", "error");
                        }
                      }}>Remove</Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Panel>
        <Panel title="Grant Gmail login">
          <form onSubmit={add} className="space-y-3">
            <Field label="Tourist">
              <select className="field" required value={code} onChange={(e) => setCode(e.target.value)}>
                <option value="">Choose a tourist…</option>
                {(tourists.data?.items ?? []).filter((t) => !linked.has(t.tourist_code)).map((t) => (
                  <option key={t.tourist_code} value={t.tourist_code}>{t.tourist_code} · {t.name}</option>
                ))}
              </select>
            </Field>
            <Field label="Gmail address" hint="Must end with @gmail.com. Dots and +tags are treated as the same inbox.">
              <input className="field" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@gmail.com" />
            </Field>
            <Button variant="primary" type="submit" loading={busy} className="w-full">Grant access</Button>
          </form>
        </Panel>
      </div>
    </>
  );
}
