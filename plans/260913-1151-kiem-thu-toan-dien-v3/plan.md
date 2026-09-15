# Plan — Kiểm thử toàn diện V3: toàn bộ dự án, đầy đủ bước & ngữ cảnh

**Ngày:** 2026-09-13 11:51 · **Nhánh:** `feature/wip` (từ `main` @ `fb8577a`) · **Thay đổi treo:** `scripts/seed_professional_fixture.py` (dọn gộp import `datetime` — vô hại, cần commit để truy vết)

## Outcome

Chạy lại toàn diện toàn bộ dự án NHỊP QUÁN theo 10 giai đoạn liên hoàn: cổng tĩnh → 790 unit test → fixture/seed → solver → API local → web e2e → Docker toàn tuyến → eval replay → kịch bản nghiệp vụ 10 bước 3 vai trò → báo cáo nghiệm thu. Mọi kết quả PASS/FAIL gắn với commit hash, **0 tương tác với kênh/khách hàng thật**, DB có thể khôi phục về trạng thái trước test.

## Nguồn bằng chứng (đã xác minh 2026-09-13)

- `pytest --collect-only` trên `apps/api/tests/unit` + `packages/agents/tests` = **790 tests** (Python 3.12.10 hệ thống).
- Kế hoạch V2 (`docs/KE_HOACH_KIEM_THU_TOAN_DIEN_V2.md`) tham chiếu `scratch/*.py` — **thư mục `scratch/` không tồn tại** → V2 lỗi thời về lệnh; V3 thay bằng tài sản thực có: `scripts/` (validate_professional_fixture, solve_tuan, verify_hard, eval_*, do_metrics, docker_stack), Playwright `apps/web/e2e/` (4 spec), task VS Code `validate-all-gates`.
- `.env` hiện đặt `CA_AGENT_MODE=live`, `NHIPQUAN_PAGE_MODE=live`, `NHIPQUAN_FB_AUTO_SEND=1`, token Fanpage **thật** (Nhịp Quán), SMTP **thật** → bắt buộc trung hòa trước mọi bước test (Giai đoạn 0).
- `packages/agents/src/ca_agents/llm.py::load_dotenv(override=False)`: **biến môi trường set trong shell thắng `.env`** → có thể trung hòa mà không sửa file.
- `infra/docker/compose.yml`: `NHIPQUAN_PAGE_MODE` / `NHIPQUAN_FB_AUTO_SEND` **không** nằm trong mục `environment:` → lấy thẳng từ `env_file: ../../.env` → Docker stack **bắt buộc** chỉnh `.env` tạm thời (Giai đoạn 7).
- `.venv` của repo là Python **3.10.10** (< yêu cầu ≥3.12) → mọi lệnh Python dùng `C:\Users\84788\AppData\Local\Programs\Python\Python312\python.exe` (giống task `validate-all-gates`).
- `apps/web` có `node_modules`, **chưa có `.next`** → Playwright (`next start -p 3001`) cần `npm run build` trước.
- Playwright config tự khởi API (`scripts/demo_api.py`, port 8000, tái dùng nếu đang chạy) + web port 3001; e2e ghi user `e2e_%` vào `data/quan.db` thật → cần snapshot + reset sau.

---

## Giai đoạn 0 — An toàn & chốt mốc (BẮT BUỘC, chặn mọi giai đoạn sau)

### 0.1 Commit thay đổi treo để có commit hash truy vết
```cmd
git add scripts/seed_professional_fixture.py
git commit -m "chore(seed): gop import datetime trong seed_professional_fixture"
git log --oneline -1   < ghi hash vào báo cáo
```

### 0.2 Snapshot DB + `.env`
```cmd
copy data\quan.db data\backups\quan-pre-test-260913.db
copy .env data\backups\env-pre-test-260913.bak
```

### 0.3 Trung hòa kênh live (mọi terminal chạy API/test đều set trước)
```cmd
set CA_AGENT_MODE=replay
set NHIPQUAN_PAGE_MODE=disconnected
set NHIPQUAN_FB_AUTO_SEND=0
```
- Cơ chế: `load_dotenv` không đè biến đã có trong process → 3 lệnh `set` trên thắng `.env`.
- Tác dụng: agent chạy replay (tất định, 0 đồng, không gọi LLM thật); `_page_mode()` trả `disconnected` (không đồng bộ Fanpage thật); không tự gửi tin trả lời khách.
- **Riêng Gmail/SMTP:** `ag_mail` ở chế độ replay chỉ ghi log — giữ `CA_AGENT_MODE=replay` là đủ chặn gửi mail thật.

