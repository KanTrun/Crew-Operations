---
title: "Brainstorm — Unblock phase-01 without fraud"
created: 2026-08-21
status: accepted
---

# Brainstorm — Hoàn thiện phase-01 không vướng

## Outcome

Phase-01 đủ cổng ra kỹ thuật để mở Sprint 1: contracts/ADR, seed 25×21×8, golden synthetic, tham số LĐ có nguồn, THIRD_PARTY có ngày kiểm, đường đối tác **Quán Fixture** + slot quán thật, checklist Todo xanh theo nghĩa *interim honest*.

## Constraints

- Không bịa tin nhắn/chữ ký quán ngoài đời
- Mọi số giả thuyết hồ sơ gắn nhãn `gia_thuyet_ho_so` hoặc `synthetic`
- `main` qua PR; giữ 4 quy tắc bất biến hồ sơ

## Non-goals

- Đo 7 số tại quán thật (ghi rõ pending field)
- Ảnh TKB sinh viên thật (thay bằng SVG/JSON synthetic có nhãn)
- Claim κ gán nhãn người thật

## Acceptance

- [ ] ADR-012 đường fixture
- [ ] 5 schema contracts + seed chạy
- [ ] Golden messages ≥200 + TKB synthetic ≥50 ground-truth
- [ ] `tham-so-lao-dong.yaml` có số + điều khoản
- [ ] THIRD_PARTY cập nhật ngày kiểm
- [ ] phase-01 Todo/Success đánh dấu theo interim; `ak plan` phản ánh
- [ ] PR merge được

## Recommendation

**Interim partner = Quán Fixture nội bộ** (ADR-012). Thay thế bằng quán thật khi có — không dừng scaffold.
