# GitHub operating model — NHỊP QUÁN

Nguồn: hồ sơ v3.0 §12. Tài liệu này là bản vận hành trong repo.

## 1. Bốn vùng nhánh

Không dùng bốn nhánh cá nhân sống suốt 8 tuần.

| Người | Tiền tố | Ví dụ |
|-------|---------|--------|
| A | `feat/solver-*` `feat/gates-*` `feat/ops-*` `feat/playbook-*` | `feat/solver-rang-buoc-cung-c01-c03` |
| B | `feat/api-*` `feat/orc-*` `ci/*` `chore/infra-*` | `ci/11-cong-chat-luong` |
| C | `feat/agents-*` `feat/router-*` `feat/eval-*` | `feat/agents-ag-tkb` |
| D | `feat/web-*` `feat/tpl-*` `docs/*` | `feat/web-luoi-lich-tuan` |

**WIP:** `wip/a|b|c|d/...` — thử nghiệm, **cấm** PR thẳng vào `main`. Rebase sang `feat/...` đúng vùng trước khi mở PR.

## 2. Luật nhánh

| Quy tắc | Giá trị |
|---------|---------|
| Tuổi tối đa nhánh `feat` | 3 ngày |
| Số nhánh mở / người | ≤ 2 |
| Cập nhật từ main | `git pull --rebase origin main` — không merge main vào feat |
| Vào main | Squash merge |
| Release | `release/semifinal` (tuần 6), `release/final` (tuần 8) — chỉ cherry-pick hotfix |
| Tags | `v0.1.0-semifinal`, `v1.0.0-final` (+ Docker image từ đúng tag) |

## 3. CODEOWNERS

Xem `.github/CODEOWNERS`. Điểm đặc biệt:

- `orchestration/` — B sở hữu, A đồng duyệt  
- `packages/contracts/` — cả bốn người duyệt  

## 4. Bảo vệ `main`

Khi đủ collaborator, Settings → Branches → Rule:

- Require pull request  
- Require review from CODEOWNERS  
- Dismiss stale reviews  
- Require status checks (11 cổng CI)  
- Require branch up to date  
- Do not allow force push / deletion  
- Include administrators  

## 5. Conventional Commits

```
<loai>(<vung>): <mô tả mệnh lệnh, không dấu chấm cuối>

loai: feat | fix | refactor | perf | test | docs | chore | ci
vung: solver | gates | ops | playbook | api | orc | agents | router | web | tpl | contracts | infra
```

`commitlint` chặn commit sai format (xem `commitlint.config.cjs`).

## 6. Checklist duyệt PR

Dừng ở lỗi đầu tiên:

1. Mô tả **vì sao**, không chỉ cái gì  
2. Có test cho hành vi mới (và đỏ nếu xoá mã mới)  
3. Không phá 5 quy tắc kiến trúc §11.2  
4. Không số/chuỗi trần / `Any` mới trong domain/packages  
5. Chạm contracts → đã `make contracts`  
6. Thêm lib → ghi `docs/THIRD_PARTY.md`  
7. Chạm agent → bump prompt version + `make eval`  
8. Chạm orc/lõi → test tất định còn xanh  

Nhãn bình luận: `[chặn]` · `[nên]` · `[hỏi]`

## 7. Mười một cổng CI

| # | Cổng | Khi | Đỏ khi |
|---|------|-----|--------|
| 1 | Lint + type | luôn | ruff / mypy --strict / eslint / tsc |
| 2 | Unit | luôn | fail hoặc coverage packages+domain < 85% |
| 3 | Integration | luôn | postgres/redis/migration đỏ |
| 4 | Architecture | luôn | vi phạm §11.2 |
| 5 | Solver bench | chạm solver | chậm >20% so main |
| 6 | Agent eval | chạm agents | dưới ngưỡng / prompt không version |
| 7 | Web | chạm web | vitest đỏ |
| 8 | E2E | main + release | Playwright 3 luồng chính đỏ |
| 9 | Docker build | luôn | build fail |
| 10 | No live LLM | luôn | test mở mạng ra ngoài |
| 11 | YAML templates | chạm templates | schema / SKU sai |

Gate 10: `CA_AGENT_MODE=replay` + vá socket trong `conftest.py`.
