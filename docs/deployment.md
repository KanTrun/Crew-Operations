# Deployment — NHỊP QUÁN

> Cập nhật: 2026-09-05. Kết quả nghiên cứu nền tảng: [`research-oracle-cloud.md`](./research-oracle-cloud.md) · [`research-google-cloud.md`](./research-google-cloud.md).

## Platform

| Thành phần | Nền tảng | Plan | URL |
|---|---|---|---|
| Web (Next.js 15) | **Vercel** | Hobby (free vĩnh viễn, 100GB b/w) | `nhip-quan.vercel.app` |
| API (FastAPI + ortools) | **Render** | Free (512MB RAM, 750h/tháng, Singapore) | `nhip-quan-api.onrender.com` |
| Database (PostgreSQL) | **Neon** | Free vĩnh viễn (0.5GB, Singapore) | `ep-*.ap-southeast-1.aws.neon.tech` |

**Lý do chọn** (so sánh đầy đủ trong 2 file research):
- Vercel: CDN edge Singapore/HK — web tải ~50-80ms từ VN; Next.js native.
- Render Singapore: Docker native (dùng sẵn `infra/docker/Dockerfile.api`), vùng Singapore ~60ms từ VN, 512MB đủ ortools solve 60s.
- Neon: Postgres vĩnh viễn free không cần thẻ — disk Render free là **ephemeral** nên DB phải ngoài Render.
- Loại: Fly.io (bỏ free 2024), Railway ($5/30 ngày), Koyeb (chỉ Frankfurt), Oracle/GCP (rủi ro đăng ký VN + chính sách — chi tiết research).

## URL

- **Web:** https://nhip-quan.vercel.app (sau khi deploy)
- **API:** https://nhip-quan-api.onrender.com (sau khi deploy)
- **Health:** `GET /api/health` — trả `{"status": "ok"}`
- **OpenAPI:** `GET /docs`

## Deploy Command

### Lần đầu (3 dịch vụ)

```bash
# 1. Neon: đăng ký console.neon.tech (GitHub) → project vùng Singapore
#    Copy connection string (chọn "python" → psycopg) → dán vào .env.production
make migrate-neon          # alembic upgrade head 0001→0007 lên Neon

# 2. Render: dashboard.render.com/blueprints → New Blueprint → chọn repo
#    (render.yaml tự cấu hình: Docker, Singapore, free, healthcheck /health)
#    Điền DATABASE_URL (Neon) + NHIPQUAN_CORS_ORIGINS (URL web Vercel)

# 3. Vercel: vercel login → từ repo root:
cd apps/web && vercel --prod
#    Đặt NEXT_PUBLIC_API_URL = https://nhip-quan-api.onrender.com
```

### Deploy lại

```bash
git push origin main        # Render autoDeploy + Vercel auto-deploy từ Git
```

## Environment Variables

### API (Render — render.yaml)

| Biến | Giá trị | Ghi chú |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://…neon.tech/neondb?sslmode=require` | từ Neon console |
| `NHIPQUAN_CORS_ORIGINS` | `https://nhip-quan.vercel.app` | origin web, phẩy nếu nhiều |
| `CA_AGENT_MODE` | `live` hoặc `replay` | replay an toàn quota; live dùng LLM thật |
| `GROQ_API_KEY` / `GEMINI_API_KEY` / `OPENROUTER_API_KEY` | key thật | chỉ cần khi `live` |
| `NHIPQUAN_FB_PAGE_TOKEN` / `NHIPQUAN_FB_PAGE_ID` | token Graph API v26 | Page quán |
| `NHIPQUAN_PAGE_MODE` | `live` | bật webhook Messenger |
| `NHIPQUAN_FB_WEBHOOK_VERIFY` | secret | verify token webhook |

### Web (Vercel)

| Biến | Giá trị |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://nhip-quan-api.onrender.com` |

**Lưu ý build-time:** `NEXT_PUBLIC_API_URL` được nhúng khi build — đổi URL API thì phải redeploy web.

## Custom Domain

- Vercel: Project → Domains → Add → tự config CNAME `cname.vercel-dns.com` (miễn phí SSL).
- Render: Settings → Custom Domain (chỉ khi có domain riêng; subdomain `.onrender.com` đã có SSL).

## Rollback

- Render: service → Events → deploy cũ → *Rollback* (hoặc `render deploys rollback <id>`).
- Vercel: Deployments → deploy cũ → *Promote to Production*.
- Neon: **Point-in-time restore** 7 ngày (free) — console → Restore branch.
- Database schema rollback: `alembic -c apps/api/alembic/alembic.ini downgrade <rev>`.

## Cold-start & giới hạn free (quan trọng khi demo)

- **Render free ngủ sau 15 phút idle** — request đầu sau ngủ mất 30-60s (khởi động lại container).
- **Neon scale-to-zero** sau inactive — kết nối đầu tiên +~500ms đánh thức.
- Giữ ấm khi demo: ping `/health` mỗi 5 phút (vd UptimeRobot free cron).
- Nếu vượt 750h/tháng: nâng Render Starter $7/tháng — không cần đổi code.

## Troubleshooting

| Triệu chứng | Nguyên nhân | Xử lý |
|---|---|---|
| Web gọi API lỗi `api_0` | API đang ngủ/cold start | chờ 60s hoặc ping giữ ấm; web hiện "mất kết nối" là đúng thiết kế |
| Lỗi CORS khi deploy | thiếu `NHIPQUAN_CORS_ORIGINS` | set trên Render → redeploy |
| `relation "ai_rule_proposals" does not exist` | migration chưa chạy | `make migrate-neon` (chain 0001→0007) |
| 500 khi solve CP-SAT | RAM 512MB sát ortools | kiểm log Render; solve 60s ~400MB bình ổn |
| Web trắng, API OK | `NEXT_PUBLIC_API_URL` sai hoặc là build-time cũ | redeploy web sau khi đổi |
