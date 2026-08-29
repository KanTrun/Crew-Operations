"use client";

/**
 * Một ngày của quán, viết thẳng ra chữ.
 *
 * Tour phủ lên `/hom-nay` chỉ nói được một câu cho mỗi vùng. Người mới còn cần
 * thứ tự: sáng ai làm gì, tối ai chốt gì. Trang này không gọi API — nó là bản
 * đồ của sản phẩm, đọc được cả khi chưa có tài khoản, nên cũng là đích cho liên
 * kết ở màn đăng nhập và đăng ký.
 */

import { BtnLink, Kicker, OpsCard, PageActions, PageHeader } from "../../ui/kit";

type Buoc = { ai: string; viec: string; giai_thich: string; hoi?: string };

const MOT_NGAY: Buoc[] = [
  {
    ai: "Nhân viên ca sáng",
    viec: "Điểm danh rồi mở phiếu Mở quán",
    giai_thich:
      "Phiếu mở quán có 20 bước, hiện từng bước một. Bước cần ảnh thì phiếu mở camera, bước cần số thì phiếu hỏi số. Bước gần cuối là đọc việc treo của ca trước — đó là chỗ hai ca nói chuyện với nhau.",
    hoi: "Mở quán gồm những bước nào?",
  },
  {
    ai: "Nhân viên trong ca",
    viec: "Kẹt gì thì treo lại, đừng nhớ bằng miệng",
    giai_thich:
      "Máy pha kêu lạ, hết ống hút cỡ lớn, tủ mát không đủ lạnh: treo ngay trên phiếu. Việc treo có hạn; quá hạn thì nổi lên đầu danh sách và hiện trên bảng Hôm nay của quản lý.",
    hoi: "Việc treo thì ai phải xử lý?",
  },
  {
    ai: "Nhân viên giao ca",
    viec: "Chạy phiếu Bàn giao ca 5 bước",
    giai_thich:
      "Kể đã xảy ra gì, cần để ý gì, việc gì treo lại, rồi người nhận ca xác nhận đã đọc. Không xác nhận thì phiếu chưa đóng được.",
  },
  {
    ai: "Nhân viên ca cuối",
    viec: "Chạy phiếu Đóng quán 4 bước",
    giai_thich:
      "Kiểm kê 8 mặt hàng chính, ghi hao hụt trong ca, tắt gas và điện, khoá cửa. Số kiểm kê chảy vào sổ tiêu thụ; mặt hàng dưới ngưỡng sẽ thành cảnh báo tồn sáng mai.",
    hoi: "Hao phí ghi thế nào cho đúng?",
  },
  {
    ai: "Quản lý",
    viec: "Xếp lịch tuần rồi công bố",
    giai_thich:
      "Ghim người vào ô ca, hệ thống kiểm ràng buộc và gợi ý. Trước khi công bố thì nhân viên chưa thấy lịch, nên bạn sửa thoải mái. Mỗi lần sửa đều để lại vết.",
    hoi: "Ca sáng cần bao nhiêu người?",
  },
  {
    ai: "Quản lý",
    viec: "Quyết hộp thư ràng buộc",
    giai_thich:
      "Khi hai ràng buộc đâm nhau, hệ thống không tự chọn. Nó tóm tắt kèm độ tin cậy rồi để bạn duyệt hoặc từ chối. Đó là chỗ người giữ quyền quyết, không phải máy.",
    hoi: "Khi nào một đề nghị đổi ca được coi là đã đồng ý?",
  },
  {
    ai: "Cả quán",
    viec: "Cẩm nang tự lớn lên từ việc thật",
    giai_thich:
      "Bốn lần sửa cùng một kiểu thì hệ thống đề xuất thành luật, qua vòng kiểm rồi tập sự 5 lượt mới vào hiệu lực. Luật nói về một người cụ thể bị loại thẳng; luật lâu không ai dùng thì tự tắt.",
    hoi: "Ly nhựa còn bao nhiêu thì phải nhập thêm?",
  },
];

export default function HuongDanPage() {
  return (
    <div className="nq-page">
      <PageHeader
        kicker="Người lần đầu đọc trang này"
        title="Một ngày của quán"
        meta="Bảy việc, theo đúng thứ tự chúng xảy ra trong ngày. Mỗi việc nói rõ ai làm và làm để được gì."
      />

      <OpsCard eyebrow="Thứ tự trong ngày" title="Từ mở quán tới khoá cửa" count={MOT_NGAY.length} countLabel="việc">
        <ol className="nq-flow">
          {MOT_NGAY.map((b) => (
            <li key={b.viec}>
              <p className="nq-flow-who">{b.ai}</p>
              <p className="nq-flow-title">{b.viec}</p>
              <p className="nq-flow-what">{b.giai_thich}</p>
              {b.hoi ? (
                <a className="nq-ask" href={`/sop?q=${encodeURIComponent(b.hoi)}`}>
                  Hỏi cẩm nang: {b.hoi}
                </a>
              ) : null}
            </li>
          ))}
        </ol>
      </OpsCard>

      <OpsCard eyebrow="Hỏi khi bí" title="Hỏi cẩm nang, không phải hỏi chatbot">
        <Kicker>Trả lời có trích dẫn</Kicker>
        <p className="nq-muted" style={{ maxWidth: "64ch" }}>
          Trang Hỏi SOP chỉ đọc mẫu phiếu và luật đã duyệt của quán rồi dẫn lại kèm nguồn. Không có
          căn cứ thì nó nói thẳng là chưa có trong cẩm nang, để bạn làm theo cách quán đang làm rồi
          nhờ quản lý ghi thành luật. Nó không đoán, nên câu trả lời nào cũng kiểm được.
        </p>
        <PageActions>
          <BtnLink href="/sop">Mở trang Hỏi SOP</BtnLink>
          <BtnLink href="/them" variant="ghost">
            Xem lại hướng dẫn từng vùng
          </BtnLink>
        </PageActions>
      </OpsCard>
    </div>
  );
}
