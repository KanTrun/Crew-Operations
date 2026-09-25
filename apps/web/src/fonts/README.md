# Font trong repo này

File `.woff2` ở đây là **font đã tải sẵn**, không phải sinh tự động. Chúng được
commit vào repo có chủ đích — xem lý do bên dưới.

## Vì sao không dùng `next/font/google`

`next/font/google` tải font **lúc build**. Trong Docker build của CI, lời gọi tới
`@next/font/dist/google/loader.js` vỡ:

```
An error occurred in `next/font`.
TypeError: Cannot read properties of null (reading '1')
    at .../@next/font/dist/google/loader.js:122:78
    at async nextFontGoogleFontLoader
```

Triệu chứng đánh lừa: `next build` ở máy local **xanh**, chỉ image build trong
Docker **đỏ**. Lỗi ẩn tới tận bước deploy vì job `Build & push images to GHCR`
mới là chỗ hỏng.

Nguyên nhân: loader của Next đọc phản hồi Google như CSS và không khớp khi Google
trả trang khác (400 / rate-limit / trang đồng ý), rồi truy cập nhóm bắt `null`.
Nói cách khác: **build phụ thuộc vào một dịch vụ bên ngoài không cam kết gì**.

Guideline của repo (`docs/design-guidelines.md` §Typography) vốn đã yêu cầu
"self-host, không CDN" và nêu cổng §14.9: **demo phải chạy khi đã rút mạng**.
`next/font/local` với file trong repo thoả cả hai: build không cần mạng, runtime
cũng không.

## Danh sách file

Ba họ, ba vai:

| Họ | Vai | Weight | Subset |
|---|---|---|---|
| Space Grotesk | tiêu đề (`--nq-font-display`) | 400/500/600/700 | latin, latin-ext, vietnamese |
| IBM Plex Sans | chữ đọc chính (`--nq-font-body`) | 400/500/600 | latin, latin-ext, vietnamese |
| IBM Plex Mono | số liệu (`--nq-font-mono`) | 400/500 | latin, latin-ext, vietnamese |

Tên file: `<ho>-<weight>-<subset>.woff2`. Tổng 27 file, ~324 KB.

## Tải lại / cập nhật

Nếu cần đổi font hoặc thêm weight, chạy lại script tải (tạo một lần, không commit
script — nó là công cụ dùng một lần):

```bash
# Tải CSS từ Google (kèm User-Agent hiện đại để nhận woff2, không phải TTF),
# tách URL woff2 theo từng (họ, weight, subset), tải về đây, rồi cập nhật
# apps/web/src/ui/fonts.ts.
```

Sau khi đổi, kiểm theo guideline:

```bash
cd apps/web && npx next build
# .next/static/media phải có file .woff2
# HTML đã render phải có 0 tham chiếu fonts.googleapis / fonts.gstatic
```

## Lưu ý kỹ thuật

`next/font/local` phân tích `src` ở tầng **biên dịch** và đòi mọi giá trị phải là
**chuỗi viết thẳng**. Không dùng được vòng lặp hay hàm sinh mảng — build sẽ báo
`Font loader values must be explicitly written literals`. Vì vậy khối `src` trong
`apps/web/src/ui/fonts.ts` dài, và đó là điều bắt buộc.

## Giấy phép

Cả ba họ đều theo **SIL Open Font License 1.1** — cho phép dùng, sửa, và phân
phối kèm sản phẩm, với điều kiện không bán font riêng lẻ. Xem:
- Space Grotesk — https://fonts.google.com/specimen/Space+Grotesk
- IBM Plex Sans — https://fonts.google.com/specimen/IBM+Plex+Sans
- IBM Plex Mono — https://fonts.google.com/specimen/IBM+Plex+Mono
