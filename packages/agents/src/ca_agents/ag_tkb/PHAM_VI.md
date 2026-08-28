# AG-TKB — Phạm Vi

Trích xuất thời khoá biểu (TKB) từ ảnh hoặc file SVG/JSON.

**Đầu vào**: đường dẫn ảnh hoặc ID fixture  
**Đầu ra**: `{rows, confidence, spans, blur}`  
**Chế độ**: `replay` (đọc golden JSON), live (LLM vision — chưa triển khai)  
**Cấm**: không gọi DB, không gọi API bên ngoài, không gọi agent khác.
