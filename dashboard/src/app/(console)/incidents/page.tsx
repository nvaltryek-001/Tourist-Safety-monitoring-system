"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { LiveBadge } from "@/components/LiveBadge";
import { Badge, EmptyState, ErrorState, PageHeader, Panel, SkeletonRows, StatusBadge, useToast } from "@/components/ui";
import { coords, humanize, timeAgo } from "@/lib/format";
import { useApi, useLiveEvents } from "@/lib/hooks";
import type { SOSAlert } from "@/lib/types";

const COLUMNS: { status: SOSAlert["status"]; title: string }[] = [
  { status: "OPEN", title: "New" },
  { status: "ACKNOWLEDGED", title: "Acknowledged" },
  { status: "RESPONDING", title: "Responding" },
  { status: "RESOLVED", title: "Resolved" },
];

export default function IncidentsPage() {
  const alerts = useApi<SOSAlert[]>("/api/v1/sos?limit=300");
  const toast = useToast();
  const [showCancelled, setShowCancelled] = useState(false);
  const live = useLiveEvents((event) => {
    if (event.type === "sos.created") {
      const a = event.data as unknown as SOSAlert;
      toast(`New SOS #${a.id} from ${a.tourist_name ?? a.tourist_code}`, "error");
    }
    if (event.type.startsWith("sos.")) void alerts.reload();
  });

  const grouped = useMemo(() => {
    const out: Record<string, SOSAlert[]> = {};
    for (const a of alerts.data ?? []) (out[a.status] ??= []).push(a);
    return out;
  }, [alerts.data]);

  return (
    <>
      <PageHeader
        title="SOS command centre"
        subtitle="Every alert here was confirmed by the server. Resolution always needs an officer's notes."
        actions={<LiveBadge status={live} />}
      />
      {alerts.loading ? (
        <Panel><SkeletonRows rows={6} /></Panel>
      ) : alerts.error ? (
        <Panel><ErrorState message={alerts.error} onRetry={alerts.reload} /></Panel>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {COLUMNS.map((col) => {
              const items = grouped[col.status] ?? [];
              return (
                <section key={col.status} className="panel flex max-h-[calc(100vh-220px)] flex-col">
                  <header className="flex items-center justify-between border-b hairline px-4 py-3">
                    <h2 className="text-sm font-semibold">{col.title}</h2>
                    <StatusBadge status={col.status} label={String(items.length)} />
                  </header>
                  <div className="flex-1 space-y-2 overflow-y-auto p-3">
                    {!items.length && <EmptyState title="Nothing here" />}
                    {items.map((a) => (
                      <Link
                        key={a.id}
                        href={`/incidents/${a.id}`}
                        className={`block rounded border p-3 transition-colors hover:border-brand-500 ${a.status === "OPEN" ? "border-red-300 bg-red-50/60 dark:border-red-500/40 dark:bg-red-500/5" : "hairline"}`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-semibold">#{a.id}</span>
                          <span className="text-[11px] muted">{timeAgo(a.created_at)}</span>
                        </div>
                        <p className="mt-1 text-sm">{a.tourist_name ?? a.tourist_code}</p>
                        <p className="mt-0.5 font-mono text-[11px] muted">{coords(a.latitude, a.longitude)}</p>
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          <Badge tone="info">{humanize(a.alert_type)}</Badge>
                          {a.assigned_officer ? <Badge tone="neutral">{a.assigned_officer.name}</Badge> : col.status !== "RESOLVED" && <Badge tone="caution">Unassigned</Badge>}
                          {a.resolution_outcome && <Badge tone="safe">{humanize(a.resolution_outcome)}</Badge>}
                        </div>
                      </Link>
                    ))}
                  </div>
                </section>
              );
            })}
          </div>
          <button className="mt-4 text-xs text-brand-600 hover:underline" onClick={() => setShowCancelled((s) => !s)}>
            {showCancelled ? "Hide" : "Show"} cancelled alerts ({grouped.CANCELLED?.length ?? 0})
          </button>
          {showCancelled && (
            <ul className="mt-2 space-y-1 text-sm">
              {(grouped.CANCELLED ?? []).map((a) => (
                <li key={a.id}>
                  <Link href={`/incidents/${a.id}`} className="hover:underline">
                    #{a.id} · {a.tourist_name ?? a.tourist_code} · cancelled {timeAgo(a.resolved_at)}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </>
  );
}
