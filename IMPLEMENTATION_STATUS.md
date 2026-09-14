# IMPLEMENTATION_STATUS — Khảo sát Giá & Định vị Thị trường F&B theo Bán kính

> **Plan nguồn:** [plans/260913-1455-khao-sat-gia-fb-online-dinein-substitutes/plan.md](plans/260913-1455-khao-sat-gia-fb-online-dinein-substitutes/plan.md) (v2.1)
> **Bản gốc v1.0:** [plan-v1.0.md](plans/260913-1455-khao-sat-gia-fb-online-dinein-substitutes/plan-v1.0.md)
> **Nhánh:** `feature/wip` · **Vùng sở hữu:** C (`ag_pricing`, `sources`) · B (`ca_api`) · D (Web UI)

File này là bảng trạng thái sống. Cập nhật sau mỗi phase, không cập nhật giữa chừng.

---

## Tổng quan phase (plan mục 10)

| Phase | Nội dung | Trạng thái | Test | Ghi chú |
|---|---|---|---|---|
| **1 — Contracts & Domain Logic** | Pydantic contracts (mục 3), Math Layer tất định (mục 4), `substitute_taxonomy` (mục 3.4) | ✅ Code complete — **chờ chủ dự án duyệt tham số** | ✅ 1288 pass | ADR-003 gate đã thoả: contract + test tồn tại trước logic nghiệp vụ |
| **2 — Data Sources & Vision OCR** | ShopeeFood network interception, Google Maps menu, Gemini Vision OCR guardrail (mục 2.2) | ✅ Code complete | ✅ 60 pass | Dish normalizer, ShopeeFood v2 parser, Vision OCR rewrite (Qwen/GROQ), 2-step GMaps photo fetch, SOURCE_BLOCKED handling |
| **3 — Orchestrator & Backend API** | Async job state machine (mục 2.4), endpoint `ca_api` (mục 5), rate limit, idempotency | ✅ Code complete | ✅ 69 pass | `POST /catchment-survey` → `202 Accepted` + `job_id`; State Machine 8 trạng thái; Gate PR13 đã đóng (6 capability entry) |
| **4 — UI Dashboard** | Nhập liệu, tiến trình, review thủ công, dashboard (mục 6) | ✅ Code complete | ✅ `tsc` + `next build` + **22 Playwright pass** | `/khao-sat-gia` 4 màn hình (nhập → chạy → review → kết quả); route 9.41 kB; Playwright spec `khao-sat-gia-review.spec.ts` phủ luồng `NEEDS_REVIEW` (API stub) |
| **5 — Kiểm thử toàn diện & Vận hành thí điểm** | import-linter, canary daily, cost dashboard, thí điểm 1 khu vực | ✅ Code complete | ✅ 500 pass (16 suite) | Math-Layer purity gate, cost dashboard + alerting, canary selector chạy thật, `make canary`. **Chưa chạy thí điểm 2 tuần** (cần chủ dự án bật) |

**Toàn nhánh:** `1587 passed` (full suite, `CA_AGENT_MODE=replay`, **KHÔNG cần `--ignore`** — 3 test treo mạng đã được làm hermetic) · `ruff check apps/api/src packages scripts` → **All checks passed!** · `mypy` trên toàn bộ file của tính năng này → **Success: no issues found in 37 source files**.

---

## Blocker đang mở

| Blocker | Nguồn | Chủ sở hữu | Hướng xử lý |
|---|---|---|---|
| ~~Gate PR13 chặn route `/catchment-survey` — chưa có `deep_link` trong `CAPABILITY_REGISTRY`, chưa có lý do trong `EXCLUDED_ROUTES`~~ | [plans/260913-1151-kiem-thu-toan-dien-v3/bao-cao.md](plans/260913-1151-kiem-thu-toan-dien-v3/bao-cao.md) dòng 93–102 | Nhánh này (plan mục 13.4) | ✅ **ĐÃ XONG Phase 3** — 6 entry `CAPABILITY_REGISTRY` cùng `deep_link` `/khao-sat-gia`, không cần `EXCLUDED_ROUTES`. `test_capability_coverage.py` **4 passed** |
| ~~`gmaps_menu_source.fetch_gmaps_menu_images_page` hard-code `rating=4.5, review_count=100` cho mọi place → quán giả mạo này luôn lọt Dual-Gate~~ | [packages/agents/src/ca_agents/sources/gmaps_menu_source.py](packages/agents/src/ca_agents/sources/gmaps_menu_source.py) | Nhánh này | ✅ **ĐÃ XONG Phase 2** — đọc rating/review thật từ DOM, 2-step photo fetch (menu tab → all_photos fallback), SOURCE_BLOCKED handling |
| ~~`numpy` / `hypothesis` chưa khai báo trong `packages/agents/pyproject.toml`~~ | Plan mục 4.1 + 4.6 | Nhánh này | ✅ **ĐÃ XONG Phase 1** — `numpy>=2.0`, `pyyaml>=6.0` + `dev = [hypothesis>=6.100]`; đồng bộ `Makefile` và `infra/docker/Dockerfile.test` |
| ~~3 test có sẵn của repo gọi mạng thật/treo khi offline: `packages/agents/tests/test_ag_trend.py`, `apps/api/tests/unit/test_trends_api.py`, `packages/solver/tests/test_fairness_property.py`~~ | Phát hiện khi chạy regression Phase 1 (không do nhánh này gây ra) | Nhánh này | ✅ **ĐÃ XONG** — (1) `threads_direct_source.py`: lazy-init `ssl.create_default_context()` (treo ở import khi load certs trên Windows); (2) `test_ag_trend.py` + `test_trends_api.py`: mock 5 scraper nội bộ thay vì gọi mạng thật (đúng plan mục 1.4, ADR-002); (3) `test_fairness_property.py`: hoá ra KHÔNG treo — chỉ là solver chậm (~9s), pass bình thường. **Full suite `1587 passed` KHÔNG cần `--ignore`** |
| **Canary đang báo ĐỎ cho ShopeeFood** — trang thật trả `captcha` + `403` khi canary chạy | Bằng chứng canary (xem nhật ký Phase 5) | Nhánh này + vận hành | Đây đúng là tín hiệu cảnh báo sớm mà plan mục 7 yêu cầu, KHÔNG phải lỗi repo. Nguồn ShopeeFood đang bị chặn → phải đi qua SerpApi/proxy hoặc tạm dừng thu thập delivery. **Không tự tắt alert** (ADR-008) |
| ~~Chưa có Playwright spec cho luồng review `NEEDS_REVIEW` trên `/khao-sat-gia`~~ | Plan mục 10 — tiêu chí nghiệm thu Phase 4: *"Người dùng thử nghiệm hoàn thành được luồng review một mục `NEEDS_REVIEW` mà không cần hướng dẫn"* | Nhánh này (D) | ✅ **ĐÃ XONG** — `apps/web/e2e/khao-sat-gia-review.spec.ts` (303 dòng, 3 test) stub API theo convention `fb-inbox.spec.ts`, chứng minh ADR-008 (điểm dừng thật, không auto-approve). **22/22 Playwright pass** với Python 3.12 trên PATH |
| Chưa chạy thí điểm 2 tuần trên 1 khu vực thật | Plan mục 10 — tiêu chí nghiệm thu Phase 5 | Chủ dự án | Cần bật cờ + cấp ngân sách Vision/proxy. Code đã sẵn sàng |

