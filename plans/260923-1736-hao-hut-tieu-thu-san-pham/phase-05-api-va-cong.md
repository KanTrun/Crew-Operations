---
phase: 5
title: "API & cổng"
status: pending
priority: P1
effort: "0.5 ngày"
dependencies: [4]
---

# Phase 5: API & cổng

## Overview

Mở bề mặt HTTP cho hao hụt, khai capability theo cổng PR13, và vá hai lỗ đã xác
nhận ở phase 1 (thiếu audit, `worker` đọc sai khoá thời gian).

## Requirements

- Functional: `GET /api/v1/hao-hut` trả `LossSummary` từ dữ liệu thật.
- Functional: `POST /api/v1/hao-hut` ghi một dòng hao hụt **có audit**.
- Functional: `GET /api/v1/hao-hut/nguong` đọc ngưỡng đang áp dụng (để UI giải thích).
- Functional: vá `worker._tong_ket_ngay` đọc đúng `luc`/`created_at`.
- Non-functional: quyền theo đúng house style (`_require_role` / `_require_manager`).
- Non-functional: cổng PR13 xanh — route mới phải khai capability hoặc exclusion.

## Architecture

`GET` là hàm đọc thuần: gom ba nguồn → gọi engine con → `LossSummary.model_dump()`.
`POST` dùng `kv_mutate` theo mẫu `waste_ghi` nhưng **thêm** `_audit`.

```text
GET  /api/v1/hao-hut      → dựng map mat_hang → engine → LossSummary
POST /api/v1/hao-hut      → chuẩn hoá + kv_mutate("waste_notes") + _audit
GET  /api/v1/hao-hut/nguong → config/nguong-hao-hut.yaml đã resolve
```

Giữ `POST/GET /api/v1/waste` cũ chạy nguyên vẹn để UI cũ và e2e không vỡ; `/hao-hut`
là bề mặt mới, đầy đủ hơn.

## Related Code Files

- Create: `apps/api/src/ca_api/interfaces/http/hao_hut.py`
- Modify: `apps/api/src/ca_api/interfaces/http/main.py` (gắn router)
- Modify: `apps/api/src/ca_api/interfaces/http/sprint45.py` (thêm `_audit` cho `waste_ghi`)
- Modify: `apps/api/src/ca_api/worker.py` (`_tong_ket_ngay` đọc đúng khoá thời gian)
- Modify: `packages/contracts/src/ca_contracts/__init__.py` (2 capability mới)
- Modify: `apps/api/tests/unit/test_capability_coverage.py` (chỉ khi cần exclusion)
- Create: `apps/api/tests/unit/test_hao_hut_api.py`

## Implementation Steps

1. Viết `hao_hut.py`: đọc `kiem_ke`, `menu_mon`, `waste_notes`; dựng map; gọi engine.
2. `POST` ghi hao hụt: chuẩn hoá `mat_hang`/`nguyen_nhan`, gọi `_audit("hao_hut", ...)`.
3. `GET /nguong` trả ngưỡng mặc định + theo mặt hàng.
4. Thêm capability `GET_LOSS_SUMMARY` (R0_READ, deep-link `/hao-phi`) và
   `PROPOSE_LOSS_RECORD` (R2_CONFIRM, deep-link `/hao-phi`).
5. Vá `waste_ghi` thiếu audit; vá `_tong_ket_ngay` đọc `luc`/`created_at`/`ngay`/`at`.
6. Test: rỗng ⇒ tổng 0 dòng, không bịa; có dữ liệu ⇒ dòng khớp công thức §4.3;
   thiếu vế ⇒ `thieu_du_lieu`; `POST` ghi vết audit.

## Success Criteria

- [ ] `pytest apps/api -q` xanh, gồm `test_capability_coverage.py`.
- [ ] `GET /api/v1/hao-hut` với KV rỗng trả `tong_dong: 0`, **không** raise.
- [ ] Dòng `sua_tuoi` khớp số với `kiem_ke` (test đọc thẳng seed để đối chiếu).
- [ ] `POST /api/v1/hao-hut` xuất hiện trong `/api/v1/vet` (audit có ghi).
- [ ] `_tong_ket_ngay` đếm đúng số bản ghi trong ngày (test với `luc`).
- [ ] `GET` và `POST` cũ ở `/api/v1/waste` vẫn xanh (test cũ không sửa).

## Risk Assessment

Rủi ro: `POST /api/v1/waste` khi thêm `_audit` làm test seed đếm audit lệch.
**Tín hiệu:** test seed/audit đỏ vì số vết tăng. **Phản ứng:** xem đó là hành vi
đúng (ghi dữ liệu phải có vết); cập nhật kỳ vọng trong test seed kèm ghi chú lý do,
không gỡ `_audit` để cho test xanh.

