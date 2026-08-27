---
title: "TKB từ ảnh — upload → AI → xác nhận → gắn NV"
status: done
created: 2026-08-27
---

# TKB ảnh (user duyệt thực hiện)

## Outcome
NV/QL upload ảnh TKB → AG-TKB đọc → sửa/xác nhận khoảng bận → lưu theo `nv_id` → solver dùng khi `dang_giai`.

## Scope
1. AG-TKB live: SVG text như cũ; PNG/JPEG/WebP qua Gemini vision (fail-closed).
2. API: `POST /tkb/upload`, `POST /tkb/confirm`, `GET /tkb/mine` + `/tkb/{nv_id}`.
3. Web `/tkb`: chọn ảnh (hoặc thử fixture), hiện khoảng, sửa, gắn NV.
4. `_run_solver` merge `kv tkb_nv` vào `LichInput.tkb`.

## Non-goals
PaddleOCR riêng; Meta; CRM.

## Acceptance
- Replay `tkb_01` vẫn xanh.
- Upload binary không còn `binary_unsupported` khi có Gemini.
- Confirm → GET thấy khoảng; solver nhận TKB đã lưu.
