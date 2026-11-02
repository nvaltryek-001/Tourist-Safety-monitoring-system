"use client";

import { MarkerClusterer, type Marker } from "@googlemaps/markerclusterer";
import { AdvancedMarker, APIProvider, InfoWindow, Map, Pin, useMap, type MapMouseEvent } from "@vis.gl/react-google-maps";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { coords, humanize, metres, statusTone, timeAgo } from "@/lib/format";
import { FACILITY_STYLE, GOOGLE_MAP_ID, geometryPaths, googleDirectionsUrl, zoneColor } from "@/lib/maps";
import type { Facility, SOSAlert, Tourist, Zone } from "@/lib/types";
import type { MapViewProps } from "../MapView";
import { TONE_HEX } from "../ui";
import { Circle, DirectionsRoute, GeoJsonLayer, Polygon, Polyline, type RouteStatus } from "./overlays";

type Selected =
  | { kind: "zone"; zone: Zone; at: google.maps.LatLngLiteral }
  | { kind: "tourist"; tourist: Tourist }
  | { kind: "alert"; alert: SOSAlert }
  | { kind: "facility"; facility: Facility }
  | { kind: "layer"; props: Record<string, unknown>; at: google.maps.LatLngLiteral }
  | null;

export default function GoogleMapView(props: MapViewProps & { apiKey: string; onLoadError?: () => void }) {
  const { apiKey, onLoadError, height = "520px" } = props;
  return (
    <div style={{ height }} className="relative overflow-hidden rounded-lg border hairline">
      <APIProvider apiKey={apiKey} libraries={["marker", "routes"]} onError={() => onLoadError?.()}>
        <Inner {...props} />
      </APIProvider>
    </div>
  );
}

