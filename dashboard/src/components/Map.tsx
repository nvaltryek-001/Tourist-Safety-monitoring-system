"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { GOOGLE_MAPS_API_KEY, hasGoogleMaps } from "@/lib/maps";
import type { MapViewProps } from "./MapView";
import { Skeleton } from "./ui";

const LeafletMap = dynamic(() => import("./MapView"), { ssr: false, loading: () => <Skeleton className="h-[520px] w-full" /> });
const GoogleMap = dynamic(() => import("./google/GoogleMapView"), { ssr: false, loading: () => <Skeleton className="h-[520px] w-full" /> });

/**
 * Google Maps when NEXT_PUBLIC_GOOGLE_MAPS_API_KEY is set (and loads);
 * otherwise the OpenStreetMap/Leaflet fallback with the same features.
 */
export function SafetyMap(props: MapViewProps) {
  const [failed, setFailed] = useState(false);
  if (hasGoogleMaps() && !failed) {
    return <GoogleMap {...props} apiKey={GOOGLE_MAPS_API_KEY} onLoadError={() => setFailed(true)} />;
  }
  return (
    <div className="relative">
      <LeafletMap {...props} />
      {failed && (
        <p className="absolute left-3 top-3 z-[500] rounded bg-amber-50 px-2 py-1 text-[11px] text-amber-900 shadow">
          Google Maps failed to load (check the API key restrictions) — showing OpenStreetMap.
        </p>
      )}
    </div>
  );
}

export const MAP_PROVIDER = hasGoogleMaps() ? "Google Maps" : "OpenStreetMap";

export function MapLegend({ facilities = false }: { facilities?: boolean }) {
  const items: [string, string, boolean?][] = [
    ["Safe", "#15803d"],
    ["Caution", "#d97706"],
    ["Restricted zone", "#ea580c"],
    ["SOS / emergency", "#dc2626"],
    ["Stale location", "#64748b"],
    ["Restricted area", "#dc2626", true],
    ["Synthetic test zone", "#7c3aed", true],
  ];
  if (facilities) items.push(["Police", "#1d4ed8"], ["Hospital", "#be123c"], ["Fire station", "#c2410c"]);
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs muted">
      {items.map(([label, color, ring]) => (
        <span key={label} className="inline-flex items-center gap-1.5">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={ring ? { border: `2px solid ${color}`, background: `${color}22` } : { background: color }}
          />
          {label}
        </span>
      ))}
      <span className="ml-auto text-[10px] uppercase tracking-wider">Map: {MAP_PROVIDER}</span>
    </div>
  );
}
