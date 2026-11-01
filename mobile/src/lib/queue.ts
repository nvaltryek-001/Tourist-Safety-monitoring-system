/**
 * Offline location queue (pure logic, no React Native imports — unit tested).
 *
 * Every fix gets a client_id so the server ignores replays; the queue is
 * capped so a long offline period cannot exhaust storage.
 */
export interface QueuedPoint {
  client_id: string;
  latitude: number;
  longitude: number;
  accuracy: number | null;
  speed: number | null;
  recorded_at: string;
}

export const MAX_QUEUE = 500;
export const BATCH_SIZE = 100;

export function makeClientId(timestamp: number, lat: number, lon: number): string {
  return `${timestamp}-${lat.toFixed(6)}-${lon.toFixed(6)}`;
}

export function enqueue(queue: QueuedPoint[], point: QueuedPoint, max = MAX_QUEUE): QueuedPoint[] {
  if (queue.some((p) => p.client_id === point.client_id)) return queue;
  const next = [...queue, point];
  // Keep the newest points: they matter most to responders.
  return next.length > max ? next.slice(next.length - max) : next;
}

export function nextBatch(queue: QueuedPoint[], size = BATCH_SIZE): QueuedPoint[] {
  return queue.slice(0, size);
}

export function removeSent(queue: QueuedPoint[], sent: QueuedPoint[]): QueuedPoint[] {
  const ids = new Set(sent.map((p) => p.client_id));
  return queue.filter((p) => !ids.has(p.client_id));
}

/** Exponential backoff for weak networks: 5 s, 10 s, 20 s … capped at 5 min. */
export function backoffMs(failures: number): number {
  return Math.min(5 * 60_000, 5_000 * 2 ** Math.max(0, failures - 1));
}