---

## Quyết định nghiệp vụ chờ chủ dự án duyệt (plan mục 1.5)

Tất cả đang chạy ở dạng **default cấu hình được** trong
[config/khao-sat-gia-tham-so.yaml](config/khao-sat-gia-tham-so.yaml), mỗi khóa gắn nhãn
`# BUSINESS_DECISION_PENDING_REVIEW`. **Chưa có khóa nào được chốt thay chủ dự án.**

| Tham số | Giá trị tạm | Plan | Trạng thái |
|---|---|---|---|
| `target_margin_ratio` | `0.30` | 1.5.1 / 4.4.2 | ⏳ Chờ duyệt |
| Công thức Sweet Spot (`P40` / `min(AMBI, P60)`) | như plan | 4.4 | ⏳ Chờ duyệt |
| Bội số làm tròn giá (beverage `1.000đ`, món chính `5.000đ`) | như plan | 1.5.7 / 4.4.1 | ⏳ Chờ duyệt |
| Heuristic `positioning_tier` (street_food / casual_dine_in / branded_chain) | chưa code hoá | 1.5.3 | ⏳ Chờ duyệt |
| `radius_profile` theo mật độ đô thị (dine_in `1.0km`, delivery `5.0km`) | như plan | 1.1 / 3.1 | ⏳ Chờ duyệt |
| Trọng số AMBI `0.5 / 0.5` | như plan v1.0 | 1.3 / 4.3 | ⏳ Chờ duyệt |
| Ngưỡng `low_confidence` (`review_count < 10` khi qua Gate 1 nhờ badge) | như plan | 4.2 | ⏳ Chờ duyệt |
| Hệ số giảm trọng số cho bản ghi `low_confidence` | `0.5` | **không có trong plan** | ⏳ Chờ duyệt — plan chỉ nói "trọng số giảm", không cho con số |
| Ngưỡng `min_wr` Gate 2 | `4.0` | 1.4 / 4.2 | ⏳ Chờ duyệt |
| Ngưỡng `insufficient_data` | `sample_size < 5` | 4.1 / 5.3 | ⏳ Chờ duyệt |

---

## Nhật ký triển khai

### Phase 1 — Contracts & Domain Logic

**Code complete, test xanh.** Phạm vi đã giao:

- [x] `packages/contracts/src/ca_contracts/catchment_survey_v2.py` — contracts v2.1 (plan mục 3.1–3.4)
- [x] `packages/contracts/schema/CatchmentPriceSurveyV2.json` — JSON Schema export (`scripts/export_contracts.py`, 25 schemas + ts types)
- [x] `packages/contracts/tests/test_catchment_survey_v2_contracts.py` — test validate contract
- [x] `config/khao-sat-gia-tham-so.yaml` — tham số nghiệp vụ, không hard-code (14 nhãn `BUSINESS_DECISION_PENDING_REVIEW`)
- [x] `config/substitute-taxonomy.yaml` — taxonomy versioned (plan mục 3.4), 4 nhóm JTBD active + 2 nhóm `entries_cho_duyet` KHÔNG được nạp
- [x] `packages/agents/src/ca_agents/ag_pricing/math_layer.py` — §4.1–§4.5, thuần, không LLM
- [x] `packages/agents/src/ca_agents/ag_pricing/pricing_config.py` — loader YAML tất định, fail-fast, frozen dataclass
- [x] `packages/agents/src/ca_agents/ag_pricing/substitute_taxonomy.py` — thay `_MEAL_GROUPS` hard-code
- [x] `packages/agents/tests/test_pricing_math_layer.py` — unit test phủ nhánh
- [x] `packages/agents/tests/test_pricing_math_properties.py` — `hypothesis` cho bất biến §4.6
- [x] `packages/agents/tests/test_pricing_config.py` — test loader + nhãn chờ duyệt
- [x] `packages/agents/tests/test_substitute_taxonomy.py` — test loader config
- [x] Báo cáo Phase 1 theo mẫu
- [ ] **Chủ dự án duyệt các tham số `[ĐỀ XUẤT MỚI]`** — đây là một phần của AC Phase 1, agent không được tự chốt (plan mục 1.5)

#### Bằng chứng test (chạy trên Python 3.12.10, `CA_AGENT_MODE=replay`, không network)

| Phạm vi | Kết quả |
|---|---|
| 4 file test mới của Phase 1 | **241 passed** trong 9.32s |
| `packages/agents/tests` + `packages/contracts/tests` (trừ `test_ag_trend.py`) | **712 passed** trong 17.64s |
| `apps/api/tests` (trừ `test_trends_api.py`) | **414 passed** trong 92.70s |
| `packages/gates` | **50 passed** trong 0.62s |
| `packages/solver` + `opsengine` + `playbook` (trừ `test_fairness_property.py`) | **112 passed** trong 1.94s |
| **Tổng** | **1288 passed, 0 failed** |
| `ruff check` trên toàn bộ file mới/sửa | **All checks passed** |
| `mypy --strict` trên `ag_pricing` + `catchment_survey_v2.py` | Chỉ còn 1 lỗi `no-redef` cho pattern `StrEnum` fallback — **giống hệt** lỗi có sẵn trong `ca_contracts/__init__.py` (quy ước repo, Python 3.10 fallback); CI mypy đang để `|| true` |

Bất biến §4.6 được chứng minh bằng `hypothesis` (200–400 mẫu/test, không phải vài ca cố định):
$P_{25} \le P_{50} \le P_{75}$; $\text{WR} \in [\min(R,4.2), \max(R,4.2)]$;
AMBI nằm trong khoảng trung vị Core/Substitutes;
`sweet_spot_*_display` lệch `*_raw` không quá $\pm \text{step}/2$.

#### Giả định phát sinh ngoài plan (đã ghi trong docstring mã nguồn)

1. **`compute_sweet_spot` KHÔNG kẹp khoảng bị lộn.** Khi AMBI < P40, công thức plan cho ra
   `high_raw < low_raw`. Kẹp sẽ phá bất biến `high_raw = min(AMBI, P60)` của plan mục 4.4,
   nên hàm giữ nguyên kết quả công thức và chỉ đặt cờ `inverted=True` để caller hiển thị cảnh báo.
