export function timeAgo(iso: string | null | undefined, now: number = Date.now()): string {
  if (!iso) return "never";
  const t = new Date(iso.endsWith("Z") || /[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`).getTime();
  if (Number.isNaN(t)) return "unknown";
  const s = Math.max(0, Math.round((now - t) / 1000));
  if (s < 45) return "just now";
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  return `${Math.round(s / 86400)} d ago`;
}

export function dateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso.endsWith("Z") || /[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export function coords(lat: number | null | undefined, lon: number | null | undefined): string {
  if (lat == null || lon == null) return "No location";
  return `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
}

export function metres(m: number | null | undefined): string {
  if (m == null) return "—";
  return m >= 1000 ? `${(m / 1000).toFixed(1)} km` : `${Math.round(m)} m`;
}

export function humanize(value: string | null | undefined): string {
  if (!value) return "—";
  return value
    .toLowerCase()
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export type Tone = "safe" | "caution" | "danger" | "sos" | "neutral" | "info";

export function statusTone(status: string | null | undefined): Tone {
  switch ((status || "").toUpperCase()) {
    case "SAFE":
    case "RESOLVED":
    case "LOW":
    case "ACCEPTED_BY_PROVIDER":
    case "DELIVERED_IN_APP":
      return "safe";
    case "CAUTION":
    case "ACKNOWLEDGED":
    case "MEDIUM":
    case "NOT_CONFIGURED":
      return "caution";
    case "DANGER":
    case "RESTRICTED":
    case "HIGH":
    case "HIGH_RISK":
    case "RESPONDING":
    case "FAILED":
      return "danger";
    case "SOS":
    case "OPEN":
    case "CRITICAL":
      return "sos";
    case "CANCELLED":
    case "UNKNOWN":
      return "neutral";
    default:
      return "info";
  }
}

export const STATUS_LABEL: Record<string, string> = {
  SAFE: "Safe",
  CAUTION: "Caution",
  DANGER: "Restricted zone",
  SOS: "Emergency",
  UNKNOWN: "Location unavailable",
};
