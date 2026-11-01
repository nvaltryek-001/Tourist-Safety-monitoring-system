/**
 * Real phone GPS: permissions, foreground watching, optional background task,
 * offline queue with batched, de-duplicated sync. Never fakes coordinates.
 */
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Location from "expo-location";
import * as TaskManager from "expo-task-manager";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { AppState } from "react-native";
import { api, ApiError } from "./api";
import { useAuth } from "./auth";
import { backoffMs, enqueue, makeClientId, nextBatch, removeSent, type QueuedPoint } from "./queue";

export const BACKGROUND_TASK = "safetrail-background-location";
const QUEUE_KEY = "safetrail.queue";
const SYNC_INTERVAL_MS = 30_000;

export type PermissionState = "unknown" | "granted" | "denied" | "services_off";

export interface Fix {
  latitude: number;
  longitude: number;
  accuracy: number | null;
  timestamp: number;
}

interface LocationState {
  permission: PermissionState;
  background: boolean;
  sharing: boolean;
  lastFix: Fix | null;
  lastSyncAt: number | null;
  pending: number;
  syncError: string | null;
  start: () => Promise<boolean>;
  stop: () => Promise<void>;
  enableBackground: () => Promise<boolean>;
  currentFix: () => Promise<Fix | null>;
  syncNow: () => Promise<void>;
}

const LocationContext = createContext<LocationState | null>(null);

async function readQueue(): Promise<QueuedPoint[]> {
  try {
    const raw = await AsyncStorage.getItem(QUEUE_KEY);
    return raw ? (JSON.parse(raw) as QueuedPoint[]) : [];
  } catch {
    return [];
  }
}

async function writeQueue(queue: QueuedPoint[]) {
  try {
    await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
  } catch {
    /* storage full: the queue stays in memory until the next write */
  }
}

function toPoint(loc: Location.LocationObject): QueuedPoint {
  return {
    client_id: makeClientId(loc.timestamp, loc.coords.latitude, loc.coords.longitude),
    latitude: loc.coords.latitude,
    longitude: loc.coords.longitude,
    accuracy: loc.coords.accuracy ?? null,
    speed: loc.coords.speed != null && loc.coords.speed >= 0 ? loc.coords.speed : null,
    recorded_at: new Date(loc.timestamp).toISOString(),
  };
}

// Background fixes are queued and synced the next time the app is active or
// the foreground sync runs. Defining the task at module scope is required.
if (!TaskManager.isTaskDefined(BACKGROUND_TASK)) {
  TaskManager.defineTask(BACKGROUND_TASK, async ({ data, error }) => {
    if (error || !data) return;
    const { locations } = data as { locations: Location.LocationObject[] };
    let queue = await readQueue();
    for (const loc of locations) queue = enqueue(queue, toPoint(loc));
    await writeQueue(queue);
  });
}