### 0.4 Chốt môi trường
- Python: `C:\Users\84788\AppData\Local\Programs\Python\Python312\python.exe` (3.12.10, đã có pytest 9.1.1 / ruff / mypy). **Không dùng `.venv` (3.10).**
- Node ≥ 20 đã có; web đã `npm install`.

**Điều kiện qua:** 3 biến env đã set trong terminal hiện hành · 2 file backup tồn tại · commit hash đã ghi.

---

## Giai đoạn 1 — Cổng tĩnh (ruff · mypy · tsc)

Chạy nhanh bằng task VS Code `validate-all-gates` (chạy kèm 5 file test khói), hoặc lệnh tách:

```cmd
C:\Users\84788\AppData\Local\Programs\Python\Python312\Scripts\ruff.exe check apps/api/src packages/agents/src packages/gates/src packages/opsengine/src packages/playbook/src
C:\Users\84788\AppData\Local\Programs\Python\Python312\Scripts\mypy.exe apps/api/src packages/agents/src packages/gates/src packages/opsengine/src packages/playbook/src
cd apps\web && npm run lint && cd ..\..
```

**Kỳ vọng:** ruff 0 lỗi · mypy strict 0 lỗi · `tsc --noEmit` 0 lỗi. · Thời lượng ≈ 3–5 phút.

---

## Giai đoạn 2 — Unit test pytest toàn bộ (790 tests, replay)

```cmd
set CA_AGENT_MODE=replay
C:\Users\84788\AppData\Local\Programs\Python\Python312\python.exe -m pytest -q > .test_pytest_full.txt 2>&1
powershell -Command "Get-Content .test_pytest_full.txt -Tail 5"
```

- `pyproject.toml` đặt `testpaths = ["apps", "packages"]` → phủ `apps/api/tests/unit` (44 file) + `packages/agents/tests` (37 file).
- Mỗi test dùng store SQLite tạm (conftest `_isolated_store`) → **không** đụng `data/quan.db`.
- **Kỳ vọng:** `790 passed` (cho phép số tăng nếu có test mới). Nếu có fail → ghi file:dòng, sửa hoặc lập issue, không bỏ qua.
- Thời lượng ≈ 5–10 phút.

---

## Giai đoạn 3 — Fixture & seed (tính toàn vẹn dữ liệu gốc)

```cmd
C:\Users\84788\AppData\Local\Programs\Python\Python312\python.exe scripts\validate_professional_fixture.py
C:\Users\84788\AppData\Local\Programs\Python\Python312\python.exe scripts\seed_professional_fixture.py --reset
```

Kiểm tra sạch (theo `docs/runbook-demo-sach.md`):
```cmd
C:\Users\84788\AppData\Local\Programs\Python\Python312\python.exe -c "import sqlite3; cx=sqlite3.connect('data/quan.db'); print('e2e users:', cx.execute(\"SELECT COUNT(*) FROM users WHERE username LIKE 'e2e_%'\").fetchone()[0]); print('eval rows:', cx.execute(\"SELECT COUNT(*) FROM fb_review_queue WHERE external_thread_id LIKE 'fb_eval%'\").fetchone()[0])"
```

**Kỳ vọng:** validate pass (10 staff · 21 ca · tham chiếu chéo khớp) · seed `--reset` thành công (backup tự lưu `data/backups/`) · clean check = `e2e users: 0 · eval rows: 0`. · Thời lượng ≈ 2 phút.

---

## Giai đoạn 4 — Solver bench (CP-SAT + ràng buộc cứng)

```cmd
C:\Users\84788\AppData\Local\Programs\Python\Python312\python.exe scripts\solve_tuan.py
C:\Users\84788\AppData\Local\Programs\Python\Python312\python.exe scripts\verify_hard.py
```

**Kỳ vọng:** solver trả trạng thái (OPTIMAL hoặc best_effort có báo ca thiếu) · `verify_hard` xác nhận C01–C06 không vi phạm. · Thời lượng ≈ 1–3 phút (đặt timeout 10 phút; nếu treo → xem rủi ro R4).

---

## Giai đoạn 5 — API local + smoke HTTP

Terminal 1 (đã set 3 biến env ở Giai đoạn 0):
```cmd
C:\Users\84788\AppData\Local\Programs\Python\Python312\python.exe scripts\demo_api.py
```

Terminal 2 — smoke thủ công lõi:
```cmd
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d "{\"username\":\"lan\",\"password\":\"nhipquan\"}"
curl http://localhost:8000/docs   < OpenAPI liệt kê endpoint, đối chiếu độ phủ
```

