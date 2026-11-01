import type { Session } from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");
const STORAGE_KEY = "tsm.session";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function readSession(): Session | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const session = JSON.parse(raw) as Session;
    if (new Date(session.expiresAt).getTime() < Date.now()) {
      window.localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return session;
  } catch {
    return null;
  }
}

export function writeSession(session: Session | null): void {
  if (typeof window === "undefined") return;
  try {
    if (session) window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    else window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* storage blocked: session lives in memory only */
  }
}

export function errorMessage(body: unknown, status: number): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    const errors = (body as { errors?: { field: string; message: string }[] }).errors;
    if (Array.isArray(errors) && errors.length) {
      return errors.map((e) => (e.field ? `${e.field}: ${e.message}` : e.message)).join("; ");
    }
    if (typeof detail === "string") return detail;
  }
  if (status === 0) return "Cannot reach the server. Check your connection or NEXT_PUBLIC_API_URL.";
  return `Request failed (${status})`;
}

type Options = Omit<RequestInit, "body"> & { body?: unknown; raw?: boolean };

export async function api<T = unknown>(path: string, options: Options = {}): Promise<T> {
  const session = readSession();
  const headers = new Headers(options.headers);
  let body: BodyInit | undefined;
  if (options.body instanceof FormData) {
    body = options.body;
  } else if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.body);
  }
  if (session) headers.set("Authorization", `Bearer ${session.token}`);

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...options, headers, body });
  } catch {
    throw new ApiError(0, errorMessage(null, 0));
  }
  if (response.status === 401 && session) {
    writeSession(null);
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login?expired=1";
    }
  }
  if (options.raw) {
    if (!response.ok) throw new ApiError(response.status, `Request failed (${response.status})`);
    return response as unknown as T;
  }
  const text = await response.text();
  const data = text ? safeJson(text) : null;
  if (!response.ok) throw new ApiError(response.status, errorMessage(data, response.status));
  return data as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text.slice(0, 200) };
  }
}

export function wsUrl(token: string): string {
  return `${API_URL.replace(/^http/, "ws")}/ws?token=${encodeURIComponent(token)}`;
}
