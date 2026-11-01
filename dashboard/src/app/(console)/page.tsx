"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { LiveBadge } from "@/components/LiveBadge";
import { MapLegend, SafetyMap } from "@/components/Map";
import { EmptyState, ErrorState, PageHeader, Panel, SkeletonRows, Stat, StatusBadge } from "@/components/ui";
import { isAdminRole, useAuth } from "@/lib/auth";
import { dateTime, humanize, timeAgo } from "@/lib/format";
import { useApi, useLiveEvents } from "@/lib/hooks";
import type { Overview, Paged, SOSAlert, Tourist, Zone } from "@/lib/types";

export default function OverviewPage() {
  const { session } = useAuth();
  const router = useRouter();
  const admin = isAdminRole(session?.user.role);
  useEffect(() => {
    if (session && !admin) router.replace("/police");
  }, [session, admin, router]);

  const overview = useApi<Overview>(admin ? "/api/v1/analytics/overview" : null, 60000);
  const tourists = useApi<Paged<Tourist>>(admin ? "/api/v1/admin/tourists?page_size=200" : null);
  const zones = useApi<Zone[]>(admin ? "/api/v1/zones?active=true" : null);
  const alerts = useApi<SOSAlert[]>(admin ? "/api/v1/sos?scope=active" : null);

  const live = useLiveEvents((event) => {
    if (event.type.startsWith("sos.")) {
      void overview.reload();
      void alerts.reload();
    }
    if (event.type === "location.updated") void tourists.reload();
  });

  if (!admin) return null;
  const k = overview.data?.kpis;

  return (
    <>
      <PageHeader
        title="Operations overview"
        subtitle={`Live figures from the backend · updated ${overview.data ? timeAgo(overview.data.generated_at) : "…"}`}
        actions={<LiveBadge status={live} />}
      />
      {overview.error ? (
        <Panel>
          <ErrorState message={overview.error} onRetry={overview.reload} />
        </Panel>
      ) : (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          <Stat label="Registered tourists" value={k?.registered_tourists ?? "–"} />
          <Stat label="Active now" value={k?.active_tourists ?? "–"} hint={`updated in last ${overview.data?.stale_after_minutes ?? 15} min`} />
          <Stat label="Need attention" value={k?.tourists_requiring_attention ?? "–"} tone={k?.tourists_requiring_attention ? "caution" : undefined} />
          <Stat label="New SOS alerts" value={k?.active_sos ?? "–"} tone={k?.active_sos ? "sos" : undefined} />
          <Stat label="Open incidents" value={k?.open_incidents ?? "–"} tone={k?.open_incidents ? "danger" : undefined} />
          <Stat label="Safety zones" value={k?.safety_zones ?? "–"} hint={k ? `${k.active_zones} active · ${k.synthetic_zones} synthetic` : undefined} />
        </div>
      )}

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.6fr_1fr]">
        <Panel title="Live situation map" action={<Link href="/map" className="text-xs text-brand-600 hover:underline">Open full map</Link>}>
          <SafetyMap zones={zones.data ?? []} tourists={tourists.data?.items ?? []} alerts={alerts.data ?? []} height="420px" />
          <div className="mt-3">
            <MapLegend />
          </div>
        </Panel>

        <Panel title="Active emergencies" bodyClass="p-0" action={<Link href="/incidents" className="text-xs text-brand-600 hover:underline">Command centre</Link>}>
          {alerts.loading ? (
            <SkeletonRows rows={4} />
          ) : alerts.error ? (
            <ErrorState message={alerts.error} onRetry={alerts.reload} />
          ) : !alerts.data?.length ? (
            <EmptyState title="No active SOS alerts" hint="New alerts appear here instantly over the live connection." />
          ) : (
            <ul className="divide-y hairline">
              {alerts.data.map((a) => (
                <li key={a.id}>
                  <Link href={`/incidents/${a.id}`} className="flex items-start justify-between gap-3 px-4 py-3 hover:bg-black/[.02] dark:hover:bg-white/[.03]">
                    <div>
                      <p className="text-sm font-medium">
                        SOS #{a.id} · {a.tourist_name ?? a.tourist_code}
                      </p>
                      <p className="text-xs muted">
                        {humanize(a.alert_type)} · {timeAgo(a.created_at)}
                        {a.assigned_officer ? ` · ${a.assigned_officer.name}` : " · unassigned"}
                      </p>
                    </div>
                    <StatusBadge status={a.status} />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <DistributionPanel title="Tourist status" data={overview.data?.tourist_status_distribution} />
        <DistributionPanel title="Active zones by type" data={overview.data?.zone_type_distribution} />
        <Panel title="Recent system events" bodyClass="p-0">
          {!overview.data?.recent_events.length ? (
            <EmptyState title="No events yet" />
          ) : (
            <ul className="divide-y hairline">
              {overview.data.recent_events.map((e) => (
                <li key={e.id} className="px-4 py-2.5">
                  <p className="text-xs font-medium">{humanize(e.action)}</p>
                  <p className="text-[11px] muted">
                    {e.target ?? e.actor_type} · {dateTime(e.created_at)}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </>
  );
}

function DistributionPanel({ title, data }: { title: string; data?: Record<string, number> }) {
  const rows = Object.entries(data ?? {}).map(([name, value]) => ({ name: humanize(name), value }));
  return (
    <Panel title={title}>
      {!data ? (
        <SkeletonRows rows={3} />
      ) : !rows.length ? (
        <EmptyState title="No data yet" />
      ) : (
        <div className="h-56">
          <ResponsiveContainer>
            <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 16 }}>
              <CartesianGrid horizontal={false} strokeOpacity={0.15} />
              <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 11 }} />
              <Tooltip cursor={{ fillOpacity: 0.05 }} />
              <Bar dataKey="value" fill="#0f766a" radius={[0, 3, 3, 0]} barSize={16} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </Panel>
  );
}
