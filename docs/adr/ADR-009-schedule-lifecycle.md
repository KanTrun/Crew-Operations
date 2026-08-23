# ADR-009 — Vòng đời lịch năm trạng thái

- Status: accepted
- Date: 2026-08-22

## Decision

`nháp → đang giải → chờ duyệt → đã công bố → đã đóng`. Chỉ quản lý/chủ chuyển. Mọi chuyển trạng thái ghi audit append-only. Công bố kèm ICS.

## Consequences

Solver nền ở demo trả best-effort cùng process, không phải worker riêng.
