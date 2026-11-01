"use client";

import { Plus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Badge, Button, EmptyState, ErrorState, Field, Modal, PageHeader, Panel, SkeletonRows, StatusBadge, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { isAdminRole, useAuth } from "@/lib/auth";
import { coords, timeAgo } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { Paged, Tourist } from "@/lib/types";

const STATUSES = ["", "SAFE", "CAUTION", "DANGER", "SOS", "UNKNOWN"];

export default function TouristsPage() {
  const { session } = useAuth();
  const admin = isAdminRole(session?.user.role);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [sort, setSort] = useState("last_seen");
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const params = new URLSearchParams({ page: String(page), page_size: "25", sort });
  if (query) params.set("search", query);
  if (status) params.set("status", status);
  const list = useApi<Paged<Tourist>>(`/api/v1/admin/tourists?${params}`);
  const pages = list.data ? Math.max(1, Math.ceil(list.data.total / list.data.page_size)) : 1;

  return (
    <>
      <PageHeader
        title="Tourist management"
        subtitle={admin ? "Full profiles are visible to administrators." : "Contact details are masked unless you are handling the tourist's active SOS."}
        actions={
          admin && (
            <Button variant="primary" onClick={() => setCreating(true)}>
              <Plus className="h-4 w-4" /> Register tourist
            </Button>
          )
        }
      />
      <Panel bodyClass="p-0">
        <form
          className="flex flex-wrap items-end gap-3 border-b hairline p-4"
          onSubmit={(e) => {
            e.preventDefault();
            setPage(1);
            setQuery(search.trim());
          }}
        >
          <Field label="Search by code or name">
            <input className="field w-64" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="e.g. T001 or Asha" />
          </Field>
          <Field label="Status">
            <select className="field w-44" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
              {STATUSES.map((s) => (
                <option key={s} value={s}>{s ? s.charAt(0) + s.slice(1).toLowerCase() : "Any status"}</option>
              ))}
            </select>
          </Field>
          <Field label="Sort">
            <select className="field w-40" value={sort} onChange={(e) => setSort(e.target.value)}>
              <option value="last_seen">Last seen</option>
              <option value="name">Name</option>
              <option value="code">Code</option>
              <option value="status">Status</option>
            </select>
          </Field>
          <Button type="submit">Search</Button>
        </form>
        {list.loading ? (
          <SkeletonRows />
        ) : list.error ? (
          <ErrorState message={list.error} onRetry={list.reload} />
        ) : !list.data?.items.length ? (
          <EmptyState title="No tourists found" hint={query || status ? "Try clearing the filters." : "Register a tourist to get started."} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px]">
              <thead className="border-b hairline">
                <tr>
                  <th className="th">Tourist</th>
                  <th className="th">Status</th>
                  <th className="th">Last known location</th>
                  <th className="th">Last seen</th>
                  <th className="th">Consent</th>
                  <th className="th">Phone</th>
                </tr>
              </thead>
              <tbody className="divide-y hairline">
                {list.data.items.map((t) => (
                  <tr key={t.tourist_code} className="hover:bg-black/[.02] dark:hover:bg-white/[.03]">
                    <td className="td">
                      <Link href={`/tourists/${encodeURIComponent(t.tourist_code)}`} className="font-medium hover:text-brand-600">{t.name}</Link>
                      <p className="text-xs muted">{t.tourist_code}</p>
                    </td>
                    <td className="td"><StatusBadge status={t.safety_status} /></td>
                    <td className="td font-mono text-xs">{coords(t.latitude, t.longitude)}</td>
                    <td className="td text-xs">
                      {timeAgo(t.last_location_update)} {t.location_stale && <Badge tone="neutral" className="ml-1">stale</Badge>}
                    </td>
                    <td className="td">{t.consent_given ? <Badge tone="safe">Given</Badge> : <Badge tone="neutral">Not given</Badge>}</td>
                    <td className="td text-xs">{t.phone ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {list.data && list.data.total > list.data.page_size && (
          <div className="flex items-center justify-between border-t hairline px-4 py-3 text-xs muted">
            <span>{list.data.total} tourists · page {page} of {pages}</span>
            <div className="flex gap-2">
              <Button size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button>
              <Button size="sm" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</Button>
            </div>
          </div>
        )}
      </Panel>
      <CreateTouristModal open={creating} onClose={() => setCreating(false)} onCreated={list.reload} />
    </>
  );
}

function CreateTouristModal({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: () => void }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fields: [string, string, string?][] = [
    ["tourist_code", "Tourist code *"],
    ["name", "Full name *"],
    ["login_gmail", "Login Gmail (for the mobile app)", "email"],
    ["phone", "Phone", "tel"],
    ["college_email", "College email", "email"],
    ["enrollment_number", "Enrollment number"],
    ["emergency_contact_name", "Emergency contact name"],
    ["emergency_contact_phone", "Emergency contact phone", "tel"],
    ["emergency_contact_email", "Emergency contact email", "email"],
  ];
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const data = Object.fromEntries([...new FormData(e.currentTarget).entries()].map(([k, v]) => [k, String(v).trim() || null]));
    try {
      await api("/api/v1/admin/tourists", { method: "POST", body: data });
      toast("Tourist registered");
      onCreated();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal open={open} title="Register tourist" onClose={onClose}>
      <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2">
        {fields.map(([name, label, type]) => (
          <Field key={name} label={label}>
            <input className="field" name={name} type={type ?? "text"} required={label.endsWith("*")} />
          </Field>
        ))}
        {error && <p className="text-sm text-red-700 sm:col-span-2">{error}</p>}
        <div className="flex justify-end gap-2 sm:col-span-2">
          <Button type="button" onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" loading={busy}>Register</Button>
        </div>
      </form>
    </Modal>
  );
}
