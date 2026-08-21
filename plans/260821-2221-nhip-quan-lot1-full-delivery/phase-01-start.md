---
phase: 1
title: "Tuần 0 — Ngày 1–2 và chuẩn bị"
status: pending
priority: P1
effort: "2d calendar (13 checklist items)"
dependencies: []
---

# Phase 1: Tuần 0 — Ngày 1–2 và chuẩn bị

## Overview

Mở khoá toàn dự án: có quán, có hợp đồng dữ liệu, có đo hiện trạng, có CI tối thiểu. Việc 1–3 chặn mọi việc còn lại (hồ sơ §18.1).

## Requirements

- Functional: 13 việc §18.1 có bằng chứng “xong nghĩa là gì”
- Non-functional: không tiêu ngày người xây dựng ngoài việc đã liệt kê; bảng 12 số dựng sẵn với “chưa đo”

## Architecture

Chưa ship runtime đầy đủ. Output: thoả thuận quán, ADR-001..003, schema contracts draft, `docs/hien-trang.md`, bộ mẫu vàng bắt đầu thu, `THIRD_PARTY.md` ngày kiểm tra.

## Related Code Files

- Create: `docs/adr/ADR-001..003.md`, `docs/hien-trang.md`, `docs/ket-qua-tong-hop.md`, `packages/contracts/` (stub), `.github/` (stub)
- Modify: — (repo hiện chỉ có hồ sơ)
- Delete: —

## Implementation Steps

1. `/ak:research` — quán chính + dự bị; C kiểm hạn mức miễn phí + Zalo OA ToS
2. Ký thoả thuận 1 trang với quán chính
3. Buổi 2h chốt **5 hợp đồng dữ liệu** + ADR-001/002/003 → chuẩn bị merge `main`
4. D ngồi xem trọn 1 ca mở quán → ghi thứ tự thật → phác 3 YAML
5. Đo 7 số hiện trạng §3.3 → `docs/hien-trang.md`
6. B khởi tạo monorepo skeleton + pre-commit; dựng CI khung; CODEOWNERS
7. C+A thu 50 ảnh TKB + 200 tin (che tên); 2 người gán nhãn độc lập
8. A: `make seed` data 25 NV / 21 ca / 8 tuần; tham số LĐ từ Bộ luật → config
9. D: bảng 12 số §18.2 mọi dòng “chưa đo”
10. `ak plan check` phase này chỉ khi checklist Todo xanh

## AgentKit commands

```text
ak doctor
ak plan use ./plans/260821-2221-nhip-quan-lot1-full-delivery
/ak:research   # 18.3 items 1–4
/ak:docs       # ADR + hien-trang + ket-qua-tong-hop + design-guidelines seed
/ak:devops     # CI stub + branch protection prep
/ak:bootstrap  # monorepo skeleton
# UI/UX: phase này CHỈ seed docs/design-guidelines.md — chưa build surface
# Cook web bắt đầu phase-02 với:
#   /ak:ui-ux-pro-max → /ak:frontend-design → /ak:frontend-development
/ak:journal    # cuối ngày 2
```

## Todo

- [ ] Hai quán đồng ý (chính + dự bị), có ảnh tin nhắn
- [ ] Thoả thuận 1 trang 2 chữ ký
- [x] ADR-001/002/003 trên repo (mở rộng 5 schema contracts tiếp S1)
- [ ] 3 mẫu phiếu YAML **từ ca thật** (hiện có 3 YAML mẫu kỹ thuật — phải thay sau khi D ngồi ca)
- [ ] 7 số hiện trạng có nguồn (template `docs/hien-trang.md` đã dựng)
- [ ] THIRD_PARTY có ngày kiểm hạn mức LLM (bảng có — C phải xác nhận trang giá)
- [x] Monorepo + CODEOWNERS + CI khung (bootstrap đã merge main)
- [ ] CI chặn đúng trên PR thử (cần PR thật)
- [ ] Bộ mẫu vàng + κ đồng thuận ghi nhận
- [ ] `make seed` chạy được với data thật
- [ ] Config giờ làm có số điều khoản (file placeholder + “chưa kiểm chứng”)
- [x] Bảng 12 số “chưa đo” (`docs/ket-qua-tong-hop.md`)
- [x] `docs/design-guidelines.md` seed cho UI pipeline

## Success Criteria

- [ ] Việc 1–3 §18.1 xong (chặn cứng)
- [ ] Có thể mở Sprint 1 mà không ai chờ contracts
- [ ] Rủi ro “không có quán” đã loại hoặc đã chuyển dự bị

## Risk Assessment

| Risk | Signal | Response |
|------|--------|----------|
| Quán từ chối | Không có tin nhắn ngày 2 | Chuyển dự bị ngay; không bắt đầu S1 UI phiếu |
| Contracts tranh cãi | Buổi 2h không chốt | Kéo thêm 1 buổi; **không** bắt đầu feature song song |
