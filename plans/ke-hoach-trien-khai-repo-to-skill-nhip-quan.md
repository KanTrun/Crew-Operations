# Kế hoạch Triển khai Kiến trúc "Repo-To-Skill & Playbook-To-Skill"
## Dự án NHỊP QUÁN (Crew-Operations)

| | |
|---|---|
| **Phiên bản tài liệu** | v2.0 (bản hoàn chỉnh) |
| **Trạng thái** | Chờ phê duyệt các mục Quyết định Thiết kế (Mục 5) |
| **Phạm vi** | Toàn bộ monorepo NHỊP QUÁN — packages/contracts, solver, gates, opsengine, playbook, agents, apps |

---

## 0. Tóm tắt Điều hành (Executive Summary)

NHỊP QUÁN hiện vận hành theo triết lý *"Ca làm việc là hạt nhân; cẩm nang tự viết là bộ nhớ; điều phối lõi không dùng LLM"*, nhưng đang tồn tại một khoảng trống giữa lớp agent (LLM) và lớp lõi tất định (solver CP-SAT, cổng an toàn VF-*, cẩm nang SOP). Agent phải dùng prompt cồng kềnh hoặc hardcode để gọi lõi, dễ ảo giác tham số, còn cẩm nang vận hành chỉ tồn tại dưới dạng văn bản tĩnh mà không có cơ chế kiểm tra tự động.

Kế hoạch này áp dụng phương pháp luận **Repo-To-Skill** (dựa trên DisCo/AREX-Skill) để chưng cất các package lõi và cẩm nang SOP thành các **gói kỹ năng thực thi có kiểm chứng** (`SKILL.md` + `references/` + `scripts/`), được nạp theo cơ chế **Progressive Disclosure Router** nhằm giữ context window dưới ngưỡng mục tiêu (~1.500 token/lượt gọi) mà không đánh đổi độ chính xác hay an toàn fail-closed.

Điểm khác biệt so với bản nháp trước: tài liệu này bổ sung **khuyến nghị rõ ràng cho các quyết định thiết kế còn mở**, **lộ trình theo thứ tự ưu tiên** (không gắn mốc thời gian cụ thể), **bảng rủi ro & giảm thiểu**, và **tiêu chí thành công** — đủ điều kiện làm tài liệu trình bày/phê duyệt chính thức.

---

## 1. Bối cảnh & Vấn đề Nghiệp vụ

### 1.1 Hiện trạng Monorepo
- `packages/contracts` — JSON Schema, hợp đồng dữ liệu chuẩn giữa các dịch vụ.
- `packages/solver` — Bộ giải CP-SAT (Google OR-Tools) xếp lịch ca kíp, ràng buộc cứng C01–C06.
- `packages/gates` — Hệ thống cổng kiểm duyệt an toàn fail-closed (VF-TRACE, VF-CONF, VF-SCHEMA).
- `packages/opsengine` — Quản lý treo việc, nhắc việc, ghi sổ tiêu thụ nguyên vật liệu.
- `packages/playbook` — Cẩm nang 8 bước, ghi nhận chỉnh sửa quy trình quán.
- `packages/agents` — 10 agent chuyên biệt Lô 1 (AG-TKB, AG-MSG, AG-SOP, AG-RULE, AG-SUPERVISOR, AG-CONCIERGE, AG-BARISTA...).
- `apps/api` & `apps/web` — Backend FastAPI, Frontend Next.js PWA.

### 1.2 Ba vấn đề cốt lõi
1. **Lệch pha Agent ↔ Lõi tất định**: agent phải dùng prompt cồng kềnh hoặc hardcode để gọi solver/gate, dễ ảo giác tham số C01–C06 hoặc bỏ sót điều kiện tiên quyết của cổng VF.
2. **Cẩm nang dạng "văn bản chết"**: SOP chỉ là tài liệu tĩnh — agent trả lời lý thuyết nhưng không có công cụ kiểm tra tự động xem nhân viên có làm đúng checklist hay không.
3. **Bùng nổ context window**: nhồi toàn bộ code + schema + cẩm nang vào prompt của 10 agent gây chi phí token cao, độ trễ lớn.

