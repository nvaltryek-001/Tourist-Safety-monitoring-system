"use client";

import { Plus } from "lucide-react";
import { useState } from "react";
import { Badge, Button, EmptyState, ErrorState, Field, Modal, PageHeader, Panel, SkeletonRows, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { dateTime, humanize } from "@/lib/format";
import { useApi } from "@/lib/hooks";

interface Staff {
  id: number;
  email: string;
  name: string;
  role: string;
  active: boolean;
  badge_number: string | null;
  station: string | null;
  last_login_at: string | null;
  locked: boolean;
}

export default function OfficersPage() {
  const { session } = useAuth();
  const toast = useToast();
  const staff = useApi<Staff[]>("/api/v1/admin/staff");
  const [open, setOpen] = useState(false);
  const [resetFor, setResetFor] = useState<Staff | null>(null);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const isSuper = session?.user.role === "SUPER_ADMIN";

  async function patch(user: Staff, body: Record<string, unknown>, msg: string) {
    try {
      await api(`/api/v1/admin/staff/${user.id}`, { method: "PATCH", body });
      toast(msg);
      void staff.reload();
      return true;
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed", "error");
      return false;
    }
  }

  async function create(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    const data = Object.fromEntries([...new FormData(e.currentTarget).entries()].map(([k, v]) => [k, String(v).trim() || null]));
    try {
      await api("/api/v1/admin/staff", { method: "POST", body: data });
      toast("Account created");
      setOpen(false);
      void staff.reload();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed", "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Officers & staff"
        subtitle="Admins manage police accounts. Only a super admin can create or change admin accounts."
        actions={<Button variant="primary" onClick={() => setOpen(true)}><Plus className="h-4 w-4" /> New account</Button>}
      />
      <Panel bodyClass="p-0">
        {staff.loading ? <SkeletonRows /> : staff.error ? <ErrorState message={staff.error} onRetry={staff.reload} /> : !staff.data?.length ? <EmptyState title="No staff accounts" /> : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px]">
              <thead className="border-b hairline"><tr><th className="th">Name</th><th className="th">Role</th><th className="th">Badge / station</th><th className="th">Last login</th><th className="th">Status</th><th className="th" /></tr></thead>
              <tbody className="divide-y hairline">
                {staff.data.map((u) => {
                  const canEdit = isSuper || u.role === "POLICE";
                  return (
                    <tr key={u.id}>
                      <td className="td"><p className="font-medium">{u.name}</p><p className="text-xs muted">{u.email}</p></td>
                      <td className="td"><Badge tone={u.role === "POLICE" ? "info" : "neutral"}>{humanize(u.role)}</Badge></td>
                      <td className="td text-xs">{u.badge_number ?? "—"}<p className="muted">{u.station ?? ""}</p></td>
                      <td className="td text-xs">{dateTime(u.last_login_at)}</td>
                      <td className="td">{!u.active ? <Badge tone="neutral">Disabled</Badge> : u.locked ? <Badge tone="caution">Locked</Badge> : <Badge tone="safe">Active</Badge>}</td>
                      <td className="td whitespace-nowrap text-right">
                        {canEdit && u.id !== session?.user.id && (
                          <>
                            <Button size="sm" variant="ghost" onClick={() => patch(u, { active: !u.active }, u.active ? "Account disabled" : "Account enabled")}>{u.active ? "Disable" : "Enable"}</Button>
                            <Button size="sm" variant="ghost" onClick={() => setResetFor(u)}>Reset password</Button>
                          </>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Modal open={open} title="New staff account" onClose={() => setOpen(false)}>
        <form onSubmit={create} className="grid gap-3 sm:grid-cols-2">
          <Field label="Full name"><input className="field" name="name" required /></Field>
          <Field label="Email"><input className="field" name="email" type="email" required /></Field>
          <Field label="Role">
            <select className="field" name="role" defaultValue="POLICE">
              <option value="POLICE">Police officer</option>
              {isSuper && <option value="ADMIN">Admin</option>}
              {isSuper && <option value="SUPER_ADMIN">Super admin</option>}
            </select>
          </Field>
          <Field label="Initial password" hint="10+ chars, upper, lower, digit"><input className="field" name="password" type="password" minLength={10} required /></Field>
          <Field label="Badge number"><input className="field" name="badge_number" /></Field>
          <Field label="Station"><input className="field" name="station" /></Field>
          <div className="flex justify-end gap-2 sm:col-span-2">
            <Button type="button" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" variant="primary" loading={busy}>Create</Button>
          </div>
        </form>
      </Modal>

      <Modal
        open={!!resetFor}
        title={`Reset password · ${resetFor?.name ?? ""}`}
        onClose={() => { setResetFor(null); setPassword(""); }}
        footer={<><Button onClick={() => setResetFor(null)}>Cancel</Button><Button variant="primary" disabled={password.length < 10} onClick={async () => { if (resetFor && (await patch(resetFor, { password }, "Password reset; account unlocked"))) { setResetFor(null); setPassword(""); } }}>Set password</Button></>}
      >
        <Field label="New password" hint="Share it with the officer through a secure channel."><input className="field" type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
      </Modal>
    </>
  );
}
