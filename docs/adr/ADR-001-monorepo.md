# ADR-001 — Monorepo và ranh giới gói

## Bối cảnh

Đội 4 người cần ship song song mà không chặn nhau; hợp đồng dữ liệu phải là nguồn sự thật chung.

## Quyết định

Monorepo: `apps/api`, `apps/web`, `packages/{contracts,solver,gates,opsengine,playbook,agents}`, `infra/`.

## Hệ quả

CODEOWNERS theo path; CI một pipeline; `make demo` từ root.

## Phương án loại

Đa repo theo người — loại vì xung đột contracts và demo không thống nhất.
