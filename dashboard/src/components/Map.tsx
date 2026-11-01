"use client";

import dynamic from "next/dynamic";
import type { MapViewProps } from "./MapView";
import { Skeleton } from "./ui";

const MapView = dynamic(() => import("./MapView"), {
  ssr: false,
  loading: () => <Skeleton className="h-[520px] w-full" />,
});

export function SafetyMap(props: MapViewProps) {
  return <MapView {...props} />;
}

export function MapLegend() {
  const items: [string, string, boolean?][] = [
    ["Safe", "#15803d"],
    ["Caution", "#d97706"],
    ["Restricted zone", "#ea580c"],
    ["SOS / emergency", "#dc2626"],
    ["Stale location", "#64748b"],
    ["Restricted area", "#dc2626", true],
    ["Synthetic test zone", "#7c3aed", true],
  ];
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs muted">
      {items.map(([label, color, ring]) => (
        <span key={label} className="inline-flex items-center gap-1.5">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={ring ? { border: `2px solid ${color}`, background: `${color}22` } : { background: color }}
          />
          {label}
        </span>
      ))}
    </div>
  );
}
