# DEMO QA RESULTS — Kết quả kiểm thử trình duyệt từng chức năng NHỊP QUÁN

> **Ngày chạy:** 2026-09-26 · **Môi trường:** https://nhipquan.duckdns.org (PRODUCTION)
> **Phiên:** `lan` (quản_ly) — đăng nhập qua quick-login · đồng thời kiểm tra nhánh `hung` (chu_quan) và `minh` (nhan_vien) ở các gate quyền
> **Nguyên tắc an toàn đã tuân thủ:** KHÔNG bấm nút gửi ra bên ngoài (Facebook/email). Mọi đề xuất 2 pha được **TỪ CHỐI** để giữ nguyên dữ liệu production. Đã xác minh reject thực sự không ghi DB.
> **Tham chiếu kế hoạch:** [`DEMO_BROWSER_PLAN.md`](./DEMO_BROWSER_PLAN.md)
>
> ## ✅ TRẠNG THÁI FIX (2026-09-26, cùng ngày)
> **Cả 5 bug đã được sửa** — xem §6 "Đã sửa gì" cuối tài liệu. Lint `ruff check apps/api/src packages scripts` = **All checks passed**; `tsc --noEmit` web = **sạch**; test liên quan **77 passed** (`test_vf_num_conflict.py` 7 · `test_predict_playbook.py` 7 · `test_ag_explain.py` · `test_ops_predict_api.py` · `test_ops_explain_api.py` · `test_vf_gates.py`).

---

## 1. Bảng tổng hợp kết quả

