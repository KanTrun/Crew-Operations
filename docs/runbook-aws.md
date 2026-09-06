# Runbook — Deploy NHỊP QUÁN lên AWS EC2 (Singapore) với Free Plan

> Mục tiêu: toàn bộ stack (Postgres + Redis + API + worker + web) trên **1 EC2 thật**,
> tên miền riêng + HTTPS, vùng Singapore (~60ms từ VN).
> **Chi phí:** $200 credit + 6 tháng Free Plan (tài khoản tạo sau 15/07/2025) —
> t3.small ~$14/tháng → credit phủ trọn 6 tháng. Hết 6 tháng: ~$14/tháng,
> hoặc chuyển về stack Vercel+Render+Neon 0đ (vẫn đang chạy song song).
> So sánh nền tảng: [`research-oracle-cloud.md`](./research-oracle-cloud.md) ·
> [`research-google-cloud.md`](./research-google-cloud.md) · stack 0đ: [`deployment.md`](./deployment.md).

## 0. Điều kiện

- ✅ Thẻ tín dụng quốc tế (Visa/Master credit hoặc debit quốc tế — AWS chấp nhận rộng hơn Oracle).
- ✅ SĐT nhận OTP.

## 1. Đăng ký AWS (10 phút)

1. **https://portal.aws.amazon.com/billing/signup**
2. Email chưa từng dùng với AWS → password → **Continue**.
3. Account type: **Personal** (Business không cần lúc này).
4. Contact info: địa chỉ VN, SĐT — AWS gọi/OTP xác minh.
5. Thẻ tín dụng: authorize tạm ~1-2 USD rồi hoàn.
6. **Support plan**: chọn **Basic support — Free**.
7. Sau khi vào console: gõ **EC2** vào thanh tìm kiếm → region selector (góc phải trên) → chọn
   **Asia Pacific (Singapore) ap-southeast-1**.

> ⚠️ **Chống cháy tiền:** Billing → Budgets → tạo budget $5/tháng với alert 100%.
> Free plan hết 6 tháng AWS **không tự trừ tiền** nhưng để an toàn: sau khi hết
> credit, xóa instance nếu không muốn trả tiếp (§8).

## 2. Tạo SSH key (PowerShell trên máy bạn)

```powershell
ssh-keygen -t ed25519 -f $env:USERPROFILE\.ssh\nhipquan_aws -N '""'
```

EC2 console → **Network & Security → Key Pairs → Create key pair** → name `nhipquan-aws`
→ type **ED25519** → *Import* file `.pub` (mở bằng notepad copy).

## 3. Tạo EC2 instance (5 phút)

1. EC2 console → **Launch instance**.
2. **Name**: `nhipquan-prod`
3. **AMI**: Ubuntu Server 24.04 LTS (free tier eligible).
4. **Instance type**: **t3.small** (2 vCPU, 2GB RAM — đủ full stack + swap 4G).
   *(t3.micro 1GB quá sát cho ortools + Postgres; small là an toàn.)*
5. **Key pair**: `nhipquan-aws`.
6. **Network settings** → *Edit*:
   - VPC mặc định · subnet mặc định · **Auto-assign public IP: Enable**
   - Security group: **Create** `nhipquan-sg` mở 3 rule:
     - SSH (22) — source **My IP** (không All!)
     - HTTP (80) — Anywhere 0.0.0.0/0
     - HTTPS (443) — Anywhere 0.0.0.0/0
7. **Storage**: 20 GiB gp3 (đủ compose + data; credit dư sức).
8. **Advanced details** → *User data* → dán toàn bộ nội dung
   [`infra/aws/user-data.yaml`](../infra/aws/user-data.yaml) → *Summary* → **Launch instance**.
9. Chờ ~2 phút → chọn instance → copy **Public IPv4**.

## 4. Tên miền DuckDNS (2 phút)

1. **https://www.duckdns.org** → login GitHub/Google → tạo subdomain (vd `nhipquan`).
2. Dán **Public IPv4 của EC2** → *Update*.

## 5. Duyệt workflow build image

