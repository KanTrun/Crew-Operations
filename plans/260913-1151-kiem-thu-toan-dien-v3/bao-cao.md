# Báo cáo kiểm thử toàn diện V3 — 2026-09-13

**Commit:** `fb8577a8b84b1061dad0c0cb0950d6532e6f1756` · **Nhánh:** `feature/wip` · **Python:** 3.12.10 (host) / 3.12.14 (container Linux) · **Node:** v24.13.0 · **Docker:** Engine 29.7.2, Compose v5.4.0

**Người thực hiện:** GitHub Copilot (tự động). **Người phê duyệt:** chưa chỉ định.

## Kết luận

**GO cho phạm vi đã kiểm thử**, kèm **1 blocker ngoài phạm vi** thuộc về nhánh làm việc song song `pricing-radar` (xem mục "Blocker ngoài phạm vi").

Toàn bộ 10 giai đoạn đã chạy đủ. **3 lỗi production mức High được phát hiện và đã sửa**, trong đó 1 lỗi là vector DoS trên endpoint công khai. **21 test hồi quy mới** được bổ sung. Bộ edge case GĐ9 đạt **7/7**. Coverage **77.05%** vượt sàn 75% đã chốt thành gate.

> Báo cáo này thay thế bản NO-GO lúc 12:43 — bản đó dừng ở GĐ2 vì 1 test fail, và fail đó sau này được chứng minh là do code WIP chưa commit của phiên khác, không phải do code đã kiểm thử.

## Bảng kết quả theo giai đoạn

| GĐ | Hạng mục | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Cổng tĩnh: ruff | **PASS** | `All checks passed`, exit=0 trên 3 file src đã sửa |
| 1 | Cổng tĩnh: mypy strict | **PASS** | `Success: no issues found in 122 source files`, exit=0 |
| 1 | Cổng tĩnh: `tsc --noEmit` | **PASS** | exit=0 |
| 1 | Web build (next 15.5.25) | **PASS** | exit=0 |
| 2 | Pytest toàn bộ trên Docker | **1002 passed, 1 failed** | 174.13s (0:02:54), [pytest-final-edge.log](pytest-final-edge.log) |
| 2 | Coverage gate | **PASS** | `TOTAL 13700 3144 77%` · `Required test coverage of 75% reached. Total coverage: 77.05%` |
| 2 | Baseline xanh trước đó | 967 passed | 147.06s, [pytest-coverage.log](pytest-coverage.log) |
| 3 | Validate fixture | **PASS** | `staff=10 shifts=21 orders=6 runs=3 bindings=4 threads=3` |
| 3 | Seed + clean check | **PASS** | `e2e users: 0 · eval rows: 0` · `session mo coi: 0` |
| 4 | Solver CP-SAT | **PASS** | `status=OPTIMAL ok=True elapsed=0.16s violations=0 luat=1` |
| 4 | `verify_hard` ràng buộc cứng | **PASS** | c01–c06 đều 0, `TOTAL 0` |
| 5 | Cách ly mạng | **PASS** | `internal: true`, TCP probe ra ngoài bị chặn |
| 5 | Cổng an toàn kênh | **PASS** | `SAFETY_GATE=PASS` · `agent_mode=replay` · zalo/telegram/facebook `connected: false` |
| 6 | Playwright e2e | **PASS 19/19** | `19 passed (38.8s)`, `PHIEU_DEMO_MS=555` |
| 7 | Smoke nghiệp vụ | **PASS (XANH)** | phieu `mo_quan` `so_buoc: 20` · SOP `mode: keyword` `do_tin: 0.48` |
| 7 | seed-ops | **PASS** | exit=0, idempotent, nhãn `mo_phong_fixture` |
| 8 | `eval_ag_tkb` | **PASS** | `51/53 accuracy=96.23% blur_items=2 escalate=3.8%` |
| 8 | `eval_ag_msg` | **PASS** | `197/200 accuracy=98.50% hard=74/77 (96.10%)` |
| 8 | `measure_group_a` | **PASS** | `quyet_dinh=91 sua=30 khong_can_sua=67.0%` · VF escalations `total=3` |
| 8 | `do_metrics` | **PASS** | 7/12 số §18.2, `chế độ agent: replay` |
| 9 | Ma trận edge case | **PASS 7/7** | xem bảng bên dưới · 159 passed in 41.29s |
| 10 | Toàn vẹn `.env` | **PASS** | `ENV_INTEGRITY=PASS` |
| 10 | Dọn dẹp + trả trạng thái | **PASS** | `CLEAN_CHECK=PASS (0 · 0)`, stack Docker đã hạ |
| — | Dependency audit | **Đã xử lý** | 2 Critical + 1 High fixed, 1 High accepted |

## Lỗi production phát hiện — cả 3 đều đã SỬA

Cả 3 lỗi cùng một lớp: `AttributeError` → HTTP 500.

