---
title: "Brainstorm — NHỊP QUÁN Lô 1 Full Delivery"
created: 2026-08-21
source: "NHIP-QUAN-HO-SO-TONG-THE .md v3.0"
status: accepted
---

# Brainstorm — NHỊP QUÁN

## Summary

Hồ sơ v3.0 đã chốt kiến trúc, 8 sprint, phân công 4 người và cổng ra. Brainstorm không thiết kế lại sản phẩm; nó chuyển hồ sơ thành **hợp đồng giao hàng AgentKit** + **playbook lệnh** để chạy tuần tự từ tuần 0 đến bảo vệ.

## Outcome

Một monorepo `nhip-quan/` chạy được trên `main` (`make demo`), ship Lô 1 gồm **10 agent + lõi tất định + Cẩm nang sống**, qua 8 sprint (6 xây + 2 hoàn thiện), nộp bán kết `v0.1.0-semifinal` và bảo vệ `v1.0.0-final`, ngân sách **0 đồng**.

## Constraints

- 4 người × 25,5 ngày xây dựng trong 6 tuần (sức chứa 108; kế hoạch 104); sprint 7–8 không thêm tính năng
- Hợp đồng dữ liệu trước mã; `main` luôn xanh + demo được; mọi thay đổi qua PR + CODEOWNERS
- Điều phối = máy trạng thái tất định; lõi = CP-SAT / rule / opsengine / playbook — **không LLM ghi lịch hay điều phối**
- 15 việc cấm agent hoá (ADR-008); 6 cổng VF thất bại đóng
- Không tích hợp POS; không module tài chính; AG-VOC chỉ nhận phản hồi quán tự cung cấp

## Non-goals

- Lô 2: AG-FORECAST, AG-INVOICE, AG-SHELF, AG-MENUOPS (đã thiết kế, chưa xây)
- Smart Ordering / Barista Copilot / Personalized Retention / agent chiến lược (đã loại)
- Thu thập tự động Google Maps / ShopeeFood / Grab
- Viết lại hồ sơ đề tài hay đổi hạt nhân (ca làm việc + cẩm nang sống)

## Acceptance criteria

- [ ] 9 phase plan AgentKit (T0 + S1–S8) có cổng ra khớp mục 14 + 18.1
- [ ] Playbook lệnh AgentKit phủ vòng đời: init → brainstorm → plan → cook → test/fix → ship → journal/retro
- [ ] Mỗi sprint có đúng 1 mục tiêu, 1 thứ chiếu được, 1 cổng ra kiểm được
- [ ] `ak plan validate` xanh trên thư mục plan
- [ ] Lô 2 chỉ xuất hiện như backlog sau bảo vệ, không chiếm sức chứa 6 tuần

## Approaches compared

| # | Approach | Assumes | Fails first when |
|---|----------|---------|------------------|
| A | **Một plan 9 phase bám 8 sprint hồ sơ** | Hồ sơ v3.0 ổn định | Đội muốn đổi thứ tự ghi nhận luật / cắt soft constraint |
| B | 4 plan theo người A/B/C/D | Phối hợp chéo dễ | Contracts & orchestration bị lệch phiên bản |
| C | Plan theo package (solver, agents, web…) | Ranh giới package = ranh giới delivery | Cổng sprint “chiếu được” bị phân mảnh |

**Khuyến nghị: A.** Rẻ bỏ nhất nếu sprint trượt (cắt soft constraint / nói thật về luật, đúng hồ sơ). B và C tăng chi phí đồng bộ mà không tăng bằng chứng demo.

## Unresolved risks

1. Chưa có quán chính + dự bị (chặn T0 việc 1–2)
2. Bốn mục “chưa tự kiểm chứng” (18.3): luật lao động, hạn mức miễn phí, LICENSE, Zalo OA
3. Repo hiện chỉ có hồ sơ + `.agentkit` — chưa khởi tạo monorepo `nhip-quan/`
