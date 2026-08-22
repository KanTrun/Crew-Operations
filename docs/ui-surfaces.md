# Ánh xạ mặt hồ sơ → web sản phẩm

Hồ sơ §11 (`apps/web` constraints-inbox / run-form / today / playbook / sop-chat) và `docs/design-guidelines.md`.

| Mặt hồ sơ | Route | Vai trò chính |
|-----------|-------|----------------|
| today | `/hom-nay` | Cả hai — hub sau đăng nhập |
| run-form | `/phieu` | Nhân viên, một tay |
| staff schedule | `/toi` | Nhân viên |
| treo | `/treo` | Cả hai |
| roster-grid | `/roster` | Quản lý — ghim ô + vòng đời lịch |
| constraints-inbox | `/inbox` | Quản lý duyệt |
| playbook | `/cam-nang` | Quản lý chạy 8 bước |
| sop-chat | `/sop` | Cả hai, bắt buộc trích dẫn |
| fairness | `/cong-bang` | Không xếp hạng tên |
| swap-market | `/doi-ca` | Ba nhánh |
| QR | `/qr` | Quản lý phát, NV dùng |
| tieu_thu | `/tieu-thu` | Số lượng, không kế toán |
| waste | `/hao-phi` | Ghi chú → cụm |
| handover | `/handover` | SBAR |
| agent-trace | `/vet` | Append-only audit |
| overflow | `/them` | Nav ≤5 trên điện thoại |

Trang `/` chỉ đưa vào đăng nhập hoặc chuyển `/hom-nay`. Không dump 10 liên kết.