| # | Severity | Vị trí | Mô tả | Trạng thái |
|---|---|---|---|---|
| 1 | **High** | [apps/api/src/ca_api/interfaces/http/sprint3.py](../../../apps/api/src/ca_api/interfaces/http/sprint3.py) `POST /api/v1/diem-danh` | KV `diem_danh` định dạng cũ là `list` nv_id tích luỹ; code mới đọc như `dict` theo ngày → `'list' object has no attribute 'get'` → 500. UI hiện "Không ghi được điểm danh" và **ẩn luôn nút Mở quán** → quán không mở được. | **FIXED** + migrate tương thích ngược |
| 2 | **High** | [apps/api/src/ca_api/interfaces/http/sprint45.py](../../../apps/api/src/ca_api/interfaces/http/sprint45.py) `POST /api/v1/qr/{token}` | Cùng lớp lỗi ở nhánh ghi QR → nhân viên **không check-in bằng QR được**. | **FIXED** + migrate tương thích ngược |
| 3 | **High (DoS)** | [apps/api/src/ca_api/interfaces/http/channels.py](../../../apps/api/src/ca_api/interfaces/http/channels.py) `POST /api/v1/channels/facebook/webhook` | **Endpoint công khai, không cần đăng nhập.** Payload `{"entry": "khong_phai_list"}` → `for entry in "..."` lặp qua từng ký tự → `entry.get` → `AttributeError` → 500. Ai cũng bắn được từ Internet. Cùng lớp với `messaging`/`ev`/`msg`/`sender`/`postback`/`attachments[0]`/`changes`/`change`/`value`/`author` không phải dict, và `timestamp`/`created_time` không phải số. | **FIXED** — guard `isinstance` toàn diện + `_safe_float()`, fail-closed về `continue`/`ignored` thay vì 500 |

**Bài học quan trọng:** lỗi #1 và #2 **bị che khuất hoàn toàn khi chạy trong Docker** (container có DB sạch, không tồn tại dữ liệu định dạng cũ). Chỉ Playwright chạy trên DB host thật mới bắt được. Đây là lý do e2e trên DB host là bắt buộc, không thể thay bằng suite trong container.

Lỗi #3 được phát hiện **trong lúc đang viết test** cho mục "malformed webhook" của GĐ9 — không nằm trong kế hoạch ban đầu.

## 21 test hồi quy mới

| File | Test | Số lượng |
|---|---|---|
| `test_sprint3.py` | `test_diem_danh_tuong_thich_nguoc_du_lieu_list_cu`, `test_diem_danh_khong_loi_khi_kv_hong` | 2 |
| `test_sprint45.py` | `test_qr_write_path_tuong_thich_nguoc_du_lieu_list_cu` | 1 |
| `test_chat_api.py` | `test_chat_upload_media_chan_path_traversal` | 4 params |
| `test_copilot_api.py` | `test_copilot_hai_quan_ly_duyet_cung_de_xuat_mot_thanh_cong` | 1 |
| `test_fb_moderation.py` | `test_webhook_payload_rac_khong_crash_khong_ban_ghi_rac` | 13 params |

Test 2-quản-lý khẳng định: người thứ nhất `200`/`executed`, người thứ hai `409`/`idempotency_conflict`, draft vẫn `executed`, và **đúng 1** bản ghi audit `approve` — chống thực thi kép.

Test webhook rác khẳng định: không 500, `n == 0`, và **không sinh bản ghi nào** vào `fb_review_queue` / `fb_processed_events`.

## Ma trận edge case GĐ9 — 7/7 COVERED

| Edge case | Mã lỗi kỳ vọng | Trạng thái |
|---|---|---|
| VF-SCOPE chặn role | 403 `scope_blocked` | COVERED — `test_copilot_vf_scope_insufficient_role`, `test_copilot_idempotent_replay_still_enforces_scope`, `test_vf_scope_stale.py` (6 tests) |
| VF-STALE dữ liệu cũ | 409 `stale_data` | COVERED — `test_copilot_vf_stale_detection`, `test_inventory_proposal_rejects_live_source_change`, `test_vf_stale_diverged_hash` |
| Magic bytes `.exe` đổi tên `.png` | 415 | COVERED — `test_chat_upload_media_magic_bytes` |
| Path traversal `../../etc/passwd` | 4xx | COVERED — `test_chat_upload_media_chan_path_traversal` (4 params) |
| 2 quản lý duyệt cùng đề xuất | 200 + 409 | **COVERED (MỚI)** |
| Webhook FB payload dị dạng | 2xx, bỏ qua | **COVERED (MỚI)** — 13 params |
| QR one-shot | 403/409/404 | COVERED — `test_qr_one_shot`, `test_qr_can_only_be_used_by_target_employee` |

## Blocker ngoài phạm vi — KHÔNG thuộc code đã kiểm thử

**Test fail duy nhất:** `test_capability_coverage.py::test_every_user_facing_route_has_capability_or_exclusion`

