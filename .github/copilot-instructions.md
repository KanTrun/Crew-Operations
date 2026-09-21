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

## Quy ước UI & code (áp dụng khi viết code)

- **Không lạm dụng icon/emoji.** Chỉ dùng icon khi thực sự tăng rõ ràng cho người dùng (ví dụ trạng thái, cảnh báo). Không chèn icon trang trí vào mọi dòng, tiêu đề, nút bấm hay log.
- Ưu tiên text rõ ràng hơn icon; một màn hình không nên có quá nhiều icon khác nhau.
- Giữ giao diện tối giản, nhất quán với thiết kế hiện có của `apps/web`.

## Quy ước dùng Terminal (áp dụng khi chạy lệnh)

- **Ghép lệnh độc lập vào một lần chạy** bằng `&&` thay vì chạy từng lệnh rời rạc — giảm spam lệnh và số lần mở terminal.
- **Không mở terminal mới khi đã có terminal đang chạy.** Ưu tiên tái sử dụng terminal hiện có; chỉ mở mới khi thật sự cần (ví dụ cần giữ server chạy nền riêng).
- **Không chạy lệnh song song** — chờ lệnh trước hoàn tất rồi mới chạy lệnh sau, tránh xung đột.
- **Lệnh dài chạy nền** (server, watcher, dev daemon) dùng chế độ async/background; không chặn terminal.
- **Khi cần dừng** một tiến trình đang chạy, dùng đúng cách (Ctrl+C / kill theo PID) thay vì mở terminal mới để chạy lệnh khác.
- **Không dùng `sleep`/poll** để chờ — chờ thông báo hoàn tất từ hệ thống.