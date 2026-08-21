# ADR-003 — Hợp đồng dữ liệu trước mã nguồn

## Bối cảnh

Bốn người sẽ bị chặn lẫn nhau nếu chờ implementation xong mới có kiểu.

## Quyết định

Chốt `packages/contracts` (Pydantic → JSON Schema → TS) trong 2 ngày đầu; mock server trả đủ 5 hợp đồng; D làm UI trên mock.

## Hệ quả

Mọi thay đổi contracts cần duyệt cả bốn (CODEOWNERS).

## Phương án loại

Mỗi app tự định nghĩa DTO — loại.
