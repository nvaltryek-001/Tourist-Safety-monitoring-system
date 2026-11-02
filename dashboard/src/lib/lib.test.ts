import { describe, expect, it } from "vitest";
import { clusterPoints } from "./cluster";
import { errorMessage } from "./api";
import { coords, humanize, metres, statusTone, timeAgo } from "./format";

describe("format helpers", () => {
  it("formats relative time", () => {
    const now = Date.parse("2026-11-01T12:00:00Z");
    expect(timeAgo("2026-11-01T11:59:50Z", now)).toBe("just now");
    expect(timeAgo("2026-11-01T11:30:00Z", now)).toBe("30 min ago");
    expect(timeAgo("2026-11-01T09:00:00", now)).toBe("3 h ago");
    expect(timeAgo(null, now)).toBe("never");
  });
  it("formats coordinates and distances", () => {
    expect(coords(13.1, 77.5)).toBe("13.10000, 77.50000");
    expect(coords(null, 1)).toBe("No location");
    expect(metres(1500)).toBe("1.5 km");
    expect(metres(42.4)).toBe("42 m");
  });
  it("maps statuses to tones", () => {
    expect(statusTone("SOS")).toBe("sos");
    expect(statusTone("DANGER")).toBe("danger");
    expect(statusTone("SAFE")).toBe("safe");
    expect(humanize("FALSE_ALARM")).toBe("False Alarm");
  });
});

describe("api error messages", () => {
  it("prefers validation details", () => {
    expect(errorMessage({ detail: "Validation failed", errors: [{ field: "email", message: "bad" }] }, 422)).toBe(
      "email: bad",
    );
    expect(errorMessage({ detail: "Nope" }, 403)).toBe("Nope");
    expect(errorMessage(null, 0)).toMatch(/Cannot reach/);
  });
});

describe("clustering", () => {
  const pts = Array.from({ length: 100 }, (_, i) => ({ lat: 13 + (i % 2) * 0.0001, lon: 77, item: i }));
  it("clusters dense points at low zoom", () => {
    const clusters = clusterPoints(pts, 8);
    expect(clusters.length).toBeLessThan(5);
    expect(clusters.reduce((n, c) => n + c.items.length, 0)).toBe(100);
  });
  it("does not cluster small sets or high zoom", () => {
    expect(clusterPoints(pts.slice(0, 5), 5)).toHaveLength(5);
    expect(clusterPoints(pts, 17)).toHaveLength(100);
  });
});

import { boundsOf, geometryPaths, googleDirectionsUrl, hasGoogleMaps, zoneColor, zonesToFeatureCollection } from "./maps";

describe("map helpers", () => {
  it("detects whether a Google key is configured", () => {
    expect(hasGoogleMaps("")).toBe(false);
    expect(hasGoogleMaps("short")).toBe(false);
    expect(hasGoogleMaps("AIza" + "x".repeat(35))).toBe(true);
  });
  it("converts GeoJSON rings to lat/lng paths including holes", () => {
    const paths = geometryPaths({
      type: "Polygon",
      coordinates: [
        [[77, 13], [77.1, 13], [77.1, 13.1], [77, 13]],
        [[77.02, 13.02], [77.03, 13.02], [77.03, 13.03], [77.02, 13.02]],
      ],
    });
    expect(paths).toHaveLength(2);
    expect(paths[0][1]).toEqual({ lat: 13, lng: 77.1 });
  });
  it("builds feature collections only for polygon zones", () => {
    const base = { latitude: 13, longitude: 77, radius_meters: 10, zone_type: "RESTRICTED", risk_level: null, description: null, active: true, source: null, verification_status: null, synthetic: false, college_demo: false, updated_at: null };
    const fc = zonesToFeatureCollection([
      { ...base, id: 1, name: "circle", geometry: null },
      { ...base, id: 2, name: "poly", geometry: { type: "Polygon", coordinates: [[[77, 13], [77.1, 13], [77, 13.1], [77, 13]]] } },
    ]);
    expect(fc.features.map((f) => f.id)).toEqual([2]);
  });
  it("colours synthetic zones distinctly and builds directions links", () => {
    expect(zoneColor({ zone_type: "RESTRICTED", synthetic: true })).toBe("#7c3aed");
    expect(zoneColor({ zone_type: "RESTRICTED", synthetic: false })).toBe("#dc2626");
    expect(googleDirectionsUrl([13.1, 77.5], [13, 77])).toContain("destination=13.1%2C77.5");
    expect(boundsOf([{ lat: 1, lng: 2 }, { lat: -1, lng: 5 }])).toEqual({ south: -1, west: 2, north: 1, east: 5 });
  });
});
