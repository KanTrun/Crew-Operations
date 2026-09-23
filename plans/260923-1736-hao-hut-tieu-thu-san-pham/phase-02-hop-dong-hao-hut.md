---
phase: 2
title: "Hợp đồng hao hụt"
status: pending
priority: P1
effort: "0.5 ngày"
dependencies: [1]
---

# Phase 2: Hợp đồng hao hụt

## Overview

Định hình `LossLine` / `LossSummary` / `LossCauseRank` và **ngưỡng hao hụt có
nguồn** trước khi viết bất kỳ logic nào (ADR-003).

## Requirements

- Functional: mô tả được một dòng hao hụt theo nguyên liệu; một tổng; một hạng mục
  nguyên nhân.
- Functional: ngưỡng lấy từ `config/` — không hard-code trong mã nghiệp vụ.
- Non-functional: schema JSON sinh ra được, TS sinh ra được, round-trip pydantic.
- Non-functional: enum `LossLevel` phải có nhánh `thieu_du_lieu` — không cho phép
  biểu diễn "không biết" bằng số 0.

## Architecture

Enum và model thuần dữ liệu, **không** chứa suy luận (ADR-002). Ngưỡng là tham số
cấu hình truyền vào hàm, không phải hằng số trong model.

```text
ca_contracts/loss.py
  LossLevel      = dat | canh_bao | nghiem_trong | thieu_du_lieu
  LossBasis      = ke_hoach_kiem_ke | don_quay_thuc_te | hon_hop
  LossLine       mat_hang, ten, don_vi, ly_thuyet*, thuc_te*, lech*,
                 ty_le_phan_tram*, muc_do, co_so, ghi_chu
  LossCauseRank  nguyen_nhan, so_lan, mat_hang_lien_quan, ty_le_tong
  LossSummary    ky, tong_dong, so_nghiem_trong, so_canh_bao, so_thieu_du_lieu,
                 ty_le_trung_binh, dong[], nguyen_nhan_hang_dau[],
                 nguon, co_du_lieu_mau
```

`*` = `float | None`. `None` nghĩa là **chưa có dữ liệu**, khác hẳn `0.0`.

## Related Code Files

- Create: `packages/contracts/src/ca_contracts/loss.py`
- Create: `packages/contracts/tests/test_loss_contracts.py`
- Create: `config/nguong-hao-hut.yaml`
- Modify: `packages/contracts/src/ca_contracts/__init__.py` (import + `CONTRACTS` + `__all__`)
- Modify: `packages/contracts/tests/test_contracts.py` (bổ sung tên vào set kỳ vọng)
- Modify: `packages/contracts/schema/index.json` + `packages/contracts/ts/contracts.ts` (sinh tự động)

## Implementation Steps

1. Viết `loss.py` với 3 enum + 3 model, `Field` có ràng buộc (`ge=0`, mô tả tiếng Việt).
2. Viết test hợp đồng: round-trip, `None` khác `0.0`, `ty_le_phan_tram` âm hợp lệ
   (hao hụt âm = đếm dư), từ chối giá trị ngoài enum.
3. Đăng ký vào `CONTRACTS`, `__all__`, và set kỳ vọng trong `test_contracts.py`.
4. Viết `config/nguong-hao-hut.yaml` theo house style của `tham-so-lao-dong.yaml`
   (có `phien_ban`, `ngay_kiem`, `nguon`, `ghi_chu`).
5. Chạy `make contracts`; kiểm `contracts.ts` có interface mới, không có `unknown` stub.

## Success Criteria

- [ ] `pytest packages/contracts -q` xanh.
- [ ] `test_contracts_registered` xanh sau khi thêm tên.
- [ ] `make contracts` chạy lại không tạo drift (chạy hai lần, `git diff` rỗng lần hai).
- [ ] `config/nguong-hao-hut.yaml` parse được bằng `yaml.safe_load`, có ngưỡng mặc định + theo mặt hàng.

## Risk Assessment

Rủi ro: sửa `test_contracts.py` (set kỳ vọng cứng) có thể va chạm nếu nhánh khác
cũng thêm contract. **Tín hiệu:** `git status` thấy file này đã đổi trước khi mình
sửa. **Phản ứng:** đọc lại file ngay trước khi sửa, chèn theo thứ tự chữ cái trong
khối, không viết lại cả set.