---

## 2. Mục tiêu & Phạm vi

### 2.1 Mục tiêu kỹ thuật
- Xây dựng **Pipeline Chưng cất** tự động quét package lõi và tài liệu SOP thành gói Skill chuẩn.
- Đóng gói `solver-scheduling-skill` và `vf-gate-verification-skill` như các skill thực thi, kiểm chứng được offline.
- Chuyển SOP trong `packages/playbook` thành checklist validator có thể thực thi độc lập (**Playbook-To-Skill**).
- Triển khai **Router điều hướng tăng dần**, giữ context mỗi lượt gọi agent dưới ngưỡng mục tiêu ~1.500 token.

### 2.2 Trong phạm vi (In scope)
- Toàn bộ solver, gates, playbook distillation, router, và tích hợp vào `packages/agents/runtime.py`.
- Bộ test tự động (unit + smoke test) cho từng skill được sinh ra.

### 2.3 Ngoài phạm vi giai đoạn này (Out of scope — đưa vào backlog)
- Tích hợp kênh ngoài (Zalo ZNS, Facebook Page Webhook) — xem khuyến nghị ở Mục 5.3.
- Tối ưu hiệu năng solver cho quy mô nhiều chi nhánh/nhiều nhân viên (để lại cho giai đoạn mở rộng).

---

## 3. Kiến trúc & Thay đổi Mã nguồn

### 3.1 Core Skills & Router (`skills/`)
| Thành phần | Nội dung |
|---|---|
| `skills/repositories/repo-skills-router/SKILL.md` | Bảng tra cứu phân cấp Area → Family → Skill; cấu hình `disable-model-invocation: true` ở nhánh con để tránh nạp toàn bộ vào context. |
| `skills/repositories/repo-skills/solver-scheduling/SKILL.md` | Phạm vi năng lực xếp ca; `references/constraints_c01_c06.md` giải thích chi tiết từng ràng buộc; `scripts/validate_solver_payload.py` kiểm tra toàn vẹn dữ liệu nhân sự trước khi gửi CP-SAT. |
| `skills/repositories/repo-skills/vf-gates-audit/SKILL.md` | Quy tắc cổng VF-TRACE, VF-CONF, VF-SCHEMA; `scripts/run_fail_closed_audit.py` kiểm tra offline đề xuất agent có vi phạm cổng an toàn không. |

### 3.2 Playbook Distillation Engine (`packages/playbook`)
- **[NEW]** `packages/playbook/src/ca_playbook/distiller.py` — parse SOP markdown thành cấu trúc State Machine: Mục tiêu → Điều kiện tiên quyết → Checklist bắt buộc → Xử lý sự cố. Tự sinh `SKILL.md` + script kiểm tra tương ứng.
- **[MODIFY]** `packages/playbook/src/ca_playbook/__init__.py` — xuất hàm giao tiếp cho distillation engine.

### 3.3 Distillation CLI & Verification Tooling (`scripts/`)
- **[NEW]** `scripts/distill_project_skills.py` — chu trình 4 bước **Scope → Ground → Construct → Verify**:
  1. *Scope*: đọc metadata và API endpoint của các package.
  2. *Ground*: kiểm tra imports, dependencies, hợp đồng trong `packages/contracts`.
  3. *Construct*: sinh thư mục skill hoàn chỉnh.
  4. *Verify*: chạy smoke test từng skill; chỉ khi pass 100% mới ghi vào `skills_index.jsonl`.

### 3.4 Tích hợp Agent Runtime (`packages/agents`)
- **[MODIFY]** `packages/agents/src/ca_agents/runtime.py` — bổ sung `SkillLoader`: agent (AG-TKB, AG-SOP, AG-SUPERVISOR) truy vấn router, chèn nội dung `SKILL.md` kèm đường dẫn script thực thi vào ngữ cảnh khi phát hiện trigger intent.

---

## 4. Sơ đồ luồng vận hành (tóm tắt)

