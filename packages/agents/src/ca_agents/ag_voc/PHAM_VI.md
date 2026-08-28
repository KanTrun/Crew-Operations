# AG-VOC — phạm vi

| Thuộc tính | Giá trị |
|---|---|
| Nhiệm vụ | Đọc phản hồi khách **do quán tự chuyển vào**, phân loại thành sự cố vận hành, nối vào **việc treo** |
| Phạm vi | Một phản hồi. Không gộp, không suy ra chân dung khách |
| Đầu vào | `phan_hoi: str` — nội dung quán dán, chuyển tiếp, hoặc chụp ảnh |
| Đầu ra | `{la_su_co_van_hanh, loai, tu_khoa, source_span, cau_viec_treo, han_gio, do_tin_cay, ghi_chu}` |
| Mô hình | Nhỏ là đủ. Nhận nhóm sự cố, không suy luận dài |
| Song song | Có. Mỗi phản hồi độc lập |
| Điều kiện dừng | Trả một nhóm sự cố, hoặc `chua_phan_loai_duoc` để đẩy lên người |
| **Cấm** | Thu thập tự động từ Google Maps / ShopeeFood / Grab · **trả lời khách thay quán** · nêu tên hoặc đánh giá nhân viên · lưu dữ liệu định danh khách · nối phản hồi giá cả vào việc treo · ghi DB · gọi agent khác · quyết định luồng |
| Cổng | VF-SCHEMA, **VF-TRACE** |

## Vì sao chỉ nhận nội dung quán tự chuyển vào

Hồ sơ §6.2: thu thập tự động từ các nền tảng đánh giá **có thể vi phạm điều
khoản sử dụng** của họ, và đội **chưa kiểm chứng được** điều đó (§18.3 việc 4).
Tài liệu không giả định là được phép. Nên phiên bản này chỉ nhận nội dung do
chủ quán chủ động đưa vào.

## Vì sao phản hồi giá cả không thành việc treo

Giá và khuyến mãi là quyết định kinh doanh của chủ, không phải sự cố có người
phải xử lý trong ca. Đề tài đã tuyên bố không làm module tài chính (§6.2), nên
agent nhận ra nhóm này chỉ để **loại**, và ghi rõ
`ngoai_pham_vi_van_hanh_khong_noi_viec_treo`.

## Vì sao sự cố vận hành xét trước marketing

Một phản hồi có thể vừa nói giá vừa báo chờ lâu. Phần vận hành mới là phần có
người phải làm gì đó, nên nó được ưu tiên.

## VF-TRACE

`source_span = {"text_offset": vị trí từ khoá}` trỏ về đúng đoạn trong phản hồi
gốc. Không có span thì cổng đẩy lên người — phân loại không nguồn bị loại.

## Ranh giới với dữ liệu cá nhân

Agent chỉ đọc **nội dung** phản hồi. Không lưu tên, số điện thoại, hay bất kỳ
định danh khách nào. Đây là ranh giới của thể lệ về dữ liệu cá nhân (§6.3).