```
AssertionError: Các route sau chưa có capability hoặc explicit exclusion: /catchment-survey
assert not ['/catchment-survey']
```

**Nguyên nhân:** `pricing_radar.py:27` khai báo `@router.post("/catchment-survey")` (prefix `/api/v1/market`) nhưng chưa có `deep_link` tương ứng trong `CAPABILITY_REGISTRY`, cũng chưa có lý do trong `EXCLUDED_ROUTES`. **Gate PR13 đang hoạt động đúng thiết kế** — nó chặn route mới chưa khai báo capability.

**Chứng minh lỗi này không phải của đợt kiểm thử:**

1. **Dòng thời gian:** các file WIP được tạo lúc **14:34:50–14:36:26**. Lượt chạy xanh cuối cùng của tôi lúc **14:27** (967 passed). Lượt chạy có fail lúc **14:57**.
2. **Số học:** `967` (baseline xanh) `+ 21` (test mới của tôi) `+ 15` (test WIP pricing, chạy riêng xác nhận `15 passed in 2.35s`) `= 1003` `= 1002 passed + 1 failed`. ✓ Khớp tuyệt đối.
3. **Diff của tôi không thêm route nào:** `git diff -U0` trên `channels.py` + `sprint3.py` + `sprint45.py` lọc `^\+.*@router\.` → **0 kết quả**.
4. **`pricing_radar.py` là untracked:** `git ls-files` trả về rỗng.

**Quyết định:** KHÔNG sửa file của phiên song song, KHÔNG tự ý thêm entry vào `CAPABILITY_REGISTRY` dùng chung (sẽ xung đột khi họ commit). **Chủ sở hữu blocker:** nhánh `plans/260913-1455-khao-sat-gia-fb-online-dinein-substitutes/` — cần thêm capability entry hoặc lý do exclusion trước khi merge.

**Ruff toàn phạm vi báo 12 lỗi — tất cả đều trong WIP untracked:** `main.py:14` (I001, do họ đặt import), `ag_pricing/orchestrator.py` ×5, `ag_pricing/qualifier.py` ×3, `delivery_camoufox_source.py` ×3. Ruff trên 3 file src tôi đã sửa: `All checks passed!` exit=0.

## Kiểm toán phụ thuộc — phân loại theo severity

| Severity | Gói / CVE | Áp dụng thực tế | Trạng thái |
|---|---|---|---|
| **Critical** | `next` — GHSA-p293-qw3h-jr36 (Unauthenticated RCE trên server host Windows) | **Áp dụng trực tiếp**: mục tiêu triển khai là máy Windows có host, endpoint public | **FIXED** — khai báo `^15.1.0` → `^15.5.24`; lockfile phân giải **15.5.23 → 15.5.25**. Xác minh lại: build exit=0, `tsc --noEmit` exit=0, Playwright 19/19 |
| **Critical** | `next` — GHSA-2xp9-vwfh-vxw4 (Unauthenticated RCE trong Image Optimization API khi dùng AVIF) | Cùng vector qua xử lý ảnh | **FIXED** — cùng bản nâng 15.5.25 |
| **High** | `sharp` ≤0.35.4-rc.0 — CVE-2026-33327/33328/35590/35591 (libvips, GHSA-f88m-g3jw-g9cj), GHSA-g89c-p67h-r497 + GHSA-2jg2-4ch7-h545 (libheif, GHSA-rgj7-g3m4-5g8c) | Xử lý ảnh upload | **FIXED** — `npm audit fix` |
| **High** | `postcss` ≤8.5.22 — GHSA-r28c-9q8g-f849 (path traversal, lộ file `.map`), GHSA-qx2v-qp2m-jg93 (XSS), GHSA-6g55-p6wh-862q + GHSA-fxqj-rqcc-2cmp (đọc file tuỳ ý qua `sourceMappingURL`) | **ACCEPTED RISK** — xem phân tích dưới | **CHẤP NHẬN CÓ LÝ DO** |
| **Moderate** | `next` 9.3.4-canary.0 – 16.3.0-preview.10 (kế thừa postcss) | Hệ quả của postcss | **CHẤP NHẬN** cùng postcss |
| **Medium** | 12 advisory PYSEC trong pip | Chuỗi cung ứng build | **FIXED** — nâng pip → **26.2.1**; `pip_audit` xác nhận `No known vulnerabilities found` |

**Phân tích ACCEPTED RISK cho postcss:**
- Là **phụ thuộc bắc cầu lồng sâu** tại `node_modules/next/node_modules/postcss`, không phải dependency trực tiếp của dự án.
- Chỉ sửa được bằng `npm audit fix --force` → cài `next@16.3.5`, là **breaking change major** (từ 15.x). Không đánh đổi ổn định của bản đã kiểm thử 19/19 để lấy một bản major chưa kiểm thử.
- **Phạm vi tác động hẹp:** lỗ hổng là path traversal khi auto-load source map, chỉ kích hoạt **lúc build**, và chỉ trên **CSS tailwind do chính đội viết** — không có nguồn `.map` bên thứ ba không tin cậy trong chuỗi build.
- Không xuất hiện ở runtime production (asset đã build sẵn).

