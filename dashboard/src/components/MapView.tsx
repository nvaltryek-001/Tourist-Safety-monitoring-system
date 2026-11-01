"use client";

import { Circle, CircleMarker, MapContainer, Polygon, Popup, TileLayer, Tooltip, useMap, useMapEvents } from "react-leaflet";
import { useEffect, useMemo, useState } from "react";
import type { LatLngExpression } from "leaflet";
import { clusterPoints } from "@/lib/cluster";
import { coords, humanize, statusTone, timeAgo } from "@/lib/format";
import type { SOSAlert, Tourist, Zone } from "@/lib/types";
import { TONE_HEX } from "./ui";

export interface MapViewProps {
  zones?: Zone[];
  tourists?: Tourist[];
  alerts?: SOSAlert[];
  center?: [number, number];
  zoom?: number;
  height?: string;
  focus?: [number, number] | null;
  track?: [number, number][];
  onTouristClick?: (t: Tourist) => void;
  onAlertClick?: (a: SOSAlert) => void;
  onMapClick?: (lat: number, lon: number) => void;
  draft?: { latitude: number; longitude: number; radius_meters: number } | null;
}

export const ZONE_COLORS: Record<string, string> = {
  RESTRICTED: "#dc2626",
  HIGH_RISK: "#ea580c",
  CAUTION: "#d97706",
  SAFE: "#15803d",
};

function zoneColor(z: Zone): string {
  if (z.synthetic) return "#7c3aed";
  return ZONE_COLORS[z.zone_type] ?? "#0284c7";
}

function ZoomWatcher({ onZoom, onClick }: { onZoom: (z: number) => void; onClick?: (lat: number, lon: number) => void }) {
  useMapEvents({
    zoomend: (e) => onZoom(e.target.getZoom()),
    click: (e) => onClick?.(e.latlng.lat, e.latlng.lng),
  });
  return null;
}

function FocusOn({ focus }: { focus?: [number, number] | null }) {
  const map = useMap();
  useEffect(() => {
    if (focus) map.flyTo(focus, Math.max(map.getZoom(), 15), { duration: 0.6 });
  }, [focus, map]);
  return null;
}

function polygonPositions(z: Zone): LatLngExpression[][] {
  if (!z.geometry) return [];
  const polys = (z.geometry.type === "Polygon" ? [z.geometry.coordinates] : z.geometry.coordinates) as number[][][][];
  return polys.map((rings) => rings[0].map(([lon, lat]) => [lat, lon] as LatLngExpression));
}

