---
phase: 3
title: "Classify vao inbox va hieu luc ca"
status: done
priority: P1
effort: "2-3d"
dependencies: [2]
---

# Phase 3: Classify → inbox + hiệu lực ca

## Overview

Nối AG-MSG vào `inbox_rang_buoc` (kèm nguồn kênh + raw), mở rộng `/inbox` chip kênh, và khi duyệt thì gọi đúng cổng ca / chợ — **không** silent ghi `phan_cong`.

## Requirements

- Functional: inbound đã bind → `classify` → enqueue; UI chip `telegram|console|zalo`; duyệt theo intent
- Non-functional: giữ `PHAM_VI` AG-MSG; mọi mutate ca qua API đã có

## Architecture

| Intent | Sau duyệt |
|--------|-----------|
| `doi_ca` / `nhan_ca` | Mở/validate hàng chợ đổi ca hoặc tạo ràng buộc chờ solver — không auto swap |
| `xin_nghi` / `bao_tre` / `cap_nhat_tkb` | Ghi ràng buộc + audit; ảnh hưởng lịch qua quy trình đã có |
| `khac` | Lưu + có thể việc treo; không đổi lịch |
| (phase 4) xem lịch | Không cần duyệt — xem phase 4 |

## Related Code Files

- Modify: `apps/api/.../sprint3.py` (`msg/classify` → enqueue)
- Modify: `apps/api/.../sprint45.py` (`inbox_decide` effects)
- Modify: `apps/web/src/app/inbox/page.tsx`
- Modify: `packages/agents/src/ca_agents/ag_msg/extract.py` (nếu cần field `rang_buoc` giàu hơn)
- Modify: e2e `apps/web/e2e/flows.spec.ts` hoặc API tests

## Implementation Steps

1. Sau classify: `POST` nội bộ tạo mục inbox với `y_dinh`, `do_tin_cay`, `nguon`, `noi_dung_goc`
2. UI: chip nguồn + preview raw text
3. `inbox_decide(duyet)`: switch intent → ca/chợ/treo helpers hiện có
4. `tu_choi`: audit + optional MessagePort “đã từ chối”
5. Test: fixture 6 intent → duyệt từng loại

## Success Criteria

- [ ] Classify không còn “probe only” — có bản ghi inbox
- [ ] Duyệt `doi_ca` không rewrite `phan_cong` im lặng
- [ ] E2E/API replay xanh cho ≥3 intent

## Risk Assessment

Inbox constraints schema thiếu field kênh — signal: UI không hiện nguồn; response: migration thêm cột JSON `meta` sớm ở phase 1–3.
