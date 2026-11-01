"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, readSession, wsUrl } from "./api";
import type { LiveEvent } from "./types";

export interface Resource<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => Promise<void>;
  setData: React.Dispatch<React.SetStateAction<T | null>>;
}

/** Fetch an API path; re-fetches when `path` changes or `reload` is called. */
export function useApi<T>(path: string | null, intervalMs?: number): Resource<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(!!path);

  const load = useCallback(async () => {
    if (!path) return;
    try {
      const result = await api<T>(path);
      setData(result);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    setLoading(!!path);
    void load();
    if (!intervalMs || !path) return;
    const id = window.setInterval(() => void load(), intervalMs);
    return () => window.clearInterval(id);
  }, [load, intervalMs, path]);

  return { data, error, loading, reload: load, setData };
}

export type LiveStatus = "connecting" | "live" | "reconnecting" | "offline";

/** Subscribe to backend WebSocket events with exponential-backoff reconnects. */
export function useLiveEvents(onEvent: (event: LiveEvent) => void): LiveStatus {
  const [status, setStatus] = useState<LiveStatus>("connecting");
  const handler = useRef(onEvent);
  handler.current = onEvent;

  useEffect(() => {
    let socket: WebSocket | null = null;
    let attempt = 0;
    let timer: number | undefined;
    let ping: number | undefined;
    let closed = false;

    const connect = () => {
      const session = readSession();
      if (!session) {
        setStatus("offline");
        return;
      }
      socket = new WebSocket(wsUrl(session.token));
      socket.onopen = () => {
        attempt = 0;
        setStatus("live");
        ping = window.setInterval(() => socket?.readyState === WebSocket.OPEN && socket.send("ping"), 25000);
      };
      socket.onmessage = (msg) => {
        try {
          handler.current(JSON.parse(msg.data) as LiveEvent);
        } catch {
          /* ignore malformed frames */
        }
      };
      socket.onclose = (ev) => {
        window.clearInterval(ping);
        if (closed) return;
        if (ev.code === 4401) {
          setStatus("offline");
          return;
        }
        setStatus("reconnecting");
        attempt += 1;
        timer = window.setTimeout(connect, Math.min(30000, 1000 * 2 ** attempt));
      };
    };
    connect();
    return () => {
      closed = true;
      window.clearTimeout(timer);
      window.clearInterval(ping);
      socket?.close();
    };
  }, []);

  return status;
}
