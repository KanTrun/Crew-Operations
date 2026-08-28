# 2026-08-27 — TKB: toast đáy màn đè nút Xác nhận

## Triệu chứng
Trên `/tkb`, sau khi đọc ảnh (escalate), hộp đỏ «Máy đọc chưa chắc…» phủ lên **Xác nhận gắn TKB** — không bấm được; chữ đen trên đỏ khó đọc.

## Root cause
`push(..., "err")` + `Toasts` `fixed bottom-24 z-[100] pointer-events-auto` trùng vùng CTA đáy trang.

## Sửa
1. Escalate → `Alert kind="info"` inline (`hint`), không toast đáy.
2. Toasts chuyển `top-20` / `top-24`, chữ normal-case.
3. CTA có `pb-24` mobile; file picker tùy chỉnh; bỏ label lồng nhau.

## Verify
Rebuild `nhipquan-web`; thử ảnh mẫu → chỉnh khung → **Xác nhận** click được; «Đã gắn cho bạn» hiện đúng.