2. **`competitive_intensity` kẹp `radius_km` về >= 0** và trả `0.0` khi diện tích không phải
   số dương hữu hạn usable. Plan viết `area_km2 = pi * radius_km**2` nên bán kính âm vẫn cho
   diện tích dương (bịa mật độ), và bán kính cỡ subnormal làm `count/area` tràn thành `inf`
   (không serialize JSON được) — `hypothesis` đã bắt được ca này.
3. `low_confidence_weight_factor = 0.5` — plan chỉ nói "trọng số giảm", không cho con số.
   Để ở config, gắn nhãn `KHÔNG có trong plan`, chờ duyệt.
4. Contract bổ sung các trường plan liệt kê thiếu: `StoreRecord.has_favorite_badge` (§4.2 đọc nhưng §3.2 không khai báo),
   `PercentileStats.insufficient_data` (§4.1 yêu cầu, §3.3 bỏ sót), `CatchmentSurveyResponse.error_code` (§5.3 cần).
   Cùng `SurveyJobStatus` / `SURVEY_JOB_TRANSITIONS` / `SurveyErrorCode` / `SubstituteTaxonomy` không có trong listing plan.
5. `MenuSnapshotV2` được đổi tên để tránh va chạm v1.0; `scripts/export_contracts.py` nhận thêm
   `EXTRA_SCHEMAS` (side-channel) để không phá assert 24 tên trong `packages/contracts/tests/test_contracts.py`.

**Ràng buộc đang tuân thủ:**

- ADR-002 — mọi con số nghiệp vụ nằm trong hàm Python thuần, không LLM, không network, offline, tất định.
- ADR-003 — contract Pydantic + unit test validate **phải tồn tại trước** khi viết logic nghiệp vụ.
- ADR-008 — không có đường dẫn nào tự ghi đè giá lên POS/ShopeeFood merchant; `NEEDS_REVIEW` là điểm dừng thật, không auto-approve.
- Plan mục 1.4 — test suite không gọi mạng thật; fixture khai báo rõ là dữ liệu mô phỏng.
- Plan mục 1.5 — không tự chốt tham số `[ĐỀ XUẤT MỚI]`; để ở config riêng + nhãn `BUSINESS_DECISION_PENDING_REVIEW`.

**Tương thích ngược (plan mục 3.5):** module v1.0
[packages/contracts/src/ca_contracts/catchment_survey.py](packages/contracts/src/ca_contracts/catchment_survey.py)
được **giữ nguyên không sửa**. Contracts v2.1 nằm ở module riêng để hai phiên bản chạy song song
tối thiểu 1 chu kỳ release; 5 file test WIP hiện có tiếp tục pass.

### Phase 2 — Data Sources & Vision OCR

**Code complete, test xanh.** Phạm vi đã giao:

- [x] `packages/contracts/src/ca_contracts/catchment_survey_v2.py` — mở rộng `MenuSnapshotV2` với `photo_source` và `photo_taken_recency_days` (plan mục 3.2)
- [x] `packages/agents/src/ca_agents/ag_pricing/dish_name_normalizer.py` — chuẩn hóa tên món ăn Việt (bỏ dấu, lowercase, loại cooking method/filler words, Jaccard similarity)
- [x] `packages/agents/tests/test_dish_name_normalizer.py` — 27 tests (normalize, batch, similarity)
- [x] `packages/agents/src/ca_agents/sources/shopeefood_v2_parser.py` — parser v2 tách `original_price_vnd` vs `effective_price_vnd`, detect combo, fallback từ discount_pct
- [x] `packages/agents/tests/test_shopeefood_v2_parser.py` — 14 tests (price pair extraction, discount fallback, combo detection, fixture validation)
- [x] `packages/agents/tests/fixtures/shopeefood/shopeefood_sample_v2.json` — fixture 5 quán với các kịch bản giá (original+sale, discount%, single price, combo)
- [x] `packages/agents/src/ca_agents/ag_pricing/vision_menu_extractor.py` — rewrite dùng Qwen/GROQ structured output, retry logic (max 2), NEEDS_REVIEW queue cho ảnh mờ
- [x] `packages/agents/tests/test_vision_menu_extractor.py` — 19 tests (price validation, JSON parsing, retry logic, NEEDS_REVIEW queue, backward-compat wrapper)
- [x] `packages/agents/src/ca_agents/sources/gmaps_menu_source.py` — 2-step photo fetch (menu tab → all_photos fallback), fix hard-coded rating/review_count, SOURCE_BLOCKED handling với exponential backoff
- [x] `packages/agents/tests/fixtures/gmaps/gmaps_places_sample.json` — fixture 5 places với menu_tab photos và all_photos scenarios

#### Bằng chứng test (chạy trên Python 3.10.10, `CA_AGENT_MODE=replay`, không network)

| Phạm vi | Kết quả |
|---|---|
| `test_dish_name_normalizer.py` | **27 passed** |
| `test_shopeefood_v2_parser.py` | **14 passed** |
| `test_vision_menu_extractor.py` | **19 passed** |
| **Tổng Phase 2** | **60 passed, 0 failed** |

#### Thiết kế kỹ thuật

**1. Dish Name Normalizer (ADR-002 compliant)**
- Pure function, không LLM, không network
- Pipeline: lowercase → remove diacritics → tokenize → filter cooking methods/filler words/stopwords → sort alphabetically
- Jaccard similarity cho matching món ăn (threshold 0.7)
- Xử lý đúng tiếng Việt: "Phở bò tái" → "bo pho tai", "Cà phê sữa đá" → "ca phe da sua"

**2. ShopeeFood v2 Parser (plan mục 1.5.2)**
- Tách rõ `original_price_vnd` (giá gốc, cơ sở tính AMBI) vs `effective_price_vnd` (giá sale, chỉ tham khảo)
- Fallback logic: nếu chỉ có `discount_pct` → suy ngược `original = effective / (1 - discount_pct/100)`
- Detect combo từ field `is_combo` hoặc tên chứa "combo"/"set"
- Log warning khi không tách được giá (có tín hiệu khuyến mãi nhưng giá trùng)

**3. Vision Menu Extractor (Qwen/GROQ structured output)**
- Rewrite từ Gemini-only sang multi-provider (Qwen/GROQ → Gemini fallback)
- Structured output: response_schema = `list[MenuItemPrice]`
- Retry logic: max 2 retries khi JSON parse fail hoặc schema validation fail
- NEEDS_REVIEW queue: món OCR không đọc được giá (ảnh mờ) → `confidence="low"`, đẩy vào `needs_review` list
- Backward-compat wrapper `extract_dishes_from_menu_image()` cho code cũ

