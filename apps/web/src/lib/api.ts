export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function authHeaders(): HeadersInit {
  if (typeof window === "undefined") return {};
  const token = sessionStorage.getItem("nq_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`GET ${path} failed`);
  return res.json() as Promise<T>;
}

export async function apiSend<T>(path: string, body?: unknown): Promise<T>;
export async function apiSend<T>(path: string, method: string, body?: unknown): Promise<T>;
export async function apiSend<T>(path: string, methodOrBody?: string | unknown, body?: unknown): Promise<T> {
  const methods = new Set(["GET", "POST", "PUT", "PATCH", "DELETE"]);
  let method = "POST";
  let payload: unknown = undefined;

  if (typeof methodOrBody === "string" && methods.has(methodOrBody.toUpperCase())) {
    method = methodOrBody.toUpperCase();
    payload = body;
  } else if (methodOrBody !== undefined) {
    payload = methodOrBody;
  }

  const res = await fetch(`${API}${path}`, {
    method,
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: payload !== undefined ? JSON.stringify(payload) : undefined,
  });
  if (!res.ok) throw new Error(`${method} ${path} failed`);
  return res.json() as Promise<T>;
}