**Trạng thái audit sau xử lý (xác minh lại bằng `npm audit --omit=dev`):** còn `2 vulnerabilities (1 moderate, 1 high)` — cả hai đều là cặp postcss/next nêu trên. **0 critical.**

> **Đính chính (sửa theo đúng bằng chứng):**
> 1. Bản đầu ghi mã `CVE-2026-75604` cho lỗ hổng RCE của `next`. Mã đó **không xuất hiện trong `audit-deps.log`** — mã thật là **GHSA-p293-qw3h-jr36**.
> 2. Bản đầu ghi "nâng 15.5.23 → 15.5.24". Thực tế `15.5.24` chỉ là **phạm vi khai báo tối thiểu** trong `package.json`; bản **phân giải** trong lockfile và trong `node_modules` là **15.5.25**.
> 3. Hai lỗ hổng **Critical RCE đã hết** sau bản nâng. `next` vẫn bị đếm là **moderate** vì lý do khác: nó *kế thừa* `postcss` dễ tổn thương (khoảng bị ảnh hưởng `9.3.4-canary.0 – 16.3.0-preview.10` bao trùm cả 15.5.25). Đây chính là rủi ro postcss đã ACCEPTED ở trên, không phải RCE còn sót.
>
> Xác minh bằng `scripts/verify_next_upgrade.py` (đối chiếu git object HEAD~2 với working tree) và `scripts/read_evidence_logs.py` (trích mã advisory từ log).

## Rủi ro còn lại

| Severity | Vị trí | Phát hiện | Trạng thái |
|---|---|---|---|
| **High** | `pricing_radar.py` route `/catchment-survey` | Gate PR13 chặn: route mới chưa khai báo capability. Thuộc WIP untracked của phiên song song. | **OPEN — ngoài phạm vi**, chủ sở hữu là nhánh pricing-radar |
| **High** | `node_modules/next/node_modules/postcss` | Path traversal lúc build (GHSA-r28c-9q8g-f849) | **ACCEPTED** — phân tích ở trên |
| **Low** | `infra/docker/compose.test.yml` | API healthy trong container nhưng `localhost:18000` từ host không truy cập được. **Đã vượt qua** bằng cách chạy smoke **bên trong** network container (`docker exec`), không phải bằng port publishing. | **WORKAROUND** — không chặn giai đoạn nào; cần điều tra riêng nếu muốn e2e từ host vào stack Docker |
| **Low** | `scripts/seed_professional_fixture.py` `wipe_db()` | **Xoá DB không tự backup**, trái với ghi chú ở plan.md:96 ("backup tự lưu `data/backups/`"). Đã tự tạo backup thủ công trước khi chạy. | **ĐÃ SỬA** — thêm `backup_db()`, `--reset` tự sao lưu vào `data/backups/quan-pre-reset-<moc>.db` trước khi xoá |
| **Low** | `scripts/e2e_safe_api.py` | Harness `SystemExit` khi thiếu `.env.e2e`, mà file đó bị `.gitignore` (`.gitignore:80:.env*`) → **harness chết trên clone mới**. | **ĐÃ SỬA** — thiếu file chỉ cảnh báo; 7 cờ an toàn được đặt mặc định cứng trong script |
| **Low** | `test_chat_api.py`, `test_copilot_api.py` | 8 lỗi ruff (I001, F401, B017, E741) có sẵn từ trước. **Ngoài phạm vi gate ruff** của dự án (gate chỉ quét `apps/api/src packages/*/src`). | **OPEN — pre-existing**, không do đợt này gây ra |
| **Low** | 11/17 log bằng chứng trong thư mục này | **Trộn encoding**: PowerShell 5.1 `Out-File -Append` mặc định ghi UTF-16LE trong khi lượt ghi đầu dùng `-Encoding utf8`. Mở trong editor vẫn đọc được, nhưng `grep`/`Select-String` **không khớp** → dễ kết luận sai "log không có dòng X". | **ĐÃ GIẢM THIỂU** — dùng `scripts/read_evidence_logs.py` (bỏ byte null rồi decode latin-1) để trích bằng chứng thay vì grep thô. Chính công cụ này đã lật ra mã CVE bịa ở mục Audit |
| **Low** | 17 file `.log` bằng chứng | Không được commit (`.gitignore:49:*.log`; repo chưa từng track `.log`) → link trong báo cáo **chết trên clone sạch**. | **OPEN — đã khai báo** ở đầu mục "Bằng chứng (log)" |

### Hai rủi ro Low vừa đóng (hậu báo cáo)

