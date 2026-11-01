"use client";

import { LocateFixed } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { IncidentActions, IncidentSummary, Timeline } from "@/components/IncidentPanel";
import { LiveBadge } from "@/components/LiveBadge";
import { SafetyMap } from "@/components/Map";
import { Badge, Button, EmptyState, ErrorState, PageHeader, Panel, SkeletonRows, StatusBadge, useToast } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { humanize, metres, timeAgo } from "@/lib/format";
import { useApi, useLiveEvents } from "@/lib/hooks";
import type { SOSAlert } from "@/lib/types";

export default function PoliceWorkspace() {
  const { session } = useAuth();
  const toast = useToast();
  const [here, setHere] = useState<[number, number] | null>(null);
  const nearQuery = here ? `&near_lat=${here[0]}&near_lon=${here[1]}` : "";
  const mine = useApi<SOSAlert[]>("/api/v1/sos?scope=mine");
  const active = useApi<SOSAlert[]>(`/api/v1/sos?scope=active${nearQuery}`);
  const history = useApi<SOSAlert[]>("/api/v1/sos?scope=mine&status=RESOLVED&limit=20");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const selected = useApi<SOSAlert>(selectedId ? `/api/v1/sos/${selectedId}` : null);

  const live = useLiveEvents((event) => {
    if (event.type === "sos.created") toast("New SOS alert received", "error");
    if (event.type.startsWith("sos.")) {
      void mine.reload();
      void active.reload();
      if (selectedId) void selected.reload();
    }
  });

  const myActive = (mine.data ?? []).filter((a) => ["OPEN", "ACKNOWLEDGED", "RESPONDING"].includes(a.status));
  const unassigned = (active.data ?? []).filter((a) => !a.assigned_officer_id);

  function locate() {
    if (!navigator.geolocation) return toast("This browser cannot share location", "error");
    navigator.geolocation.getCurrentPosition(
      (p) => setHere([p.coords.latitude, p.coords.longitude]),
      () => toast("Location permission denied — alerts are listed newest first", "info"),
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }

  return (
    <>
      <PageHeader
        title={`Officer workspace · ${session?.user.name ?? ""}`}
        subtitle="Your assigned incidents and unassigned SOS alerts awaiting a responder."
        actions={
          <>
            <Button size="sm" onClick={locate}>
              <LocateFixed className="h-4 w-4" /> {here ? "Sorted by distance" : "Sort by my distance"}
            </Button>
            <LiveBadge status={live} />
          </>
        }
      />
      <div className="grid gap-6 xl:grid-cols-[380px_1fr]">
        <div className="space-y-6">
          <AlertList title={`Assigned to me (${myActive.length})`} res={mine} items={myActive} selectedId={selectedId} onSelect={setSelectedId} empty="No active incidents assigned to you." />
          <AlertList title={`Unassigned nearby (${unassigned.length})`} res={active} items={unassigned} selectedId={selectedId} onSelect={setSelectedId} empty="No unassigned alerts." />
          <Panel title="My response history" bodyClass="p-0">
            {!history.data?.length ? (
              <EmptyState title="No resolved incidents yet" />
            ) : (
              <ul className="divide-y hairline">
                {history.data.map((a) => (
                  <li key={a.id} className="flex items-center justify-between px-4 py-2.5 text-sm">
                    <Link href={`/incidents/${a.id}`} className="hover:underline">#{a.id} · {a.tourist_name ?? a.tourist_code}</Link>
                    <Badge tone="safe">{humanize(a.resolution_outcome)}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
        <div className="space-y-6">
          <SafetyMap alerts={[...myActive, ...unassigned]} center={here ?? undefined} height="360px" onAlertClick={(a) => setSelectedId(a.id)} />
          {!selectedId ? (
            <Panel><EmptyState title="Select an incident" hint="Choose an alert on the left or on the map to see details and respond." /></Panel>
          ) : selected.loading ? (
            <Panel><SkeletonRows /></Panel>
          ) : selected.error || !selected.data ? (
            <Panel><ErrorState message={selected.error ?? "Not found"} onRetry={selected.reload} /></Panel>
          ) : (
            <div className="grid gap-6 2xl:grid-cols-2">
              <div className="space-y-6">
                <IncidentSummary alert={selected.data} />
                <Panel title="Respond">
                  <IncidentActions
                    alert={selected.data}
                    onChange={(a) => {
                      selected.setData(a);
                      void mine.reload();
                      void active.reload();
                    }}
                  />
                </Panel>
              </div>
              <Timeline alert={selected.data} />
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function AlertList({ title, res, items, selectedId, onSelect, empty }: {
  title: string;
  res: { loading: boolean; error: string | null; reload: () => Promise<void> };
  items: SOSAlert[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  empty: string;
}) {
  return (
    <Panel title={title} bodyClass="p-0">
      {res.loading ? (
        <SkeletonRows rows={3} />
      ) : res.error ? (
        <ErrorState message={res.error} onRetry={res.reload} />
      ) : !items.length ? (
        <EmptyState title={empty} />
      ) : (
        <ul className="divide-y hairline">
          {items.map((a) => (
            <li key={a.id}>
              <button
                onClick={() => onSelect(a.id)}
                className={`flex w-full items-start justify-between gap-2 px-4 py-3 text-left ${selectedId === a.id ? "bg-brand-50 dark:bg-brand-600/10" : "hover:bg-black/[.02]"}`}
              >
                <span>
                  <span className="block text-sm font-medium">#{a.id} · {a.tourist_name ?? a.tourist_code}</span>
                  <span className="text-xs muted">
                    {humanize(a.alert_type)} · {timeAgo(a.created_at)}
                    {a.distance_meters != null ? ` · ${metres(a.distance_meters)} away` : ""}
                  </span>
                </span>
                <StatusBadge status={a.status} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
