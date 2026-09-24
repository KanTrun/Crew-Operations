---
phase: 7
title: "Giao diện & trang liên kết"
status: completed
priority: P1
effort: "1 ngày"
dependencies: [6]
---

# Phase 7: Giao diện & trang liên kết

## Overview

Dựng lại `/hao-phi` thành màn hao hụt hoàn thiện, và **nối các trang đang liên
quan** để người dùng đi được từ hao hụt sang tiêu thụ, menu, hôm nay, bản đồ hệ thống.

## Requirements

- Functional: bảng hao hụt theo nguyên liệu — lý thuyết, thực tế, lệch, tỷ lệ, mức độ.
- Functional: xếp hạng nguyên nhân; dòng nào `thieu_du_lieu` phải nói rõ **thiếu vế nào**.
- Functional: vùng hỏi agent mẹ (AG-COPILOT) ngay trên trang, gửi `ANALYZE_LOSS`.
- Functional: giữ nguyên khả năng ghi ghi chú hao hụt (không bỏ tính năng cũ).
- Non-functional: mọi mã trạng thái đi qua `present.ts`; không in mã thô, không `[object Object]`.
- Non-functional: mọi lỗi đi qua `viError()`; dùng kit (`OpsCard`, `PageHeader`, `StatusChip`).
- Non-functional: token màu/bo góc/bóng theo `docs/design-guidelines.md`; T0 cho route ops.
- Non-functional: e2e hiện có cho `/hao-phi` (heading "Hao phí") **không được vỡ**.

## Architecture

Trang mới gồm bốn khối, thứ tự đọc từ trên xuống:

```text
/hao-phi
  1. PageHeader            — kicker nói rõ đang xem gì
  2. OpsCard "Hao hụt theo nguyên liệu"   ← bảng mới (từ GET /api/v1/hao-hut)
  3. OpsCard "Nguyên nhân lặp lại"        ← xếp hạng (cùng payload)
  4. OpsCard "Ghi chú trong ca"           ← giữ form + cụm cũ (GET/POST /api/v1/waste)
  5. Vùng hỏi agent                        ← gửi intent ANALYZE_LOSS
```

Nối trang: `/tieu-thu` và `/menu` trỏ sang `/hao-phi`; `/hom-nay` thêm thẻ hao hụt;
`/huong-dan/map-data.ts` cập nhật mô tả `/hao-phi`.

## Related Code Files

- Modify: `apps/web/src/app/hao-phi/page.tsx`
- Modify: `apps/web/src/app/tieu-thu/page.tsx` (liên kết sang hao hụt)
- Modify: `apps/web/src/app/menu/page.tsx` (liên kết sang hao hụt)
- Modify: `apps/web/src/app/hom-nay/page.tsx` (thẻ hao hụt)
- Modify: `apps/web/src/app/huong-dan/map-data.ts`
- Modify: `apps/web/src/lib/present.ts` (nhãn `LossLevel`, `LossBasis`, nguyên nhân mới)
- Modify: `apps/web/src/app/AppShell.tsx` nếu cần đổi nhãn nav (giữ `/hao-phi`)
- Create: `apps/web/e2e/hao-hut.spec.ts`

## Implementation Steps

1. Thêm nhãn tiếng Việt cho `LossLevel`/`LossBasis` vào `present.ts` (theo mẫu `NGUYEN_NHAN`).
2. Dựng lại `hao-phi/page.tsx`: gọi `GET /api/v1/hao-hut`, render bảng + xếp hạng.
3. Giữ khối ghi chú cũ nguyên chức năng; đặt xuống dưới bảng mới.
4. Thêm vùng hỏi agent (theo mẫu các trang đã có paner AG-COPILOT).
5. Nối `/tieu-thu`, `/menu`, `/hom-nay`, `/huong-dan`.
6. Viết e2e `hao-hut.spec.ts`: bảng hiện, dòng thiếu dữ liệu nói đúng, không có `[object Object]`.
7. Chạy `tsc --noEmit`, `next build`, e2e cũ.

## Success Criteria

- [x] `npm run lint` (tsc) sạch.
- [x] `/hao-phi` hiển thị bảng hao hụt theo nguyên liệu với số thật từ API.
- [x] Dòng `thieu_du_lieu` nói rõ thiếu vế nào (lý thuyết hay thực tế).
- [x] Mọi món ở `/menu` hiện ảnh (không rơi về chữ cái đầu).
- [x] `/tieu-thu` → `/hao-phi` và `/menu` → `/hao-phi` bấm được.
- [x] e2e `/hao-phi` cũ (flows.spec.ts) vẫn xanh; e2e mới xanh.
- [x] Không có `[object Object]` hay mã trạng thái thô trên UI.

## Risk Assessment

Rủi ro: e2e `flows.spec.ts` assert `getByRole("heading", { name: /Hao phí/i })`.
**Tín hiệu:** test đỏ vì tiêu đề đổi. **Phản ứng:** giữ từ "Hao phí" trong tiêu đề
chính và kicker; nếu buộc đổi thì sửa đúng một dòng test kèm lý do, không nới lỏng
assertion.

