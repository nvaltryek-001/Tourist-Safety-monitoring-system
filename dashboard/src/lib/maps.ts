/** Map helpers shared by the Google and OpenStreetMap renderers (pure, unit-tested). */
import type { Facility, FacilityType, GeoJSONGeometry, Zone } from "./types";

export const GOOGLE_MAPS_API_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "";
// "DEMO_MAP_ID" is Google's documented development Map ID for AdvancedMarkers.
export const GOOGLE_MAP_ID = process.env.NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID || "DEMO_MAP_ID";
export const hasGoogleMaps = (key: string = GOOGLE_MAPS_API_KEY) => key.trim().length > 20;

export const ZONE_COLORS: Record<string, string> = {
  RESTRICTED: "#dc2626",
  HIGH_RISK: "#ea580c",
  CAUTION: "#d97706",
  SAFE: "#15803d",
};

export const FACILITY_STYLE: Record<FacilityType, { color: string; glyph: string; label: string }> = {
  POLICE: { color: "#1d4ed8", glyph: "P", label: "Police" },
  HOSPITAL: { color: "#be123c", glyph: "H", label: "Hospital" },
  CLINIC: { color: "#e11d48", glyph: "+", label: "Clinic" },
  FIRE_STATION: { color: "#c2410c", glyph: "F", label: "Fire station" },
  PHARMACY: { color: "#059669", glyph: "Rx", label: "Pharmacy" },
};

export function zoneColor(z: Pick<Zone, "zone_type" | "synthetic">): string {
  if (z.synthetic) return "#7c3aed";
  return ZONE_COLORS[z.zone_type] ?? "#0284c7";
}

/** GeoJSON (lon, lat) rings -> Google/Leaflet style {lat, lng} paths (outer rings + holes). */
export function geometryPaths(geometry: GeoJSONGeometry): { lat: number; lng: number }[][] {
  const polys = (geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates) as number[][][][];
  return polys.flatMap((rings) => rings.map((ring) => ring.map(([lng, lat]) => ({ lat, lng }))));
}

export function zonesToFeatureCollection(zones: Zone[]) {
  return {
    type: "FeatureCollection" as const,
    features: zones
      .filter((z) => z.geometry)
      .map((z) => ({ type: "Feature" as const, id: z.id, geometry: z.geometry, properties: { id: z.id, name: z.name } })),
  };
}

export function boundsOf(points: { lat: number; lng: number }[]) {
  if (!points.length) return null;
  let south = 90, west = 180, north = -90, east = -180;
  for (const p of points) {
    south = Math.min(south, p.lat);
    north = Math.max(north, p.lat);
    west = Math.min(west, p.lng);
    east = Math.max(east, p.lng);
  }
  return { south, west, north, east };
}

export function googleDirectionsUrl(to: [number, number], from?: [number, number]): string {
  const q = new URLSearchParams({ api: "1", destination: `${to[0]},${to[1]}`, travelmode: "driving" });
  if (from) q.set("origin", `${from[0]},${from[1]}`);
  return `https://www.google.com/maps/dir/?${q}`;
}

export function facilityLabel(f: Pick<Facility, "facility_type">): string {
  return FACILITY_STYLE[f.facility_type]?.label ?? f.facility_type;
}
