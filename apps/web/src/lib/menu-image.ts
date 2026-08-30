import { API } from "./api";

/** URL ảnh món — GET public trên API để dùng trong thẻ img. */
export function menuImageUrl(monId: string, hinhUrl?: string): string {
  if (hinhUrl?.startsWith("http")) return hinhUrl;
  return `${API}/api/v1/menu/${monId}/anh`;
}
