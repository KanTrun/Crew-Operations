# AG-MEETING — phạm vi

| Thuộc tính | Giá trị |
|---|---|
| Nhiệm vụ | Đọc âm thanh / transcript cuộc họp thành biên bản có cấu trúc: Tóm tắt · Quyết định · Action Items · Đề xuất Cẩm nang |
| Phạm vi | Một cuộc họp (Giao ca, Họp tuần, Đào tạo) qua Google Meet tab hoặc ghi âm trực tiếp |
| Đầu vào | `{audio_bytes}` hoặc `{text, segments[], staff_list[]}` |
| Đầu ra | `{id, tieu_de, loai_hop, tom_tat, quyet_dinh[], action_items[], de_xuat_sop[], do_tin_cay_tong_the}` |
| Mô hình | `gemini-3.5-transcribe` / Gemini Flash / Groq Whisper (Live); Replay fixture (CI) |
| Song song | Không |
| Điều kiện dừng | Trả đủ 4 khối thông tin; nếu thông tin mơ hồ đánh dấu `do_tin_cay < 0.8` |
| Cấm | Tự ý ghi đè DB, tự ý sửa cẩm nang không qua người phê duyệt (Human-in-the-loop) |
| Cổng | VF-SCHEMA, VF-TRACE, VF-CONF |