```
Người quản lý sửa SOP trên Web PWA
        │
        ▼
packages/playbook (SOP markdown mới/sửa)
        │  (Batch trigger — xem Mục 5.2)
        ▼
distiller.py  →  scripts/distill_project_skills.py
        │  Scope → Ground → Construct → Verify
        ▼
skills/repositories/...  (SKILL.md + script mới)
        │  chỉ ghi index nếu Verify = 100% pass
        ▼
skills_index.jsonl  ←── repo-skills-router (Progressive Disclosure)
        │
        ▼
packages/agents/runtime.py :: SkillLoader
        │  nạp đúng skill khi phát hiện trigger intent
        ▼
Agent (AG-TKB / AG-SOP / AG-SUPERVISOR...) trả lời / hành động
```

---

## 5. Quyết định Thiết kế & Khuyến nghị

> Đây là hai điểm trong bản nháp gốc được đánh dấu "cần người dùng phê duyệt". Theo yêu cầu, mỗi mục dưới đây có **phân tích trade-off và khuyến nghị rõ ràng** để người duyệt quyết định nhanh hơn — quyết định cuối cùng vẫn thuộc về chủ dự án.

### 5.1 Vị trí đặt thư mục Skills

| Tiêu chí | Phương án A — `skills/` (gốc repo) | Phương án B — `packages/skills/` (Python package) |
|---|---|---|
| Tương thích chuẩn mở Agent Skills/DisCo | Cao — đúng quy ước, dễ đồng bộ với công cụ AI coding agent bên ngoài (Claude Code, Cursor, Windsurf...) | Thấp — các công cụ ngoài mặc định tìm skill ở gốc repo, không phải trong package Python lồng |
| Khả năng chia sẻ/tái sử dụng skill độc lập với vòng đời code | Cao — skill không bị ràng buộc bởi versioning của Python package | Thấp — skill gắn chặt với `pyproject.toml`, khó tách rời khi cần chia sẻ |
| Tích hợp pipeline packaging/test Python có sẵn | Trung bình — cần thêm bước CI riêng để test script trong skill | Cao — tận dụng ngay `pytest`, `pip install -e` |
| Độ phức tạp quản lý dependency cho scripts | Cần xử lý `sys.path`/import tương đối tới `packages/solver`, `packages/gates` | Tự nhiên hơn vì cùng nằm trong hệ Python package |

**Khuyến nghị: Chọn Phương án A (`skills/` ở gốc repo).**
Lý do: mục tiêu chính của kiến trúc này là để agent runtime *và* các công cụ AI coding ngoài đọc trực tiếp theo chuẩn mở — giá trị tương thích này quan trọng hơn tiện lợi đóng gói Python. Để giảm nhược điểm về import, quy định: script trong `skills/.../scripts/` **không viết lại logic**, chỉ import trực tiếp hàm từ `packages/solver`, `packages/gates` qua đường dẫn tương đối đã thêm vào `sys.path` khi khởi tạo — tránh trùng lặp logic giữa hai nơi.

### 5.2 Mức độ tự động hoá chưng cất SOP (Batch vs Live)

| Tiêu chí | Batch | Live | **Hybrid (khuyến nghị)** |
|---|---|---|---|
| Tốc độ cập nhật cẩm nang mới lên agent | Chậm (theo commit/CI) | Tức thời | Gần tức thời (trigger ngay khi API cập nhật) |
| Rủi ro an toàn (script tự sinh chưa qua review) | Thấp — có điểm dừng CI để kiểm tra trước khi merge | **Cao** — vi phạm triết lý "điều phối lõi không dùng LLM" nếu skill mới chạy runtime ngay mà chưa qua kiểm chứng | Thấp — vẫn giữ bước Verify bắt buộc trước khi ghi index, dù trigger là tự động |
| Khả năng rollback khi SOP viết sai định dạng | Dễ — commit chưa merge chưa ảnh hưởng runtime | Khó — skill lỗi có thể đã được agent nạp trước khi phát hiện | Dễ — skill lỗi bị chặn ở bước Verify, không lọt vào index |
| Trải nghiệm người quản lý quán (không kỹ thuật) | Kém — phải chờ chu kỳ CI/commit thủ công | Tốt | Tốt — gần như Live nhưng vẫn an toàn |

