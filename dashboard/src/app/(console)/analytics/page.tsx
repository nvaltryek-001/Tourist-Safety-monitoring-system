"use client";

import { useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { OperationalAnalytics } from "@/components/OperationalAnalytics";
import { Reports } from "@/components/Reports";
import { isAdminRole, useAuth } from "@/lib/auth";
import { Button, EmptyState, ErrorState, PageHeader, Panel, SkeletonRows, Stat } from "@/components/ui";
import { humanize } from "@/lib/format";
import { useApi } from "@/lib/hooks";

interface Trends {
  window_days: number;
  daily: { date: string; count: number }[];
  restricted_entries_daily: { date: string; count: number }[];
  by_status: Record<string, number>;
  by_type: Record<string, number>;
  total: number;
  median_ack_minutes: number | null;
  acknowledged_count: number;
}

export default function AnalyticsPage() {
  const [days, setDays] = useState(30);
  const { session } = useAuth();
  const admin = isAdminRole(session?.user.role);
  const trends = useApi<Trends>(`/api/v1/analytics/trends?days=${days}`);
  const t = trends.data;
  const daily = t ? t.daily.map((d, i) => ({ date: d.date.slice(5), sos: d.count, entries: t.restricted_entries_daily[i]?.count ?? 0 })) : [];
  const byType = t ? Object.entries(t.by_type).map(([k, v]) => ({ name: humanize(k), value: v })) : [];

  return (
    <>
      <PageHeader
        title="Analytics"
        subtitle="Computed from recorded SOS alerts and geofence events. Empty charts mean no events were recorded — no figures are invented."
        actions={[7, 30, 90].map((d) => <Button key={d} size="sm" variant={d === days ? "primary" : "secondary"} onClick={() => setDays(d)}>{d} days</Button>)}
      />
      {trends.loading ? <SkeletonRows rows={6} /> : trends.error || !t ? <Panel><ErrorState message={trends.error ?? "Unavailable"} onRetry={trends.reload} /></Panel> : (
        <>
          <div className="stagger grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label="SOS alerts (all time)" value={t.total} />
            <Stat label={`SOS in last ${days} days`} value={t.daily.reduce((n, d) => n + d.count, 0)} />
            <Stat label="Median time to acknowledge" value={t.median_ack_minutes != null ? `${t.median_ack_minutes} min` : "—"} hint={`${t.acknowledged_count} acknowledged`} />
            <Stat label="Resolved" value={t.by_status.RESOLVED ?? 0} tone="safe" />
          </div>
          <div className="mt-6 grid gap-6 xl:grid-cols-[1.6fr_1fr]">
            <Panel title="Daily SOS alerts and restricted-zone entries">
              <div className="h-72">
                <ResponsiveContainer>
                  <AreaChart data={daily} margin={{ left: -16, right: 8 }}>
                    <CartesianGrid strokeOpacity={0.12} vertical={false} />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Area type="monotone" dataKey="sos" name="SOS alerts" stroke="#dc2626" fill="#dc2626" fillOpacity={0.12} />
                    <Area type="monotone" dataKey="entries" name="Zone entries" stroke="#0f766a" fill="#0f766a" fillOpacity={0.1} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Panel>
            <Panel title="SOS by emergency type">
              {!byType.length ? <EmptyState title="No SOS alerts recorded" /> : (
                <div className="h-72">
                  <ResponsiveContainer>
                    <BarChart data={byType} margin={{ left: -16 }}>
                      <CartesianGrid strokeOpacity={0.12} vertical={false} />
                      <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                      <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Bar dataKey="value" name="Alerts" fill="#0f766a" radius={[3, 3, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Panel>
          </div>
          <Panel title="Incidents by status" className="mt-6">
            <div className="flex flex-wrap gap-6 text-sm">
              {Object.entries(t.by_status).map(([k, v]) => <div key={k}><p className="text-xs muted">{humanize(k)}</p><p className="text-lg font-semibold">{v}</p></div>)}
              {!Object.keys(t.by_status).length && <p className="muted">No incidents recorded.</p>}
            </div>
          </Panel>
          <OperationalAnalytics days={days} />
          {admin && <div className="mt-6"><Reports days={days} /></div>}
        </>
      )}
    </>
  );
}
