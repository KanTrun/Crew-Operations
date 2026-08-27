# AG-TKB — Phạm Vi

Trích xuất thời khoá biểu (TKB) từ ảnh (PNG/JPEG/WebP) hoặc file SVG/JSON.

**Đầu vào**: đường dẫn ảnh hoặc ID fixture  
**Đầu ra**: `{rows, confidence, spans, blur}`  
<<<<<<< Updated upstream
**Chế độ**: `replay` (đọc golden JSON), live (LLM vision — chưa triển khai)  
**Cấm**: không gọi DB, không gọi API bên ngoài, không gọi agent khác.
=======
**Chế độ**: `replay` (đọc golden JSON); `live` (LLM text trên SVG hoặc vision trên ảnh, fail-closed)  
**Cấm**: không gọi DB, không gọi agent khác, không bịa giờ khi LLM lỗi. CI luôn `replay`.
>>>>>>> Stashed changes