**Khuyến nghị: Chọn Hybrid** — API cập nhật SOP trên Web PWA **tự động trigger** `scripts/distill_project_skills.py`, nhưng skill mới chỉ được coi là "sẵn sàng" (ghi vào `skills_index.jsonl`) **sau khi** bước Verify (smoke test) pass 100%. Nếu Verify fail, giữ nguyên skill cũ và gửi cảnh báo cho quản trị viên. Cách này giữ được tốc độ gần thời gian thực của Live nhưng vẫn tuân thủ nguyên tắc fail-closed cốt lõi của dự án.

### 5.3 Câu hỏi nghiệp vụ còn lại (giữ ở dạng mở, kèm khuyến nghị tham khảo)

1. **Agent gọi solver qua hàm Python cục bộ hay qua API `apps/api`?**
   Khuyến nghị: môi trường dev/test — skill wrap hàm Python cục bộ để test offline nhanh, độc lập; môi trường production — agent runtime gọi qua API để đảm bảo một nguồn sự thật duy nhất (single source of truth) và tránh lệch trạng thái giữa các tiến trình. Cấu hình này nên là một flag môi trường (`SKILL_BACKEND=local|api`) chứ không hardcode một chiều.
2. **Có ưu tiên chưng cất tích hợp bên ngoài (Zalo ZNS/Facebook Webhook) ngay giai đoạn này không?**
   Khuyến nghị: **Không** ưu tiên trong giai đoạn này — đưa vào backlog (xem Phase 5, Mục 6). Lý do: giá trị cốt lõi của kiến trúc Repo-To-Skill nằm ở Lõi Tất định + Cẩm nang; tích hợp kênh ngoài không phụ thuộc vào pipeline chưng cất và có thể làm song song sau khi Phase 1–4 ổn định.

---

## 6. Lộ trình theo Thứ tự Ưu tiên

*(Không gắn mốc thời gian cụ thể theo yêu cầu — thứ tự dưới đây phản ánh mức độ phụ thuộc kỹ thuật, ưu tiên cao nhất trước.)*

| Giai đoạn | Nội dung | Phụ thuộc |
|---|---|---|
| **Phase 0 — Nền tảng** | Dựng cấu trúc `skills/` (Phương án A), định nghĩa schema `SKILL.md` + front-matter, khởi tạo `repo-skills-router` | Không |
| **Phase 1 — Core Deterministic Skills** | `solver-scheduling-skill` (kèm `constraints_c01_c06.md`, `validate_solver_payload.py`), `vf-gates-audit-skill` (kèm `run_fail_closed_audit.py`) | Phase 0 |
| **Phase 2 — Playbook Distillation Engine** | `distiller.py`, CLI `distill_project_skills.py` (Scope→Ground→Construct→Verify), cấu hình Hybrid trigger | Phase 0, 1 |
| **Phase 3 — Tích hợp Agent Runtime** | `SkillLoader` trong `runtime.py`, trigger intent detection cho AG-TKB/AG-SOP/AG-SUPERVISOR | Phase 1, 2 |
| **Phase 4 — Kiểm chứng & Hoàn thiện** | Full test suite, review an toàn cho script tự sinh, đo token trước/sau, tài liệu hoá + demo | Phase 3 |
| **Phase 5 — Backlog (không ưu tiên hiện tại)** | Tích hợp Zalo ZNS / Facebook Webhook | Sau Phase 4 |

---

## 7. Rủi ro & Giảm thiểu

