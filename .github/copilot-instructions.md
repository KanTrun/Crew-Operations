# Hướng dẫn review code cho GitHub Copilot — NHỊP QUÁN

File này cấu hình **GitHub Copilot code review** để tự động review PR theo đúng
quy ước của dự án. Copilot đọc file này và áp dụng các quy tắc khi đưa nhận xét.

## Ngữ cảnh dự án

- **Monorepo** `d:\Crew-Operations`: `apps/api` (FastAPI), `apps/web` (Next.js/React/TS), `packages/*` (Python).
- **Python 3.12**, `ruff` (E,F,I,UP,B), `mypy --strict`.
- **TypeScript** `tsc --noEmit` (strict).
- **CI 11 cổng** — xem `docs/github-operating-model.md` §7.
- **Nguyên tắc Fail-Closed** — mọi đề xuất AI phải có bằng chứng (ADR-008).

## Quy tắc review (ưu tiên theo thứ tự)

1. **Lỗi chặn merge (`[chặn]`)** — dừng review ở lỗi đầu tiên:
   - Bug logic, lỗi runtime, race condition.
   - Lộ secret/token/key (pattern trong `scripts/scan_secrets_before_commit.py`).
   - Vi phạm 5 quy tắc kiến trúc §11.2.
   - Số/chuỗi trần hoặc `Any` mới trong `packages/*` và `domain/`.
   - Thêm thư viện mà không ghi `docs/THIRD_PARTY.md`.
   - Chạm contracts mà không chạy `make contracts`.
   - Chạm agent mà không bump prompt version + `make eval`.

2. **Nên sửa (`[nên]`)**:
   - Thiếu test cho hành vi mới.
   - Code không rõ ràng, thiếu docstring.
   - Không tuân thủ Conventional Commits.

3. **Hỏi (`[hỏi]`)**:
   - Nghi vấn về intent, cần làm rõ.

## Ngôn ngữ

- Nhận xét viết bằng **tiếng Việt** (ngắn gọn, dùng nhãn `[chặn]`/`[nên]`/`[hỏi]`).
- Trích dẫn file + dòng cụ thể.
- Không tự ý sửa code — chỉ nhận xét.