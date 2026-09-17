# Tự động xếp lịch và chợ ca

## Outcome
Tự động hóa luồng availability đã xác nhận -> CP-SAT chính thức -> xử lý ca thiếu qua open shift -> quản lý giải quyết khi hết SLA -> duyệt cuối -> tự công bố và thông báo đúng tuần, không cần thao tác `Nháp` trong trường hợp bình thường.

## Constraints
- CP-SAT production là solver duy nhất; mọi trigger đi qua application service được ủy quyền, idempotent và audit.
- Availability định danh bằng `store_id + nv_id + tuan_iso`; không dùng `display_name` làm khóa.
- Chỉ dùng confirmation `da_xac_nhan` đúng tuần; cô lập dữ liệu giữa các tuần.
- Giữ tương thích API/lifecycle/swap cũ khi không xung đột; open shift và application là mô hình mới.
- Fail-closed khi thiếu cấu hình, không đủ điều kiện hoặc fingerprint stale.
- Claim first-eligible phải nguyên tử; deadline mặc định khoảng 120 phút và cấu hình được.
- Lịch đủ người vẫn chờ quản lý duyệt cuối; còn ca thiếu không được công bố trước khi xử lý xong.

## Non-goals
- Không thay CP-SAT bằng heuristic hoặc LLM.
- Không xóa âm thầm workflow swap ba bên hiện có.
- Không cho metadata chat tự áp lịch.
- Không sửa CI/Facebook replay ngoài phạm vi test hoặc contract bị tác động trực tiếp.

## Acceptance criteria
1. `build_schedule_plan()` không còn là đường tạo lịch authoritative; chat và worker gọi cùng application service/CP-SAT.
2. Hai nhân viên trùng tên không bị gộp; confirmation và schedule input đúng `nv_id + tuan_iso`.
3. Có get-or-create hội thoại riêng employee <-> `ai_scheduler`, có kiểm tra quyền.
4. Có `schedule_run` snapshot input, fingerprint, version và idempotency.
5. Có bảng/API `open_shift`, `shift_application`; claim nguyên tử, chỉ ứng viên đủ điều kiện.
6. Worker quét SLA configurable, mặc định 120 phút, escalates ca chưa được claim.
7. Quản lý xử lý gap phải revalidate, chạy lại CP-SAT, ghi assignment chính thức, chuyển chờ duyệt; duyệt thành công tự công bố và tạo notification cho toàn bộ nhân viên.
8. Metadata tin chat chỉ là dữ liệu hiển thị; mọi mutation đi qua service có authorization, idempotency, audit.
9. Có test cho duplicate names, cross-week isolation, private conversation, solver/run fingerprint, claim race, SLA, manager resolution, approval/publication/notification.
10. Backend tests, frontend typecheck/build/lint và code review không phát hiện regression hoặc lỗi mới.

## Plan
1. Mở rộng persistence additive với schedule runs, availability normalized, open shifts/applications, audit/outbox và transaction helpers; giữ KV legacy đọc được.
2. Tạo scheduling application service: snapshot confirmed availability, dựng `LichInput`, gọi duy nhất `solve_cpsat`, fingerprint/version/idempotency, ghi assignment authoritative và gap records.
3. Đổi chat sang private Bot conversation và route availability/schedule trigger qua service; không dùng display name hay metadata mutation.
4. Thêm open-shift/application API/UI và atomic first claim; giữ route swap legacy.
5. Thêm worker SLA/escalation và manager resolution với revalidation + rerun CP-SAT.
6. Guard approval/publication, outbox notifications, exact-week links; cập nhật roster/chat/doi-ca.
7. Thêm focused tests rồi full validation, tester/debugger/code-reviewer, docs và plan sync.

## Validation and rollback
- Chạy focused backend tests sau mỗi slice, sau đó toàn bộ test liên quan và frontend checks.
- Kiểm tra diagnostics/build/lint và review các caller của `_run_solver`, chat, lifecycle, swap.
- Rollback bằng các migration additive và revert service/routes; dữ liệu legacy không bị xóa.

## Implementation status

- **Status: Done** (synced from [plan triển khai](./260917-1129-hon-thin-scheduling-v-thng-bo-lch/plan.md))
- Done: normalized exact-week availability, versioned/idempotent schedule runs, CP-SAT authority path, stable scheduler conversation route, authoritative assignment records, manager gap-resolution/revalidation endpoint, guarded approval-to-publication flow with exact-week notifications, open-shift persistence/API, atomic first claim with run/week eligibility checks, SLA escalation, neutral solver adapter extraction from legacy HTTP module, regression fixtures, E2E notification deep-link test, and frontend typecheck/build.
- Validation evidence: `apps/api` full suite **455 passed in 1460.60s**; focused lifecycle **4 passed**; exact-week export **1 passed**; focused sprint45 **31 passed**; web `npm run typecheck` and `npm run build` passed, generating **39/39** pages.
- Remaining: none within scheduling scope.
