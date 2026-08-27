---
title: Brainstorm nối lại logic lịch ↔ inbox ↔ TKB ↔ Telegram
date: 2026-08-27
status: accepted
evidence: live localhost:3000 + :8000
---

# Brainstorm — Logic tương tác lịch / inbox / TKB / kênh tin

## Summary

Trên instance đang chạy, **Duyệt / Từ chối không đổi lịch** không phải ảo giác: đó là hành vi code + UI viết đúng, nhưng **đường ống “áp vào lượt xếp lịch tới” bị đứt**. Lịch hiển thị là **synthetic + tuần đóng**; hộp thư **trộn Telegram thật với fixture**; TKB đang **`CA_AGENT_MODE=replay`**. Docker compose không có container up (API/web chạy ngoài compose); GitHub remote `KanTrun/CA-CONG-BANG`.

## Contract

| Field | Value |
|-------|-------|
| **Outcome** | Một chuỗi ops rõ: tin NV (Telegram/Zalo) → classify có chọn lọc → `/inbox` → duyệt có **hiệu lực quan sát được** trên lịch (đổi ca hoàn chỉnh **hoặc** ràng buộc thật sự vào lượt solver) → `/toi` / MessagePort / roster cùng một nguồn `phan_cong`. TKB ảnh chỉ vào solver sau xác nhận + lọc tin cậy. Mock/fixture không lẫn ops. |
| **Constraints** | Giữ ADR: AG-MSG không silent ghi `phan_cong`; Docker + GitHub là đường giao hàng; tái dùng `/inbox` + lifecycle; bí mật kênh chỉ env; CI replay tách khỏi quán. |
| **Non-goals** | Meta/Facebook live; CRM; LLM tự duyệt đổi ca; redesign UI lớn; thay solver CP-SAT. |
| **Acceptance** | (1) Duyệt `doi_ca` → phiếu chợ đủ `ca_id`/đối tác **hoặc** CTA buộc hoàn tất; lịch đổi sau khi chợ xong. (2) Duyệt `xin_nghi`/`cap_nhat_tkb` → xuất hiện trong input solver lần `dang_giai` kế tiếp (test chứng minh). (3) `khac`/`/help`/`hi` không vào inbox. (4) UI tách nguồn `telegram` vs fixture; cấm seed fixture khi đã có tin kênh. (5) `/hom-nay` không hứa “lượt xếp tới” khi lifecycle `da_dong`. (6) Compose + CI xanh với `CA_AGENT_MODE` tường minh. |

## Evidence (đã bắt được trên live)

### Web `/hom-nay`
- «**Đã đóng** Lịch tuần **2026-W01**»
- 7 mục chờ duyệt · 18 việc treo
- Ngày UI `2026-08-27` lệch tuần lịch đóng

### Web `/inbox`
- Footer: «Ràng buộc đã duyệt chỉ có tác dụng ở **lượt xếp lịch kế tiếp**»
- Telegram đã duyệt `cho em đổi ca chiều` → «**Đã mở phiếu chợ đổi ca — chưa đổi lịch tự động**»
- Telegram `hi` đã duyệt → «**Đã ghi nhận — không đổi lịch**»
- Trộn mục `mo_phong_fixture` hiện «Kênh khác» cạnh Telegram thật

### API
- `agent_mode=replay`; channels `telegram.connected=false` nhưng có bind + tin `in_ch_*`
- Inbox 18 mục: 4 Telegram + 14 fixture
- `doi_ca` duyệt → `hieu_luc.cho_doi_ca` + `sw_inbox_d0a524` với **`ca_id=""`, `b=""`, `c=""`**, `cho_3_nhanh` — kẹt
- `_run_solver` chỉ merge `tkb_nv` + luật cẩm nang — **không đọc** `inbox_rang_buoc` đã duyệt
- `/lich-tuan?tuan=2026-W34` → `may_sinh`, **25/25** NV `synthetic`; file `lich_tuan.json` ghi `tuan_iso=2026-W01`
- Lifecycle `da_dong` → không còn chuyển `dang_giai` để chạy lại solver từ UI

### Docker / GitHub
- `docker compose ps` trống; API `:8000` + web `:3000` chạy local ngoài stack
- `origin` = `https://github.com/KanTrun/CA-CONG-BANG.git`

## Mâu thuẫn logic (đã chứng minh)

1. **Hứa hiệu lực lịch vs không wire solver** — UI/API ghi `rang_buoc_cho_solver` / «lượt xếp tới»; solver không consume inbox.
2. **Đổi ca duyệt mở phiếu rỗng** — không đủ dữ liệu để chợ 3 nhánh hoàn tất → lịch đứng yên.
3. **Tuần đã đóng** — «lượt xếp tới» unreachable trong ops hiện tại.
4. **Lịch mock đội lốt máy sinh** — synthetic + overlay tuần query; `/toi`/Telegram đọc `phan_cong` kv khác cảm giác với lưới W34.
5. **Inbox nhiễm fixture** — duyệt thật lẫn kịch bản giả → không biết quyết cái nào là quán.
6. **TKB «nhận diện kém»** — mode replay + confirm fixture `tkb_01`; live vision chưa là path đang chạy; lọc chỉ `_clean_khoang` format, không chọn lọc nghiệp vụ.
7. **Classify không cổng** — `/help`, `hi` vào inbox như ràng buộc.

## Approaches

### A — Nối ống deferred (khuyến nghị)
Wire inbox đã duyệt → input solver; hoàn thiện `doi_ca` (bắt chọn ca/đối tác hoặc deep-link chợ); chặn `khac`/noise; tách fixture; UI lifecycle trung thực; Docker env `CA_AGENT_MODE` rõ.
- **Giả định tải:** quán chấp nhận lịch đổi ở **lượt xếp / chợ**, không bấm Duyệt là xong ngay.
- **Gãy trước khi:** QL kỳ vọng bấm Duyệt → lưới đổi tức thì.

### B — UI trung thực + CTA (nhỏ hơn, không đủ một mình)
Sửa copy/CTA, ẩn «lượt tới» khi `da_dong`, link phiếu đổi ca — **không** sửa wire solver.
- **Giả định:** user chỉ cần hiểu đúng.
- **Gãy:** user vẫn thấy «đã duyệt mà lịch không đổi» về mặt nghiệp vụ.

### C — Duyệt = mutate `phan_cong` ngay
Vi phạm ADR silent rewrite; phá fairness/solver; rẻ cảm giác, đắt nợ kỹ thuật.
- **Giả định:** ưu tiên demo tức thì.
- **Gãy:** xung đột pin/solver/đóng tuần; khó bảo vệ trên GitHub CI.

## Recommendation

**A** (có lớp trung thực UI của B). Rẻ bỏ nếu sau này đổi ADR; khớp plan kênh tin hiện có.

## Decisions (user duyệt — tư duy dự án)

1. **`doi_ca`:** Không tạo phiếu chợ rỗng. QL phải đủ `ca_id` + đối tác (form inbox hoặc deep-link `/cho`/`cho-doi-ca`) **trước** khi mục thành `duyet` + `cho_3_nhanh`. Lịch chỉ đổi khi chợ hoàn tất — giữ ADR không silent `phan_cong`.
2. **Sau `da_dong`:** Cho **mở tuần mới / chuyển lại `nhap`→`dang_giai`**, không sửa âm thầm tuần đã đóng.
3. **Fixture inbox:** Gate env (`NHIPQUAN_INBOX_SEED_FIXTURE=1` chỉ CI); quán không seed khi đã có tin kênh / mặc định tắt.