Workflow `.github/workflows/docker-ghcr.yml` build image (amd64+arm64) push GHCR khi push main.
Lần đầu chạy vào GitHub repo → tab **Actions** → nếu hiển thị chờ duyệt workflow mới →
**Approve and run**. Chờ build xong (~3-5 phút, 2 jobs xanh).

> Image GHCR private mặc định. VM cần pull:
> tạo Personal Access Token (classic) scope `read:packages` → dùng khi `docker login ghcr.io`.

## 6. Lên stack (5 phút, SSH)

```powershell
ssh -i $env:USERPROFILE\.ssh\nhipquan_aws ubuntu@<EC2_PUBLIC_IP>
```

```bash
[ -f /var/lib/nhipquan-bootstrapped ] && echo "bootstrap OK"
sudo cp /opt/nhipquan/repo/.env.example /opt/nhipquan/.env
sudo nano /opt/nhipquan/.env
```

Nội dung `.env` tối thiểu:

```bash
DOMAIN=nhipquan.duckdns.org
CA_AGENT_MODE=live            # AI thật (điền GROQ_API_KEY bên dưới) hoặc replay
GROQ_API_KEY=sk-...
NHIPQUAN_CORS_ORIGINS=https://nhipquan.duckdns.org
# kênh tin FB/Telegram/Zalo/SMTP nếu dùng — copy từ .env máy dev
```

```bash
# Pull image (private GHCR → login bằng PAT read:packages)
sudo docker login ghcr.io -u KanTrun
cd /opt/nhipquan
sudo docker compose up -d
sudo docker compose ps                  # chờ 5 services healthy
curl -fsS https://nhipquan.duckdns.org/health   # HTTPS đã có cert Let's Encrypt
```

## 7. Deploy lại khi code đổi

```bash
git push origin main            # CI build image mới
ssh ubuntu@<EC2_IP> "cd /opt/nhipquan && sudo docker compose pull && sudo docker compose up -d"
```

## 8. Hết 6 tháng Free Plan — 3 lựa chọn

1. **Tiếp tục trả** ~$14/tháng (t3.small + 20GB gp3, region Singapore) — không cần đổi gì.
2. **Đóng gói:** `sudo docker compose down` → snapshot EBS → terminate instance
   (giữ snapshot ~$2/tháng nếu muốn hồi sinh sau).
3. **Chuyển về stack 0đ** Vercel+Render+Neon (đang chạy song song — chỉ cần trỏ domain
   về Vercel): Neon giữ nguyên DB, không mất dữ liệu.

## 9. Sự cố thường gặp

| Triệu chứng | Xử lý |
|---|---|
| Signup thẻ bị từ chối | Thử debit quốc tế (Visa/Master có thanh toán online), hoặc credit thật. AWS rộng hơn Oracle. |
| Web trắng / API lỗi | `NHIPQUAN_CORS_ORIGINS` phải khớp domain (không `/` cuối); `docker compose logs api -f` |
| Solve chậm | Swap đã có 4G; kiểm `docker stats`; t3.small đủ cho solve 60s của quán nhỏ |
| Let's Encrypt fail | Chờ 1-2 phút sau lần request đầu; kiểm DuckDNS trỏ đúng IP; port 80/443 mở SG |
| Không SSH được | SG rule SSH source = IP nhà bạn (đổi IP thì update rule); đúng key file, `chmod 400` trên Linux |

## 10. Khác biệt với stack Vercel+Render+Neon (0đ)

| | AWS EC2 (runbook này) | Vercel+Render+Neon |
|---|---|---|
| Phí | 0đ × 6 tháng → $14/th | 0đ vĩnh viễn |
| VM thật full stack | ✅ 1 máy trọn compose | ❌ 3 dịch vụ rời |
| Worker nền (nhắc phiếu) | ✅ chạy 24/7 | ❌ Render free 750h chỉ đủ API |
| Vùng | Singapore ~60ms | Singapore ~60ms |
| Tên miền + HTTPS | ✅ Caddy + DuckDNS | ✅ vercel.app |
| Rủi ro | Hết credit phải quyết định | Cold start 15' idle (giải quyết bằng UptimeRobot) |
