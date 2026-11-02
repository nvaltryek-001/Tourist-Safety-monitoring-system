"use client";

import type { FeatureCollection } from "geojson";
import { useMemo } from "react";
import { humanize } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import { isAdminRole, useAuth } from "@/lib/auth";
import { SafetyMap } from "./Map";
import { EmptyState, Panel, SkeletonRows, Stat } from "./ui";

interface Hotspots {
  status: "OK" | "INSUFFICIENT_DATA";
  events: number;
  cells: { latitude: number; longitude: number; count: number; by_kind: Record<string, number>; first: string; last: string }[];
  note: string;
  min_events?: number;
}
interface ResponseTimes {
  alerts: number;
  acknowledged: number;
  resolved: number;
  ack_minutes: { median: number | null; p90: number | null };
  resolve_minutes: { median: number | null; p90: number | null };
  ack_median_by_type: Record<string, number | null>;
  resolve_median_by_officer: Record<string, number | null>;
  outcomes: Record<string, number>;
}
interface ZoneActivity {
  events: number;
  zones: { zone_id: number; zone_name: string | null; zone_type: string | null; entries: number; exits: number; unique_tourists: number; median_dwell_minutes: number | null; currently_inside: number }[];
}
interface Movement {
  tourists: { tourist_code: string; points: number; distance_km: number; max_speed_kmh: number; stationary_minutes: number; route_deviation: boolean }[];
}

/** Square polygon (cell_m wide) around each hotspot so both map providers can draw it. */
function cellsToGeoJSON(cells: Hotspots["cells"], cellM: number): FeatureCollection {
  return {
    type: "FeatureCollection",
    features: cells.map((c) => {
      const dLat = cellM / 2 / 111320;
      const dLon = cellM / 2 / (111320 * Math.cos((c.latitude * Math.PI) / 180));
      const ring = [
        [c.longitude - dLon, c.latitude - dLat], [c.longitude + dLon, c.latitude - dLat],
        [c.longitude + dLon, c.latitude + dLat], [c.longitude - dLon, c.latitude + dLat], [c.longitude - dLon, c.latitude - dLat],
      ];
      return { type: "Feature", geometry: { type: "Polygon", coordinates: [ring] }, properties: { name: `${c.count} events`, ...c.by_kind } };
    }),
  };
}