**4. Google Maps 2-Step Photo Fetch**
- Step 1: Menu tab → ảnh menu trực tiếp (`photo_source="menu_tab"`)
- Step 2: All Photos fallback → lọc ảnh có menu board (`photo_source="all_photos_filtered"`)
- Fix hard-coded `rating=4.5, review_count=100` → đọc từ DOM thật
- SOURCE_BLOCKED handling: exponential backoff + jitter (max 3 retries), track block rate per source

**5. Fixture-Based Testing (ADR-002)**
- Tất cả tests dùng fixture JSON, không gọi mạng thật
- ShopeeFood fixture: 5 quán với các kịch bản giá phức tạp
- Google Maps fixture: 5 places với menu_tab và all_photos scenarios
- Vision tests mock LLM response, không gọi API thật

#### Giả định phát sinh ngoài plan

1. **`original_price_vnd` nullable (`int | None`)** — cho phép OCR model refuse đoán giá trên ảnh mờ thay vì bịa số. Plan không nói rõ, nhưng phù hợp ADR-008 (con người quyết định giá, không auto-fill).
2. **Dish normalizer loại "kem" khỏi stopwords** — "kem" vừa là "ice cream" (món thật) vừa là filler word. Ưu tiên giữ món thật, chấp nhận false positive.
3. **Vision retry logic retry cả "not_a_menu"** — ban đầu chỉ retry JSON parse fail, nhưng model có thể hallucinate format nên retry cả trường hợp `is_valid_menu=false`.
4. **SOURCE_BLOCKED exponential backoff** — plan không yêu cầu, nhưng cần thiết để tránh bị block vĩnh viễn khi scrape Google Maps.

**Ràng buộc đang tuân thủ:**

- ADR-002 — dish normalizer và ShopeeFood parser là pure functions, không LLM, không network
- ADR-003 — contracts v2.1 mở rộng trước, tests viết trước khi implement logic
- ADR-008 — NEEDS_REVIEW queue là điểm dừng thật, không auto-approve giá OCR
- Plan mục 1.4 — tất cả tests dùng fixture, không gọi mạng thật
- Plan mục 1.5.2 — tách rõ original vs effective price ngay tại tầng parse

**Tương thích ngược:** module v1.0 `catchment_survey.py` và `DishItem` vẫn được giữ nguyên. Vision extractor có backward-compat wrapper `extract_dishes_from_menu_image()` trả `list[MenuItemPrice]` thay vì `list[DishItem]` — code cũ cần migrate sang `extract_menu_from_image()` để dùng v2 contracts đầy đủ.

---

### Phase 3 — Orchestrator & Backend API

**Code complete, test xanh.** Phạm vi đã giao:

- [x] `packages/agents/src/ca_agents/ag_pricing/job_manager.py` — `JobStore` + State Machine. `SURVEY_JOB_TRANSITIONS` khai báo tường minh mọi cạnh hợp lệ: `QUEUED→{SCRAPING_ONLINE,FAILED}` · `SCRAPING_ONLINE→{SCRAPING_DINEIN,FAILED}` · `SCRAPING_DINEIN→{OCR_PROCESSING,FAILED}` · `OCR_PROCESSING→{AGGREGATING,NEEDS_REVIEW,FAILED}` · `NEEDS_REVIEW→{AGGREGATING,FAILED}` · `AGGREGATING→{COMPLETED,FAILED}` · `COMPLETED→{}` · `FAILED→{}`. Chuyển trạng thái ngoài bảng → raise, không âm thầm bỏ qua.
- [x] `packages/agents/src/ca_agents/ag_pricing/orchestrator_v2.py` — điều phối toàn luồng: tải danh sách quán (online → dine-in), tải ảnh menu, Vision OCR, tổng hợp, đẩy `NEEDS_REVIEW`, `resume_after_review` sau khi người dùng xác nhận giá.
- [x] `apps/api/src/ca_api/interfaces/http/pricing_radar.py` — `POST /catchment-survey` trả **`202 Accepted` + `job_id`** (không còn đồng bộ); `GET /catchment-survey/{job_id}` (tiến trình); `GET /catchment-survey/{job_id}/result` (`409` nếu chưa `COMPLETED`); `POST /catchment-survey/{job_id}/review`; `GET /catchment-survey-metrics`; `GET /catchment-survey-dashboard`; `GET /serpapi/quota`.
- [x] `packages/contracts/src/ca_contracts/__init__.py` — `CatchmentSurveyParams` (contract cho Copilot) + 3 intent mới `RUN_CATCHMENT_SURVEY`, `GET_SERPAPI_QUOTA`, `GET_SURVEY_RESULT`.
- [x] **Gate PR13 đã đóng** — 6 entry `CAPABILITY_REGISTRY` (`RUN_CATCHMENT_SURVEY` R2_CONFIRM · `GET_SURVEY_STATUS`/`GET_SURVEY_RESULT`/`GET_SURVEY_METRICS`/`GET_SERPAPI_QUOTA` R0_READ · `REVIEW_SURVEY_ITEMS` R2_CONFIRM), tất cả `deep_link = "/khao-sat-gia"`. Không cần `EXCLUDED_ROUTES`.
- [x] Idempotency: `Idempotency-Key` bắt buộc, tối đa 200 ký tự (dài hơn → `400`), khoá theo key để không tạo job trùng.
- [x] Error taxonomy (plan mục 5.3) map sang HTTP: `400 INVALID_RADIUS` · `409 SCHEMA_VERSION_MISMATCH` · `422 INSUFFICIENT_MARKET_DATA` · `429 RATE_LIMITED` · `502 SOURCE_BLOCKED` · `503 VISION_QUOTA_EXCEEDED`.

#### Bằng chứng test

| Phạm vi | Kết quả |
|---|---|
| `test_pricing_radar_api.py` | **24 passed** |
| `test_pricing_orchestrator_v2.py` | **20 passed** |
| `test_pricing_job_manager.py` | **25 passed** |
| `test_capability_coverage.py` (Gate PR13) | **4 passed** |
| **Tổng Phase 3** | **73 passed, 0 failed** |

**Ràng buộc đang tuân thủ:** ADR-003 (contract trước, endpoint sau) · ADR-008 (`NEEDS_REVIEW` là điểm dừng thật — endpoint review chỉ ghi nhận quyết định của người, không có nhánh auto-approve) · plan mục 1.4 (test không gọi mạng thật, dùng fixture + monkeypatch).

---

### Phase 4 — UI Dashboard

**Code complete, build xanh.** Phạm vi đã giao:

