"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { IncidentActions, IncidentSummary, Timeline } from "@/components/IncidentPanel";
import { SafetyMap } from "@/components/Map";
import { Button, ErrorState, PageHeader, Panel, SkeletonRows } from "@/components/ui";
import { useApi, useLiveEvents } from "@/lib/hooks";
import type { SOSAlert, Zone } from "@/lib/types";

export default function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const alert = useApi<SOSAlert>(`/api/v1/sos/${id}`);
  const zones = useApi<Zone[]>("/api/v1/zones?active=true");
  useLiveEvents((event) => {
    if (event.type === "sos.updated" && String((event.data as { id?: number }).id) === id) void alert.reload();
  });

  if (alert.loading) return <SkeletonRows rows={8} />;
  if (alert.error || !alert.data) return <Panel><ErrorState message={alert.error ?? "Incident not found"} onRetry={alert.reload} /></Panel>;
  const a = alert.data;

  return (
    <>
      <PageHeader
        title={`Incident #${a.id}`}
        subtitle="Emergency response record"
        actions={
          <>
            <Link href={`/tourists/${encodeURIComponent(a.tourist_code)}`}><Button size="sm">Tourist profile</Button></Link>
            <Link href="/incidents"><Button size="sm">← Command centre</Button></Link>
          </>
        }
      />
      <div className="grid gap-6 xl:grid-cols-[1.3fr_1fr]">
        <div className="space-y-6">
          <IncidentSummary alert={a} />
          <Panel title="Location">
            {a.latitude != null && a.longitude != null ? (
              <SafetyMap alerts={[a]} zones={zones.data ?? []} center={[a.latitude, a.longitude]} zoom={16} height="380px" />
            ) : (
              <p className="text-sm muted">The tourist&apos;s device did not provide a location with this SOS.</p>
            )}
          </Panel>
        </div>
        <div className="space-y-6">
          <Panel title="Response">
            <IncidentActions alert={a} onChange={(next) => alert.setData(next)} />
          </Panel>
          <Timeline alert={a} />
        </div>
      </div>
    </>
  );
}
