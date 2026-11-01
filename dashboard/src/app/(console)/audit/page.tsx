"use client";

import { useState } from "react";
import { Button, EmptyState, ErrorState, PageHeader, Panel, SkeletonRows } from "@/components/ui";
import { dateTime, humanize } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { Paged } from "@/lib/types";

interface Log {
  id: number;
  actor_type: string;
  actor_id: string | null;
  action: string;
  target: string | null;
  detail: string | null;
  ip_address: string | null;
  created_at: string;
}

export default function AuditPage() {
  const [filter, setFilter] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const logs = useApi<Paged<Log>>(`/api/v1/admin/audit-logs?page=${page}&page_size=50${query ? `&action=${encodeURIComponent(query)}` : ""}`);
  const pages = logs.data ? Math.max(1, Math.ceil(logs.data.total / 50)) : 1;

  return (
    <>
      <PageHeader title="Audit log" subtitle="Logins, data access, zone changes and every incident action. Entries cannot be edited from the dashboard." />
      <Panel bodyClass="p-0">
        <form className="flex gap-2 border-b hairline p-3" onSubmit={(e) => { e.preventDefault(); setPage(1); setQuery(filter.trim()); }}>
          <input className="field h-9 w-64" placeholder="Filter by action, e.g. LOGIN or SOS" value={filter} onChange={(e) => setFilter(e.target.value)} />
          <Button size="sm" type="submit">Filter</Button>
        </form>
        {logs.loading ? <SkeletonRows /> : logs.error ? <ErrorState message={logs.error} onRetry={logs.reload} /> : !logs.data?.items.length ? <EmptyState title="No entries" /> : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px]">
              <thead className="border-b hairline"><tr><th className="th">Time</th><th className="th">Action</th><th className="th">Actor</th><th className="th">Target</th><th className="th">Detail</th><th className="th">IP</th></tr></thead>
              <tbody className="divide-y hairline">
                {logs.data.items.map((l) => (
                  <tr key={l.id}>
                    <td className="td whitespace-nowrap text-xs">{dateTime(l.created_at)}</td>
                    <td className="td text-xs font-medium">{humanize(l.action)}</td>
                    <td className="td text-xs">{humanize(l.actor_type)} {l.actor_id ? `· ${l.actor_id}` : ""}</td>
                    <td className="td font-mono text-xs">{l.target ?? "—"}</td>
                    <td className="td max-w-xs truncate font-mono text-[11px] muted" title={l.detail ?? ""}>{l.detail ?? ""}</td>
                    <td className="td font-mono text-[11px] muted">{l.ip_address ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {logs.data && pages > 1 && (
          <div className="flex items-center justify-between border-t hairline px-4 py-3 text-xs muted">
            <span>{logs.data.total} entries · page {page} of {pages}</span>
            <div className="flex gap-2">
              <Button size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button>
              <Button size="sm" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</Button>
            </div>
          </div>
        )}
      </Panel>
    </>
  );
}