function Inner({
  zones = [],
  tourists = [],
  alerts = [],
  facilities = [],
  layers = [],
  center,
  zoom = 12,
  focus,
  track,
  route,
  draft,
  onTouristClick,
  onAlertClick,
  onMapClick,
}: MapViewProps) {
  const [selected, setSelected] = useState<Selected>(null);
  const [routeStatus, setRouteStatus] = useState<{ status: RouteStatus; summary?: string }>({ status: "idle" });
  const located = tourists.filter((t) => t.latitude != null && t.longitude != null);
  const initial = useMemo<google.maps.LatLngLiteral>(() => {
    if (center) return { lat: center[0], lng: center[1] };
    if (located[0]) return { lat: located[0].latitude as number, lng: located[0].longitude as number };
    if (zones[0]) return { lat: zones[0].latitude, lng: zones[0].longitude };
    return { lat: 12.9716, lng: 77.5946 };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleMapClick = useCallback(
    (ev: MapMouseEvent) => {
      setSelected(null);
      const ll = ev.detail.latLng;
      if (ll) onMapClick?.(ll.lat, ll.lng);
    },
    [onMapClick],
  );

  return (
    <>
      <Map
        mapId={GOOGLE_MAP_ID}
        defaultCenter={initial}
        defaultZoom={zoom}
        gestureHandling="greedy"
        disableDefaultUI={false}
        mapTypeControl
        streetViewControl={false}
        fullscreenControl
        clickableIcons={false}
        onClick={handleMapClick}
        style={{ width: "100%", height: "100%" }}
      >
        <FocusOn focus={focus} />

        {layers.map((layer) => (
          <GeoJsonLayer
            key={layer.id}
            data={layer.data}
            style={{ fillColor: layer.color, strokeColor: layer.color, strokeWeight: 1, fillOpacity: 0.12 }}
            onFeatureClick={(p, at) => at && setSelected({ kind: "layer", props: { ...p, layer: layer.label }, at })}
          />
        ))}

        {zones.map((z) => {
          const color = zoneColor(z);
          const style = { strokeColor: color, strokeWeight: 1.5, fillColor: color, fillOpacity: z.active ? 0.18 : 0.05, strokeOpacity: z.active ? 0.9 : 0.4 };
          const open = () => setSelected({ kind: "zone", zone: z, at: { lat: z.latitude, lng: z.longitude } });
          return z.geometry ? (
            <Polygon key={`z${z.id}`} paths={geometryPaths(z.geometry)} {...style} onClick={open} />
          ) : (
            <Circle key={`z${z.id}`} center={{ lat: z.latitude, lng: z.longitude }} radius={z.radius_meters} {...style} onClick={open} />
          );
        })}

        {draft && (
          <Circle center={{ lat: draft.latitude, lng: draft.longitude }} radius={draft.radius_meters}
            strokeColor="#0f766a" strokeWeight={2} fillColor="#14917c" fillOpacity={0.15} />
        )}

        {track && track.length > 1 && (
          <Polyline path={track.map(([lat, lng]) => ({ lat, lng }))} strokeColor="#0f766a" strokeWeight={4} strokeOpacity={0.8} />
        )}

        <ClusteredMarkers
          items={located.map((t) => ({ key: `t-${t.tourist_code}`, lat: t.latitude as number, lng: t.longitude as number, t }))}
          render={(item) => <TouristDot tourist={item.t} />}
          onClick={(item) => {
            setSelected({ kind: "tourist", tourist: item.t });
            onTouristClick?.(item.t);
          }}
        />

        <ClusteredMarkers
          items={facilities.map((f) => ({ key: `f-${f.id}`, lat: f.latitude, lng: f.longitude, f }))}
          render={(item) => {
            const s = FACILITY_STYLE[item.f.facility_type];
            return <Pin background={s.color} borderColor="#fff" glyphColor="#fff" glyph={s.glyph} scale={0.85} />;
          }}
          onClick={(item) => setSelected({ kind: "facility", facility: item.f })}
          clusterColor="#1d4ed8"
        />

        {alerts
          .filter((a) => a.latitude != null && a.longitude != null)
          .map((a) => (
            <AdvancedMarker
              key={`s${a.id}`}
              position={{ lat: a.latitude as number, lng: a.longitude as number }}
              zIndex={1000}
              onClick={() => {
                setSelected({ kind: "alert", alert: a });
                onAlertClick?.(a);
              }}
              title={`SOS #${a.id}`}
            >
              <span className="relative flex h-7 w-7 items-center justify-center">
                <span className="sos-pulse absolute inline-flex h-full w-full rounded-full bg-red-500" />
                <span className="relative inline-flex h-5 w-5 items-center justify-center rounded-full border-2 border-white bg-red-600 text-[9px] font-bold text-white">
                  SOS
                </span>
              </span>
            </AdvancedMarker>
          ))}

        {route && (
          <>
            <DirectionsRoute
              from={{ lat: route.from[0], lng: route.from[1] }}
              to={{ lat: route.to[0], lng: route.to[1] }}
              onStatus={(status, summary) => setRouteStatus({ status, summary })}
            />
          </>
        )}

        {selected && <Details selected={selected} onClose={() => setSelected(null)} />}
      </Map>

      {route && routeStatus.status !== "idle" && (
        <div className="absolute bottom-3 left-3 z-10 rounded border hairline bg-[var(--panel)] px-3 py-2 text-xs shadow">
          <p className="font-semibold">{route.label ?? "Route"}</p>
          <p className="muted">{routeStatus.status === "loading" ? "Calculating route…" : routeStatus.summary}</p>
          <a className="text-brand-600 hover:underline" href={googleDirectionsUrl(route.to, route.from)} target="_blank" rel="noreferrer">
            Open turn-by-turn in Google Maps →
          </a>
        </div>
      )}
    </>
  );
}

/* ----------------------------------------------------------------- pieces */
function FocusOn({ focus }: { focus?: [number, number] | null }) {
  const map = useMap();
  useEffect(() => {
    if (!map || !focus) return;
    map.panTo({ lat: focus[0], lng: focus[1] });
    if ((map.getZoom() ?? 0) < 15) map.setZoom(15);
  }, [map, focus]);
  return null;
}

function TouristDot({ tourist }: { tourist: Tourist }) {
  const tone = tourist.location_stale ? "neutral" : statusTone(tourist.safety_status);
  return (
    <span
      className="block h-4 w-4 rounded-full border-2 border-white shadow-md ring-2 ring-black/10"
      style={{ background: TONE_HEX[tone] }}
      title={tourist.name}
    />
  );
}

interface Item {
  key: string;
  lat: number;
  lng: number;
}

/** Codelab pattern: collect AdvancedMarker refs and hand them to a MarkerClusterer. */
function ClusteredMarkers<T extends Item>({
  items,
  render,
  onClick,
  clusterColor = "#0f766a",
}: {
  items: T[];
  render: (item: T) => React.ReactNode;
  onClick: (item: T) => void;
  clusterColor?: string;
}) {
  const map = useMap();
  const [markers, setMarkers] = useState<Record<string, Marker>>({});
  const clusterer = useRef<MarkerClusterer | null>(null);

  useEffect(() => {
    if (!map) return;
    if (!clusterer.current) {
      clusterer.current = new MarkerClusterer({
        map,
        renderer: {
          render: ({ count, position }) => {
            const el = document.createElement("div");
            el.style.cssText = `background:${clusterColor};color:#fff;border:3px solid rgba(255,255,255,.85);border-radius:999px;min-width:34px;height:34px;display:flex;align-items:center;justify-content:center;font:600 12px var(--font-sans),sans-serif;box-shadow:0 4px 14px rgba(0,0,0,.25)`;
            el.textContent = String(count);
            return new google.maps.marker.AdvancedMarkerElement({ position, content: el, zIndex: 500 + count });
          },
        },
      });
    }
    return () => {
      clusterer.current?.clearMarkers();
      clusterer.current?.setMap(null);
      clusterer.current = null;
    };
  }, [map, clusterColor]);

  useEffect(() => {
    clusterer.current?.clearMarkers();
    clusterer.current?.addMarkers(Object.values(markers));
  }, [markers]);

  const setMarkerRef = useCallback((marker: Marker | null, key: string) => {
    setMarkers((prev) => {
      if ((marker && prev[key] === marker) || (!marker && !prev[key])) return prev;
      const next = { ...prev };
      if (marker) next[key] = marker;
      else delete next[key];
      return next;
    });
  }, []);

  return (
    <>
      {items.map((item) => (
        <AdvancedMarker
          key={item.key}
          position={{ lat: item.lat, lng: item.lng }}
          ref={(m) => setMarkerRef(m, item.key)}
          onClick={() => onClick(item)}
        >
          {render(item)}
        </AdvancedMarker>
      ))}
    </>
  );
}

function Details({ selected, onClose }: { selected: NonNullable<Selected>; onClose: () => void }) {
  let position: google.maps.LatLngLiteral;
  let body: React.ReactNode;
  if (selected.kind === "zone") {
    const z = selected.zone;
    position = selected.at;
    body = (
      <>
        <p className="text-sm font-semibold">{z.name}</p>
        <p>{humanize(z.zone_type)}{z.risk_level ? ` · ${humanize(z.risk_level)} risk` : ""} · {Math.round(z.radius_meters)} m</p>
        {z.category && <p>Category: {humanize(z.category)}</p>}
        {z.synthetic && <p className="font-semibold text-violet-700">Synthetic test data — not a real hazard</p>}
        {!z.active && <p className="text-slate-500">Inactive (no alerts)</p>}
        {z.source && <p className="text-slate-500">Source: {z.source}</p>}
      </>
    );
  } else if (selected.kind === "tourist") {
    const t = selected.tourist;
    position = { lat: t.latitude as number, lng: t.longitude as number };
    body = (
      <>
        <p className="text-sm font-semibold">{t.name}</p>
        <p>{humanize(t.safety_status)} · {timeAgo(t.last_location_update)}{t.location_stale ? " (stale)" : ""}</p>
        <p className="font-mono">{coords(t.latitude, t.longitude)} · ±{metres(t.location_accuracy)}</p>
        <a className="text-brand-600 hover:underline" href={`/tourists/${encodeURIComponent(t.tourist_code)}`}>Open profile →</a>
      </>
    );
  } else if (selected.kind === "alert") {
    const a = selected.alert;
    position = { lat: a.latitude as number, lng: a.longitude as number };
    body = (
      <>
        <p className="text-sm font-semibold text-red-700">SOS #{a.id} · {a.tourist_name ?? a.tourist_code}</p>
        <p>{humanize(a.status)} · {humanize(a.alert_type)} · {timeAgo(a.created_at)}</p>
        <a className="text-brand-600 hover:underline" href={`/incidents/${a.id}`}>Open incident →</a>
      </>
    );
  } else if (selected.kind === "facility") {
    const f = selected.facility;
    position = { lat: f.latitude, lng: f.longitude };
    body = (
      <>
        <p className="text-sm font-semibold">{f.name}</p>
        <p>{FACILITY_STYLE[f.facility_type].label}{f.distance_meters != null ? ` · ${metres(f.distance_meters)}` : ""}</p>
        {f.phone && <p>☎ <a className="text-brand-600" href={`tel:${f.phone}`}>{f.phone}</a></p>}
        {f.address && <p className="text-slate-500">{f.address}</p>}
        <p className="text-[10px] text-slate-500">{f.source === "osm" ? "© OpenStreetMap contributors" : "Added by admin"}</p>
      </>
    );
  } else {
    position = selected.at;
    body = (
      <>
        <p className="text-sm font-semibold">{String(selected.props.name ?? "Area")}</p>
        {Object.entries(selected.props)
          .filter(([k, v]) => k !== "name" && v != null && typeof v !== "object")
          .slice(0, 6)
          .map(([k, v]) => (
            <p key={k}><span className="text-slate-500">{humanize(k)}:</span> {String(v)}</p>
          ))}
      </>
    );
  }
  return (
    <InfoWindow position={position} onCloseClick={onClose} pixelOffset={[0, -12]}>
      <div className="min-w-[200px] space-y-0.5 text-xs text-slate-800">{body}</div>
    </InfoWindow>
  );
}
