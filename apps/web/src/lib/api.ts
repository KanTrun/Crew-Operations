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

  /**
   * Mã lỗi nghiệp vụ máy chủ trả kèm (trường `detail`), ví dụ `ten_da_ton_tai`.
   *
   * Đây là mã máy đọc, KHÔNG phải câu để in. Chỉ dùng làm khoá tra bảng trong
   * `src/lib/present.ts` (xem `dangKyLoi`) để chọn câu tiếng Việt cho đúng ô.
   * Không trang nào được render trực tiếp giá trị này.
   */
  readonly detail: string;

  constructor(status: number, detail = "") {
    super(`api_${status}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }

  get offline(): boolean {
    return this.status === 0;
  }
}

/**
 * Lấy `detail` từ thân lỗi. Chỉ nhận chuỗi ngắn dạng mã (chữ, số, gạch dưới) —
 * câu tiếng Anh dài hay JSON lồng nhau bị bỏ, nên không có đường nào để chuỗi
 * kỹ thuật của máy chủ đi tiếp vào lớp trình bày.
 */
async function docDetail(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown };
    const d = body?.detail;
    if (typeof d === "string" && /^[a-z0-9_]{1,48}$/.test(d)) return d;
  } catch {
    /* thân lỗi không phải JSON — bỏ qua, mã HTTP đã đủ để chọn câu */
  }
  return "";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API}${path}`, init);
  } catch {
    throw new ApiError(0);
  }
  if (!res.ok) throw new ApiError(res.status, await docDetail(res));
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