1. **`wipe_db()` xoá DB không backup** — thêm `backup_db()`: sao DB vào `data/backups/quan-pre-reset-<yymmdd-HHMMSS>.db` rồi mới xoá, in đường dẫn ra stdout. Trả về `None` khi DB chưa tồn tại (không tạo file rác). `--reset` giờ **có thể hoàn tác**.
2. **Harness e2e chết trên clone mới** — `.env.e2e` bị gitignore nên người clone không có, trong khi `_load_sanitized_env` hard-`SystemExit`. Nhưng chính `main()` mới là lớp bảo đảm an toàn (blank cứng 11 token kênh + ép 4 cờ `replay`/`disconnected`/`0`/`console`), nên file này **không phải** nguồn an toàn thật. Sửa: thiếu file → cảnh báo rồi chạy tiếp; bổ sung 3 khoá độc quyền của `.env.e2e` làm mặc định (`NHIPQUAN_ALLOW_MSG_REPLAY=1`, `NHIPQUAN_ZALO_ENABLED=0`, `NHIPQUAN_PBKDF2_VONG=1000` — khớp đúng giá trị trong `.env.e2e`). Đồng thời bỏ `import demo_api` (mượn side-effect thêm `sys.path`) và dựng `sys.path` cho 7 package ngay trong script để không phụ thuộc side-effect ẩn.

**Kiểm chứng:** `scripts/selftest_post_report_fixes.py` → **7/7 PASS** (thiếu `.env.e2e` không `SystemExit`; `backup_db` tạo bản sao đúng nội dung, không xoá DB gốc, đặt đúng `data/backups/`); `IMPORT_OK app= FastAPI` chứng minh harness vẫn import được `ca_api` sau khi bỏ `demo_api`; ruff sạch trên 7 script; gate suite **145 passed**; `CLEAN_CHECK=PASS (0 · 0)`; `data/quan.db` giữ nguyên 393216 bytes. Bằng chứng: `post-report-fixes.log`.


### Hai rủi ro Medium của bản báo cáo 12:43 — đã đóng

1. **`test_threads_apify_source.py:120`** — đã **PASS** trong lượt chạy cuối. Log xác nhận `threads_apify_source.py 102 6 94%` (được đo coverage = được thực thi). Phiên song song đã sửa file này; không cần can thiệp.
2. **Cổng `localhost:18000`** — đã vượt qua như mô tả ở bảng trên (smoke chạy trong container). Playwright chạy trên `baseURL: http://localhost:3001` (web dev server host) theo `apps/web/playwright.config.ts:12`, độc lập với stack Docker.

## An toàn và dữ liệu

### Cách ly — phòng thủ nhiều lớp

1. **Network:** `compose.test.yml` đặt `internal: true` cho network mặc định → container **không có đường ra Internet**. TCP probe ra ngoài bị chặn.
2. **Env:** `env_file: !override []` — **không nạp `.env` thật** vào api/worker. Thay bằng cờ an toàn hard-code: `CA_AGENT_MODE=replay`, `NHIPQUAN_PAGE_MODE=disconnected`, `NHIPQUAN_FB_AUTO_SEND=0`, `NHIPQUAN_MSG_BACKEND=console`.
3. **Volume:** stack dùng volume riêng (`nhipquan-test_nhipquan_pg`, `_var`, `_uploads`), **không mount DB host**.
4. **Pytest container:** chạy với `--network none`, không mount workspace hay DB host.
5. **Cổng an toàn chủ động:** `scripts/e2e_safety_check.py` xác minh runtime → `SAFETY_GATE=PASS`, `agent_mode=replay`, cả 3 kênh `connected: false`.

### `.env` thật — CHƯA TỪNG BỊ GHI

Kế hoạch yêu cầu `diff .env` với `data\backups\env-pre-test-260913.bak`, nhưng **file backup đó KHÔNG TỒN TẠI** (`data\backups` chỉ có `quan-pre-phase0.db` ngày 9/6). Đã thay bằng bằng chứng **mạnh hơn** — timestamp, qua [scripts/verify_env_integrity.py](../../../scripts/verify_env_integrity.py):

```
mtime_env=2026-09-12T13:31:58Z   moc_kiem_thu=2026-09-13T12:00:00Z
ENV_KHONG_BI_GHI=OK
live_key NHIPQUAN_FB_PAGE_TOKEN: CO_GIA_TRI(len=204)
mode_flag CA_AGENT_MODE: 'live' mong_muon='live' OK
mode_flag NHIPQUAN_PAGE_MODE: 'live' mong_muon='live' OK
mode_flag NHIPQUAN_FB_AUTO_SEND: '1' mong_muon='1' OK
DAU_VET_E2E NHIPQUAN_MSG_BACKEND: khong co (dung)
DAU_VET_E2E NHIPQUAN_ALLOW_MSG_REPLAY: khong co (dung)
DAU_VET_E2E NHIPQUAN_PBKDF2_VONG: khong co (dung)
ENV_INTEGRITY=PASS
```