- [x] `apps/web/src/app/khao-sat-gia/page.tsx` (~700 dòng) — 4 màn hình `ManHinh = "nhap" | "chay" | "review" | "ket-qua"`. Poll tiến trình mỗi `POLL_MS = 3000`.
- [x] `apps/web/src/ui/khao-sat-gia/bieu-do-gia.tsx` — `"use client"`; `PhanVi`/`HangPhanVi`/`PhanViBars` (phân vị P25–P75 dạng thanh), `GaugeInput`/`GiaGauge` (con trượt giá đề xuất).
- [x] `apps/web/src/lib/api.ts` — `apiSendHeaders<T>(path, body, extra, method)` để gửi `Idempotency-Key`.
- [x] `apps/web/src/lib/session.ts` — `/khao-sat-gia` nằm trong `MANAGER_ONLY`; `AppShell.tsx` (`MORE`) và `them/page.tsx` (`LINKS`) đã nối menu.
- [x] `present.ts` — nhãn tiếng Việt cho mã trạng thái/mã lỗi (dòng 582–666).
- [x] `RADIUS_PRESETS` theo mật độ: `dense_urban` 1/3 km · `suburban` 2/7 km · `rural` 3/10 km. Form mặc định: toạ độ `10.7769, 106.7009`, món lõi "cơm tấm", `hybrid`, 1/5 km, `minReviewCount 50`, `minRating 4.2`.
- [x] Idempotency key sinh phía client: `` `ks-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,10)}` ``.

#### Bằng chứng build

| Kiểm tra | Kết quả |
|---|---|
| `npx tsc --noEmit` | **pass** (không lỗi) |
| `npx next build` | **✓ Compiled successfully** — `├ ○ /khao-sat-gia  9.41 kB  168 kB` |

#### Ràng buộc giao diện (`docs/design-guidelines.md` v3 "Premium Ops")

- Register ops-utilitarian, T0 160ms, dùng chung design kit.
- **Không lộ mã nội bộ ra UI**: contract JSON, mã gate VF, mã chạy chỉ nằm trong `TechnicalDrawer` (mặc định thu gọn). Mọi lỗi đi qua `viError()`. Không hiện HTTP code, tên biến, hay JSON lỗi.
- Bán kính token: `--nq-radius` 6px (input/select) · `--nq-radius-bubble` 18px (card/alert) · `--nq-radius-pill` 999px (button/chip).
- Icon SVG inline, **không dùng emoji làm icon**.
- `survey_captured_at` (contract `min_length 1`) **bắt buộc hiển thị** — người dùng phải biết dữ liệu chụp lúc nào.
- Câu chốt vùng Sweet Spot viết **không nhị phân** (không "chắc chắn đúng"), đúng tinh thần ADR-008: đây là đề xuất, con người quyết định.

#### Playwright E2E — `khao-sat-gia-review.spec.ts`

Đã đóng blocker cuối cùng của Phase 4: spec 303 dòng, 3 test, phủ toàn bộ luồng `NEEDS_REVIEW` trên `/khao-sat-gia`.

- **Vì sao phải stub API:** `NEEDS_REVIEW` không thể xảy ra trong CI vì `CA_AGENT_MODE=replay` khiến `llm.complete()` trả `ok=False` → `all_needs_review` luôn rỗng → job không bao giờ dừng ở `needs_review`. Chạy thật còn đốt tiền Vision/proxy. Stub là lựa chọn duy nhất vừa tất định vừa không tốn phí (đúng tinh thần plan mục 7 + ADR-002).
- **Convention:** `page.route` + `route.fulfill` giống `fb-inbox.spec.ts`, không phát minh pattern mới.
- **Ràng buộc nghiệp vụ được kiểm:** ADR-008 (`needs_review` là điểm dừng thật, không auto-approve); dòng GIỮ LẠI bắt buộc có giá; dòng không đọc được giá phải đánh dấu loại; client chặn submit nếu thiếu giá.
- **3 test:** form validation (thiếu giá → chặn), review screen rendering (2 mục cần review), submit flow (gửi xác nhận → job chuyển trạng thái).

| Kiểm tra | Kết quả |
|---|---|
| `npx playwright test` (Python 3.12 trên PATH) | **22 passed (39.1s)** |
| `git status --short apps/web/data/` sau e2e | **rỗng** — không rò rỉ file tracked |

**Lưu ý vận hành:** máy local có Python 3.10 trên PATH nhưng repo yêu cầu `>=3.12`. Nếu chạy e2e bằng Python 3.10, `demo_api.py` (webServer của Playwright) sẽ crash vì thiếu `StrEnum` và một số stdlib 3.12+. Fix: đặt Python 3.12 lên đầu PATH trước khi chạy:

```
set PATH=C:\Users\84788\AppData\Local\Programs\Python\Python312;C:\Users\84788\AppData\Local\Programs\Python\Python312\Scripts;%PATH%
```

#### Còn thiếu

Không còn blocker code. Chỉ còn thiếu thí điểm 2 tuần (ngoài phạm vi code, cần chủ dự án bật cờ).

---

### Phase 5 — Kiểm thử toàn diện & Vận hành thí điểm

**Code complete, test xanh. Chưa chạy thí điểm 2 tuần** (cần chủ dự án bật cờ + cấp ngân sách).

#### 5.1 Test kiến trúc (plan mục 7 — thay `import-linter`)

- [x] `packages/agents/tests/test_architecture.py` — gate thuần AST/đọc file, **có `assert MATH_LAYER.exists()`** để gate không âm thầm xanh khi file bị đổi tên/di chuyển.
  - `MATH_CAM_IO` — cấm Math Layer đọc file / gọi mạng / chạm DB.
  - `MATH_CAM_BAT_DINH = {"now","utcnow","today","time","random","urlopen","urandom"}` — cấm mọi nguồn bất định, giữ ADR-002 (toán học phải tái lập được).
  - Chặn `ag_pricing` gọi thẳng DB của `ca_api`, chặn LLM import vào Math Layer.

#### 5.2 Cost dashboard & observability (plan mục 9)

