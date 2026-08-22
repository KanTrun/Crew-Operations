---
title: Brainstorm — hoàn thiện S3 + OS S4/S5 chuyên nghiệp
date: 2026-08-22
status: accepted
---

# Brainstorm: OS ca-centric S3→S5 trên đường fixture

## Summary

Không gộp S4/S5 thành “quán đã ký”. Hồ sơ cấm bịa đối tác. Cách mạnh nhất: **cùng một mô hình nghiệp vụ** (ca = hạt nhân, orc = writer, cẩm nang 8 bước, người trọng tài VF) chạy đủ **mọi chức năng phần mềm** S4+S5 trên fixture + lịch sử 8 tuần dựng lại, dán nhãn trung thực.

## Contract

| Field | Value |
|-------|-------|
| **Outcome** | Một OS vận hành quán: phiếu, lịch vòng đời, công bằng, hôm nay, hộp thư, SBAR, chợ đổi ca, QR, cẩm nang 8 bước, SOP có trích dẫn. Mọi màn hình ghi `nguon`. |
| **Constraints** | ADR-012; không fake quán/phiếu NV ngoài đời; agent không ghi DB; cổng VF fail-closed; Windows không `make`. |
| **Non-goals** | POS, Lô 2, S6 tag semifinal, S7 harden, quán ký ngoài đời. |
| **Acceptance** | Phần mềm §14.4–14.6 có mặt và kiểm được. Cổng người (§14.5.1–2 phiếu NV quán) = **chưa đo**. Luật 8 bước = **dựng lại 8 tuần**, nói số thật. |

## Options

1. **Chờ quán thật rồi mới code S4** — đúng thứ tự người, trễ contest, user bảo chạy luôn.
2. **Bịa screenshot quán** — vi phạm hồ sơ. Loại.
3. **OS fixture chuyên nghiệp (chọn)** — đủ chức năng; cổng người để trống có chữ. Rẻ bỏ nếu có quán: thay seed.

Giả định tải: chưa có đối tác (`docs/quan-doi-tac.md`). Sập trước: ai trình bày fixture như quán ký.

## Core (không cắt) + chỗ hồ sơ cho phép thêm

Hạt nhân đã chốt: xếp ca CP-SAT · sổ nợ 4 chiều · phiếu YAML · ghi nhận sửa · orc idempotent · 6 intent.

Thiếu so với §14.5–14.6 (phải có): chống tích khống · mã lý do · VF-CONFLICT/NUM/RULE · vòng đời lịch · audit append-only · ICS · AG-HANDOVER/RULE/SOP/WASTE · inbox ≥10 · fairness/today · tìm mẫu–tập sự–tự tắt · chợ 3 nhánh · QR 1 lần · SOP citation · A/B sơ bộ.

Không thêm: POS, lương, xếp hạng tên, LLM điều phối.

## Unresolved

- Walkthrough phiếu trên **điện thoại thật** (cổng §14.4.1) — người vận hành.
- Slot quán ngoài đời vẫn trống.
