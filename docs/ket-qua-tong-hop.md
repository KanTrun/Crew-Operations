# Bảng kết quả tổng hợp — 12 con số (hồ sơ §18.2)

> **Cấm số phỏng đoán.** Chỉ số đo thật hoặc chữ `chưa đo` + lý do.  
> **Phạm vi bài thi:** nhóm A (demo fixture ~80%) · nhóm B ghi *ngoài phạm vi bài thi*.

| # | Con số | Giá trị | Lý do / ghi chú | Cập nhật |
|---|--------|---------|-----------------|----------|
| 1 | Tỉ lệ không cần sửa | **W01 fixture: 38,8%** (49 quyết định, 30 sửa) | **1 tuần demo fixture** (`mo_phong_fixture`) — không phải hiệu năng ổn định lâu dài · `scripts/eval_override_demo_week.py` · **W1→W8: ngoài phạm vi bài thi** (nhóm B) | 2026-08-28 |
| 2 | Chi phí thực tế toàn dự án (0đ?) | chưa đo | Sổ 14 dòng + ảnh hạn mức API dashboard | |
| 3 | Thời gian xếp ca trước / sau | **ngoài phạm vi bài thi** | Không triển khai quán thật (nhóm B) | 2026-08-28 |
| 4 | Vi phạm ràng buộc cứng trên lịch công bố | **0** | `scripts/verify_hard.py` sau `solve_tuan.py` | 2026-08-28 |
| 5 | AG-TKB accuracy + % đẩy lên người | **96,23%** (51/53) · escalate **2 lần / 53** (blur) | Golden 53 — **hard/blur còn mỏng (~4%)**, số escalate hiện chủ yếu xác nhận 2 case blur đã biết; bổ sung golden khó trước tag semifinal · `scripts/eval_ag_tkb.py` replay | 2026-08-28 |
| 6 | AG-MSG confusion (6 ý định) | **98,50%** (197/200) · hard/medium **96,10%** (74/77) | Golden có case mơ hồ · `scripts/eval_ag_msg.py` | 2026-08-28 |
| 7 | Tỉ lệ hoàn thành phiếu + thời gian TB | **Nhóm A (latency UI):** thời gian **mở form phiếu** demo ~0,2s (`PHIEU_DEMO_MS=202` — login → `/phieu` → bước đầu; **không** phải hoàn thành checklist) · **Tỉ lệ hoàn thành theo ngày/NV: ngoài phạm vi bài thi** (nhóm B) | `e2e/phieu-timing.spec.ts` | 2026-08-28 |
| 8 | Việc treo được ca sau nhận / tổng | **ngoài phạm vi bài thi** | Không bàn giao quán thật (nhóm B) | 2026-08-28 |
| 9 | Sai số sổ tiêu thụ vs đếm tay | **ngoài phạm vi bài thi** | Cần ≥2 tuần kiểm kê quán thật (nhóm B) | 2026-08-28 |
| 10 | Luật: đề xuất / loại / tập sự / duyệt / tự tắt | dựng lại fixture: **1 / 1 / 5 / 1 / 1** · quán thật: **0** | `POST /cam-nang/chay-8-buoc` (cần ≥3 sửa thật để chạy live; fixture ADR-012) | 2026-08-22 |
| 11 | Lần cổng VF đẩy lên người (theo cổng) | **Đếm sự kiện** (1 phiên eval fixture, không phải %): VF-TRACE **1** · VF-CONF **2** · VF-SCHEMA **0** | `scripts/eval_vf_escalations.py` — n nhỏ, không đại diện traffic | 2026-08-28 |
| 12 | Gọi model/ngày · p50/p95 latency · token | chưa đo | Cần phiên eval live có kiểm soát + log router | |

**Ba dòng ưu tiên nếu thiếu thời gian:** #1 (W01 fixture) · #2 · #10.

**Chạy đo nhóm A:** `CA_AGENT_MODE=replay python scripts/measure_group_a.py`