**Kỳ vọng:** `/health` 200 · login trả token + role `quan_ly` · `/docs` mở đầy đủ. Giữ API chạy cho Giai đoạn 6 (Playwright tái dùng port 8000). · Thời lượng ≈ 5 phút.

---

## Giai đoạn 6 — Web: build + Playwright e2e (4 spec)

```cmd
cd apps\web
npm run build
npm run test:e2e
```

- Config tự khởi `next start -p 3001` + tái dùng API 8000 đang chạy; 4 spec: `flows` · `fb-inbox` · `meeting-clarify` · `phieu-timing`.
- **Kỳ vọng:** 4/4 spec pass. e2e tạo user `e2e_%` trong `data/quan.db` → sau khi chạy xong ghi nhận, rồi ở cuối chuỗi (Giai đoạn 10) chạy lại `seed_professional_fixture.py --reset` + clean check để trả DB sạch.
- Thời lượng ≈ 10–20 phút (gồm build).

---

## Giai đoạn 7 — Docker toàn tuyến (postgres · redis · api · worker · web)

> ⚠️ **Bước 7.1 bắt buộc:** compose nạp `NHIPQUAN_PAGE_MODE` / `NHIPQUAN_FB_AUTO_SEND` trực tiếp từ `.env` (không qua `environment:`) → **phải chỉnh `.env` tạm thời**, shell `set` không có tác dụng trong container.

### 7.1 Tạm trung hòa `.env` (đã backup ở 0.2)
Sửa 3 dòng trong `.env`:
```dotenv
CA_AGENT_MODE=replay
NHIPQUAN_PAGE_MODE=disconnected
NHIPQUAN_FB_AUTO_SEND=0
```
(và tạm comment dòng `NHIPQUAN_SMTP_*` nếu muốn chắc chắn tuyệt đối.)

### 7.2 Up + smoke + seed trong container
```cmd
C:\Users\84788\AppData\Local\Programs\Python\Python312\python.exe scripts\docker_stack.py up
C:\Users\84788\AppData\Local\Programs\Python\Python312\python.exe scripts\docker_stack.py smoke
C:\Users\84788\AppData\Local\Programs\Python\Python312\python.exe scripts\docker_stack.py seed-ops
C:\Users\84788\AppData\Local\Programs\Python\Python312\python.exe scripts\docker_stack.py ps
```
- Dùng wrapper `docker_stack.py` (không gọi `docker compose` trực tiếp) — tránh lỗi BuildKit đường dẫn non-ASCII.
- Mở http://localhost:3000 và http://localhost:8000/docs xác nhận sống.

### 7.3 Dọn & trả `.env`
```cmd
C:\Users\84788\AppData\Local\Programs\Python\Python312\python.exe scripts\docker_stack.py down
copy /Y data\backups\env-pre-test-260913.bak .env
```

**Kỳ vọng:** smoke pass toàn tuyến · seed-ops nạp 6 bề mặt vào volume container · `.env` đã trả về nguyên trạng. · Thời lượng ≈ 15–30 phút (gồm build image).

---

## Giai đoạn 8 — Eval replay + metrics §18.2 (tất định)

```cmd
set CA_AGENT_MODE=replay
C:\Users\84788\AppData\Local\Programs\Python\Python312\python.exe scripts\eval_ag_tkb.py
C:\Users\84788\AppData\Local\Programs\Python\Python312\python.exe scripts\eval_ag_msg.py
C:\Users\84788\AppData\Local\Programs\Python\Python312\python.exe scripts\measure_group_a.py
C:\Users\84788\AppData\Local\Programs\Python\Python312\python.exe scripts\do_metrics.py
```

**Kỳ vọng:** 3 bộ eval cho kết quả lặp lại được (replay) · `do_metrics` sinh 7 con số §18.2 trên fixture ADR-012, mọi bản ghi nhãn `mo_phong_fixture`. · Thời lượng ≈ 5–10 phút.

---

## Giai đoạn 9 — Kịch bản nghiệp vụ 10 bước, 3 vai trò (local stack, API + web đang chạy)

Chạy trên `http://localhost:3000` (API Giai đoạn 5 + `cd apps\web && npm run dev` nếu đã dừng). Tài khoản: `hung`/`lan`/`minh` · mật khẩu `nhipquan`. Mỗi bước ghi chụp màn hình + kết quả vào báo cáo.

