# UI Audit — NHỊP QUÁN Web (22 trang)

> Cập nhật: 2026-08-29 · Design tokens: `apps/web/src/app/globals.css` (`--nq-s*`, `--nq-accent`, `--nq-radius*`, `--nq-shadow-bubble`)
> Components chuẩn: `apps/web/src/ui/kit.tsx`, `apps/web/src/ui/list-filters.tsx`

## Design system (một bộ token)

| Token | Giá trị / class | Dùng cho |
|-------|-----------------|----------|
| Spacing | `--nq-s1`…`--nq-s8` (4px→64px) | margin/padding giữa nhóm, card, section |
| Màu chữ | `--nq-ink`, `--nq-ink-muted` | body, phụ đề |
| Màu nhấn | `--nq-accent` / `--nq-copper` | CTA, kicker, chip |
| Nền | `--nq-bg`, `--nq-surface`, `--nq-bg-elevated` | page, card, input |
| Viền | `--nq-line`, `--nq-line-strong` | card, input, bảng |
| Radius | `--nq-radius` (6px), `--nq-radius-bubble` (18px) | input vs card |
| Shadow | `--nq-shadow-bubble` | OpsCard, tile |
| Typography | `--nq-font-body`, `--nq-font-mono`, `--nq-font-display` | body / meta / hero |
| Button | `Btn`, `BtnLink` (`variant`: primary/ghost/danger) | **Không** dùng `style={btnPrimary}` |
| Input | class `nq-input`, `nq-select` | **Không** inline `border: 1px solid` |
| Page shell | `nq-page` + `PageHeader` + `OpsCard` | mọi trang ops |

---

## Bảng audit từng trang

### Đã chuẩn hoá trong đợt này (7 trang danh sách + them)

| Trang | Lỗi cũ (1 dòng) | Sau khi sửa |
|-------|-------------------|-------------|
| `/inbox` | `Kicker`+`h1` thô, không lọc, nhóm dính header | `PageHeader` + `OpsCard` + `ListToolbar` (trạng thái, NV, thời gian, tìm) |
| `/vet` | `inline style` font mono, list không lọc | `OpsCard` + lọc người/thời gian/tìm + `FilteredEmpty` |
| `/treo` | Tab `btnPrimary` inline, 2 tab dính list, không lọc | `TabBar`/`TabButton`, 2 `OpsCard` tách, lọc đầy đủ |
| `/doi-ca` | Form + list cùng flow, `h2` lệch, không lọc | 2 `OpsCard` (mở lệnh / danh sách) + lọc trạng thái & người |
| `/hao-phi` | Form dính list, `button style={btnPrimary}` | 2 `OpsCard` + `Btn` + lọc thứ/thời gian |
| `/tieu-thu` | Giống hao-phi, thiếu empty có ngữ cảnh | 2 `OpsCard` + lọc ngưỡng/thời gian + chip cảnh báo |
| `/roster` | Inline table styles, toolbar `margin: 0.75rem`, không lọc NV | `PageHeader`, `nq-roster-*`, `ListToolbar`, 2 `OpsCard` |
| `/them` | `style={{ marginBottom }}`, list thô | `PageHeader`, `LinkGrid`/`LinkTile`, `OpsCard` |

Ảnh **after**: `docs/ui-screenshots/after/` (chạy `npm run dev` + script bên dưới).

### Còn lệch — cần sprint tiếp

