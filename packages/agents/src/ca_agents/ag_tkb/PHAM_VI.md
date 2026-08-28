# AG-TKB — Phạm Vi

Trích xuất thời khoá biểu (TKB) từ ảnh hoặc file SVG/JSON.

**Đầu vào**: đường dẫn ảnh hoặc ID fixture  
**Đầu ra**: `{rows, confidence, spans, blur}`  
**Chế độ**: `replay` (đọc golden JSON); `live` (LLM text trên SVG, fail-closed)  
**Cấm**: không gọi DB, không gọi agent khác, không bịa giờ khi LLM lỗi. CI luôn `replay`.
