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
- **Dọn dẹp file tạm sau khi hoàn tất công việc.** Mỗi khi xong một đầu việc (sửa code, chạy test, kiểm tra, thu thập bằng chứng…), **phải xóa mọi file tạm do mình tạo ra** trong quá trình làm việc: script tạm (`_tmp_*.py`, `*.bat`, `*.ps1`), file output/log trung gian, file diff/status dump, ảnh chụp tạm, thư mục scratch… Chỉ giữ lại file là **kết quả thực sự của công việc** (mã nguồn, test, tài liệu, báo cáo có chủ đích). Không để lại rác trong repo hay trong thư mục làm việc — tuyệt đối không commit file tạm (kiểm tra `git status` trước khi commit).

### Xử lý khi terminal hỏng PATH (sự cố đã gặp thực tế, 2026-09-22)

Trên máy này, sau khi chạy `set`/`cmd /c` lồng nhau nhiều lớp, terminal có thể **mất PATH hoàn toàn**. Dấu hiệu:

- `'cd' is not recognized as an internal or external command`
- `'dir' is not recognized...`, `'powershell' is not recognized...`
- Lệnh sync trả **"Command produced no output"** dù thực tế lệnh ĐÃ chạy (kiểm tra bằng file output).
- `cmd /c "..."` với dấu `&` hoặc quote lồng nhau bị vỡ cú pháp.

**Cách chữa đã kiểm chứng (theo thứ tự ưu tiên):**

1. **Dùng script Python tự chứa** thay vì chuỗi lệnh shell dài: viết script chạy `subprocess.run(...)` rồi **ghi kết quả ra file**, sau đó đọc file bằng công cụ đọc file. Đừng tin shell redirection (`>`) khi terminal đã hỏng — file có thể chỉ chứa thông báo lỗi của shell.
2. **Mở terminal mới ở chế độ async** khi terminal hiện tại treo/mất stdout.
3. **Dùng đường dẫn tuyệt đối cho mọi executable**: `C:\Windows\System32\cmd.exe`, `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`, `C:\Program Files\Git\cmd\git.exe` (nhớ quote vì đường dẫn có dấu cách).
4. **Không lồng `cmd /c` trong lệnh đã có `&`/quote** — viết file `.bat` tạm rồi gọi file đó, xong thì xóa.
5. Kiểm tra kết quả bằng **nội dung file output** (timestamp + nội dung), không dựa vào output trên màn hình terminal.

### Chạy full test suite trên repo này

**LUÔN chạy pytest từ ROOT repo** (`D:\Crew-Operations`), KHÔNG chạy từ `apps/api`:

```bash
cd /d D:\Crew-Operations && python -m pytest -q
```

Lý do: `pyproject.toml` ở root khai báo `testpaths = ["apps", "packages"]` — giới hạn phạm vi suite. Chạy từ `apps/api` sẽ khiến rootdir là `apps/api`, pytest nhặt luôn `scripts/` chứa **test E2E cần server thật** (`localhost:8000` + `.env`) → **exit 2, suite chết ngay**.

Các script **cần deploy mới chạy được** (không thuộc suite, đừng đưa vào CI):
`scripts/test_e2e_copilot.py`, `scripts/test_fb_webhook_live.py`, `scripts/e2e_*.py`, `scripts/smoke_docker.py`.

- File `apps/api/tests/unit/test_schedule_consistency.py.wip_bak` là **WIP** của phiên làm việc khác (đã tách tên để pytest không nhặt). Muốn chạy lại: đổi tên bỏ hậu tố `.wip_bak` rồi sửa theo code thật.
- Nếu gặp file WIP khác làm pytest **exit 2** (lỗi collection): tạm đổi tên thêm hậu tố `.wip_bak`, chạy suite, rồi **khôi phục nguyên trạng** trong `finally`.

### Test đọc biến môi trường — LUÔN tự cô lập

`ca_agents.llm.ensure_dotenv()` nạp file `.env` THẬT vào `os.environ` khi có test gọi LLM. Hệ quả: test chạy sau đó có thể thấy `NHIPQUAN_PAGE_MODE=live`, `NHIPQUAN_FB_PAGE_TOKEN`… và **fail ngẫu nhiên theo thứ tự chạy**.

→ Mọi test assert dựa trên env PHẢI `monkeypatch.delenv(...)` / `setenv(...)` giá trị mình cần (xem pattern trong `apps/api/tests/unit/test_channels.py`).

**Đặc biệt nguy hiểm — test chạm `/api/v1/page/*`:** nếu `NHIPQUAN_PAGE_MODE=live` lọt vào env, route duyệt draft sẽ gọi `publish_page_post()` và **đăng bài THẬT lên Facebook**. Mọi test như vậy phải neo env:

```python
monkeypatch.delenv("NHIPQUAN_FB_PAGE_TOKEN", raising=False)
monkeypatch.delenv("NHIPQUAN_FB_PAGE_ID", raising=False)
monkeypatch.setenv("NHIPQUAN_PAGE_MODE", "disconnected")
```

**Mẹo chẩn đoán:** test PASS khi chạy riêng nhưng FAIL trong full suite = *test pollution* (thường do env leak), không phải bug code. Chạy `pytest <file>::<test>` để phân biệt.