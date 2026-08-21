# ADR-012 — Đối tác quán: đường Fixture trung thực

## Bối cảnh

Việc 1–2 §18.1 (hai quán đồng ý + thoả thuận ký) chưa có đối tác ngoài đời. Chờ sẽ chặn Sprint 1. Bịa chữ ký/tin nhắn là gian dối và trái nguyên tắc hồ sơ (“không bịa chuyện”).

## Quyết định

1. **Quán chính kỹ thuật:** `Quán Fixture NHỊP QUÁN` — dataset + YAML + seed nội bộ, nhãn `synthetic` / `fixture`.
2. **Quán dự bị ngoài đời:** slot trống trong `docs/quan-doi-tac.md` — điền khi có tin nhắn thật.
3. Thoả thuận fixture ký nội bộ đội (trưởng nhóm) ghi rõ đây **không** thay thoả thuận quán thật.
4. Khi có quán thật: thay YAML từ quan sát ca, thay số hiện trạng, giữ fixture làm regression.

## Hệ quả

- Sprint 1–3 chạy trên fixture được phép.
- Slide/bảo vệ: nói thẳng “đối tác thật: chưa / đang thay fixture” — không khoe số đo giả.
- Cẩm nang sống trên dữ liệu thật chỉ claim khi đã có sửa từ người quán thật.

## Phương án loại

- Bịa screenshot Zalo quán — loại.
- Dừng toàn bộ dự án đến khi có quán — loại (phá lịch 8 tuần).
