# Runbook — Deploy NHỊP QUÁN lên Oracle Cloud Always Free (Singapore)

> Mục tiêu: toàn bộ stack (Postgres + Redis + API + worker + web) trên **1 VM thật**,
> tên miền riêng, HTTPS, dữ liệu bền vững — **0đ/tháng**.
> Nghiên cứu nền tảng: [`research-oracle-cloud.md`](./research-oracle-cloud.md) (A1 2 OCPU/12GB, ping VN→SG 36ms).
> So sánh với stack Vercel+Render+Neon hiện tại: [`deployment.md`](./deployment.md).

## 0. Điều kiện tiên quyết

- ✅ Thẻ tín dụng quốc tế thật (Visa/Master **CREDIT**, không phải debit PIN/ảo/prepaid — Oracle từ chối).
- ✅ SĐT nhận OTP.
- ⚠️ **Home region chọn SAI là mất cả tenancy** — Oracle không cho đổi home region sau signup. Chọn đúng ngay bước 1.

## 1. Đăng ký (10 phút, làm cẩn thận từng bước)

1. Vào **https://signup.cloud.oracle.com** — điền email chưa từng dùng với Oracle.
2. **Password**: ≥12 ký tự, có hoa/thường/số/đặc biệt.
3. **Country**: Vietnam · **Home Region: `Singapore`** ← bước quan trọng nhất.
   Always Free chỉ tạo được ở home region; A1 ở Singapore ping từ VN ~36ms.
4. Xác minh SĐT (OTP SMS).
5. Thẻ tín dụng: Oracle authorize tạm ~1-2 USD rồi hoàn (không trừ thật).
   Nếu bị lỗi "We can't register you": thử lại sau 24h, đổi trình duyệt ẩn danh,
   tắt VPN. User quốc tế cũng hay gặp — nếu fail 3-5 lần thì phải chuyển hướng.
6. Bấm **Start my free trial** — tenancy có $300 credit 30 ngày (tránh dùng vào
   dịch vụ trả phí!) + Always Free vĩnh viễn sau đó.

## 2. Tạo SSH key (làm trên máy Windows, PowerShell)

```powershell
ssh-keygen -t ed25519 -f $env:USERPROFILE\.ssh\nhipquan_oracle -N '""'
# Giữ 2 file: nhipquan_oracle (private) + nhipquan_oracle.pub (public)
```

## 3. Tạo VM A1 (5 phút)

1. Console Oracle → menu ☰ → **Compute → Instances → Create instance**.
2. **Name**: `nhipquan-prod`
3. **Image**: Canonical **Ubuntu 24.04** (bấm *Change image* → Ubuntu; không dùng Oracle Linux).
4. **Shape**: bấm *Change shape* → **Ampere** (Arm) →
   **2 OCPU + 12 GB RAM** · boot volume: để mặc định 47GB (đủ, tổng quota 200GB).
5. **SSH keys**: *Upload key file* → chọn `nhipquan_oracle.pub`.
6. **Boot volume**: mở *Specify a custom boot volume size* nếu muốn >47GB (tối đa ~150GB an toàn).
7. Mục **Advanced** → *Cloud-init* → dán toàn bộ nội dung [`infra/oracle/cloud-init.yaml`](../infra/oracle/cloud-init.yaml) vào ô **Paste custom cloud-init script**.
8. **Create** — chờ ~2 phút. Nếu lỗi **"Out of host capacity"**: thử lại sau
   (lỗi này phổ biến với A1; đôi khi phải thử vài lần/ngày) — xem §8.

> **IP public**: sau khi tạo, bấm vào VM → copy **Public IP**.
> Ephemeral IP giữ nguyên khi reboot; muốn IP không bao giờ đổi → *Reserved public IP*
> (miễn phí trên Oracle, khác AWS/GCP).

## 4. Mở port trong Security List (1 phút)

Console → Networking → Virtual Cloud Networks → vcn-… → Security Lists → Default Security List → **Add Ingress Rules**:

| Source | Port | Protocol |
|---|---|---|
| 0.0.0.0/0 | 80 | TCP |
| 0.0.0.0/0 | 443 | TCP |
| (SSH 22 đã có mặc định) | 22 | TCP |

*(UFW trên VM cloud-init đã mở sẵn — chỉ cần Security List phía Oracle.)*

## 5. Tên miền DuckDNS (2 phút, free)

