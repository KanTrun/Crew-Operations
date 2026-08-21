# ADR-002 — Bộ điều phối tất định

## Bối cảnh

MAST / Anthropic / Cognition: đa agent thất bại khi LLM điều phối và agent gọi agent.

## Quyết định

Orchestration là máy trạng thái mã nguồn trong `apps/api/.../orchestration`. Không LLM quyết định luồng. Agent không ghi DB, không gọi agent khác.

## Hệ quả

A đồng duyệt mọi PR chạm orchestration; 15 việc cấm agent hoá (ADR-008 sau).

## Phương án loại

LLM router / multi-agent framework làm điều phối — loại.
