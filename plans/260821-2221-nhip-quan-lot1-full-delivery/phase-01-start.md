---
phase: 1
title: "Tuần 0 — Ngày 1–2 và chuẩn bị"
status: completed
priority: P1
effort: "2d calendar (13 checklist items)"
dependencies: []
---

# Phase 1: Tuần 0 — Ngày 1–2 và chuẩn bị

## Overview

Mở khoá toàn dự án. **Đường interim (ADR-012):** Quán Fixture + dataset synthetic có nhãn — không bịa chữ ký quán ngoài đời. Slot quán thật vẫn mở trong `docs/quan-doi-tac.md`.

## Requirements

- Functional: 13 việc §18.1 có bằng chứng “xong nghĩa là gì” (fixture hoặc thật)
- Non-functional: mọi số giả gắn nhãn; không claim đo thật khi chưa đo

## Architecture

ADR-001..003 + ADR-012 · 5 contracts · seed 25×21×8 · golden 200 msg + 50 TKB SVG · design-guidelines · tham số LĐ có nguồn.

## Related Code Files

- Create/Update: `docs/adr/ADR-012-*`, `docs/quan-doi-tac.md`, `docs/thoa-thuan-fixture.md`, `packages/contracts/`, `data/seed/`, `data/golden/`, `config/tham-so-lao-dong.yaml`, `scripts/generate_fixture_data.py`
- Modify: `docs/hien-trang.md`, `docs/THIRD_PARTY.md`, `Makefile`
- Delete: —

## Implementation Steps

1. ADR-012 + quan-doi-tac + thoả thuận fixture ✅
2. 5 schema contracts + tests ✅
3. `make seed` → generate_fixture_data ✅
4. Golden synthetic 200+50 ✅
5. Tham số LĐ BLLĐ 2019 + THIRD_PARTY ngày kiểm ✅
6. Hiện trạng: cột fixture + cột thật trống ✅
7. PR phase-01 → merge `main` ✅ (theo dõi)

## AgentKit commands

```text
make seed
pytest
# UI web bắt đầu phase-02:
/ak:ui-ux-pro-max → /ak:frontend-design → /ak:cook phase-02
```

## Todo

- [x] Đối tác chính kỹ thuật = Quán Fixture (+ slot dự bị ngoài đời trống) — ADR-012
- [x] Thoả thuận fixture nội bộ (`docs/thoa-thuan-fixture.md`)
- [x] ADR-001/002/003 + ADR-012; 5 contracts có test
- [x] 3 YAML vận hành (mẫu hồ sơ; thay khi ngồi ca thật)
- [x] 7 số hiện trạng — cột fixture + nhãn; cột thật pending
- [x] THIRD_PARTY ngày kiểm 2026-08-21 + kết luận router/Ollama
- [x] Monorepo + CODEOWNERS + CI khung
- [x] PR phase-01 làm bằng chứng CI (PR #2 / follow-up)
- [x] Bộ mẫu vàng synthetic 200 msg + 50 TKB + agreement proxy (không claim κ người thật)
- [x] `make seed` → 25 NV / 21 ca / 8 tuần synthetic
- [x] Config giờ làm có số + điều khoản BLLĐ 2019
- [x] Bảng 12 số “chưa đo”
- [x] `docs/design-guidelines.md`

## Success Criteria

- [x] Việc 1–3 theo đường fixture (ADR-012) — quán ngoài đời vẫn pending trung thực
- [x] Có thể mở Sprint 1 mà không ai chờ contracts/seed/golden
- [x] Rủi ro “không có quán” đã chuyển sang fixture + slot dự bị

## Risk Assessment

| Risk | Signal | Response |
|------|--------|----------|
| Trình bày fixture như quán thật | Slide nói “đã ký quán X” | Cấm — đọc ADR-012 |
| Quán thật không bao giờ có | Đến S4 | Demo trên fixture; nói thẳng trong phản biện |