`.env` LastWriteTime **9/12/2026 20:31:58** — **trước** toàn bộ cửa sổ kiểm thử (log đầu tiên 9/13 13:26). Ba cờ live thật còn nguyên; **không có dấu vết nào của harness e2e bị ghi ngược** vào `.env`. Harness dùng `.env.e2e` riêng (mtime 9/13 13:36:49, 1355 bytes) đúng thiết kế.

Script chỉ in **trạng thái và độ dài**, không in giá trị, để secret không lọt vào log kiểm thử.

### **0 tương tác kênh thật**

Không một tin nhắn Facebook/Zalo/Telegram hay email SMTP nào được gửi ra ngoài trong suốt đợt kiểm thử. Bằng chứng: `SAFETY_GATE=PASS` + `agent_mode=replay` + cả 3 kênh `connected: false` + network `internal: true` + `--network none` cho pytest.

### Toàn vẹn DB host & dọn dẹp GĐ10

- **Truy nguyên rác:** clean check đầu tiên báo `eval rows: 221`. Đã truy nguyên bằng [scripts/trace_eval_residue.py](../../../scripts/trace_eval_residue.py): toàn bộ 221 dòng có `created_at` trong khoảng **2026-09-03T17:40:13Z → 18:50:44Z** — **10 ngày trước** cửa sổ V3. **Không phải do đợt kiểm thử này.** DB mtime lúc đó là 00:53 sáng, trước cả log đầu tiên (13:26).
- **Backup trước khi phá:** `wipe_db()` không tự backup nên đã tự tạo `data/backups/quan-pre-gd10-260913.db` (606208 bytes) → thao tác **có thể hoàn tác**.
- **Reset + clean check:** `database wiped cleanly` → `users_added=7 menu_upserted=8 orders_added=6` → **`CLEAN_CHECK=PASS (0 · 0)`**, `session mo coi: 0`, DB mới 393216 bytes.
- **Hạ stack Docker:** `docker compose -p nhipquan-test -f compose.yml -f compose.test.yml down -v --remove-orphans` → exit=0. Đã xoá 5 container, network `nhipquan-test_default`, và cả 3 volume. Container one-shot `nhipquan-test-pytest` cũng đã xoá.
- **Xác minh cuối:** `docker ps -a --filter name=nhipquan-test` → **rỗng**. Không còn listener trên cổng 8000/18000/13000. API host đã dừng, DB host đã restore (`RESTORE_OK`).

### Giới hạn trung thực — những gì KHÔNG được chứng nhận

- ~~**Không tạo commit, không khoá nhánh.**~~ — **ĐÃ COMMIT** 5 commit trên nhánh `feature/wip` (xem bảng dưới). **Chưa push** và **chưa khoá nhánh** — cả hai cần người dùng xác nhận.
- **Chưa kiểm thử restore từ backup** (chỉ tạo backup, chưa thử phục hồi).
- **Chưa kiểm thử đa profile RBAC bằng 3 browser profile** như kế hoạch đề xuất; RBAC được phủ bằng test API (`test_copilot_vf_scope_insufficient_role`, test 2-quản-lý) chứ không bằng browser riêng biệt.
- **Chưa probe từng hostname SMTP/Graph** — chỉ probe TCP tổng quát ra ngoài.
- **Coverage 77.05% là của `ca_api` + `ca_agents`**, không phải toàn repo (chưa đo `ca_gates`, `ca_opsengine`, `ca_playbook`, `ca_solver`, `ca_contracts`).
- **Không chứng nhận tuyệt đối 0 tương tác kênh thật cho các phiên trước** phiên này (stack mặc định từng bị gọi nhầm ở lượt chạy sớm, đã dừng và xác nhận Stopped).
- **1 test fail còn mở** — thuộc WIP ngoài phạm vi, chưa được chủ sở hữu xử lý.
- **Bằng chứng log không tái lập được từ clone** — 17 file `.log` bị gitignore, chỉ còn trên máy đã chạy.
- **Báo cáo này từng có 2 lỗi sự thật** (mã CVE bịa `CVE-2026-75604`, sai bản phân giải `15.5.24` thay vì `15.5.25`) — đã phát hiện bằng cách đối chiếu log thô và sửa ở mục Audit phụ thuộc. Đây là bằng chứng cho thấy **con số trong báo cáo cần được kiểm bằng script, không bằng trí nhớ**.

## Khuyến nghị