export function OperationalAnalytics({ days }: { days: number }) {
  const { session } = useAuth();
  const admin = isAdminRole(session?.user.role);
  const hot = useApi<Hotspots>(`/api/v1/analytics/hotspots?days=${Math.max(days, 30)}&cell_m=500`);
  const rt = useApi<ResponseTimes>(`/api/v1/analytics/response-times?days=${days}`);
  const za = useApi<ZoneActivity>(`/api/v1/analytics/zone-activity?days=${days}`);
  const mv = useApi<Movement>(admin ? "/api/v1/analytics/movement?hours=24" : null);
  const hotLayer = useMemo(() => (hot.data?.cells.length ? cellsToGeoJSON(hot.data.cells, 500) : null), [hot.data]);

  return (
    <div className="mt-6 space-y-6">
      <div className="stagger grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Median time to acknowledge" value={rt.data?.ack_minutes.median != null ? `${rt.data.ack_minutes.median} min` : "—"} hint={rt.data ? `p90 ${rt.data.ack_minutes.p90 ?? "—"} min` : undefined} />
        <Stat label="Median time to resolve" value={rt.data?.resolve_minutes.median != null ? `${rt.data.resolve_minutes.median} min` : "—"} hint={rt.data ? `p90 ${rt.data.resolve_minutes.p90 ?? "—"} min` : undefined} />
        <Stat label="Resolved / total SOS" value={rt.data ? `${rt.data.resolved} / ${rt.data.alerts}` : "—"} tone="safe" />
        <Stat label="Zone entry/exit events" value={za.data?.events ?? 0} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.4fr_1fr]">
        <Panel title="SOS & restricted-entry hotspots (500 m grid)">
          {hot.loading ? <SkeletonRows rows={4} /> : !hot.data ? <EmptyState title="Unavailable" /> : hot.data.status === "INSUFFICIENT_DATA" ? (
            <EmptyState title={`Not enough data yet (${hot.data.events} located events)`} hint={hot.data.note} />
          ) : (
            <>
              <SafetyMap height="380px" zoom={11}
                center={hot.data.cells[0] ? [hot.data.cells[0].latitude, hot.data.cells[0].longitude] : undefined}
                layers={[{ id: "hotspots", label: "Hotspot cell", color: "#dc2626", data: hotLayer }]} />
              <p className="mt-2 text-xs muted">{hot.data.events} events, {hot.data.cells.length} cells with 2 or more events. {hot.data.note}</p>
            </>
          )}
        </Panel>
        <Panel title="Response by type and officer">
          {!rt.data?.acknowledged ? <EmptyState title="No acknowledged SOS in this period" /> : (
            <div className="space-y-4 text-sm">
              <div>
                <p className="label">Median minutes to acknowledge, by type</p>
                {Object.entries(rt.data.ack_median_by_type).map(([k, v]) => <Row key={k} k={humanize(k)} v={`${v} min`} />)}
              </div>
              <div>
                <p className="label">Median minutes to resolve, by officer</p>
                {Object.entries(rt.data.resolve_median_by_officer).length ? Object.entries(rt.data.resolve_median_by_officer).map(([k, v]) => <Row key={k} k={k} v={`${v} min`} />) : <p className="muted">—</p>}
              </div>
              <div>
                <p className="label">Outcomes</p>
                {Object.entries(rt.data.outcomes).map(([k, v]) => <Row key={k} k={humanize(k)} v={String(v)} />)}
              </div>
            </div>
          )}
        </Panel>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Panel title="Safety-zone entries and exits" bodyClass="p-0">
          {!za.data?.zones.length ? <EmptyState title="No geofence events in this period" /> : (
            <table className="w-full">
              <thead className="border-b hairline"><tr><th className="th">Zone</th><th className="th">Entries</th><th className="th">Tourists</th><th className="th">Median dwell</th><th className="th">Inside now</th></tr></thead>
              <tbody className="divide-y hairline">
                {za.data.zones.slice(0, 15).map((z) => (
                  <tr key={z.zone_id}><td className="td">{z.zone_name ?? `Zone ${z.zone_id}`}<p className="text-xs muted">{humanize(z.zone_type)}</p></td>
                    <td className="td tabular-nums">{z.entries}</td><td className="td tabular-nums">{z.unique_tourists}</td>
                    <td className="td tabular-nums">{z.median_dwell_minutes != null ? `${z.median_dwell_minutes} min` : "—"}</td><td className="td tabular-nums">{z.currently_inside}</td></tr>
                ))}
              </tbody>
            </table>
          )}
        </Panel>
        {admin && (
          <Panel title="Tourist movement (last 24 h)" bodyClass="p-0">
            {!mv.data?.tourists.length ? <EmptyState title="No location history in the last 24 hours" /> : (
              <table className="w-full">
                <thead className="border-b hairline"><tr><th className="th">Tourist</th><th className="th">Points</th><th className="th">Distance</th><th className="th">Stationary</th><th className="th">Deviation</th></tr></thead>
                <tbody className="divide-y hairline">
                  {mv.data.tourists.map((t) => (
                    <tr key={t.tourist_code}><td className="td">{t.tourist_code}</td><td className="td tabular-nums">{t.points}</td>
                      <td className="td tabular-nums">{t.distance_km} km</td><td className="td tabular-nums">{t.stationary_minutes} min</td>
                      <td className="td">{t.route_deviation ? <span className="text-orange-700">Flagged</span> : "—"}</td></tr>
                  ))}
                </tbody>
              </table>
            )}
          </Panel>
        )}
      </div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return <div className="flex justify-between gap-3 py-0.5"><span className="muted">{k}</span><span className="tabular-nums">{v}</span></div>;
}