| # | Bước | Vai trò | Việc làm | Kỳ vọng then chốt |
|---|---|---|---|---|
| 1 | RBAC & khởi tạo | hung → lan → minh | Đăng nhập 3 vai, xem `/me`, `/nguoi`; hung nâng/hạ vai; minh thử gọi API nâng vai | Nâng/hạ vai OK có audit; minh bị **403** |
| 2 | Bảng tin + QR one-shot | lan → minh | Lan phát mã QR cho minh; minh quét; thử quét chéo (minh quét mã của tuan); quét lại mã đã dùng; quét mã rác | Điểm danh OK · quét chéo **403 qr_khong_phai_cua_ban** · quét lại **409 qr_da_dung** · mã rác **404** |
| 3 | Phiếu mở quán 20 bước | minh | Start `mo_quan`, đi 2–3 bước (nhiệt độ ngoài 2–8°C), bấm tích liên tục <200ms, bấm Treo | Cờ cảnh báo `nhanh:{ma_buoc}` · việc treo hiện ở `/viec-treo` |
| 4 | Họp giao ca AI Meeting | lan | `/cuoc-hop` dán transcript mẫu → analyze → duyệt Human-in-the-loop | Action items đẩy vào `/viec-treo`, đề xuất vào `/sop/de-xuat`; minh thử xoá cuộc họp bị **403** |
| 5 | Trong ca: đặt bàn · POS · chat · Fanpage | lan + minh | Đặt bàn VIP `/reservations` → POS `/quay` gọi món → chat thả reaction/ghim/chuyển treo → `/page-quan` xem thread + duyệt nháp (mode **disconnected**) | Đơn POS tính tiền đúng · nháp duyệt chỉ lưu nội bộ, **0 gửi ra ngoài** |
| 6 | Kết ca: hao phí + SBAR | minh → lan | `/waste` ghi hao phí, `/tieu-thu` xem; lập handover SBAR 4 ô | Tiêu thụ = (đầu + nhập) − cuối − hao · SBAR đủ 4 ô, tự liên kết việc treo chưa xong |
| 7 | TKB sinh viên | minh | `/tkb` tải ảnh mẫu (hoặc "Thử ảnh mẫu" khi replay) → confirm khung giờ bận | Khung giờ hiện đúng, ảnh mờ → cảnh báo + nhập tay được |
| 8 | Xếp lịch tuần CP-SAT | lan (duyệt) + minh (xem) | Copilot "Xếp lịch tuần sau" → thẻ Đề xuất → Duyệt & Áp dụng → `/roster` ghim ca → xuất `.ics` → `/toi/lich` → `/cong-bang` 4 trục | OPTIMAL, không trùng giờ học · pin users thật OK (không còn 404 vô hình) · `.ics` tải được |
| 9 | Chợ đổi ca 3 nhánh | minh + tuan + lan | Minh xin đổi ca: (a) đủ điều kiện → tự duyệt; (b) lệch công bằng → vào `/inbox`; (c) trùng giờ học → chặn tại chỗ | 3 nhánh đúng như thiết kế · inbox duyệt/từ chối OK |
| 10 | Học AI · Golden SOP · audit | minh → hung | `/sop` hỏi quy trình pha chế (trả lời có trích dẫn nguồn) → `/cam-nang` xem pipeline 8 bước → `/audit` xem vết | SOP có nguồn trích dẫn, không bịa · mọi thao tác bước 1–9 đều có vết audit |

**Edge case bắt buộc thêm** (từ V2 PHẦN IV, vẫn hợp lệ): VF-SCOPE chặn chi nhánh khác (**403 scope_blocked**) · VF-STALE duyệt dữ liệu bị sửa (**409 stale_data**) · magic bytes chặn `.exe` đổi đuôi `.png` (**415**) · path traversal `../../etc/passwd` (**400/404**) · 2 quản lý duyệt cùng đề xuất (một 200, một 409) · webhook FB payload dị dạng (không crash, không bản ghi rác).

Thời lượng ≈ 3–4 giờ (có thể chia 2 phiên: bước 1–6 và 7–10).

---

## Giai đoạn 10 — Nghiệm thu, trả trạng thái & báo cáo

### 10.1 Trả DB + `.env` về trạng thái sạch
```cmd
C:\Users\84788\AppData\Local\Programs\Python\Python312\python.exe scripts\seed_professional_fixture.py --reset
< chạy lại clean check Giai đoạn 3 — kỳ vọng 0 · 0 >
< xác nhận .env đã trả nguyên trạng (diff với data\backups\env-pre-test-260913.bak) >
```