| Mã | Chức năng | Kết quả | Bằng chứng |
|----|-----------|---------|------------|
| S1 | Đăng nhập quick-login + RBAC 4 vai | ✅ **PASS** | 19 nút quick-login hiển thị đúng; sai mật khẩu chặn đúng thông điệp; `minh` (nhân viên) bị chặn `/inbox` |
| S1b | RBAC âm tính (nhân viên) | ✅ **PASS** | `minh` vào `/inbox`, `/roster` → "Không đủ quyền truy cập" |
| S1c | RBAC âm tính (quản lý vs chủ quán) | ✅ **PASS (chủ ý)** | `lan` bị chặn `/menu`, `/nguoi` → đúng `OWNER_ONLY` (session.ts:99) |
| S3 | Hộp thư ràng buộc + bộ lọc | ✅ **PASS** | 23 mục (20 AI đã duyệt / 3 AI từ chối); lọc "AI đã từ chối" → 3/23 đúng |
| S3b | AI auto-approve (giao diện mới) | ✅ **PASS** | Header "AI tự động duyệt · chỉ xem"; mỗi mục có "Yêu cầu / AI quyết định / Kết quả xếp lịch" + độ tin cậy % |
| S4 | Copilot chat live (SSE) | ✅ **PASS** | "Bản tin 2026-09-26: 14 lượt phân công trong 10 ca, 6 việc treo đang chờ" — đọc dữ liệu thật |
| S4b | Copilot 2 pha (ActionProposal) | ✅ **PASS** | Thẻ `PROPOSE_HANGING_TASK`, đồng hồ `⏳ 119:48` (TTL 120′), `CHỜ DUYỆT`, diff Nội dung+Nhân viên, 2 nút Duyệt/Từ chối |
| S4c | Reject không ghi DB | ✅ **PASS** | Bấm `✕ Từ chối` → thẻ `✕ ĐÃ TỪ CHỐI`; `/treo` vẫn **9 việc** (không xuất hiện việc QA) |
| S4d | Fail-closed khi solver bất khả thi | ✅ **PASS** | "Không thể tìm phương án xếp ca khả thi cho tuần 2026-W40 (INFEASIBLE_PIN)" — từ chối thay vì bịa |
| S4e | Fail-closed khi thiếu dữ liệu | ✅ **PASS** | Chip "Đề xuất quy định mới" → "Em chưa có dữ liệu… để tổng hợp" (không bịa luật) |
| S5 | Roster: lưới lịch + lifecycle | ✅ **PASS** | Tuần 2026-W39, trạng thái **Đã công bố**, 7 ngày × 13–14 NV, mọi ca "Đủ · 4/4" |
| S5b | Roster: workflow 3 bước | ✅ **PASS** | "1. Chuẩn bị lịch → 2. Rà soát và xử lý ca thiếu → 3. Đã duyệt và công bố" |
| S5c | Roster: modal mở lại lịch | ✅ **PASS** | Modal đòi lý do bắt buộc; nút "Mở lại lịch" **disabled** khi trống; cảnh báo ghi nhật ký |
| S6a | QR: phát mã một lần | ✅ **PASS** | Toast "Đã phát mã một lần…"; mã che `•••• •••• 45a4`; 19 NV + 70 ca trong dropdown |
| S6b | QR: chặn mã sai/đã dùng | ✅ **PASS** | "Mã không đúng hoặc đã dùng rồi. Nhờ quản lý phát mã mới." |
| S8 | Việc treo: đánh dấu xong | ✅ **PASS** | Toast "Đã đánh dấu việc treo là xong."; đếm **9 → 8 việc**; việc chuyển nhóm "Đã xong" (17) |
| S11 | Cẩm nang: pipeline 8 bước | ✅ **PASS** | 211 lần sửa thật · 4 mẫu sẵn sàng · 4 đang hiệu lực; 11 luật đủ vòng đời |
| S11b | Cẩm nang: cổng VF-RULE loại luật | ✅ **PASS** | Luật *"Bạn nv_03 lười nên đừng xếp ca cuối tuần"* → **BỊ LOẠI Ở VÒNG KIỂM** |
| S11c | SOP: hỏi đáp có trích dẫn | ✅ **PASS** | "Nhiệt độ 2–8°C" + badge `Có trong cẩm nang · AI · groq · Tin cậy 85%` + **Nguồn dẫn: Phiếu — Ghi nhiệt độ tủ lạnh** |
| S12a | Tự giải thích: kết luận có căn cứ | ✅ **PASS** | "Luật Tăng cường nhân sự cho ca T6_toi do doanh thu vượt trội" |
| S12b | Tự giải thích: hiển thị chuỗi bằng chứng | ❌ **FAIL (bug UI)** | Chuỗi lặp ~13 lần cùng 3 luật — **xem Bug #1** |
| S13a | Công bằng (sổ nợ 4 trục) | ✅ **PASS** | "SỐ DƯ CỦA BẠN — Ca cuối tuần 0.0 · TB nhóm 1.1 · NHẬN ÍT HƠN" |
| S13b | Đề xuất thông minh (Predict) | ⚠️ **PARTIAL (bug)** | "21 mẫu / 21 luật" nhưng chỉ **3 mẫu khác nhau lặp 7 lần** — **xem Bug #2** |
| S10 | Bàn giao ca | ⚠️ **PARTIAL (bug)** | Tách lưu OK (8 lần lịch sử) nhưng **không phát hiện lệch số** 2.350.000 vs 2.300.000 — **xem Bug #3** |
| S18 | Vết hệ thống /vet | ✅ **PASS** | 200 vết; filter theo người → 92/200; search "Đăng nhập"=39, "Copilot"=47, "lịch"=12 |
| S17 | POS quầy | ✅ **PASS** | Menu đang bán render (Bạc xỉu, Cà phê đen, Combo sáng…), giỏ cố định, 28 nút |
| S9 | Họp giao ca (AG-MEETING) | ✅ **PASS (nổi bật)** | Bóc đúng 4 việc từ transcript (máy pha rò nước, sữa còn 4 hộp, đoàn 25 khách 19h, áo khoác); 4 tab phân loại (Vấn đề&SOP 1 / Bản tin ca 2 / Việc giao 2 / Góp ý 1); **độ tin cậy 90%**; trạng thái "CHỜ QUẢN LÝ DUYỆT" + nút "Duyệt & phân công vào ca" |
| S7 | Phiếu checklist | ✅ **PASS (render)** | 3 mẫu: Mở quán 20 bước/30′ · Đóng quán 4 bước/40′ · Bàn giao ca 5 bước/10′; nút "TÔI ĐÃ CÓ MẶT" đúng khi chưa điểm danh |
| S14 | Duyệt phản hồi Fanpage | 🚫 **BỎ QUA (an toàn)** | Rủi ro đăng thật lên Page công khai (`FB_AUTO_SEND=1`) |
| S15 | Soạn bài Page bằng AI | 🚫 **BỎ QUA (an toàn)** | Như trên |
| S16 | Khảo sát giá | ⏳ **CHƯA CHẠY** | Tốn quota SerpApi thật |
| S19 | Skills / AI Learning | ❌ **BLOCKED (bug)** | `/skills`, `/gmail` → "Không đủ quyền truy cập" với **mọi vai** — **xem Bug #4** |

