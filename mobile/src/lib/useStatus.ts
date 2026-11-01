import { useFocusEffect } from "expo-router";
import { useCallback, useRef, useState } from "react";
import { api } from "./api";

export interface ZoneHit {
  zone_id: number;
  zone_name: string;
  zone_type: string;
  risk_level: string | null;
  distance_meters: number;
  radius_meters: number;
}

export interface TimelineEvent {
  id: number;
  action: string;
  actor_name: string | null;
  to_status: string | null;
  note: string | null;
  created_at: string;
}

export interface SOSAlert {
  id: number;
  status: string;
  alert_type: string;
  message: string | null;
  latitude: number | null;
  longitude: number | null;
  created_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  resolution_outcome: string | null;
  assigned_officer?: { name: string; badge_number: string | null };
  timeline?: TimelineEvent[];
}

export interface Trip {
  id: number;
  title: string;
  destination: string | null;
  status: string;
  started_at: string;
  ended_at: string | null;
  planned_end_at: string | null;
}

export interface MyStatus {
  display_state: string;
  safety_status: string;
  location_state: "LIVE" | "STALE" | "UNAVAILABLE";
  last_location_update: string | null;
  location: { latitude: number | null; longitude: number | null; accuracy: number | null };
  zones: { status: string; inside: ZoneHit[]; nearby: ZoneHit[]; nearest_restricted: ZoneHit | null } | null;
  active_sos: SOSAlert | null;
  active_trip: Trip | null;
  unread_notifications: number;
  consent_given: boolean;
}

/** Polls /me/status while the screen is focused. */
export function useMyStatus(intervalMs = 20000) {
  const [status, setStatus] = useState<MyStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      setStatus(await api<MyStatus>("/api/v1/me/status"));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load status");
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      void load();
      timer.current = setInterval(() => void load(), intervalMs);
      return () => {
        if (timer.current) clearInterval(timer.current);
      };
    }, [load, intervalMs]),
  );

  return { status, error, reload: load };
}
