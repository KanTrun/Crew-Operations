import { getToken } from "./session";

export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function authHeaders(extra?: HeadersInit): HeadersInit {
  const token = getToken();
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  };
}

/**
 * Lỗi gọi API, mang theo mã HTTP để lớp trình bày chọn câu tiếng Việt.
 *
 * `status = 0` nghĩa là chưa gọi tới được máy chủ (mất mạng, API chưa chạy).
 * `message` chỉ là mã kỹ thuật cho log — KHÔNG bao giờ in trực tiếp lên UI;
 * mọi trang phải đi qua `viError()` trong `src/lib/present.ts`.
 */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number) {
    super(`api_${status}`);
    this.name = "ApiError";
    this.status = status;
  }

  get offline(): boolean {
    return this.status === 0;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API}${path}`, init);
  } catch {
    throw new ApiError(0);
  }
  if (!res.ok) throw new ApiError(res.status);
  try {
    return (await res.json()) as T;
  } catch {
    // Máy chủ trả 2xx nhưng thân phản hồi không phải JSON đọc được.
    throw new ApiError(502);
  }
}

export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path, { headers: authHeaders() });
}

export function apiSend<T>(path: string, body?: unknown, method = "POST"): Promise<T> {
  return request<T>(path, {
    method,
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

/** Upload multipart (ảnh TKB). Không gắn Content-Type — browser tự set boundary. */
export function apiUpload<T>(path: string, form: FormData): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: authHeaders(),
    body: form,
  });
}