**Tóm tắt: 22 PASS · 2 PARTIAL (bug) · 1 FAIL (bug UI) · 1 BLOCKED (bug quyền) · 1 chưa chạy (S16) · 2 bỏ qua vì an toàn.**

---

## 2. Bug / phát hiện thật (có bằng chứng DOM)

### 🐞 Bug #4 (P1 — chặn truy cập) — `/skills` và `/gmail` không vào được bằng BẤT KỲ vai nào
- **Hiện tượng:** Menu có link "Bộ Kỹ năng AI (13/13)" và "Quản lý Gmail", nhưng khi mở thì hiện *"Không đủ quyền truy cập — Tài khoản hiện tại không có quyền truy cập trang này."*
- **Bằng chứng (đã test 2 vai):**
  - `lan` (quản_ly) → `/skills` **BLOCKED**, `/gmail` **BLOCKED**
  - `hung` (**chu_quan** — vai cao nhất) → `/skills` **BLOCKED**, `/gmail` **BLOCKED**; trong khi `/menu` và `/nguoi` (OWNER_ONLY) **OK**
- **Chẩn đoán:** đọc `apps/web/src/lib/session.ts:47–104` cho thấy hai route này **không có trong `STAFF_ACCESS`, `MANAGER_ONLY` hay `OWNER_ONLY`** → hàm `canAccess()` rơi vào nhánh cuối `STAFF_ACCESS.has(path) && Boolean(role)` → luôn `false`.
- **Mã liên quan:** `session.ts:47–104` (`canAccess`), `AppShell.tsx:359` (gate hiển thị).
- **Đề xuất fix:** thêm `/skills` vào `STAFF_ACCESS` (API `/skills` vốn công khai 🟢 theo README) và `/gmail` vào `MANAGER_ONLY` (README ghi "Quản lý/chủ quán").

### 🐞 Bug #1 + #2 (P2 — cùng gốc) — Không khử trùng lặp mẫu/luật
- **Bug #1 (UI):** `/giai-thich` khi truy vết nhân quả hiển thị chuỗi bằng chứng **lặp lại ~13 lần** cùng 3 luật (*T6_toi*, *matcha*, *da*).
- **Bug #2 (dữ liệu):** `/de-xuat-thong-minh` báo **"21 mẫu"** và **"21 luật"**, nhưng thực tế chỉ có **3 mẫu khác nhau lặp 7 lần** (phân trang 1–8 trong 21 nhưng trang 1 đã chứa 3 mục ×2–3 lặp).
- **Tác động demo:** số liệu "21 mẫu" gây hiểu lầm về năng lực hệ thống; hội đồng có thể hỏi ngay.
- **Đề xuất fix:** khử trùng lặp theo khoá `(loai, doi_tuong)` ở pipeline `ag_predict.detect_success_patterns` và ở `build_causal_chain` (`ag_explain`) trước khi trả về/đếm.

### ⚠️ Bug #3 (P2 — thiếu tính năng) — Bàn giao không phát hiện lệch số két
- **Hiện tượng:** dán *"Ca sáng: két còn 2.350.000đ… Ca chiều: két còn 2.300.000đ…"* → tách thành công nhưng **"Đánh giá: (trống)"**, không cảnh báo lệch 50.000đ.
- **Kỳ vọng:** README quảng bá "AG-HANDOVER + VF-NUM kiểm số liệu + phát hiện mâu thuẫn"; endpoint demo `/api/v1/vf/conflict` có tồn tại.
- **Đề xuất:** kiểm tra `ca_gates.validate_num` / `present_conflict` có được gọi trong luồng `/handover` không; bổ sung cảnh báo khi 2 claim tiền lệch.