1. ~~**Commit ngay** 3 file src đã sửa lỗi + 21 test hồi quy, tách khỏi WIP pricing-radar.~~ — **ĐÃ LÀM**, tách sạch khỏi WIP (đã xác minh `git diff --cached --name-only` không chứa file pricing-radar nào ở từng commit).
2. **Chuyển blocker `/catchment-survey`** cho chủ sở hữu nhánh pricing-radar: thêm `CAPABILITY_REGISTRY` entry hoặc lý do `EXCLUDED_ROUTES`.
3. ~~**Thêm backup tự động vào `wipe_db()`**~~ — **ĐÃ LÀM** (xem "Hai rủi ro Low vừa đóng").
4. **Giữ lại harness** làm bộ e2e an toàn tái sử dụng: `.env.e2e`, `scripts/e2e_safe_api.py`, `scripts/e2e_safety_check.py`, `scripts/verify_env_integrity.py`, `scripts/clean_check_db.py`, `scripts/test_docker_safety.py`, `infra/docker/Dockerfile.test`, `infra/docker/compose.test.yml`. Sàn coverage `--cov-fail-under=75` đã nướng sẵn trong `Dockerfile.test` để chặn tụt hạng. Harness giờ **tự đủ khi thiếu `.env.e2e`** nên chạy được trên clone mới.
5. **Lên kế hoạch nâng `next@16`** trong một đợt riêng có kiểm thử đầy đủ, để xoá nốt postcss high.
6. **Điều tra port publishing** của `compose.test.yml` nếu muốn chạy e2e từ host vào stack Docker.
7. **Cân nhắc commit `.env.e2e`** (hoặc một `.env.e2e.example`) — file này chứa **0 secret** (mọi token đều rỗng, chỉ 7 cờ chế độ), nhưng `.gitignore:80:.env*` đang chặn nó. Hiện harness đã có mặc định cứng nên không bắt buộc, nhưng commit sẽ giúp người mới thấy rõ ý đồ an toàn.

## Commit đã tạo (nhánh `feature/wip`, **chưa push**)

| Commit | Message | Phạm vi |
|---|---|---|
| `6e4da0d` | `fix(api): chan 3 loi gay 500 va DoS phat hien khi kiem thu toan dien V3` | 3 file src — lỗi #1 `sprint3.py`, #2 `sprint45.py`, #3 `channels.py` (77+/20−) |
| `7920c47` | `test(api): them 21 test hoi quy cho 3 loi va ma tran edge case GD9` | 5 file test (192+) |
| `5871d01` | `fix(web): nang next len 15.5.25 de va 2 loi RCE nghiem trong` | `apps/web/package.json`, `package-lock.json` (211+/171−) |
| `12a7fbc` | `test(infra): harness e2e an toan + san coverage 75% + cong cu chung minh GĐ10` | 15 file — harness, công cụ kiểm chứng, `.gitignore` (817+) |
| *(commit này)* | `docs(ops): bao cao kiem thu toan dien V3 + backup DB bang chung GĐ10` | `plans/260913-1151-kiem-thu-toan-dien-v3/`, `data/backups/quan-pre-gd10-260913.db` |

**Cách tách khỏi WIP song song:** mỗi commit đều `git add` theo **đường dẫn cụ thể**, không dùng `git add -A`; sau mỗi lần stage đều kiểm `git diff --cached --name-only | findstr pricing catchment main.py threads_apify mail_log ag_pricing camoufox gmaps .env` → **rỗng**. Trước khi stage còn chạy `scripts/scan_secrets_before_commit.py` (quét tolerant cả log UTF-16) → 0 secret trên 84 file; nghi vấn duy nhất `infra/docker/.env:7` đã bị `.gitignore:80:.env*` chặn nên không thể lọt vào commit.

**Vì sao commit `.db` binary:** `quan-pre-gd10-260913.db` là **bằng chứng GĐ10** được báo cáo trích dẫn. Đã kiểm riêng tư bằng `scripts/inspect_backup_privacy.py` trước khi commit: 31 bảng, `fb_review_queue` 221 dòng **toàn bộ** `source='messenger'` + `external_thread_id LIKE 'fb_eval%'` (dữ liệu mô phỏng), `fb_processed_events` 0 dòng, `users` 23 người đều là tên fixture → **không có dữ liệu khách hàng thật**. Tiền lệ: repo đã track `data/backups/quan-pre-phase0.db`.

## Bằng chứng (log)

