# Brainstorm: Đóng phase-02 để mở phase-03

## Summary

Phase-02 **đã cook xong trên nhánh**; thiếu bước đóng cổng governance: merge PR #3 vào `main`, đồng bộ `plan.md`, rồi mới được mở phase-03. Không cần viết thêm feature Sprint 1.

## Contract

| Field | Content |
|-------|---------|
| **Outcome** | `main` chứa Sprint 1; phase-01/02 = Completed trên plan; gate mở phase-03 rõ ràng |
| **Constraints** | Chỉ merge khi CI bắt buộc xanh; không bịa quán thật; không mở soft-constraint/S2 scope |
| **Non-goals** | Không cook phase-03; không fix soft×5 / AG-TKB đầy đủ / roster UI; không bắt buộc merge PR #4 riêng |
| **Acceptance** | (1) PR #3 merged; (2) `origin/main` có contracts + demo + c01–c06; (3) `plan.md` phase 1–2 = Completed; (4) smoke: `make demo` + login `quanly/demo` trên tip `main` |

## Evidence

- `phase-02-…md`: `status: completed`, todo/success đã `[x]`
- `phase-01-…md`: `status: completed`
- `plan.md` bảng phase: **vẫn Pending** cho 1 và 2 (lệch)
- PR [#3](https://github.com/KanTrun/CA-CONG-BANG/pull/3): OPEN, MERGEABLE, CI required xanh (05/08 skip đúng policy); đã gồm rename docs
- PR [#4](https://github.com/KanTrun/CA-CONG-BANG/pull/4): docs rename only; CI fail vì `main` chưa có `package-lock.json` (đã có trên #3)
- GitHub repo đã rename `CA-CONG-BANG` (không phụ thuộc merge #4)

## Options

| # | Approach | Pros | Cons / fails when |
|---|----------|------|-------------------|
| **A** | Merge #3 → đóng/hủy #4 → sync `plan.md` → smoke | Nhỏ nhất; #3 đã xanh + đủ Sprint 1 + rename | Fail nếu branch protection chặn thiếu review |
| B | Merge #4 trước rồi #3 | Docs tên repo vào main sớm | #4 CI đỏ trên baseline cũ; lãng phí |
| C | Cook thêm “đủ checklist hồ sơ” trước merge | Ảo giác hoàn thiện | Phình scope; chặn S2 không cần thiết |

**Recommend A.** Assumption: owner `@KanTrun` có quyền merge. Fails first if protection requires second reviewer không tồn tại → merge bằng admin hoặc tạm nới rule.

## Handoff sequence (cook / ops)

1. `gh pr merge 3 --repo KanTrun/CA-CONG-BANG` (squash hoặc merge theo convention repo)
2. `gh pr close 4` (redundant; rename GitHub đã xong; docs trong #3)
3. Trên tip `main`: cập nhật `plan.md` phase 1–2 → Completed (+ tick checklist 18.1 nếu còn)
4. Smoke acceptance trên `main`
5. Báo “phase-02 closed” → sẵn sàng `/ak:cook` phase-03

## Execution (2026-08-21)

- [x] Merged PR #3 → `main` (`f43d568`)
- [x] Closed PR #4 (redundant)
- [x] Merged PR #5 plan sync → phase 1–2 Completed on `main` (`7e1811c`)
- [x] Smoke on tip: `/health` 200 · `/api/v1/contracts` `nguon=fixture_synthetic`
- Branch protection: none (404) — merge không bị chặn review

**Gate phase-03:** OPEN — next `/ak:cook` `phase-03-sprint-2-moc-sinh-tu-solver.md`
