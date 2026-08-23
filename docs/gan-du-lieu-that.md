# Gắn dữ liệu quán thật (sau khi web + API sẵn sàng)

Phần mềm Lô 1 (S3–S5) chạy với **instance NHỊP QUÁN** (`data/seed`, `infra/templates`, SQLite `data/quan.db`). Dữ liệu quán đối tác gắn **sau**, không chặn merge phần mềm (ADR-012).

## Thứ tự khuyến nghị

1. **Hợp đồng & seed** — cập nhật `data/seed/sample.json`, chạy `python scripts/generate_fixture_data.py` nếu cần regen.
2. **Template vận hành** — chỉnh `infra/templates/mo_quan.yaml` (bước phiếu, ngưỡng tồn).
3. **Nhân sự & đăng nhập** — thêm user trong `apps/api/src/ca_api/persist.py` (hoặc migration DB khi có Alembic đầy đủ).
4. **Quán đối tác** — điền `docs/quan-doi-tac.md`; mục tiêu ≥5 phiếu NV quán (§14.5.2).
5. **Cẩm nang** — mỗi lần sửa thật qua UI/API → `so_lan_sua.jsonl` → AG-RULE/VF-RULE; **không** seed luật giả.

## Biến môi trường

| Biến | Mục đích |
|------|----------|
| `NHIPQUAN_DB` | SQLite (mặc định `data/quan.db`) |
| `NHIPQUAN_SUA` | JSONL ghi nhận sửa |
| `NHIPQUAN_CAMNANG` | JSON luật cẩm nang |

## Kiểm tra sau khi gắn

```bash
python scripts/solve_tuan.py
python scripts/verify_hard.py
CA_AGENT_MODE=replay pytest -q
make eval
```

## Trung thực slide

- `so_luat_that_quan = 0` cho đến khi có luật từ sửa thật của quán.
- §14.5 / §14.6: ghi rõ “software-complete” vs “đã chứng minh tại quán”.
