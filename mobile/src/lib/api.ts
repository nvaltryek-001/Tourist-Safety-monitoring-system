import * as SecureStore from "expo-secure-store";

export const API_URL = (process.env.EXPO_PUBLIC_API_URL || "http://10.0.2.2:8000").replace(/\/+$/, "");
const TOKEN_KEY = "safetrail.token";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

let memoryToken: string | null = null;
let onUnauthorized: (() => void) | null = null;

export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler;
}

export async function loadToken(): Promise<string | null> {
  try {
    memoryToken = await SecureStore.getItemAsync(TOKEN_KEY);
  } catch {
    memoryToken = null;
  }
  return memoryToken;
}

export async function saveToken(token: string | null): Promise<void> {
  memoryToken = token;
  try {
    if (token) await SecureStore.setItemAsync(TOKEN_KEY, token);
    else await SecureStore.deleteItemAsync(TOKEN_KEY);
  } catch {
    /* secure storage unavailable: token stays in memory for this session */
  }
}

function messageFrom(body: unknown, status: number): string {
  if (body && typeof body === "object") {
    const b = body as { detail?: unknown; errors?: { message: string }[] };
    if (Array.isArray(b.errors) && b.errors.length) return b.errors.map((e) => e.message).join("; ");
    if (typeof b.detail === "string") return b.detail;
  }
  return `Request failed (${status})`;
}

export async function api<T = unknown>(path: string, init: { method?: string; body?: unknown; timeoutMs?: number } = {}): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), init.timeoutMs ?? 15000);
  const headers: Record<string, string> = { Accept: "application/json" };
  if (init.body !== undefined) headers["Content-Type"] = "application/json";
  if (memoryToken) headers.Authorization = `Bearer ${memoryToken}`;
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: init.method ?? "GET",
      headers,
      body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
      signal: controller.signal,
    });
  } catch {
    throw new ApiError(0, "No connection to the safety server. Check your internet connection.");
  } finally {
    clearTimeout(timer);
  }
  const text = await response.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { detail: text.slice(0, 200) };
  }
  if (response.status === 401 && memoryToken) {
    await saveToken(null);
    onUnauthorized?.();
  }
  if (!response.ok) throw new ApiError(response.status, messageFrom(data, response.status));
  return data as T;
}
