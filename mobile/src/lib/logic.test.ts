import { describe, expect, it } from "vitest";
import { backoffMs, enqueue, makeClientId, nextBatch, removeSent, type QueuedPoint } from "./queue";
import { accuracyLabel, isGmail, sosStatusText, statusView } from "./status";
import { formatDistance, haversineMeters, navigationUrl, normalizeUrl } from "./url";

const point = (i: number): QueuedPoint => ({
  client_id: makeClientId(1000 + i, 13 + i / 1000, 77),
  latitude: 13 + i / 1000,
  longitude: 77,
  accuracy: 10,
  speed: null,
  recorded_at: new Date(1000 + i).toISOString(),
});

describe("offline queue", () => {
  it("deduplicates by client id", () => {
    const q = enqueue(enqueue([], point(1)), point(1));
    expect(q).toHaveLength(1);
  });
  it("caps the queue keeping newest points", () => {
    let q: QueuedPoint[] = [];
    for (let i = 0; i < 10; i++) q = enqueue(q, point(i), 5);
    expect(q).toHaveLength(5);
    expect(q[0].client_id).toBe(point(5).client_id);
  });
  it("removes only points that were sent", () => {
    const q = [point(1), point(2), point(3)];
    const batch = nextBatch(q, 2);
    expect(removeSent(q, batch)).toEqual([point(3)]);
  });
  it("backs off exponentially with a cap", () => {
    expect(backoffMs(1)).toBe(5000);
    expect(backoffMs(3)).toBe(20000);
    expect(backoffMs(20)).toBe(300000);
  });
});

describe("status helpers", () => {
  it("never shows safe for unknown states", () => {
    expect(statusView("SOMETHING").label).toBe("Location unavailable");
    expect(statusView("RESTRICTED").label).toBe("Restricted zone");
  });
  it("describes accuracy", () => {
    expect(accuracyLabel(8)).toMatch(/High/);
    expect(accuracyLabel(120)).toMatch(/Low/);
    expect(accuracyLabel(null)).toBe("Unknown accuracy");
  });
  it("accepts only Gmail addresses", () => {
    expect(isGmail("name.surname@gmail.com")).toBe(true);
    expect(isGmail("x@googlemail.com")).toBe(true);
    expect(isGmail("x@yahoo.com")).toBe(false);
    expect(isGmail("not an email")).toBe(false);
  });
  it("explains SOS states", () => {
    expect(sosStatusText("OPEN")).toMatch(/Received by the server/);
  });
});

describe("server url and distance helpers", () => {
  it("normalises typed server addresses", () => {
    expect(normalizeUrl("192.168.1.10")).toBe("http://192.168.1.10:8000");
    expect(normalizeUrl("192.168.1.10:9000/")).toBe("http://192.168.1.10:9000");
    expect(normalizeUrl("https://safetrail-api.onrender.com/")).toBe("https://safetrail-api.onrender.com");
  });
  it("computes distances and navigation links", () => {
    expect(haversineMeters(0, 0, 1, 0)).toBeGreaterThan(111000);
    expect(haversineMeters(0, 0, 1, 0)).toBeLessThan(111400);
    expect(formatDistance(850)).toBe("850 m");
    expect(formatDistance(2400)).toBe("2.4 km");
    expect(navigationUrl(13.1, 77.5)).toContain("destination=13.1,77.5");
  });
});
