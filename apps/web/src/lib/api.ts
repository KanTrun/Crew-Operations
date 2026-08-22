import { getToken } from "./session";

export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function authHeaders(extra?: HeadersInit): HeadersInit {
  const token = getToken();
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  };
}

export async function apiGet<T>(path: string): Promise<T> {
  const r = await fetch(`${API}${path}`, { headers: authHeaders() });
  if (!r.ok) throw new Error(String(r.status));
  return r.json() as Promise<T>;
}

export async function apiSend<T>(path: string, body?: unknown, method = "POST"): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    method,
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!r.ok) throw new Error(String(r.status));
  return r.json() as Promise<T>;
}