export default function MapView({
  zones = [],
  tourists = [],
  alerts = [],
  center,
  zoom = 12,
  height = "520px",
  focus,
  track,
  onTouristClick,
  onAlertClick,
  onMapClick,
  draft,
}: MapViewProps) {
  const [currentZoom, setCurrentZoom] = useState(zoom);
  const located = tourists.filter((t) => t.latitude != null && t.longitude != null);
  const initial: [number, number] =
    center ??
    (located[0] ? [located[0].latitude as number, located[0].longitude as number] : zones[0] ? [zones[0].latitude, zones[0].longitude] : [12.9716, 77.5946]);

  const clusters = useMemo(
    () => clusterPoints(located.map((t) => ({ lat: t.latitude as number, lon: t.longitude as number, item: t })), currentZoom),
    [located, currentZoom],
  );

  return (
    <div style={{ height }} className="overflow-hidden rounded-lg border hairline">
      <MapContainer center={initial} zoom={zoom} style={{ height: "100%", width: "100%" }} scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <ZoomWatcher onZoom={setCurrentZoom} onClick={onMapClick} />
        <FocusOn focus={focus} />

        {zones.map((z) =>
          z.geometry ? (
            <Polygon
              key={`z${z.id}`}
              positions={polygonPositions(z)}
              pathOptions={{ color: zoneColor(z), weight: 1.5, fillOpacity: z.active ? 0.15 : 0.04, dashArray: z.active ? undefined : "4 4" }}
            >
              <ZonePopup z={z} />
            </Polygon>
          ) : (
            <Circle
              key={`z${z.id}`}
              center={[z.latitude, z.longitude]}
              radius={z.radius_meters}
              pathOptions={{ color: zoneColor(z), weight: 1.5, fillOpacity: z.active ? 0.15 : 0.04, dashArray: z.active ? undefined : "4 4" }}
            >
              <ZonePopup z={z} />
            </Circle>
          ),
        )}

        {draft && (
          <Circle
            center={[draft.latitude, draft.longitude]}
            radius={draft.radius_meters}
            pathOptions={{ color: "#0f766a", weight: 2, dashArray: "6 4", fillOpacity: 0.1 }}
          />
        )}

        {track && track.length > 1 &&
          track.slice(1).map((p, i) => (
            <CircleMarker key={`tr${i}`} center={p} radius={2.5} pathOptions={{ color: "#0f766a", fillOpacity: 0.8, weight: 0 }} />
          ))}

        {clusters.map((c, i) =>
          c.items.length > 1 ? (
            <CircleMarker
              key={`c${i}`}
              center={[c.lat, c.lon]}
              radius={14 + Math.min(14, c.items.length)}
              pathOptions={{ color: "#0f766a", fillColor: "#0f766a", fillOpacity: 0.85, weight: 2 }}
            >
              <Tooltip permanent direction="center" className="!border-0 !bg-transparent !p-0 !text-white !shadow-none">
                <span className="font-semibold">{c.items.length}</span>
              </Tooltip>
            </CircleMarker>
          ) : (
            <TouristMarker key={`t${c.items[0].tourist_code}`} t={c.items[0]} onClick={onTouristClick} />
          ),
        )}

        {alerts
          .filter((a) => a.latitude != null && a.longitude != null)
          .map((a) => (
            <CircleMarker
              key={`s${a.id}`}
              center={[a.latitude as number, a.longitude as number]}
              radius={11}
              pathOptions={{ color: "#7f1d1d", fillColor: "#dc2626", fillOpacity: 0.9, weight: 3 }}
              eventHandlers={{ click: () => onAlertClick?.(a) }}
            >
              <Tooltip direction="top" offset={[0, -10]}>
                SOS #{a.id} · {a.tourist_name ?? a.tourist_code} · {humanize(a.status)}
              </Tooltip>
            </CircleMarker>
          ))}
      </MapContainer>
    </div>
  );
}

function TouristMarker({ t, onClick }: { t: Tourist; onClick?: (t: Tourist) => void }) {
  const tone = t.location_stale ? "neutral" : statusTone(t.safety_status);
  return (
    <CircleMarker
      center={[t.latitude as number, t.longitude as number]}
      radius={8}
      pathOptions={{ color: "#fff", fillColor: TONE_HEX[tone], fillOpacity: 1, weight: 2 }}
      eventHandlers={{ click: () => onClick?.(t) }}
    >
      <Tooltip direction="top" offset={[0, -8]}>
        <div className="text-xs">
          <p className="font-semibold">{t.name}</p>
          <p>
            {humanize(t.safety_status)} · {timeAgo(t.last_location_update)}
            {t.location_stale ? " (stale)" : ""}
          </p>
        </div>
      </Tooltip>
    </CircleMarker>
  );
}

function ZonePopup({ z }: { z: Zone }) {
  return (
    <Popup>
      <div className="min-w-[200px] text-xs">
        <p className="text-sm font-semibold">{z.name}</p>
        <p className="mt-1">
          {humanize(z.zone_type)}
          {z.risk_level ? ` · ${humanize(z.risk_level)} risk` : ""} · {Math.round(z.radius_meters)} m
        </p>
        <p className="mt-1 font-mono">{coords(z.latitude, z.longitude)}</p>
        {z.synthetic && <p className="mt-1 font-semibold text-violet-700">Synthetic test data — not a real hazard</p>}
        {!z.active && <p className="mt-1 text-slate-500">Inactive (no alerts)</p>}
        {z.description && <p className="mt-1 text-slate-600">{z.description.slice(0, 160)}</p>}
      </div>
    </Popup>
  );
}
