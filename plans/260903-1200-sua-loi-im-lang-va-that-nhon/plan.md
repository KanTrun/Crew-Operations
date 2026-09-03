# Sửa lỗi im lặng + thất hứa stub (worker, contracts.ts)

**Trạng thái:** done · **Ngày:** 2026-09-03 · **Cờ:** `--advice` (kongming rate-limit lúc mở đầu — review ở checkpoint cuối)

## Outcome

Ba chỗ hệ thống "hứa mà không làm" được biến thành hành vi thật, có test:

1. Đề xuất SOP đã duyệt từ cuộc họp **biến mất im lặng** (TypeError bị `except: pass` nuốt) → lưu thật, đọc được qua API.
2. `worker` Docker là `sleep(60)` rỗng → bộ chạy việc định kỳ thật: nhắc việc hai cấp qua cổng thời gian tiêm được (hồ sơ §13.2 mục B).
3. `contracts.ts` là stub `Record<string, unknown>` → sinh type TS thật từ JSON Schema, thuần stdlib.

## Constraints

- Không ghi đề xuất họp vào `so_lan_sua.jsonl` — bảng đó là bằng chứng sửa ca thật nuôi khai khẩn luật; ghi vào đó là tái phạm loại bịa vừa dọn.
- Không sửa YAML templates lúc chạy.
- Test tất định: `CA_AGENT_MODE=replay`, không sleep thật, không mở mạng.
- Conventional commits, không AI reference.
- stdlib only cho script contracts.

## Non-goals

- Không refactor `apps/web` sang import type mới sinh (giữ nguyên hành vi web).
- Không dựng eslint/vitest thay `echo lint-ok` — quyết định quản trị riêng, báo cáo.
- Không mở rộng worker ngoài job nhắc việc.

## Acceptance (quan sát được)

- [ ] `POST /api/v1/meeting/apply` với `de_xuat_sop`/`de_xuat_phe_duyet` đã duyệt → `sop_proposals >= 1`, entry nằm trong `GET /api/v1/sop/de-xuat`, apply lặp không nhân đôi.
- [ ] `worker._chay_vong(clock, port, kv)` với FakeClock: phiếu quá hạn gửi `nhac_nhan_vien` đúng 1 lần/lần/cấp; quá hạn x2 gửi `bao_chu_quan`; phiếu closed → im lặng; không import time trong vòng lặp lõi.
- [ ] `python scripts/export_contracts.py` → `contracts.ts` chứa `export interface CuocHop {` và các kiểu literal/union thật; không còn `Record<string, unknown>`.
- [ ] `pytest -q` toàn bộ xanh; `ruff check` sạch; `docker_stack.py up` healthy + `smoke` pass.

## Phase 1 — meeting SOP proposals thật

- `meeting.py`: xoá 2 khối `record_sua(...)` sai + import `record_sua`; thêm `_luu_de_xuat_sop(meeting, items)` dùng `kv_mutate("sop_de_xuat", ...)` (dedupe theo nội dung), trả số bản ghi mới. Thêm `GET /api/v1/sop/de-xuat` (`_require_role`).
- Test: `apps/api/tests/unit/test_meeting_api.py` — luồng analyze→apply có SOP đề xuất; đếm + dedupe + GET; role khách không đọc được.

## Phase 2 — worker thật

- `worker.py`: `_chay_vong(clock: Clock, port: MessagePort) -> int` đọc `kv "phieu"`, bỏ qua closed, `escalate(run, clock.now_ms())`, dedupe qua `kv "worker_da_nhac"` (atomic `kv_mutate`), gửi `port.send(nv_id, text)`. `main()` lặp `time.sleep(WORKER_INTERVAL_S)` ngoài lõi.
- Test: `apps/api/tests/unit/test_worker.py` — port giả ghi lại send, FrozenClock ms tuỳ chọn; 4 case trên.

## Phase 3 — contracts.ts thật

- `export_contracts.py`: hàm `ts_types_from_schemas(schemas) -> str` (interface từ properties/required, `$ref`→tên, `anyOf`+null→`| null`, enum→union literal, array→`T[]`, additionalProperties→`Record<string, T>`). Ghi đè file ts.
- Chạy script, kiểm tra output; CI gate 02 đã chạy script này sẵn.

## Phase 4 — cổng + git + Docker

- `pytest -q`, `ruff check`, `tsc --noEmit` (web không đổi nhưng chạy cho chắc).
- Commits (4 cái, tách theo type): refactor cam-nang đang chờ; fix(api); feat(api) worker; chore(contracts). Push `main` (solo owner, lịch sử repo đổ thẳng main).
- `python scripts/docker_stack.py up` → healthy → `smoke` → báo trạng thái.

## Risk / Rollback

- `sop_de_xuat` là key kv mới → không migrate, không đụng dữ liệu cũ. Rollback = revert commit.
- Worker ghi key `worker_da_nhac` mới; api không đọc → không xung đột.
- Emitter TS sai → chỉ ảnh hưởng file generated; web không import nó.
