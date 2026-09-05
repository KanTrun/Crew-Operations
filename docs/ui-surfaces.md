# Ánh xạ mặt hồ sơ → web sản phẩm

Hồ sơ §11 (`apps/web` constraints-inbox / run-form / today / playbook / sop-chat) và `docs/design-guidelines.md`.

| Mặt hồ sơ | Route | Vai trò chính |
|-----------|-------|----------------|
| today | `/hom-nay` | Cả hai — hub sau đăng nhập |
| run-form | `/phieu` | Nhân viên, một tay |
| staff schedule | `/toi` | Nhân viên |
| tkb-photo | `/tkb` | Upload ảnh TKB → AI đọc → xác nhận gắn NV |
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
| channels bind | `/toi` (mục Nối Zalo/Telegram) | NV lấy mã bind; ưu tiên Zalo OA |
| page-quan | `/page-quan` | Facebook Page quán — trống tới khi nối Meta |

Trang `/` chỉ đưa vào đăng nhập hoặc chuyển `/hom-nay`. Không dump 10 liên kết.

## AG-COPILOT trong vận hành

Pane AG-COPILOT là lớp đề xuất có duyệt, không phải điểm ghi dữ liệu trực tiếp. Người vận hành mở pane bằng nút `Hỏi AG-COPILOT` tại các route có ngữ cảnh thao tác: `/roster`, `/qr`, `/phieu`, `/treo`, `/cong-bang`, `/tkb`, `/handover`, và `/doi-ca`. Proposal từ cả JSON lẫn SSE phải có draft và audit bền vững trước khi UI hiển thị thao tác duyệt.

Kênh tin: Zalo trước, Telegram phụ; webhook + token trong `.env` — xem `docs/runbooks/zalo-oa-connect.md`. Replay fixture chỉ CI.
