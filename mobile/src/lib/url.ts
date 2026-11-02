/** Pure helpers (unit-tested without React Native). */

export function normalizeUrl(input: string): string {
  let url = input.trim().replace(/\/+$/, "");
  if (url && !/^https?:\/\//i.test(url)) url = `http://${url}`;
  if (/^http:\/\/[\d.]+$/.test(url)) url = `${url}:8000`;
  return url;
}

export function haversineMeters(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const r = (d: number) => (d * Math.PI) / 180;
  const a = Math.sin(r(lat2 - lat1) / 2) ** 2 + Math.cos(r(lat1)) * Math.cos(r(lat2)) * Math.sin(r(lon2 - lon1) / 2) ** 2;
  return 6371000 * 2 * Math.asin(Math.min(1, Math.sqrt(a)));
}

export function formatDistance(m: number | null | undefined): string {
  if (m == null) return "—";
  return m >= 1000 ? `${(m / 1000).toFixed(1)} km` : `${Math.round(m)} m`;
}

/** Google Maps navigation deep link (opens the Google Maps app if installed, else the browser). */
export function navigationUrl(lat: number, lon: number): string {
  return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lon}&travelmode=driving`;
}
