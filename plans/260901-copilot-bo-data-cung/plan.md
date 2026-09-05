# Kế hoạch hoàn thiện AG-COPILOT — bỏ dữ liệu cứng, nối data thật

> Nhánh: `feat/agents-ag-copilot` · Ngày: 2026-09-01
> Trạng thái trước kế hoạch: 7/7 intent có pipeline thật (parse → phân quyền → proposal → duyệt 2 pha → audit), nhưng 6/7 tool trả dữ liệu fixture cứng.

## Đã xong trong đợt này

| Tool | Trước | Sau |
|---|---|---|
| `SCHEDULE_SOLVE` | Thật (CP-SAT) | Thật (giữ nguyên) |
| `APPROVE_SHIFT_SWAP` | Fixture `swap_01` Minh→Lan | Đọc KV `swap`/`shift_swaps` thật + kiểm 5 điều kiện thật |
| `GENERATE_DAILY_BRIEF` | Fixture "Lan/Minh/sữa 6 hộp" | Tổng hợp từ `phan_cong`, `treo`, `tieu_thu` thật |
| `QUERY_SOP` | Match 3 cụm từ cứng | `ag_sop.answer` thật trên YAML `mo_quan/dong_quan/ban_giao_ca` + luật hiệu lực |
| `ANALYZE_WASTE` | Fixture "400ml sữa" | `ag_waste.cluster` thật trên `waste_notes` thật |
| `CREATE_RULE_PROPOSAL` | Fixture `rule_prop_01` | `tim_mau` + `de_xuat` thật trên lịch sử sửa (`list_sua`) |
| `INVENTORY_RESTOCK_CHECK` | Fixture "sữa 6 hộp" | Đọc `tieu_thu` thật, cảnh báo `duoi_nguong` thật |

Kiến trúc: agents **không import** `ca_api`/`ca_playbook`/agent khác (giữ rule `test_architecture.py`). API layer inject data sources qua `configure_data_sources()` tại `apps/api/src/ca_api/interfaces/http/main.py`. Khi source chưa cấu hình → tool trả lời trung thực "chưa cấu hình", không bịa.

Nguyên tắc dữ liệu rỗng: **báo thật "chưa có dữ liệu"** — không fallback sang số liệu mẫu.

Test: 370/370 pass (agents + playbook + gates + api).

## Giai đoạn 1 — Hoàn thiện nối dữ liệu (tuần này)

1. **KV fallback standalone**: `_kv_get` fallback đọc `data/out/kv.json` — cần đồng bộ format với SQLite KV thật của `ca_api.persist` (hiện persist dùng bảng kv riêng). Việc: thêm hàm export KV → JSON cho debug, hoặc bỏ fallback nếu gây hiểu nhầm.
2. **`users` source**: `tool_get_daily_brief` + `tool_prepare_swap_approval` đọc `users` để map `nv_id → tên`. Inject `list_users` từ `ca_api.persist`.
3. **5 điều kiện đổi ca thật sự**: hiện 3.4 (không trùng ca khác) hardcode `True`. Việc: đọc `phan_cong` tuần, kiểm tra người nhận không có ca chồng giờ cùng ngày.
4. **Citations cho QUERY_SOP**: trả `citations` trong `CopilotResponse` (contract đã có slot ở UI) để khung chat hiện "Nguồn tham chiếu" thật.

## Giai đoạn 2 — Đóng vòng đời đề xuất (tuần sau)

5. **Apply INVENTORY_RESTOCK_CHECK thật**: khi duyệt, tạo đơn trong `restock_orders` KV + đẩy item vào inbox quản lý (hiện đã ghi KV, cần UI xem đơn tại `/them` hoặc `/inbox`).
6. **Apply CREATE_RULE_PROPOSAL thật**: khi duyệt, luật vào `cam_nang.json` qua `save_luat` với trạng thái `de_xuat` (hiện ghi KV `rules` riêng — trùng lặp nguồn sự thật).
7. **APPROVE_SHIFT_SWAP apply thật**: khi duyệt, cập nhật `phan_cong` (hoán đổi người) + ghi `swap` trạng thái `da_duyet` (hiện chỉ đổi trạng thái swap, chưa đụng phân công).

## Giai đoạn 3 — Trải nghiệm & độ tin cậy

8. **LLM parse thật khi `CA_AGENT_MODE=live`**: intent parser hiện rule-based; nối `FreeTierRouter` (Groq→Gemini→static) cho câu ngoài từ khoá, giữ rule-based làm fast-path.
9. **Streaming thật (SSE)**: thay typing-effect client bằng SSE từ `copilot.py` khi LLM live.
10. **Đo chất lượng**: golden set câu hỏi → intent đúng/sai, thêm vào `scripts/eval_ag_msg.py`.

## Rủi ro & lưu ý

- `.env` máy thật có token FB/Zalo — test `test_channels_status_zalo_first_disconnected` đã neo env sạch (monkeypatch.delenv). Quy ước mới: **mọi test đọc env kênh phải neo env**, không tin env máy.
- `ensure_dotenv()` trong agents load `.env` vào process env — chỉ gọi trong luồng live, không gọi trong import-time.
- Fixture vẫn giữ cho CI replay (`CA_AGENT_MODE=replay`) — nhưng giờ nằm ở tầng messaging/meeting, không còn ở copilot tools.

## Tiến độ thực tế (Đã ship trong PR #27 — 2026-09-03)

- **Giai đoạn 1**: Đã xong toàn bộ 4 mục (conflict check 5 điều kiện thật sự trong commit `db12fac`, users mapping, dọn sạch dữ liệu cứng trong `tool_registry.py`).
- **Giai đoạn 2**: Đã xong toàn bộ 3 mục apply thật trong commit `8186e6f` (restock orders KV, rule proposal vào `cam_nang.json`, shift swap apply vào phân công thật).
- **Giai đoạn 3**: Đã xong SSE streaming (`/api/v1/copilot/message/stream`) trong commit `200c00c` và bổ sung E2E test smoke toàn diện trong commit `d4c57ea`.
- **Bổ sung độ tin cậy (2026-09-04)**: JSON và SSE cùng đi qua `_record_copilot_response()`. Mọi `action_proposal` được lưu draft và ghi audit `propose` trước khi stream `meta` cho UI; test hồi quy xác nhận proposal stream có thể được duyệt qua `action_id` bền vững.
- **Bổ sung điểm vào vận hành (2026-09-04)**: Pane AG-COPILOT đã có launcher có kiểm soát ở `/roster`, `/qr`, `/phieu`, `/treo`, `/cong-bang`, `/tkb`, `/handover`, và `/doi-ca`.
- **Tổng test xác nhận gần nhất (2026-09-04)**: 636/636 tests pass xanh ở `CA_AGENT_MODE=replay`; Docker smoke và `npm run typecheck` cũng xanh.

## Định nghĩa "xong"

- [x] Không còn chuỗi số liệu cố định trong `tool_registry.py` (grep `nv_0`, `Minh`, `Lan`, `400`, `6 hộp` → 0 kết quả ngoài test)
- [x] Mọi tool có nhánh "không dữ liệu" trung thực + test riêng
- [x] Duyệt 1 proposal → dữ liệu thật thay đổi trong KV/cam_nang, xem được trên UI
- [x] 370+ test pass, không skip âm thầm (thực tế: 475 tests pass)
