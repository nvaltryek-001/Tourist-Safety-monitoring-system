"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { IncidentActions, IncidentSummary, Timeline } from "@/components/IncidentPanel";
import { SafetyMap } from "@/components/Map";
import { Button, ErrorState, PageHeader, Panel, SkeletonRows, StatusBadge } from "@/components/ui";
import { metres } from "@/lib/format";
import { FACILITY_STYLE, googleDirectionsUrl } from "@/lib/maps";
import { useApi, useLiveEvents } from "@/lib/hooks";
import type { Facility, NearestHelp, RouteRequest, SOSAlert, WeatherInfo, Zone } from "@/lib/types";

export default function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const alert = useApi<SOSAlert>(`/api/v1/sos/${id}`);
  const zones = useApi<Zone[]>("/api/v1/zones?active=true");
  const help = useApi<NearestHelp>(`/api/v1/sos/${id}/nearest-help`);
  const [routeTo, setRouteTo] = useState<Facility | null>(null);
  const weather = useApi<WeatherInfo>(
    alert.data?.latitude != null && alert.data?.longitude != null ? `/api/v1/weather?lat=${alert.data.latitude.toFixed(3)}&lon=${alert.data.longitude.toFixed(3)}` : null,
  );
  useLiveEvents((event) => {
    if (event.type === "sos.updated" && String((event.data as { id?: number }).id) === id) void alert.reload();
  });

  if (alert.loading) return <SkeletonRows rows={8} />;
  if (alert.error || !alert.data) return <Panel><ErrorState message={alert.error ?? "Incident not found"} onRetry={alert.reload} /></Panel>;
  const a = alert.data;
  const helpers = [help.data?.police, help.data?.hospital, help.data?.fire_station].filter(Boolean) as Facility[];
  const route: RouteRequest | null =
    routeTo && a.latitude != null && a.longitude != null
      ? { from: [routeTo.latitude, routeTo.longitude], to: [a.latitude, a.longitude], label: `${routeTo.name} → SOS #${a.id}` }
      : null;

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
              <SafetyMap alerts={[a]} zones={zones.data ?? []} facilities={helpers} route={route} center={[a.latitude, a.longitude]} zoom={15} height="420px" />
            ) : (
              <p className="text-sm muted">The tourist&apos;s device did not provide a location with this SOS.</p>
            )}
          </Panel>
        </div>
        <div className="space-y-6">
          <Panel title="Nearest help & SOS route">
            {help.loading ? <p className="text-sm muted">Finding nearest facilities…</p> : !helpers.length ? (
              <p className="text-sm muted">No emergency facilities on record within 50 km. Import the OSM facility dataset on the Emergency facilities page.</p>
            ) : (
              <ul className="space-y-2">
                {helpers.map((f) => (
                  <li key={f.id} className={`flex items-center justify-between gap-3 rounded border p-3 transition-colors ${routeTo?.id === f.id ? "border-red-300 bg-red-50/60 dark:bg-red-500/10" : "hairline"}`}>
                    <div>
                      <p className="text-sm font-medium"><span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full" style={{ background: FACILITY_STYLE[f.facility_type].color }} />{f.name}</p>
                      <p className="text-xs muted">{FACILITY_STYLE[f.facility_type].label} · {metres(f.distance_meters)} straight line{f.phone ? ` · ☎ ${f.phone}` : ""}</p>
                    </div>
                    <div className="flex shrink-0 gap-1.5">
                      <Button size="sm" variant={routeTo?.id === f.id ? "primary" : "secondary"} onClick={() => setRouteTo(routeTo?.id === f.id ? null : f)}>
                        {routeTo?.id === f.id ? "Hide route" : "Show route"}
                      </Button>
                      {a.latitude != null && a.longitude != null && (
                        <a href={googleDirectionsUrl([a.latitude, a.longitude], [f.latitude, f.longitude])} target="_blank" rel="noreferrer">
                          <Button size="sm" variant="ghost">Navigate</Button>
                        </a>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
          <Panel title="Weather at the SOS location">
            {!weather.data ? <p className="text-sm muted">{weather.loading ? "Loading weather…" : "No location for this SOS."}</p> : !weather.data.available ? (
              <p className="text-sm muted">Weather service unreachable from the server.</p>
            ) : (
              <div className="flex items-start justify-between gap-4 text-sm">
                <div>
                  <p>{weather.data.current?.temperature_2m} °C · rain {weather.data.current?.precipitation} mm · gusts {weather.data.current?.wind_gusts_10m} km/h</p>
                  {weather.data.reasons?.length ? <ul className="mt-1 list-disc pl-5 text-xs muted">{weather.data.reasons.map((r) => <li key={r}>{r}</li>)}</ul> : <p className="mt-1 text-xs muted">No weather hazards right now.</p>}
                  <p className="mt-1 text-[10px] muted">{weather.data.attribution}</p>
                </div>
                <StatusBadge status={weather.data.weather_risk_level} />
              </div>
            )}
          </Panel>
          <Panel title="Response">
            <IncidentActions alert={a} onChange={(next) => alert.setData(next)} />
          </Panel>
          <Timeline alert={a} />
        </div>
      </div>
    </>
  );
}
