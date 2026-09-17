---
title: "Phase 4: Review đồng bộ và phát hành"
status: done
---

# Phase 4: Review đồng bộ và phát hành

## Overview

Chạy quality gates toàn diện, review độc lập khi runtime cho phép, đồng bộ hồ sơ plan,
và giao thay đổi lên remote `main` mà không cuốn theo local CI edit.

## Requirements

- [ ] Full backend tests, frontend typecheck/build và focused E2E pass.
- [ ] Reviewer kiểm correctness, regressions, permissions, race handling và test gaps.
- [ ] Hai plan tiền nhiệm phản ánh phần đã hoàn thành và liên kết plan triển khai này.
- [ ] Commit chỉ chứa file thuộc scope; remote divergence được giải quyết trước push.

## Implementation Steps

1. Chạy full validation và kiểm Problems/diff; sửa lỗi liên quan thay đổi này.
2. Retry tester và code-reviewer delegation; nếu hạ tầng tiếp tục lỗi, ghi rõ và tự review theo cùng checklist.
3. Cập nhật plan này cùng `260916-thong-bao-cap-nhat-lich.md` và `260917-tu-dong-xep-lich-va-cho-ca.md` dựa trên bằng chứng test.
4. Fetch/rebase `origin/main`, giải quyết conflict theo hành vi mới nhất, rerun checks bị ảnh hưởng.
5. Stage danh sách file tường minh, commit conventional, push `main`, rồi verify local/remote SHA.

## Todo

- [ ] Full test matrix pass.
- [ ] Security/correctness self-review hoặc delegated review hoàn tất.
- [ ] Plans được validate và sync status.
- [ ] `.github/workflows/ci.yml` không nằm trong staged scheduling diff.
- [ ] Commit và push `main` thành công.

## Success Criteria

Remote `main` chứa implementation đã kiểm thử; working tree vẫn bảo toàn mọi thay đổi người
dùng ngoài scope; plan và test evidence đủ để người tiếp theo xác minh trạng thái.