### 10.2 Tiêu chí chấp nhận (Acceptance / Exit)
1. **790/790** pytest pass ở `CA_AGENT_MODE=replay` (log đính kèm).
2. ruff · mypy strict · `tsc --noEmit` — 0 lỗi.
3. **4/4** Playwright spec pass.
4. Docker smoke pass + seed-ops container nạp thành công.
5. Solver: OPTIMAL (hoặc best_effort có báo rõ) + `verify_hard` pass.
6. 3 bộ eval replay lặp lại được + `do_metrics` sinh đủ 7 số §18.2.
7. 10 bước nghiệp vụ + toàn bộ edge case: đúng mã lỗi kỳ vọng (403/409/404/415), không có bước bỏ qua.
8. **0** tương tác kênh thật: không tin FB/Zalo/Telegram/mail nào ra ngoài (kiểm tra log + mode `disconnected`/`replay` hiển thị ở `/channels/status`).
9. Toàn vẹn DB sau test: clean check 0 · 0, không bản ghi mồ côi, sổ công bằng khớp.
10. Báo cáo ghi **commit hash** + thời gian chạy từng giai đoạn.

### 10.3 Template báo cáo (điền sau khi chạy — không ghi kết quả trước)
```markdown
# Báo cáo kiểm thử toàn diện V3 — 2026-09-13
Commit: <hash> · Nhánh: feature/wip · Python 3.12.10 · Node <ver>
| Giai đoạn | Kết quả | Thời lượng | Ghi chú / log |
|---|---|---|---|
| 1 Cổng tĩnh | ☐ | | |
| 2 Pytest 790 | ☐ | | |
| ... | | | |
Lỗi phát hiện: <file:dòng — mô tả — trạng thái>
```
Lưu tại `plans/260913-1151-kiem-thu-toan-dien-v3/bao-cao.md`.

---

## Risk ledger

| # | Rủi ro | Mức độ | Giảm thiểu |
|---|---|---|---|
| R1 | Token Fanpage thật + `NHIPQUAN_FB_AUTO_SEND=1` → AI nhắn khách thật | **Nghiêm trọng** | Giai đoạn 0.3 (local) + 7.1 (Docker bắt buộc sửa `.env`); kiểm tra `/channels/status` trước mỗi phiên |
| R2 | Dùng nhầm `.venv` Python 3.10 (<3.12) → hành vi khác yêu cầu | Trung bình | Luôn dùng đường dẫn Python312 đầy đủ; không gọi `python` trần |
| R3 | e2e Playwright ghi rác `e2e_%` vào `data/quan.db` | Thấp | Snapshot 0.2 + reset 10.1 + clean check |
| R4 | CP-SAT không hội tụ (25 NV × đầy đủ ràng buộc) | Trung bình | Timeout 10 phút; kịch bản best_effort đã có; fixture 10 NV là bản chuẩn |
| R5 | Playwright fail vì chưa build web (`next start` cần `.next`) | Thấp | Giai đoạn 6 có `npm run build` trước |
| R6 | Docker BuildKit lỗi đường dẫn non-ASCII | Thấp | Đã dùng wrapper `docker_stack.py` |
| R7 | Ghi "PASS 100%" trước khi chạy (bài học V2) | Cao | Template 10.3 trống, chỉ điền sau; tách rõ "kế hoạch" (file này) và "báo cáo" |
| R8 | Thao tác không hoàn tác được (QR one-shot, đóng phiếu, đóng lịch tuần) làm hỏng dữ liệu giữa chừng | Trung bình | Snapshot 0.2; chạy lại `--reset` để tái tạo fixture; các bước 10-bước có thể lặp |

## Thứ tự phụ thuộc & tổng thời lượng

```mermaid
graph LR
    G0["GĐ0 An toàn+chốt mốc"] --> G1["GĐ1 Cổng tĩnh"]
    G1 --> G2["GĐ2 Pytest 790"]
    G2 --> G3["GĐ3 Fixture+seed"]
    G3 --> G4["GĐ4 Solver bench"]
    G4 --> G5["GĐ5 API local"]
    G5 --> G6["GĐ6 Web e2e"]
    G6 --> G7["GĐ7 Docker toàn tuyến"]
    G7 --> G8["GĐ8 Eval+metrics"]
    G8 --> G9["GĐ9 10 bước nghiệp vụ"]
    G9 --> G10["GĐ10 Nghiệm thu+báo cáo"]
```

Tổng ước tính: **6–8 giờ** (GĐ9 chiếm 3–4h, chia 2 phiên được). GĐ7 độc lập với GĐ5–6 (có thể hoán đổi); GĐ8 chỉ phụ thuộc GĐ3.