> **⚠️ Giới hạn về khả năng kiểm chứng:** 17 file `.log` dưới đây **KHÔNG được commit** — `.gitignore:49:*.log` chặn toàn bộ, và repo chưa từng track file `.log` nào (`git ls-files '*.log'` → 0 kết quả; `plans/` chỉ chứa `.md`). Các link chỉ mở được **trên máy đã chạy đợt kiểm thử này**, tức `D:\Crew-Operations\plans\260913-1151-kiem-thu-toan-dien-v3\`. Người review từ clone sạch sẽ thấy link chết.
>
> Con số trong cột "Nội dung" được chép nguyên văn từ log và **đã đối chiếu lại bằng script** (`read_evidence_logs.py`, `verify_next_upgrade.py`) chứ không dựa vào trí nhớ — chính nhờ vậy mới phát hiện 2 lỗi sự thật ở mục Audit phụ thuộc. Nếu cần bằng chứng tái lập được, phải chạy lại các lệnh trong `plan.md` thay vì tin vào bảng này.

| Thời điểm | File | Nội dung |
|---|---|---|
| 13:26:41 | [smoke-docker.log](smoke-docker.log) | Backend XANH — 8 mục nghiệp vụ |
| 13:29:35 | [stage3-8-docker.log](stage3-8-docker.log) | GĐ3–8: fixture, solver, seed-ops, eval, metrics |
| 13:40:14 | [e2e-safety-gate.log](e2e-safety-gate.log) | `SAFETY_GATE=PASS` |
| 13:52:19 | [playwright-phieu-retry.log](playwright-phieu-retry.log) | Lượt retry — phát hiện lỗi #1 |
| 13:58:37 | [playwright-phieu-fixed.log](playwright-phieu-fixed.log) | Sau fix |
| 13:59:50 | [playwright-docker.log](playwright-docker.log) | 19 passed (37.1s) |
| 14:04:37 | [pytest-docker.log](pytest-docker.log) | 967 passed, chưa đo coverage |
| 14:07:14 | [audit-deps.log](audit-deps.log) | Snapshot audit **trước** fix (3 vulns: 2 high, 1 critical) |
| 14:20:23 | [playwright-next-bump.log](playwright-next-bump.log) | **19 passed (38.8s)** sau nâng next lên 15.5.25 |
| 14:27:33 | [pytest-coverage.log](pytest-coverage.log) | 967 passed, **77.05%** — baseline xanh |
| 14:46:07 | [pytest-edge-cases.log](pytest-edge-cases.log) | **159 passed in 41.29s** (subset edge case trên host) |
| 14:46:45 | [static-after-edge.log](static-after-edge.log) | ruff 12 / mypy 3 — **trước** khi sửa mypy |
| 14:49:21 | [static-my-changes.log](static-my-changes.log) | ruff 8 (chỉ file test, pre-existing) / **mypy Success 122 files** |
| 14:57:03 | [pytest-final-edge.log](pytest-final-edge.log) | **1 failed, 1002 passed in 174.13s · 77.05%** |
| 15:11:02 | [gd10-cleanup.log](gd10-cleanup.log) | backup + validate + seed `--reset` + **CLEAN_CHECK=PASS (0 · 0)** |
| 15:22:48 | [env-integrity.log](env-integrity.log) | **ENV_INTEGRITY=PASS** + clean check + truy nguyên 221 dòng + ruff 3 script mới `All checks passed!` + xác nhận stack Docker đã hạ hết |
| 15:44 | [post-report-fixes.log](post-report-fixes.log) | Hậu báo cáo: DB thật không bị đụng (393216) · ruff sạch 7 script · gate suite **145 passed** · **CLEAN_CHECK=PASS (0 · 0)** |

**File thay đổi trong đợt kiểm thử:**

| File | Loại |
|---|---|
| `apps/api/src/ca_api/interfaces/http/sprint3.py` | **FIX lỗi #1** |
| `apps/api/src/ca_api/interfaces/http/sprint45.py` | **FIX lỗi #2** |
| `apps/api/src/ca_api/interfaces/http/channels.py` | **FIX lỗi #3 (DoS)** |
| `apps/api/tests/unit/test_sprint3.py`, `test_sprint45.py`, `test_chat_api.py`, `test_copilot_api.py`, `test_fb_moderation.py` | 21 test hồi quy mới |
| `apps/web/package.json`, `package-lock.json` | next khai báo `^15.5.24` → phân giải **15.5.25** (xoá 2 Critical RCE) |
| `scripts/verify_env_integrity.py`, `scripts/clean_check_db.py`, `scripts/trace_eval_residue.py` | **MỚI** — công cụ chứng minh GĐ10 |
| `scripts/seed_professional_fixture.py` | Gộp import `datetime` + **thêm `backup_db()`** (`--reset` tự sao lưu trước khi xoá) |
| `scripts/e2e_safe_api.py` | **MỚI** — harness e2e an toàn; giờ tự đủ khi thiếu `.env.e2e`, tự dựng `sys.path` |
| `scripts/selftest_post_report_fixes.py`, `scripts/inspect_env_structure.py` | **MỚI** — kiểm chứng 2 fix hậu báo cáo (7/7 PASS) và soi cấu trúc env không lộ secret |
| `scripts/inspect_backup_privacy.py`, `scripts/scan_secrets_before_commit.py` | **MỚI** — kiểm riêng tư backup DB trước khi commit, và quét secret (tolerant UTF-16) trước khi stage |
| `scripts/read_evidence_logs.py`, `scripts/verify_next_upgrade.py` | **MỚI** — đọc log trộn encoding và đối chiếu git object; chính 2 script này phát hiện 2 lỗi sự thật của báo cáo |
| `infra/docker/Dockerfile.test` | **MỚI** — sàn coverage 75% |
| `infra/docker/compose.test.yml`, `.env.e2e`, `scripts/e2e_safe_api.py`, `scripts/e2e_safety_check.py`, `scripts/test_docker_safety.py` | **MỚI** — harness e2e an toàn |