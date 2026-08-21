# Checklist Tuần 0 — trạng thái cook

Cập nhật: 2026-08-21 (agent cook phase-01)

## Đã xong (kỹ thuật / docs)

| # | Việc | Bằng chứng |
|---|------|------------|
| 3* | ADR-001..003 | `docs/adr/` |
| — | Monorepo + Docker + CODEOWNERS + CI khung | `main` / bootstrap |
| 13 | Bảng 12 số “chưa đo” | `docs/ket-qua-tong-hop.md` |
| — | Template hiện trạng 7 số | `docs/hien-trang.md` |
| — | Mẫu thoả thuận 1 trang | `docs/thoa-thuan-quan.template.md` |
| — | Tham số LĐ placeholder | `config/tham-so-lao-dong.yaml` |
| — | Design guidelines + UI pipeline trong plan | `docs/design-guidelines.md`, `plan.md` § UI/UX |

\*5 schema contracts đầy đủ + OpenAPI gen = Sprint 1 (stubs đã có trong `packages/contracts`).

## Blocker người (không fake)

| # | Việc | Ai | Trạng thái |
|---|------|-----|------------|
| 1 | Hai quán đồng ý | Cả đội | **BLOCKER** |
| 2 | Ký thoả thuận | Trưởng nhóm | **BLOCKER** — dùng template |
| 4 | D ngồi ca mở quán | D | **BLOCKER** — YAML hiện là mẫu kỹ thuật |
| 5 | Đo 7 số | D | **BLOCKER** |
| 6 | Xác nhận hạn mức LLM vĩnh viễn | C | **BLOCKER** |
| 10 | 50 ảnh + 200 tin + κ | C+A | **BLOCKER** |
| 11–12 | Seed thật + điều khoản LĐ | A | **BLOCKER** / chưa kiểm chứng |
| 8 | PR thử bị CI chặn đúng | B | Cần mở PR từ nhánh này |

## Cổng ra phase-01

**Chưa đạt** cho đến khi việc 1–3 xanh. Có thể song song chuẩn bị S1 contracts trên nhánh, **không** coi Tuần 0 đóng.