| Trang | Spacing | Màu/token | Button | Khối dính chùm |
|-------|---------|-----------|--------|----------------|
| `/` | Tailwind arbitrary, không `nq-page` | OK alias | Link custom class | Hero + section OK (landing) |
| `/login`, `/dang-ky` | `md:p-8`, không `--nq-s*` | copper OK | custom class, chưa `Btn` | Form 2 cột OK |
| `/hom-nay` | `nq-page` | OK | `BentoTile` | Bento + drawer cần `OpsCard` |
| `/phieu` | **0.75rem/1.25rem** lẻ, không `--nq-s*` | `var(--nq-line)` 1px thay `--nq-line-strong` 2px | **Local `btnPrimary` object** — lệch shadow 8px kit | Checklist + treo + footer **3 khối không card** |
| `/toi` | `marginTop: 1.25rem` | OK | **`style={btnPrimary}`** export rỗng | Section ngày không `OpsCard` |
| `/phieu` | xem trên | | | |
| `/cam-nang` | `nq-page` | OK | `Btn` | rule groups OK |
| `/cong-bang` | `nq-page--run` | OK | `Btn` | chart + bảng cần card tách |
| `/tkb` | `mb-8` Tailwind | OK | `Btn` | upload + kết quả dính |
| `/page-quan` | `nq-page` | OK | `Btn` + toast | status + inbox preview |
| `/qr` | `nq-page--run` | OK | `Btn` | 2 mode trong 1 flow |
| `/sop` | `nq-page--run` | OK | `Btn` | form + cites |
| `/handover` | `nq-page--run` | OK | `Btn` | 1 form — OK |
| `/contracts` | `nq-page` | OK | link thô | dev only |
| `/huong-dan` | custom `nq-map-*` | OK (map) | `BtnLink` | immersive — cố ý full bleed |

**Ưu tiên P1 tiếp:** `/phieu` (nhiều inline style nhất), `/toi`, `/tkb`, `/hom-nay`.

---

## ListToolbar — trang đã có

| Trang | Tìm kiếm | Trạng thái | Người | Thời gian |
|-------|------------|------------|-------|-----------|
| inbox | ✓ | trạng thái inbox | nv_id | 7d/30d/hôm nay |
| vet | ✓ | — | actor | ✓ |
| treo | ✓ | — | NV / ai sửa | ✓ |
| doi-ca | ✓ | swap status | a/b/c | — |
| hao-phi | ✓ | thứ | — | ✓ |
| tieu-thu | ✓ | ngưỡng | — | ✓ |
| roster | ✓ | khung ca | NV trên lưới | tuần ISO (control) |

Empty states: `Empty` (danh sách trống thật) vs `FilteredEmpty` (có data nhưng lọc không ra).

---

## Docker & GitHub

### Chạy local (không Docker)

```bash
cd apps/web
npm install
npm run dev          # http://localhost:3000
npm run build        # kiểm tra type + bundle
```

API (nếu cần data thật cho list):

```bash
# từ repo root, file .env ở root
python scripts/docker_stack.py up
# hoặc
cd infra/docker && docker compose --env-file ../../.env up -d
```

Web trong Docker: service `web` build từ `apps/web/Dockerfile`, proxy tới `api:8000`.

### GitHub

- Repo: **https://github.com/KanTrun/Crew-Operations**
- Nhánh làm việc: `main`
- Commit gợi ý: `fix(web): chuẩn hoá UI list pages + ListToolbar + audit docs`
- **Chưa push** trừ khi bạn yêu cầu — kiểm tra `git diff apps/web` trước khi PR.

### Chụp before/after

Before không lưu trong repo (trạng thái cũ đã mô tả ở bảng trên). After:

```bash
cd apps/web
npm run dev
# tab khác:
npx playwright screenshot http://localhost:3000/inbox docs/ui-screenshots/after/inbox.png
# lặp cho vet, treo, roster, tieu-thu, hao-phi, doi-ca, them
```

Hoặc mở từng URL và chụp thủ công vào `docs/ui-screenshots/after/<tên-trang>.png`.

---

## File đã thêm/sửa (đợt này)

- `apps/web/src/ui/list-filters.tsx` — `ListToolbar`, `FilteredEmpty`
- `apps/web/src/lib/list-filters.ts` — logic lọc
- `apps/web/src/app/globals.css` — `.nq-input`, `.nq-select`, `.nq-list-toolbar`
- 7 trang list + `them/page.tsx`
- `docs/ui-audit.md` (file này)