### 🐞 Bug #5 (P3 — hạ tầng) — WebSocket chat 502 trên production + 1 resource 404
- **Hiện tượng:** console log lặp `Failed to load resource: 502` cho WS `/ws/chat`; và 1 request `404` khác.
- **Nguyên nhân nghi ngờ:** reverse proxy (nginx/Caddy) chưa cấu hình `proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade";` cho `/ws/`.
- **Tác động:** chat realtime chết trên production; phần REST không ảnh hưởng.
- **Đã có trong kế hoạch:** ghi ở `DEMO_BROWSER_PLAN.md` §C — nay xác nhận lại.

---

## 3. Bằng chứng trực quan (screenshot đã lưu trong phiên)

| # | Màn hình | Nội dung xác nhận |
|---|----------|-------------------|
| 1 | `/hom-nay` (lan) | Hàng đợi "Duyệt 5 mục hộp thư", "Duyệt lịch tuần sau (92 lượt)", 9 việc treo, brief 2026-09-26 |
| 2 | `/inbox` | 23 mục, nhóm "AI đã duyệt (20)" + "AI đã từ chối (3)", panel "AI phân tích" |
| 3 | `/roster` | Lịch 2026-W39 "Đã công bố", 7 ngày, mọi ca "Đủ · 4/4", workflow 3 bước |
| 4 | `/roster` modal | "Mở lại lịch để điều chỉnh" — lý do bắt buộc, nút disabled khi trống |
| 5 | `/copilot` | 4 phản hồi live (bản tin thật, ghi nhận lịch bận, thiếu dữ liệu, INFEASIBLE_PIN) |
| 6 | `/copilot` thẻ proposal | `PROPOSE_HANGING_TASK` · `⏳ 119:48` · `CHỜ DUYỆT` · diff · Duyệt/Từ chối |
| 7 | `/treo` | 9 việc (3 quá hạn), tab "Lần sửa lịch (241)" |
| 8 | `/treo` sau đánh dấu | Toast + đếm 8 việc, mục chuyển nhóm "Đã xong" |
| 9 | `/cam-nang` | 211 lần sửa · 4 mẫu · 11 điều luật đủ vòng đời (kể cả bị loại) |
| 10 | `/sop` | Trích dẫn "Phiếu — Ghi nhiệt độ tủ lạnh" + độ tin cậy 85% |
| 11 | `/qr` | Mã một lần che `•••• •••• 45a4` + nút Sao chép |
| 12 | `/qr` lỗi | "Mã không đúng hoặc đã dùng rồi." |
| 13 | `/giai-thich` | Chuỗi bằng chứng (bằng chứng Bug #1 — lặp) |
| 14 | `/de-xuat-thong-minh` | 21 mẫu/21 luật (bằng chứng Bug #2) |
| 15 | `/handover` | Bốn phần đã tách, "Đánh giá: (trống)" (bằng chứng Bug #3) |
| 16 | `/cuoc-hop` | AG-MEETING: biên bản bóc đúng 4 việc, độ tin cậy 90%, CHỜ QUẢN LÝ DUYỆT |
| 17 | `/phieu` | 3 mẫu phiếu (Mở quán 20 bước · Đóng quán 4 bước · Bàn giao ca 5 bước) + nút TÔI ĐÃ CÓ MẶT |

---

## 4. Xác nhận nguyên tắc cốt lõi (số liệu dùng được khi thuyết trình)

| Nguyên tắc | Bằng chứng đo được |
|-----------|---------------------|
| **Hai giai đoạn (AI đề xuất — người quyết)** | Thẻ `CHỜ DUYỆT` với đồng hồ TTL 120′; reject → `/treo` không đổi (9 việc) |
| **Fail-closed, không bịa** | 3 tình huống thật: INFEASIBLE_PIN · "chưa có dữ liệu" · "Chưa có trong cẩm nang" |
| **Lõi tất định kiểm soát AI** | Cổng VF-RULE loại luật thiên vị *"nv_03 lười"* |
| **Đối soát trước/sau** | Việc treo 9→8; lọc inbox 23→3; filter /vet 200→92 |
| **Dữ liệu thật, có nhãn** | Mọi trang gắn badge "DỮ LIỆU MẪU" + ghi rõ lệnh seed để dọn |
| **RBAC 4 tầng** | `minh` chặn `/inbox`; `lan` chặn `/menu` `/nguoi`; gate ở AppShell |

---

## 5. Đề xuất ưu tiên xử lý trước demo

| Ưu tiên | Việc | Tham chiếu | Trạng thái |
|---------|------|-----------|------------|
| **P0** | Sửa Bug #4 (`/skills`, `/gmail` thêm vào tập quyền) | `session.ts:47–104` | ✅ **ĐÃ SỬA** |
| **P0** | Cấu hình proxy cho 3 WebSocket (Bug #5) | `infra/oracle/Caddyfile` | ✅ **ĐÃ SỬA** |
| **P1** | Khử trùng lặp mẫu/luật (Bug #1+#2) | `ag_predict`, `ag_explain`, `ops_predict.py` | ✅ **ĐÃ SỬA** |
| **P1** | Cảnh báo lệch số bàn giao (Bug #3) | `ca_gates/vf_num.py`, `sprint45.py`, `handover/page.tsx` | ✅ **ĐÃ SỬA** |
| **P2** | Chạy nốt S16 (khảo sát giá) trong phiên riêng | — | ⏳ chờ |
| **P2** | Quyết định `NHIPQUAN_FB_AUTO_SEND` trước khi demo luồng Page | `.env` | ⏳ chờ chủ quán |

> **Lưu ý:** phiên QA này **không** để lại dữ liệu rác: đã kiểm chứng reject không ghi DB; chỉ có 1 việc treo được đánh dấu xong (thao tác nội bộ hợp lệ, không thể hoàn tác từ UI) và 1 mã QR phát cho `uyen`/ca CN Kho (chưa dùng, tự hết hạn).

---

## 6. Đã sửa gì (2026-09-26)

### Bug #4 — `/skills` + `/gmail` chặn mọi vai (**2 nguyên nhân**)
**Nguyên nhân 1 — client gate:** `apps/web/src/lib/session.ts`
- Thêm `/skills` vào `STAFF_ACCESS` (API `/skills` vốn công khai 🟢 — mọi vai xem được).
- Thêm `/gmail` vào `MANAGER_ONLY` (khớp README: "Quản lý/chủ quán").

**Nguyên nhân 2 — API bị shadow bởi trang web (nghiêm trọng hơn):** `apps/api/src/ca_api/interfaces/http/skills.py`
- Router dùng prefix `/skills` (thiếu `/api/v1`) trong khi `apps/web` có **trang** `/skills`. Trong production, `NEXT_PUBLIC_API_URL = https://nhipquan.duckdns.org` nên `apiGet("/skills")` gọi `https://nhipquan.duckdns.org/skills` → Caddy route về **Next.js** → trả **HTML** thay vì JSON → trang báo lỗi.
- **Bằng chứng đo được:** `GET /skills` → `200`, `content-type: text/html`, body bắt đầu `<!DOCTYPE` (là trang Next.js, KHÔNG phải API).
- **Sửa:** đổi prefix thành `/api/v1/skills`; cập nhật `apps/web/src/app/skills/page.tsx` (4 lời gọi), `apps/api/tests/unit/test_skills_http.py` (4 test), `test_capability_coverage.py`, README, DEMO_PLAN.
- Sau fix, `GET /api/v1/skills` mới đúng là endpoint API (không còn trùng đường dẫn trang web).

### Bug #1 + #2 — Không khử trùng lặp mẫu/luật
**File:** `apps/api/src/ca_api/interfaces/http/ops_predict.py`, `packages/agents/src/ca_agents/ag_predict/playbook_positive.py`, `packages/agents/src/ca_agents/ag_explain/causal_memory.py`
- `POST /ops/predict/run`: khử trùng theo `pattern_id` / `id` khi ghi KV → chạy lại cùng dữ liệu không tích lũy bản sao (trước đây prepend mù sinh "21 mẫu" từ 3 mẫu thật).
- `de_xuat_luat_tich_cuc`: id luật đổi từ `pos_rule_{index}` (không ổn định) → `pos_{pattern_id}` (ổn định, cho phép dedupe).
- `build_causal_chain`: thêm dedupe node (theo `node_id`) và link (theo `from_id,to_id,ly_do`) → chuỗi nhân quả không còn lặp ~13 lần.

### Bug #3 — Bàn giao không phát hiện lệch số
**File:** `packages/gates/src/ca_gates/vf_num.py` (+ export ở `__init__.py`), `apps/api/.../sprint45.py`, `apps/web/src/app/handover/page.tsx`
- Thêm `detect_number_conflicts(text)` + dataclass `NumberConflict`: tất định, gom số tiền theo chủ đề (két / doanh thu / chi phí / hao hụt), nêu khi cùng chủ đề có ≥2 giá trị khác nhau. Chuẩn hoá `2.350.000` / `2,350,000` / `2350000`.
- `/api/v1/handover` trả thêm `vf_number_conflict` + `co_lech_so`.
- UI `/handover` hiển thị Alert đỏ liệt kê các mức lệch + câu "Hệ thống không tự chọn bên nào — quản lý đối chiếu sổ rồi chốt" (đúng ADR-008).

### Bug #5 — WebSocket 502 / thiếu upgrade
**File:** `infra/oracle/Caddyfile`
- Hệ thống có **3 WebSocket**: `/ws/chat`, `/api/v1/copilot/voice`, `/api/v1/meeting/stream` — trước đây chỉ khai `handle /ws/chat*`.
- Thêm `handle` riêng cho cả 3 với `flush_interval -1` (realtime frame đi ngay, không bị gộp buffer).

### Kiểm chứng
| Cổng | Kết quả |
|------|---------|
| `ruff check apps/api/src packages scripts` | **All checks passed!** |
| `tsc --noEmit` (web) | **sạch** (0 lỗi) |
| `pytest` test mới + liên quan | **100 passed** (0 failed) |
| Test mới thêm | `test_vf_num_conflict.py` (7) · `test_predict_playbook.py` (+2) · `test_sprint45.py` (+2 handover) · `test_http_demo.py` (+4: security headers + redact tên) |

### Bug #8 — Endpoint công khai lộ họ tên nhân viên
**File:** `apps/api/src/ca_api/interfaces/http/main.py` — `five_contracts()`
- Tên rút gọn còn họ + chữ cái đầu: `"Lan Nguyễn"` → `"Lan N."` (hàm `_rut_gon_ten`).
- Thêm cờ `la_du_lieu_mo_phong: true` + `ghi_chu` nói rõ đây là dữ liệu mẫu.
- Áp dụng cho cả `/api/v1/contracts` và bí danh `/api/v1/demo/contracts` (dùng chung hàm).
- **Kiểm chứng:** `['Lan N.', 'Hùng T.', 'Minh P.', 'An L.', 'Bảo H.']` — không còn họ tên đầy đủ.

### Bug #9 — Sai URL trong tài liệu
**File:** `README.md` — `/serpapi/quota` → `/api/v1/market/serpapi/quota`.

### Bug #10 — Swagger công khai
**File:** `apps/api/src/ca_api/interfaces/http/main.py` + `.env.example` + `README.md`
- Thêm cờ `NHIPQUAN_PUBLIC_API_DOCS` (mặc định `1` = bật cho demo/hội đồng).
- Đặt `0` → tắt `/docs`, `/redoc`, `/openapi.json` khi vận hành quán thật.
- **Kiểm chứng:** `=0` → `/docs` 404, `/openapi.json` 404, `/health` 200.

### Bug #5 (bổ sung) — CORS chặn local
**File:** `.env.example` — ghi chú rõ `NHIPQUAN_CORS_ORIGINS` **ghi đè** mặc định dev, phải để trống khi chạy local.

---

## 8. TRẠNG THÁI TRIỂN KHAI (cập nhật 2026-09-26)

> ⚠️ **Code đã sửa xong nhưng CHƯA lên production.** Kiểm tra trực tiếp `nhipquan.duckdns.org` cho kết quả:
> - `GET /api/v1/skills` → **404** (fix prefix chưa deploy)
> - Security headers → **null** (middleware chưa deploy)
> - `/api/v1/contracts` → vẫn trả `"Lan Nguyễn"` (redact chưa deploy)

### Để đưa fix lên production (theo `docs/deployment.md`)

```
1. Commit các file đã sửa (danh sách ở §8.2)
2. Push lên nhánh main
3. CI (ci.yml) chạy xanh → docker-ghcr.yml build image theo SHA
4. deploy-aws.yml tự động deploy lên EC2 /opt/nhipquan + health check
```

### 8.1 Việc KHÔNG nằm trong code (cần làm trên server)

| Việc | Lệnh / ghi chú |
|------|----------------|
| Reload Caddy (WS 502) | `infra/oracle/Caddyfile` đã sửa — cần copy lên EC2 và `caddy reload` |
| Bỏ `NHIPQUAN_CORS_ORIGINS` khi test local | Sửa `.env` trên máy dev (giữ trên server là đúng) |
| Dọn KV mẫu cũ | Chạy lại `POST /ops/predict/run` (code mới tự khử trùng) |
| Quyết định Swagger | Đặt `NHIPQUAN_PUBLIC_API_DOCS=0` trên server nếu muốn tắt `/docs` |

### 8.2 Danh sách file thay đổi (12 file code + 5 test + 3 docs)

**Code:**
- `apps/api/src/ca_api/interfaces/http/main.py` — security headers, redact tên, cờ docs
- `apps/api/src/ca_api/interfaces/http/skills.py` — prefix `/api/v1/skills`
- `apps/api/src/ca_api/interfaces/http/ops_predict.py` — dedupe patterns/rules
- `apps/api/src/ca_api/interfaces/http/sprint45.py` — `co_lech_so` ở `/handover`
- `apps/web/src/lib/session.ts` — quyền `/skills` + `/gmail`
- `apps/web/src/app/skills/page.tsx` — 4 lời gọi API mới
- `apps/web/src/app/handover/page.tsx` — Alert cảnh báo lệch số
- `packages/gates/src/ca_gates/vf_num.py` + `__init__.py` — `detect_number_conflicts`
- `packages/agents/src/ca_agents/ag_explain/causal_memory.py` — dedupe chuỗi
- `packages/agents/src/ca_agents/ag_predict/playbook_positive.py` — id ổn định
- `infra/oracle/Caddyfile` — 3 WebSocket + flush_interval

**Test (mới/sửa):**
- `packages/gates/tests/test_vf_num_conflict.py` **(MỚI, 7 test)**
- `apps/api/tests/unit/test_http_demo.py` (+4)
- `apps/api/tests/unit/test_sprint45.py` (+2)
- `packages/agents/tests/test_predict_playbook.py` (+2)
- `apps/api/tests/unit/test_skills_http.py` + `test_capability_coverage.py` (cập nhật URL)

**Tài liệu:**
- `DEMO_QA_RESULTS.md` **(MỚI)** · `DEMO_BROWSER_PLAN.md` · `DEMO_PLAN.md` · `README.md` · `.env.example`

> **Lưu ý:** nhánh hiện tại là `feat/jev-sensor-killswitch-ui`. Repo có các thay đổi của **phiên khác** (nhóm `ag_trend.py`, `camoufox_client.py`, `threads_*`, `docs/runbooks/tiktok|camoufox`, `plans/260923-*`) — **không commit gộp** để tránh lẫn việc người khác. Nếu commit, chỉ chọn đúng các file ở §8.2.

> **Việc còn lại:** deploy `Caddyfile` lên VM (reload Caddy) để WS hết 502; `/skills` và `/gmail` chỉ cần build lại web. Dữ liệu KV `/de-xuat-thong-minh` đang tích lũy bản sao cũ — sau deploy có thể dọn bằng cách chạy lại `POST /ops/predict/run` (code mới tự khử trùng) hoặc thao tác quản trị.

---

## 7. QA ĐỢT 2 — Dò lỗ hổng bảo mật & bề mặt chưa test (2026-09-26, chiều)

Đăng nhập `minh` (nhân viên) và `hung` (chủ quán) để **tấn công có kiểm soát** tầng API (không chỉ tầng UI).

### 7.1 Kết quả tấn công — PHÒNG THỦ TỐT ✅

| # | Đòn tấn công | Kết quả | Đánh giá |
|---|--------------|---------|----------|
| 1 | NV gọi `POST /copilot/message` xếp lịch | `200` + từ chối mềm "vượt phạm vi vai trò" | ✅ fail-closed đúng |
| 2 | NV gọi `GET /api/v1/audit` | `403 forbidden` | ✅ |
| 3 | NV gọi `GET /api/v1/inbox/rang-buoc` | `403 forbidden` | ✅ |
| 4 | NV gọi `GET /api/v1/nguoi` | `403 requires chu_quan` | ✅ |
| 5 | **Không token** gọi `/audit`, `/inbox` | `401 thieu_token` | ✅ |
| 6 | **Token rác** | `401 thieu_token` | ✅ |
| 7 | IDOR: xem TKB người khác (`/tkb/nv_01`) | `403 cam` | ✅ chặn |
| 8 | IDOR: xem phiếu người khác | `404 phieu_khong_tim_thay` | ✅ không rò tồn tại |
| 9 | Path traversal `/copilot/uploads/..%2f..%2f.env` | `404` | ✅ |
| 10 | Path traversal `/chat/uploads/....//....//.env` | `404` | ✅ |
| 11 | Tự thăng vai (`/nguoi/minh/nang-vai`) | `403 requires chu_quan` | ✅ |
| 12 | **Brute-force login** 8 lần sai | `401 ×5` rồi **`429 ×3`** | ✅ rate-limit hoạt động |
| 13 | CORS origin lạ (`evil.example.com`) | `ACAO: null` | ✅ chặn |
| 14 | Upload file HTML độc hại | `415 dinh_dang_tep_khong_hop_le_hoac_nguy_hiem` | ✅ |
| 15 | Payload 200KB vào copilot | `422` (validator chặn) | ✅ |
| 16 | **Stored XSS** qua chat (`<img onerror>`) | API **strip HTML**, lưu "hello" | ✅ sanitize tầng API |
| 17 | XSS qua câu hỏi SOP | không echo payload; trả `chua_co` | ✅ |
| 18 | SQL injection trong `category_keyword` | `422` (validation) | ✅ |
| 19 | WebSocket `/ws/chat` không auth | không nhận message; timeout đóng | ✅ auth-first trong 5s |
| 20 | Tạo khảo sát giá không có `Idempotency-Key` | `400 MISSING_IDEMPOTENCY_KEY` | ✅ chống double-spend quota |

### 7.2 Lỗ hổng / vấn đề MỚI phát hiện

| # | Vấn đề | Mức | Chi tiết | Trạng thái |
|---|--------|-----|----------|------------|
| **#6** | **Thiếu toàn bộ security headers** | 🟡 P1 | Không có `X-Content-Type-Options`, `X-Frame-Options`, `CSP`, `HSTS`, `Referrer-Policy`, `Permissions-Policy` trên cả trang HTML lẫn API | ✅ **ĐÃ SỬA** — thêm middleware `add_security_headers` (`main.py`) |
| **#7** | **API `/skills` bị shadow bởi trang web `/skills`** | 🔴 P0 | Router prefix `/skills` trùng route Next.js; qua Caddy, request API trả HTML → trang skills hỏng | ✅ **ĐÃ SỬA** — đổi prefix `/api/v1/skills` |
| **#8** | **`/api/v1/contracts` + `/api/v1/demo/contracts` công khai trả họ tên NV** | 🟡 P2 | Không cần token vẫn đọc được `NhanVien[].ten`. `so_dien_thoai_hash: null` nên không lộ SĐT | ✅ **ĐÃ SỬA** — tên rút gọn còn "Lan N." + cờ `la_du_lieu_mo_phong: true` |
| **#9** | README ghi `/serpapi/quota` — URL thật là `/api/v1/market/serpapi/quota` | 🟢 P3 | Sai tài liệu | ✅ **ĐÃ SỬA** — cập nhật README |
| **#10** | `/docs` (Swagger) mở công khai trên production | 🟢 P3 | Lộ toàn bộ schema API | ✅ **ĐÃ XỬ LÝ** — thêm cờ `NHIPQUAN_PUBLIC_API_DOCS` (mặc định bật cho demo; đặt `0` để tắt khi vận hành thật). Đã kiểm chứng: `=0` → `/docs` + `/openapi.json` trả 404, `/health` vẫn 200 |

### 7.3 Ghi chú vận hành phát hiện thêm

- **`NHIPQUAN_CORS_ORIGINS` trong `.env` = `https://nhipquan.duckdns.org`**: khi chạy `make docker-up` local, các lệnh gọi từ `localhost:3000` sẽ bị CORS chặn (biến này **ghi đè** danh sách mặc định dev). Cần bỏ trống biến khi làm local, hoặc thêm `localhost:3000` vào danh sách.
- Fix `/skills` (prefix) **cần deploy API + build lại web** mới có tác dụng — hiện production vẫn trả HTML.
