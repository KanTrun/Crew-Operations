# ADR-006 — YAML templates là nguồn phiếu vận hành

- Status: accepted
- Date: 2026-08-22

## Decision

Mẫu phiếu (`infra/templates/*.yaml`) do D sở hữu. Opsengine chỉ diễn giải YAML, không hard-code bước.

## Consequences

Đổi quy trình = PR `feat/tpl-*`, không sửa Python nghiệp vụ.
