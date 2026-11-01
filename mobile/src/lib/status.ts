/** Mapping of server display states to what the tourist sees (pure, tested). */
export type DisplayState =
  | "SAFE"
  | "CAUTION"
  | "RESTRICTED"
  | "EMERGENCY"
  | "LOCATION_UNAVAILABLE"
  | "LOCATION_STALE";

export interface StatusView {
  label: string;
  message: string;
  color: string;
  background: string;
}

export const STATUS_VIEW: Record<DisplayState, StatusView> = {
  SAFE: {
    label: "No known hazards",
    message: "You are not inside or near any active restricted zone. Stay alert to your surroundings.",
    color: "#14532d",
    background: "#dcfce7",
  },
  CAUTION: {
    label: "Caution",
    message: "You are close to a restricted or higher-risk area. Check the map before moving further.",
    color: "#78350f",
    background: "#fef3c7",
  },
  RESTRICTED: {
    label: "Restricted zone",
    message: "You are inside a restricted zone. Leave the area if it is safe to do so.",
    color: "#7c2d12",
    background: "#ffedd5",
  },
  EMERGENCY: {
    label: "Emergency active",
    message: "Your SOS is active. Keep your phone with you; the response team can see your location.",
    color: "#7f1d1d",
    background: "#fee2e2",
  },
  LOCATION_UNAVAILABLE: {
    label: "Location unavailable",
    message: "We cannot assess your safety without your location. Enable location sharing.",
    color: "#334155",
    background: "#e2e8f0",
  },
  LOCATION_STALE: {
    label: "Location out of date",
    message: "Your last location is old. Check your connection and that location sharing is on.",
    color: "#334155",
    background: "#e2e8f0",
  },
};

export function statusView(state: string | null | undefined): StatusView {
  return STATUS_VIEW[(state as DisplayState) in STATUS_VIEW ? (state as DisplayState) : "LOCATION_UNAVAILABLE"];
}

export function accuracyLabel(accuracy: number | null | undefined): string {
  if (accuracy == null) return "Unknown accuracy";
  if (accuracy <= 15) return `High accuracy (±${Math.round(accuracy)} m)`;
  if (accuracy <= 50) return `Moderate accuracy (±${Math.round(accuracy)} m)`;
  return `Low accuracy (±${Math.round(accuracy)} m)`;
}

export function isGmail(email: string): boolean {
  return /^[^\s@]+@(gmail|googlemail)\.com$/i.test(email.trim());
}

export function sosStatusText(status: string): string {
  switch (status) {
    case "OPEN":
      return "Received by the server — waiting for the monitoring team";
    case "ACKNOWLEDGED":
      return "Acknowledged by the monitoring team";
    case "RESPONDING":
      return "An officer is responding";
    case "RESOLVED":
      return "Resolved";
    case "CANCELLED":
      return "Cancelled";
    default:
      return status;
  }
}
