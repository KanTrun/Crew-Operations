# Brainstorm → cook: phase-04 (Sprint 3)

## Phase-03 gate

CLOSED on `origin/main` `c6a2284` (PR #6). Soft s03–s05 incomplete is a known leftover, not a §14.3 blocker.

## Contract

| Field | Content |
|-------|---------|
| **Outcome** | Phiếu mở quán chạy trên PWA điện thoại; việc treo hiện máy quản lý; ghi nhận sửa có cặp trước/sau |
| **Constraints** | ADR-012 fixture; agent không ghi DB; Zalo = stub (R8); orchestration = writer duy nhất |
| **Non-goals** | Quán thật (S4); VF-CONFLICT/NUM; Cẩm nang luật; POS |
| **Acceptance** | 5 cổng §14.4: (1) phiếu ≥20 bước UI mobile (phone thật = walkthrough, software sẵn); (2) minh chứng + timing; (3) 8 parallel tasks + idempotency test; (4) AG-MSG confusion matrix số thật; (5) so_lan_sua có before/after |

## Direction

Full cook `--auto` shape: opsengine + orc + AG-MSG + 3 message ports + playbook store + mobile `/phieu` `/toi` `/treo`.