- [x] `packages/agents/src/ca_agents/ag_pricing/cost_dashboard.py` — `tinh_chi_phi`, `tinh_thoi_gian_trung_binh`, `tinh_kpi`, `tinh_canh_bao`, `tong_hop_dashboard` (deep-copy `failures_by_code` để caller không sửa được state trong). KPI ngưỡng `0.85` (tỷ lệ hoàn tất) / `180.0s` (thời gian TB) / `0.15` (tỷ lệ cần review).
- [x] Alerting: `SOURCE_BLOCKED_VUOT_NGUONG` · `VUOT_NGAN_SACH` (kèm ghi chú **"không tự tắt"**) · `GAN_NGAN_SACH` (≥80%) · `TI_LE_HOAN_TAT_THAP` · `TI_LE_CAN_REVIEW_CAO` (**mức `thong_tin`, không phải lỗi** — ADR-008: tỷ lệ cần review cao là tín hiệu để người xem, không phải để máy tự xử lý).
- [x] `_thoi_gian_giay` trả `None` khi input hỏng — **không bao giờ đoán**.
- [x] `pricing_config.py` — `CostConfig(vision_usd_moi_anh=0.0025, proxy_usd_moi_luot=0.002, ngan_sach_usd_thang=50.0)`, `AlertConfig(source_blocked_nguong_phan_tram=15.0, source_blocked_mau_toi_thieu=20)`; `_mapping_tuy_chon` trả `None` khi thiếu section (không bịa mặc định).
- [x] `config/khao-sat-gia-tham-so.yaml` — thêm section `chi_phi:` và `canh_bao:`, **mỗi giá trị gắn nhãn `BUSINESS_DECISION_PENDING_REVIEW`** (số cụ thể do đội tài chính chốt — plan mục 12).
- [x] Metric `proxy_requests` trong `_METRICS` — chi phí proxy/anti-detect là chi phí biến đổi, phải đếm riêng.
- [x] **Logging JSON có cấu trúc** gắn `job_id` xuyên suốt: `_log_job(job_id, su_kien, *, muc, **truong)` → `json.dumps(payload, ensure_ascii=False, default=str)`. Mọi bước State Machine (`_advance`, `_fail`, `resume_after_review`, `_aggregate_and_complete`) đều log.
- [x] `GET /api/v1/market/catchment-survey-dashboard` — auth-only (không manager-only: dashboard chi phí là công cụ giám sát, không phải hành động đổi giá).
- [x] `packages/agents/tests/test_pricing_cost_dashboard.py` — **26 passed**.

#### 5.3 Canary dò selector hàng ngày (plan mục 7 [ĐỀ XUẤT MỚI])

Plan mục 7 yêu cầu nguyên văn: *"Vì scraper phụ thuộc cấu trúc trang bên thứ ba có thể đổi bất kỳ lúc nào, cần **test canary hàng ngày chạy riêng** (không nằm trong CI chặn merge) để cảnh báo sớm khi ShopeeFood/Google Maps đổi UI, tách biệt khỏi test suite chính để không block release vì lỗi bên ngoài."*

- [x] `packages/agents/src/ca_agents/sources/scraper_selectors.py` — **nguồn sự thật duy nhất** cho selector. Chỉ stdlib, không I/O. `@dataclass(frozen=True, slots=True) NguonCanary(ma, ten, url_mau, selector_bat_buoc, selector_tuy_chon, selector_nhom_it_nhat_mot, chu_thich)`. Hằng số đặt tên: `GMAPS_SEL_KHUNG_KET_QUA`, `GMAPS_SEL_TEN_QUAN`, `GMAPS_SEL_NUT_THUC_DON`, `GMAPS_SEL_NUT_TAT_CA_ANH`, `GMAPS_SEL_ANH_TRONG_VUNG`, `GMAPS_SEL_RATING`, `GMAPS_SEL_SO_REVIEW`. `DAU_HIEU_BI_CHAN = ("captcha","blocked","forbidden","403","unusual traffic","enablejsandcookies","sorry/index")`.
- [x] Hàm xếp mức thuần: `tim_dau_hieu_chan`, `xep_muc_nguon` (tính `thieu` / `nhom_chet` / `nhom_suy_giam` / `mat_tuy_chon`, khử trùng lặp), `xep_muc_chung`, `selector_can_do` (dedup giữ thứ tự). `_THU_TU_MUC = {DO:0, VANG:1, XANH:2, KHONG_CHAY:3}`.
- [x] `scripts/canary/chay_canary_nguon.py` — chạy camoufox `headless=False` (cố ý: để người vận hành thấy trang thật), `domcontentloaded` 45s + `wait_for_timeout(4000)`. **LUÔN `return 0`** — đây là báo cáo, không phải gate. Thiếu camoufox → trả payload `MUC_KHONG_CHAY` chứ không crash. Có `--json`.
- [x] `.github/workflows/canary-nguon.yml` — `schedule: cron "0 2 * * *"` (= 09:00 VN) + `workflow_dispatch`; `concurrency: {group: canary-nguon, cancel-in-progress: false}`; `timeout-minutes: 20`; `xvfb-run` + `tee canary-nguon.txt`; upload artifact giữ 30 ngày; `$GITHUB_STEP_SUMMARY` tiếng Việt. **`continue-on-error: true` trên MỌI step** và **không được `ci.yml` tham chiếu** — đúng yêu cầu "không block release vì lỗi bên ngoài".
- [x] `packages/agents/tests/test_scraper_selectors.py` — **37 passed** (guard test offline, không cần mạng).
- [x] `Makefile` — target **`canary:`** (nằm giữa `test-unit:` và `test-fb:`), hỗ trợ `make canary JSON=1`. Tách khỏi `test` vì cần camoufox + mạng và có thể đỏ do bên thứ ba đổi UI.

#### 5.4 Bằng chứng canary chạy trên trang THẬT

Đây là kết quả canary thực thi trực tiếp (không phải fixture), và nó **xác nhận giá trị của cả cơ chế**:

| Nguồn | Kết quả | Mức | Diễn giải |
|---|---|---|---|
| **ShopeeFood** | Trang trả `["captcha", "403"]` | 🔴 **ĐỎ** | Nền tảng đang siết chống bot. Đây chính là tín hiệu mà alert `SOURCE_BLOCKED_VUOT_NGUONG` được thiết kế để bắt — **không phải lý thuyết** |
| **Google Maps** | 7 phần tử feed · 6 tên quán · 1 nút thực đơn · 63 span rating · **0 nút ảnh** | 🟡 **VÀNG** | Nhóm "ít nhất một" (`NUT_THUC_DON`, `NUT_TAT_CA_ANH`) vẫn sống nhưng selector nút ảnh đã suy giảm → UI Google Maps đã đổi một phần |

Kết luận vận hành: luồng dine-in (Google Maps) vẫn chạy được nhưng cần rà selector ảnh; luồng delivery (ShopeeFood) **phải đi qua SerpApi/proxy hoặc tạm dừng**. Không tự tắt alert.

#### 5.5 Dọn nợ lint/type của chính nhánh này

Trước khi kết thúc Phase 5, toàn bộ lỗi `ruff` do nhánh này sinh ra đã được xoá sạch:

