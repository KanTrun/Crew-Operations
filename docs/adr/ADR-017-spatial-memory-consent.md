# ADR-017 — Spatial memory consent

## Status
Accepted (plan 260920-1442, Phase 05)

## Context
HỒN QUÁN lưu ký ức vận hành và sở thích khách gắn với anchor. Lưu trữ nhạy
cảm: cần consent tường minh, retention, visibility và delete path.

## Decision
- Mỗi memory có `owner_scope`, `consent_status` (required/granted/revoked/expired),
  `visibility` (private/staff/manager/public), `status` (draft/confirmed/
  superseded/deleted), `retention_until` và audit riêng.
- Consume `ag_explain/episodic_memory` qua spatial adapter — không mutate
  episodic memory gốc.
- Retrieval fail-closed: revoked/deleted/expired/private-ngoài-scope không bao
  giờ được trả. `status=draft` hiển thị nhãn “Chờ xác nhận”, không lẫn vào câu
  trả lời đã xác nhận.
- Raw audio không lưu mặc định; transcript chỉ giữ khi khách/manager confirm
  proposal. Không nhận diện khuôn mặt/biometric/identity linking ẩn.

## Consequences
- Customer có thể xem/xoá ký ức của mình; manager xoá phải có audit reason,
  không xoá dấu vết audit.
- Vector search defer sang ADR sau (deterministic filter + keyword trong MVP).

## Links
- `packages/contracts/src/ca_contracts/spatial_memory.py`
- `packages/agents/src/ca_agents/ag_spatial_memory/`
- `docs/adr/ADR-016-grand-ai-experience-boundary.md`