export function LocationProvider({ children }: { children: React.ReactNode }) {
  const { signedIn, profile } = useAuth();
  const [permission, setPermission] = useState<PermissionState>("unknown");
  const [background, setBackground] = useState(false);
  const [sharing, setSharing] = useState(false);
  const [lastFix, setLastFix] = useState<Fix | null>(null);
  const [lastSyncAt, setLastSyncAt] = useState<number | null>(null);
  const [pending, setPending] = useState(0);
  const [syncError, setSyncError] = useState<string | null>(null);
  const watcher = useRef<Location.LocationSubscription | null>(null);
  const failures = useRef(0);
  const nextAttempt = useRef(0);
  const syncing = useRef(false);

  const checkPermission = useCallback(async (): Promise<PermissionState> => {
    const services = await Location.hasServicesEnabledAsync().catch(() => true);
    if (!services) {
      setPermission("services_off");
      return "services_off";
    }
    const fg = await Location.getForegroundPermissionsAsync();
    const state: PermissionState = fg.granted ? "granted" : fg.canAskAgain ? "unknown" : "denied";
    setPermission(state);
    const bg = await Location.getBackgroundPermissionsAsync().catch(() => null);
    setBackground(!!bg?.granted);
    return state;
  }, []);

  const syncNow = useCallback(async () => {
    if (syncing.current || !signedIn || Date.now() < nextAttempt.current) return;
    syncing.current = true;
    try {
      let queue = await readQueue();
      setPending(queue.length);
      while (queue.length) {
        const batch = nextBatch(queue);
        await api("/api/v1/me/locations/batch", { method: "POST", body: { points: batch } });
        queue = removeSent(await readQueue(), batch);
        await writeQueue(queue);
        setPending(queue.length);
      }
      failures.current = 0;
      nextAttempt.current = 0;
      setLastSyncAt(Date.now());
      setSyncError(null);
    } catch (e) {
      failures.current += 1;
      nextAttempt.current = Date.now() + backoffMs(failures.current);
      const message = e instanceof Error ? e.message : "Sync failed";
      setSyncError(e instanceof ApiError && e.status === 403 ? "Location consent is required before sharing." : message);
    } finally {
      syncing.current = false;
    }
  }, [signedIn]);

  const record = useCallback(
    async (loc: Location.LocationObject) => {
      setLastFix({ latitude: loc.coords.latitude, longitude: loc.coords.longitude, accuracy: loc.coords.accuracy ?? null, timestamp: loc.timestamp });
      const queue = enqueue(await readQueue(), toPoint(loc));
      await writeQueue(queue);
      setPending(queue.length);
      void syncNow();
    },
    [syncNow],
  );

  const start = useCallback(async () => {
    if (!profile?.location_consent_at) return false;
    let state = await checkPermission();
    if (state === "services_off") return false;
    if (state !== "granted") {
      const res = await Location.requestForegroundPermissionsAsync();
      state = res.granted ? "granted" : "denied";
      setPermission(state);
    }
    if (state !== "granted") return false;
    watcher.current?.remove();
    watcher.current = await Location.watchPositionAsync(
      // Balanced accuracy, 25 m / 30 s: a battery-conscious default for walking tourists.
      { accuracy: Location.Accuracy.Balanced, distanceInterval: 25, timeInterval: 30_000 },
      (loc) => void record(loc),
    );
    setSharing(true);
    return true;
  }, [profile?.location_consent_at, checkPermission, record]);

  const stop = useCallback(async () => {
    watcher.current?.remove();
    watcher.current = null;
    setSharing(false);
    if (await Location.hasStartedLocationUpdatesAsync(BACKGROUND_TASK).catch(() => false)) {
      await Location.stopLocationUpdatesAsync(BACKGROUND_TASK).catch(() => undefined);
    }
  }, []);

  const enableBackground = useCallback(async () => {
    // Background location is not available in Expo Go; it needs a development
    // or production build (see docs/GPS_AND_LOCATION.md).
    try {
      const res = await Location.requestBackgroundPermissionsAsync();
      if (!res.granted) {
        setBackground(false);
        return false;
      }
      await Location.startLocationUpdatesAsync(BACKGROUND_TASK, {
        accuracy: Location.Accuracy.Balanced,
        distanceInterval: 50,
        timeInterval: 60_000,
        deferredUpdatesInterval: 60_000,
        pausesUpdatesAutomatically: true,
        showsBackgroundLocationIndicator: true,
        foregroundService: {
          notificationTitle: "SafeTrail safety monitoring",
          notificationBody: "Sharing your location with the safety team during your trip.",
        },
      });
      setBackground(true);
      return true;
    } catch {
      setBackground(false);
      return false;
    }
  }, []);

  const currentFix = useCallback(async (): Promise<Fix | null> => {
    try {
      const state = await checkPermission();
      if (state !== "granted") return lastFix;
      const loc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High });
      await record(loc);
      return { latitude: loc.coords.latitude, longitude: loc.coords.longitude, accuracy: loc.coords.accuracy ?? null, timestamp: loc.timestamp };
    } catch {
      return lastFix;
    }
  }, [checkPermission, lastFix, record]);

  // Auto-start after login when consent exists; re-check permission when the
  // app returns to the foreground (the user may have revoked it in Settings).
  useEffect(() => {
    if (!signedIn || !profile?.location_consent_at) {
      void stop();
      return;
    }
    void start();
    const sub = AppState.addEventListener("change", async (s) => {
      if (s !== "active") return;
      const state = await checkPermission();
      if (state !== "granted") {
        watcher.current?.remove();
        watcher.current = null;
        setSharing(false);
      } else if (!watcher.current) {
        void start();
      }
      void syncNow();
    });
    const timer = setInterval(() => void syncNow(), SYNC_INTERVAL_MS);
    return () => {
      sub.remove();
      clearInterval(timer);
    };
  }, [signedIn, profile?.location_consent_at, start, stop, checkPermission, syncNow]);

  return (
    <LocationContext.Provider
      value={{ permission, background, sharing, lastFix, lastSyncAt, pending, syncError, start, stop, enableBackground, currentFix, syncNow }}
    >
      {children}
    </LocationContext.Provider>
  );
}

export function useLocation(): LocationState {
  const ctx = useContext(LocationContext);
  if (!ctx) throw new Error("useLocation outside LocationProvider");
  return ctx;
}