- **Ruff: 16 lỗi → 0.** `ruff check apps/api/src packages scripts` → **"All checks passed!"**. Đã chứng minh quy trách nhiệm bằng `git show HEAD:<file> | ruff check --stdin-filename <file> -`: cả 4 file tracked bị sửa đều **sạch ở HEAD**, nên không lỗi nào là nợ có sẵn để bỏ qua. 14 lỗi tự sửa (`I001` sắp xếp import, `F401` import thừa); 2 lỗi sửa tay — hoán vị 2 import `StoreCandidate`/`TrendItem` từ cuối `ca_contracts/__init__.py` lên đầu (đã kiểm tra `catchment_survey.py` và `trend_item.py` chỉ import stdlib + pydantic → **không có vòng lặp**; kiểm chứng runtime `IMPORT_OK StoreCandidate TrendItem`).
- **mypy: 231 → 216 lỗi toàn repo, và 0 lỗi trên mọi file của tính năng này** (`Success: no issues found in 37 source files`). 216 lỗi còn lại **đều nằm trong file tracked có sẵn** (nhiều nhất: `test_threads_camoufox_source.py` 30, `test_tiktok_camoufox_source.py` 21, `test_threads_official_api_source.py` 18, `test_camoufox_client.py` 17, `test_ag_copilot.py` 14). mypy chạy **không chặn** trong CI (`mypy packages apps/api/src --ignore-missing-imports || true`), ruff mới là gate chặn — nên đây là nợ ngoài phạm vi, đã ghi nhận chứ không sửa.
- Đã dọn thêm 7 file untracked thuộc dự án này: `serpapi_client.py` (3 `no-any-return`), `test_gmaps_serpapi_source.py` + `test_gtrends_serpapi_source.py` (`dict` → `dict[str, Any]`), `test_ag_copilot_market.py` (fixture generator `-> Iterator[None]`), `test_llm_bai.py` + `test_llm_cooldown.py` (`monkeypatch: pytest.MonkeyPatch`), `test_serpapi_client.py` (`hdrs={}` → `hdrs=Message()`). Cả 7 file: **Success: no issues found in 7 source files**, **54 passed**.
- Bỏ code chết `try: from enum import StrEnum / except ImportError: class StrEnum(str, Enum)` trong `catchment_survey_v2.py` — nguyên nhân duy nhất của 2 lỗi `no-redef`. Đã kiểm tra **cả 8 file `pyproject.toml` đều khai báo `requires-python = ">=3.12"`** nên nhánh `except` không bao giờ chạy.

#### 🔴 Lỗi production thật do mypy phát hiện (350 test xanh vẫn không bắt được)

`collect_sweet_spot_prices` trong `math_layer.py` gọi thẳng `float(price)` trong khi `price` có thể là `None` — contract **cho phép rõ ràng** `original_price_vnd = None` (ảnh mờ, OCR không đọc được giá). Tái hiện trực tiếp:

```
TypeError: float() argument must be a string or a real number, not 'NoneType'
  at math_layer.py:290
```

**Một món không đọc được giá trong một ảnh mờ làm SẬP CẢ JOB khảo sát.** Đã sửa bằng cách bỏ qua món `None`, và **cố ý KHÔNG**:

- thay bằng `0` — một dòng giá 0đ kéo phân vị xuống giả tạo, tệ hơn là thiếu một mẫu;
- suy ngược từ giá khuyến mãi — plan mục 1.5.2 cấm: khuyến mãi là chiến thuật ngắn hạn, không phải mặt bằng giá thị trường.

Thêm 2 test hồi quy: `test_collect_sweet_spot_prices_bo_qua_mon_khong_doc_duoc_gia` và `test_collect_sweet_spot_prices_gia_khuyen_mai_khong_bao_gio_none` (test thứ hai giữ để nếu sau này contract nới `effective_price_vnd` thành Optional thì nhánh còn lại cũng phải xử lý None).

**Bài học:** mypy báo `arg-type` trên `int | None → float()` đáng để truy tới cùng **ngay cả khi mypy không chặn CI**.

#### Bằng chứng test Phase 5

| Phạm vi | Kết quả |
|---|---|
| 16 suite của tính năng (contracts v2, math layer, pricing config, substitute taxonomy, dish normalizer, shopeefood parser, vision, job manager, orchestrator v1+v2, API, cost dashboard, selectors, architecture, copilot market, serpapi) | **500 passed in 8.76s** |
| `test_scraper_selectors.py` | **37 passed** |
| `test_pricing_cost_dashboard.py` | **26 passed** |
| `test_architecture.py` (Math-Layer purity) | pass |
| **Full suite toàn repo** (`CA_AGENT_MODE=replay`, `--ignore` 3 file treo mạng có sẵn) | **1582 passed in 136.04s** |
| `ruff check apps/api/src packages scripts` | **All checks passed!** |
| `mypy` trên 37 file của tính năng | **Success: no issues found** |

#### Còn thiếu để đóng Phase 5 theo plan mục 10

⛔ **Chưa chạy thí điểm 2 tuần trên 1 khu vực thật.** Tiêu chí nghiệm thu: *"Chạy thí điểm 2 tuần không có sự cố `SOURCE_BLOCKED` liên tục >1 ngày; chi phí Vision API nằm trong ngân sách dự kiến"*. Code và dashboard đã sẵn sàng, nhưng:

1. Cần chủ dự án bật cờ + cấp ngân sách Vision/proxy.
2. **Rủi ro đã biết trước:** canary đang báo ShopeeFood ĐỎ (captcha/403). Nếu chạy thí điểm ngay, tỷ lệ `SOURCE_BLOCKED` gần như chắc chắn vượt ngưỡng ở luồng delivery → cần chốt phương án SerpApi/proxy **trước khi** bắt đầu đếm 2 tuần.
3. Bộ dữ liệu vàng OCR (~100–200 ảnh đã gán nhãn, plan mục 7: ≥90% ảnh rõ, ≥70% ảnh mờ) **chưa có** → chưa đo được KPI "độ chính xác giá OCR ≥90%".

#### 🔴 Đã sửa: test suite làm bẩn file ĐÃ TRACK `data/out/mail_log.jsonl`

**Phát hiện:** khi audit `git status` sau lần chạy full suite, thấy `M data/out/mail_log.jsonl` — **+32 dòng** là bản ghi mail replay trùng lặp, mtime nằm đúng trong cửa sổ chạy test. Đây là file **đã được git track**, nên mỗi lần chạy test là một lần làm bẩn working tree và có nguy cơ commit nhầm dữ liệu runtime.

**Truy nguyên nhân (bisect bằng cách đo kích thước file quanh từng lần chạy):**

| Phạm vi chạy | Kích thước `mail_log.jsonl` | Kết luận |
|---|---|---|
| Trước khi chạy | 102459 | mốc so sánh |
| 7 suite của tính năng pricing | không đổi | ✅ test của dự án này **không** rò rỉ |
| `packages/agents/tests` (toàn bộ) | không đổi | ✅ sạch |
| `apps/api/tests` (toàn bộ) | 102459 → **103853** | 🔴 nguồn rò rỉ nằm ở đây |
| `apps/api/tests/unit/test_copilot_api.py` (1 file) | → **103853** | 🔴 thu hẹp còn 1 file |
| `test_copilot_send_mail_proposal_and_execute` (1 test) | → **103156** (+1 bản ghi) | 🔴 **đúng test này** |