1. Vào **https://www.duckdns.org** → login bằng GitHub/Google.
2. Tạo subdomain, ví dụ `nhipquan` → domain của bạn: **`nhipquan.duckdns.org`**.
3. Mục **IP**: dán **Public IP của VM** (IPv4).
4. Lưu token trên trang (cần nếu sau này cập nhật IP tự động).

## 6. Lên stack (5 phút, SSH vào VM)

```bash
ssh -i ~/.ssh/nhipquan_oracle ubuntu@<PUBLIC_IP>

# Cloud-init đã chạy: docker, compose file, Caddyfile, cron anti-idle, swap đã sẵn.
# Kiểm tra: ls /opt/nhipquan && [ -f /var/lib/nhipquan-bootstrapped ] && echo ok

# 1) Tạo file .env (copy từ repo, điền key thật):
sudo cp /opt/nhipquan/repo/.env.example /opt/nhipquan/.env
sudo nano /opt/nhipquan/.env
```

Nội dung `.env` tối thiểu trên VM:

```bash
DOMAIN=nhipquan.duckdns.org
CA_AGENT_MODE=live            # AI thật; hoặc replay
GROQ_API_KEY=...              # nếu live
NHIPQUAN_CORS_ORIGINS=https://nhipquan.duckdns.org
# các key kênh tin (FB/Telegram/Zalo/SMTP) nếu dùng
```

```bash
# 2) Đảm bảo GHCR image đã build (CI tự chạy khi push main; hoặc chờ workflow lần đầu).
# 3) Up toàn stack:
cd /opt/nhipquan
sudo docker compose up -d
sudo docker compose ps        # chờ tất cả healthy
curl -fsS http://localhost/health | head -c 100   # qua Caddy: curl https://nhipquan.duckdns.org/health
```

**Xong — web chạy tại `https://nhipquan.duckdns.org`** (Caddy tự xin Let's Encrypt certificate ngay request đầu).

> Lần đầu GHCR chưa có image: CI workflow `.github/workflows/docker-ghcr.yml` build khi push main.
> Nếu cần chạy ngay: bấm Actions → *Build & push images to GHCR* → **Run workflow**.
> Image private mặc định → VM cần login: `sudo docker login ghcr.io -u KanTrun` (dùng Personal Access Token classic có scope `read:packages`).

## 7. Deploy lại khi code đổi

```bash
git push origin main   # CI build image mới → SSH vào VM:
ssh ubuntu@<PUBLIC_IP> "cd /opt/nhipquan && sudo docker compose pull && sudo docker compose up -d"
```

## 8. Sự cố thường gặp

| Triệu chứng | Xử lý |
|---|---|
| **Out of host capacity** (tạo A1 fail) | Thử lại sau vài giờ; đổi AD (availability domain) nếu region có 3 AD; script retry (cộng đồng dùng vòng lặp API — cần OCI CLI). Không có SLA. |
| Signup bị từ chối | Thử ẩn danh, saiIP khác, sau 24h. Thẻ debit nội địa/ảo/prepaid KHÔNG dùng được. |
| Web trắng / gọi API lỗi | Kiểm `NHIPQUAN_CORS_ORIGINS` khớp domain (không có `/` cuối); xem log: `sudo docker compose logs api -f` |
| Solve CP-SAT chậm/chiếm RAM | Đã có swap 2GB; monitor `docker stats`. A1 12GB dư sức. |
| VM bị reclaim idle | Cloud-init đã cài cron anti-idle mỗi 30 phút (CPU 2 phút + IO). |
| Reset IP sau reboot | Ephemeral IP giữ nguyên khi reboot, chỉ mất khi terminate. Nếu đổi IP: cập nhật DuckDNS. |

## 9. Giới hạn cần nhớ (Always Free)

- **2 OCPU + 12 GB RAM** tổng cho A1 (giảm từ 4/24GB giữa 2026) — 1 VM dùng hết quota.
- **200 GB** block volume tổng (boot 47GB + data).
- **10 TB** egress/tháng — quá dư cho quán cà phê.
- 1.500 OCPU-giờ + 9.000 GB-giờ/tháng = đủ chạy 24/7 không nghỉ.
- Quy tắc idle-reclaim: p95 CPU/mem/network <20% trong 7 ngày → có thể thu hồi
  (cron anti-idle trong cloud-init đã xử).
- Thay đổi chính sách: Oracle từng cắt quota không báo trước (06/2026) — luôn có
  backup: `make migrate-neon` + Neon vẫn còn nguyên DB của stack Vercel+Render cũ.