| # | Rủi ro | Mức độ | Giảm thiểu |
|---|---|---|---|
| 1 | Script tự sinh từ SOP chạy runtime mà chưa qua review, có thể chứa lỗi logic | Cao | Bắt buộc bước Verify (smoke test) trước khi ghi index; không cho phép chế độ Live thuần |
| 2 | Solver skill validate sai, bỏ lọt vi phạm ràng buộc C01–C06 | Cao | Bộ test "golden case" cho từng ràng buộc; coverage 100% cho `validate_solver_payload.py` |
| 3 | Router vẫn nạp lồng nhiều skill khiến context phình trở lại | Trung bình | Đặt ngưỡng token cứng trong router, cảnh báo/log khi vượt ngưỡng |
| 4 | Skill bị lệch (stale) khi API/logic của package lõi thay đổi | Trung bình | Gắn version skill với version package nguồn; CI diff-check khi package lõi đổi |
| 5 | Parse SOP markdown sai định dạng gây lỗi state machine | Trung bình | Schema validation cho SOP đầu vào; fallback báo lỗi rõ ràng cho người viết SOP thay vì sinh skill sai |
| 6 | Hiệu năng CP-SAT solver giảm khi số nhân viên/ca tăng | Thấp (giai đoạn hiện tại) | Benchmark test định kỳ, đặt timeout và giới hạn quy mô rõ ràng trong `SKILL.md` |

---

## 8. Tiêu chí Thành công

- 100% skill trong `skills_index.jsonl` đã pass smoke test trước khi được agent sử dụng.
- Không có vi phạm ràng buộc C01–C06 lọt qua bước validate trong bộ test.
- Token tiêu thụ trung bình mỗi lượt gọi agent giảm rõ rệt so với baseline (trước khi có router), hướng tới ngưỡng mục tiêu ~1.500 token/lượt.
- Agent AG-TKB/AG-SOP/AG-SUPERVISOR nạp đúng skill tương ứng khi được kiểm tra qua log (không nạp thừa, không nạp thiếu).
- Pipeline Hybrid (Mục 5.2) phát hiện và chặn thành công ít nhất một trường hợp SOP lỗi định dạng trong test, không để lọt vào runtime.

---

## 9. Kế hoạch Kiểm tra & Xác minh

### 9.1 Kiểm tra tự động
```bash
# Kiểm tra cú pháp và tính hợp lệ của Skill
python scripts/distill_project_skills.py --verify-only

# Kiểm tra độ chính xác của Solver Skill
pytest packages/skills/tests/test_solver_skill.py
# → xác minh validate_solver_payload.py bắt đúng các ca vi phạm C01 (nghỉ thiếu giờ) trước khi chạm solver

# Kiểm tra Gate Verification
pytest packages/skills/tests/test_gate_audit.py
# → xác minh run_fail_closed_audit.py chặn thành công payload thiếu trường bắt buộc (VF-SCHEMA)
```

### 9.2 Xác minh nghiệp vụ (thủ công/tích hợp)
1. Kích hoạt AG-TKB với câu lệnh mẫu: *"Gợi ý xếp ca tuần tới cho 3 nhân viên"* → kiểm tra log: agent có đi qua Router → nạp `solver-scheduling-skill` → gọi script kiểm tra payload hay không.
2. Đo token tiêu thụ trên một phiên làm việc của agent **trước và sau** khi áp dụng Progressive Router — so sánh với ngưỡng mục tiêu ở Mục 8.
3. Thử nghiệm với một SOP cố tình viết sai định dạng — xác nhận Hybrid pipeline (Mục 5.2) chặn đúng ở bước Verify, không ghi vào index.

---

## Phụ lục A — Giải thích thuật ngữ

| Thuật ngữ | Ý nghĩa |
|---|---|
| C01–C06 | Bộ 6 ràng buộc cứng của solver xếp ca (ví dụ: nghỉ đủ giờ giữa hai ca, không trùng ca...) |
| VF-TRACE / VF-CONF / VF-SCHEMA | Ba loại cổng kiểm duyệt fail-closed: truy vết hành động, xác nhận điều kiện, hợp lệ schema dữ liệu |
| CP-SAT | Bộ giải ràng buộc của Google OR-Tools, dùng để xếp lịch ca kíp |
| Progressive Disclosure Router | Cơ chế chỉ nạp đúng skill cần thiết theo trigger, tránh nạp toàn bộ context |
| Fail-closed | Nguyên tắc an toàn: khi không chắc chắn/thiếu dữ liệu, hệ thống mặc định từ chối thay vì cho qua |