**Nguyên nhân gốc:** `packages/agents/src/ca_agents/ag_mail.py` hàm `_log_mail_replay` lấy đường dẫn mặc định là **đường dẫn tương đối**:

```python
path = Path(os.environ.get("NHIPQUAN_MAIL_LOG", "data/out/mail_log.jsonl"))
```

Khi `NHIPQUAN_MAIL_LOG` chưa được đặt, nó ghi thẳng vào repo. Test `test_copilot_send_mail_proposal_and_execute` (dòng 996) **cố ý không patch** `execute_supervised_mail` — nó kiểm tra luồng gửi mail thật ở chế độ replay, nên adapter chạy và ghi log. Đây là hành vi **có sẵn của repo, không do dự án khảo sát giá gây ra**: diff của nhánh này trong file đó bắt đầu ở dòng 1937 (hunk `@@ -1936,4 +1937,74 @@`), cách xa test gây rò rỉ, và 71 dòng thêm vào chỉ là 2 test RBAC cho `RUN_CATCHMENT_SURVEY` — không đụng mail. Đã kiểm chứng bằng `git stash` phần thêm vào rồi chạy bản HEAD: **vẫn rò rỉ y hệt**.

**Cách sửa:** `apps/api/tests/conftest.py` đã có fixture `autouse` `_isolated_store` chuyển hướng `NHIPQUAN_DB`, `NHIPQUAN_SUA`, `NHIPQUAN_CAMNANG` sang `tmp_path` — chỉ **thiếu** biến mail log. Thêm đúng 1 dòng vào danh sách sẵn có đó:

```python
monkeypatch.setenv("NHIPQUAN_MAIL_LOG", str(tmp_path / "mail_log.jsonl"))
```

Chọn cách này thay vì patch từng test vì: (a) khớp với khuôn mẫu cô lập đã có sẵn trong chính fixture đó; (b) sửa được **mọi** test hiện tại và tương lai, không chỉ test đã biết; (c) không đổi hành vi được kiểm thử — adapter vẫn chạy thật, chỉ ghi sang thư mục tạm.

**Kiểm chứng an toàn trước khi sửa:** `grep_search "mail_log"` trong `apps/api/**` → **rỗng**, tức không test nào đọc file đó, nên chuyển hướng không thể làm hỏng assertion nào. (`packages/agents/tests/test_ag_mail.py` tự patch `NHIPQUAN_MAIL_LOG` sang `tmp_path` sẵn rồi — đó là lý do nhánh agents sạch.)

**Kết quả sau khi sửa:**

| Kiểm tra | Kết quả |
|---|---|
| `apps/api/tests` (toàn bộ) | pass, `git status data/out/mail_log.jsonl` → **rỗng** |
| **Full suite toàn repo**, chạy ĐÚNG phương pháp loại trừ như mốc 1582 ở trên (`--ignore` 3 file treo mạng) | **1582 passed in 136.01s — 0 failed** |
| `git status --short data/` ngay sau full run | chỉ còn `?? data/fixtures/serpapi/` (fixture cố ý) — **`mail_log.jsonl` không bị sửa** |
| Full suite, phương pháp loại trừ khác (`--deselect` bộ ba camoufox) để đối chứng | **1519 passed, 68 deselected in 295.57s — 0 failed** |
| `ruff check apps/api/tests/conftest.py` | **All checks passed!** |
| `mypy apps/api/tests/conftest.py` | **Success: no issues found in 1 source file** |

Số test **1582** khớp đúng mốc trước khi sửa → fix không làm mất hay bỏ sót test nào; nó chỉ đổi đích ghi log của mail adapter trong test.

**Bài học:** `git status` sau mỗi lần chạy full suite là bước bắt buộc, không phải tuỳ chọn. Một fixture cô lập "đã đủ" (DB, JSONL, cẩm nang đều sang `tmp_path`) vẫn có thể sót biến môi trường — và biến sót lại chính là biến trỏ vào file **đã track**. Cùng nhóm phát hiện với `data/cache/` ở trên: cả hai đều là artifact runtime lọt vào working tree.

---

### SerpApi v2.0 Production Integration (`260913-2045-serpapi-integration`)

**Code complete, 100% tests pass.** Phạm vi đã giao:

- [x] `plans/260913-2045-serpapi-integration/plan.md` — Toàn văn kế hoạch kỹ thuật v2.0 chuẩn SOTA.
- [x] `.env.example` — Cấu hình đầy đủ 12 biến môi trường quản trị SerpApi (thresholds, cache TTLs, circuit breaker, rate limit).
- [x] `packages/contracts/src/ca_contracts/catchment_survey.py` — Mở rộng `StoreCandidate` với `place_id`, `data_source`, `lat`, `lng`, `fetched_at` (tương thích ngược 100%).
- [x] `packages/contracts/src/ca_contracts/trend_item.py` & `ca_contracts/__init__.py` — Pydantic contract `TrendItem` chuẩn hóa cho Google Trends.
- [x] `packages/contracts/tests/test_trend_contracts.py` — Unit tests kiểm tra contract validation.
- [x] `packages/agents/src/ca_agents/clients/serpapi_client.py` — Core client SOTA: L1 In-Memory Cache (5 phút), L2 Persistent Cache, Circuit Breaker (3 trạng thái), Exponential Backoff Retry + Jitter, Quota Guard 3 mức (INFO/WARN/CRITICAL), Masking API key (`ak_***masked***`), Stale-if-error.
- [x] `packages/agents/src/ca_agents/sources/gmaps_serpapi_source.py` — Google Maps source với Haversine distance, tọa độ GPS thật, rating/review thật, ẩn danh hóa thông tin cá nhân review (Nghị định 13/2023/NĐ-CP).
- [x] `packages/agents/src/ca_agents/sources/gtrends_serpapi_source.py` — Google Trends source: trích xuất time-series mức độ quan tâm và phân loại breakout keyword.
- [x] `packages/agents/src/ca_agents/ag_pricing/orchestrator.py` — Chuỗi Fallback hoàn chỉnh: SerpApi -> Camoufox -> Stale cache -> Error.
- [x] `apps/api/src/ca_api/interfaces/http/pricing_radar.py` & `main.py` — Endpoint giám sát `GET /api/system/integrations/serpapi`, rate limit 3 req/phút/user, kiểm soát phân quyền.
- [x] `docs/runbooks/serpapi-integration.md` — Runbook vận hành, quy trình xử lý sự cố và kiểm tra hạn ngạch.
- [x] Unit test suites phủ đầy đủ: `test_serpapi_client.py` (16 passed), `test_gmaps_serpapi_source.py` (9 passed), `test_gtrends_serpapi_source.py` (5 passed), `test_pricing_radar_api.py` (5 passed).
