"use client";

import { useMemo, useState } from "react";
import {
  Btn,
  Empty,
  MeetingList,
  MeetingListItem,
  MeetingMetaRow,
  MeetingResultTabs,
  MeetingSection,
  StatusChip,
  inputClassName,
  propLabel,
  propTone,
  sopRankTone,
  vanDeLabel,
  vanDeTone,
  type ResultTab,
} from "./meeting-ui";

type ActionItem = {
  id: string;
  tieu_de: string;
  noi_dung_chi_tiet?: string;
  tinh_chat?: "bat_buoc" | "tuy_chon" | "khuyen_khich";
  ten_nguoi_giao?: string;
  ten_nguoi_nhan: string;
  pham_vi?: "ca_nhan" | "nhom";
  thoi_gian_bat_dau?: string;
  han_chot?: string;
  muc_do_uu_tien?: "cao" | "trung_binh" | "thap";
  do_tin_cay: number;
  da_chon?: boolean;
};

type CuocHop = {
  tieu_de: string;
  nguon_am_thanh?: string;
  transcript_thoai?: { nguoi_noi: string; noi_dung: string }[];
  tom_tat: string;
  van_de_phat_sinh?: { van_de: string; trang_thai: string; ghi_chu?: string }[];
  quyet_dinh?: string[];
  de_xuat_phe_duyet?: {
    id: string;
    loai_de_xuat: string;
    tieu_de: string;
    nguoi_de_xuat?: string;
    nguoi_phe_duyet?: string;
    noi_dung: string;
    ly_do?: string;
    trang_thai: string;
    quy_trinh_lien_quan?: string | null;
  }[];
  action_items: ActionItem[];
  gop_y_luu_y?: {
    id: string;
    nguoi_gop_y?: string;
    nguoi_nhan?: string;
    chu_de?: string;
    tinh_chat?: string;
    noi_dung: string;
    ghi_chu?: string;
  }[];
  audit_sop?: {
    diem_tuan_thu: number;
    xep_hang: string;
    tieu_chi: { ten_tieu_chi: string; dat: boolean; chi_tiet?: string }[];
    canh_bao_do?: string[];
    nhan_xet_chung?: string;
  };
  ban_tin_ca?: {
    ban_vip?: string[];
    luu_y_di_ung_khach?: string[];
    su_co_thiet_bi_khan?: string[];
    danh_sach_mon_86?: string[];
    noi_dung_tin_nhan_gui_nhom?: string;
  };
  huan_luyen_quan_ly?: {
    ty_le_noi_quan_ly_pct: number;
    ty_le_noi_nhan_vien_pct: number;
    diem_tuong_tac_2_chieu: number;
    diem_truyen_cam_hung: number;
    phong_cach_dieu_hanh?: string;
    loi_khuyen_ai_coaching?: string[];
  };
  de_xuat_sop?: { quy_trinh_lien_quan: string; buoc_so?: number | null; noi_dung_thay_doi: string; ly_do?: string }[];
  do_tin_cay_tong_the?: number;
  khong_lien_quan?: boolean;
};

function fbLabel(tinh_chat?: string): string {
  if (tinh_chat === "khen_ngoi") return "Khen ngợi";
  if (tinh_chat === "nhac_nho") return "Nhắc nhở";
  if (tinh_chat === "kinh_nghiem") return "Kinh nghiệm";
  return "Góp ý";
}

function fbTopic(chu_de?: string): string {
  if (chu_de === "thai_do_phuc_vu") return "Thái độ phục vụ";
  if (chu_de === "ky_nang_pha_che") return "Kỹ năng pha chế";
  if (chu_de === "ve_sinh_an_toan") return "Vệ sinh & an toàn";
  if (chu_de === "dong_vien_khen_ngoi") return "Động viên";
  return "Lưu ý chung";
}

function loaiDeXuatLabel(loai: string): string {
  if (loai === "quy_trinh_sop") return "Quy trình SOP";
  if (loai === "mua_sam_vat_tu") return "Mua sắm / vật tư";
  if (loai === "chinh_sach_nhan_su") return "Nhân sự";
  return "Khác";
}

export function MeetingResults({
  meeting,
  liveTranscript,
  manager,
  busy,
  copiedBroadcast,
  onCopyBroadcast,
  onToggleAction,
  onUpdateAssignee,
  onUpdateDue,
  onApply,
}: {
  meeting: CuocHop;
  liveTranscript: string;
  manager: boolean;
  busy: boolean;
  copiedBroadcast: boolean;
  onCopyBroadcast: (text: string) => void;
  onToggleAction: (id: string) => void;
  onUpdateAssignee: (id: string, name: string) => void;
  onUpdateDue: (id: string, due: string) => void;
  onApply: () => void;
}) {
  const [tab, setTab] = useState<ResultTab>("overview");
  const [transcriptOpen, setTranscriptOpen] = useState(false);

  const counts = useMemo(
    () => ({
      vanhanh: (meeting.van_de_phat_sinh?.length ?? 0) + (meeting.audit_sop ? 1 : 0),
      bantin:
        (meeting.ban_tin_ca ? 1 : 0) +
        (meeting.de_xuat_phe_duyet?.length ?? 0) +
        (meeting.de_xuat_sop?.length ?? 0),
      viec: meeting.action_items.length,
      coaching: (meeting.gop_y_luu_y?.length ?? 0) + (meeting.huan_luyen_quan_ly ? 1 : 0),
    }),
    [meeting],
  );

  const transcriptCount = meeting.transcript_thoai?.length ?? 0;

  return (
    <div className="space-y-4">
      <MeetingResultTabs active={tab} onChange={setTab} counts={counts} />

      {tab === "overview" ? (
        <div className="space-y-4">
          <div className="nq-meeting-transcript">
            <button
              type="button"
              className="nq-meeting-transcript__toggle"
              onClick={() => setTranscriptOpen((v) => !v)}
              aria-expanded={transcriptOpen}
            >
              <span>Bản bóc băng thoại</span>
              <span className="text-[var(--nq-ink-muted)]">
                {transcriptCount ? `${transcriptCount} đoạn` : "Ghi chép"} · {transcriptOpen ? "Thu gọn" : "Mở rộng"}
              </span>
            </button>
            {transcriptOpen ? (
              <div className="nq-meeting-transcript__body">
                {meeting.transcript_thoai && meeting.transcript_thoai.length > 0 ? (
                  meeting.transcript_thoai.map((t, idx) => (
                    <div key={idx} className="nq-meeting-transcript__line">
                      <span className="nq-meeting-transcript__speaker">{t.nguoi_noi || "Người nói"}</span>
                      <p className="m-0 text-sm leading-relaxed">{t.noi_dung}</p>
                    </div>
                  ))
                ) : (
                  <p className="m-0 text-sm text-[var(--nq-ink-muted)] italic">
                    {liveTranscript || "Đã trích xuất nội dung từ ghi chép cuộc họp."}
                  </p>
                )}
              </div>
            ) : null}
          </div>

          <div className="nq-meeting-grid-2">
            <article className="nq-meeting-panel">
              <h4 className="nq-meeting-panel__title">Tóm tắt cuộc họp</h4>
              <p className="nq-meeting-panel__body">{meeting.tom_tat}</p>
            </article>
            <article className="nq-meeting-panel">
              <h4 className="nq-meeting-panel__title">Quyết định đã chốt</h4>
              {meeting.quyet_dinh && meeting.quyet_dinh.length > 0 ? (
                <ul className="m-0 list-disc space-y-1 pl-5 text-sm leading-relaxed">
                  {meeting.quyet_dinh.map((q, idx) => (
                    <li key={idx}>{q}</li>
                  ))}
                </ul>
              ) : (
                <p className="nq-meeting-panel__body text-[var(--nq-ink-muted)] italic">
                  Duy trì đúng quy trình vận hành ca.
                </p>
              )}
            </article>
          </div>

          <p className="text-xs font-mono uppercase tracking-widest text-[var(--nq-ink-muted)]">
            Nguồn âm thanh: {meeting.nguon_am_thanh ?? "không rõ"}
          </p>
        </div>
      ) : null}

      {tab === "vanhanh" ? (
        <div className="space-y-5">
          {meeting.van_de_phat_sinh && meeting.van_de_phat_sinh.length > 0 ? (
            <MeetingSection title="Vấn đề phát sinh" count={meeting.van_de_phat_sinh.length}>
              <MeetingList>
                {meeting.van_de_phat_sinh.map((vd, idx) => (
                  <MeetingListItem
                    key={idx}
                    title={vd.van_de}
                    badge={<StatusChip tone={vanDeTone(vd.trang_thai)}>{vanDeLabel(vd.trang_thai)}</StatusChip>}
                    meta={vd.ghi_chu}
                  />
                ))}
              </MeetingList>
            </MeetingSection>
          ) : (
            <Empty>Không có vấn đề phát sinh cần theo dõi.</Empty>
          )}

          {meeting.audit_sop ? (
            <MeetingSection
              title="Kiểm soát tuân thủ SOP ca"
              hint="Đối soát nội dung briefing với tiêu chuẩn vận hành"
            >
              <div className="flex flex-wrap items-center gap-2 mb-3">
                <StatusChip tone={sopRankTone(meeting.audit_sop.xep_hang)}>
                  Hạng {meeting.audit_sop.xep_hang}
                </StatusChip>
                <StatusChip>{meeting.audit_sop.diem_tuan_thu}/100 điểm</StatusChip>
              </div>

              {meeting.audit_sop.canh_bao_do && meeting.audit_sop.canh_bao_do.length > 0 ? (
                <div className="nq-meeting-panel mb-3 border-[var(--nq-red)]">
                  <h4 className="nq-meeting-panel__title text-[var(--nq-red)]">Cảnh báo từ ban kiểm soát</h4>
                  <ul className="m-0 list-disc space-y-1 pl-5 text-sm">
                    {meeting.audit_sop.canh_bao_do.map((cb, i) => (
                      <li key={i}>{cb}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {meeting.audit_sop.tieu_chi?.length ? (
                <div className="nq-meeting-checklist">
                  {meeting.audit_sop.tieu_chi.map((tc, idx) => (
                    <div key={idx} className={`nq-meeting-check ${tc.dat ? "nq-meeting-check--ok" : ""}`}>
                      <span className="nq-meeting-check__mark">{tc.dat ? "Đạt" : "Bỏ sót"}</span>
                      <div>
                        <p className="m-0 font-semibold text-sm">{tc.ten_tieu_chi}</p>
                        {tc.chi_tiet ? <p className="m-0 mt-1 text-xs text-[var(--nq-ink-muted)]">{tc.chi_tiet}</p> : null}
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}

              {meeting.audit_sop.nhan_xet_chung ? (
                <p className="mt-3 text-sm text-[var(--nq-ink-muted)]">
                  <strong className="text-[var(--nq-fg)]">Nhận xét:</strong> {meeting.audit_sop.nhan_xet_chung}
                </p>
              ) : null}
            </MeetingSection>
          ) : null}
        </div>
      ) : null}

      {tab === "bantin" ? (
        <div className="space-y-5">
          {meeting.ban_tin_ca ? (
            <MeetingSection title="Bản tin ca khẩn" hint="VIP, dị ứng, sự cố thiết bị, món hết">
              <div className="flex flex-wrap justify-end gap-2 mb-3">
                {meeting.ban_tin_ca.noi_dung_tin_nhan_gui_nhom ? (
                  <Btn
                    variant="ghost"
                    onClick={() => onCopyBroadcast(meeting.ban_tin_ca?.noi_dung_tin_nhan_gui_nhom || "")}
                  >
                    {copiedBroadcast ? "Đã sao chép" : "Sao chép tin nhắn nhóm"}
                  </Btn>
                ) : null}
              </div>
              <div className="nq-meeting-broadcast-grid">
                <BroadcastCard title="Bàn VIP / đặt trước" items={meeting.ban_tin_ca.ban_vip} empty="Không có" />
                <BroadcastCard title="Khách dị ứng / lưu ý" items={meeting.ban_tin_ca.luu_y_di_ung_khach} empty="Không có" />
                <BroadcastCard title="Sự cố thiết bị" items={meeting.ban_tin_ca.su_co_thiet_bi_khan} empty="Bình thường" />
                <BroadcastCard title="Món hết (86)" items={meeting.ban_tin_ca.danh_sach_mon_86} empty="Đủ món" />
              </div>
              {meeting.ban_tin_ca.noi_dung_tin_nhan_gui_nhom ? (
                <pre className="mt-3 whitespace-pre-wrap rounded border border-[var(--nq-line)] bg-[var(--nq-bg)] p-3 font-mono text-xs leading-relaxed">
                  {meeting.ban_tin_ca.noi_dung_tin_nhan_gui_nhom}
                </pre>
              ) : null}
            </MeetingSection>
          ) : (
            <Empty>Chưa có bản tin ca từ cuộc họp này.</Empty>
          )}

          {meeting.de_xuat_phe_duyet && meeting.de_xuat_phe_duyet.length > 0 ? (
            <MeetingSection title="Đề xuất cần phê duyệt" count={meeting.de_xuat_phe_duyet.length}>
              <MeetingList>
                {meeting.de_xuat_phe_duyet.map((prop) => (
                  <MeetingListItem
                    key={prop.id}
                    title={prop.tieu_de}
                    badge={
                      <>
                        <StatusChip tone={propTone(prop.trang_thai)}>{propLabel(prop.trang_thai)}</StatusChip>
                        <StatusChip>{loaiDeXuatLabel(prop.loai_de_xuat)}</StatusChip>
                      </>
                    }
                    meta={
                      <>
                        <span>{prop.noi_dung}</span>
                        {prop.ly_do ? <span className="block mt-1 italic">Lý do: {prop.ly_do}</span> : null}
                        <MeetingMetaRow
                          items={[
                            ...(prop.nguoi_de_xuat ? [{ label: "Đề xuất", value: prop.nguoi_de_xuat }] : []),
                            ...(prop.nguoi_phe_duyet ? [{ label: "Duyệt", value: prop.nguoi_phe_duyet }] : []),
                            ...(prop.quy_trinh_lien_quan
                              ? [{ label: "Quy trình", value: prop.quy_trinh_lien_quan }]
                              : []),
                          ]}
                        />
                      </>
                    }
                  />
                ))}
              </MeetingList>
            </MeetingSection>
          ) : null}

          {(!meeting.de_xuat_phe_duyet || meeting.de_xuat_phe_duyet.length === 0) &&
          meeting.de_xuat_sop &&
          meeting.de_xuat_sop.length > 0 ? (
            <MeetingSection title="Đề xuất sửa cẩm nang" count={meeting.de_xuat_sop.length}>
              <MeetingList>
                {meeting.de_xuat_sop.map((sop, idx) => (
                  <MeetingListItem
                    key={idx}
                    title={`${sop.quy_trinh_lien_quan}${sop.buoc_so ? ` · bước ${sop.buoc_so}` : ""}`}
                    meta={
                      <>
                        <span>Nội dung sửa: {sop.noi_dung_thay_doi}</span>
                        {sop.ly_do ? <span className="block mt-1 italic">Lý do: {sop.ly_do}</span> : null}
                      </>
                    }
                  />
                ))}
              </MeetingList>
            </MeetingSection>
          ) : null}
        </div>
      ) : null}

      {tab === "viec" ? (
        <MeetingSection
          title="Công việc được giao"
          hint={`Độ tin cậy AI: ${Math.round((meeting.do_tin_cay_tong_the || 0.9) * 100)}%`}
          count={meeting.action_items.length}
        >
          {meeting.action_items.length === 0 ? (
            <Empty title="Không có việc giao">Không phát hiện công việc bắt buộc từ cuộc họp.</Empty>
          ) : (
            <div className="space-y-2.5">
              {meeting.action_items.map((it) => (
                <div key={it.id} className={`nq-meeting-action ${it.da_chon ? "" : "nq-meeting-action--off"}`}>
                  <div className="flex gap-3 items-start">
                    <input
                      type="checkbox"
                      checked={it.da_chon}
                      onChange={() => onToggleAction(it.id)}
                      className="mt-1 h-4 w-4 shrink-0 cursor-pointer accent-[var(--nq-copper)]"
                      aria-label={`Chọn việc ${it.tieu_de}`}
                    />
                    <div className="min-w-0 flex-1 space-y-2">
                      <div className="nq-meeting-list__row">
                        <p className="nq-meeting-list__title">{it.tieu_de}</p>
                        <StatusChip tone={it.tinh_chat === "bat_buoc" || !it.tinh_chat ? "danger" : "default"}>
                          {it.tinh_chat === "bat_buoc" || !it.tinh_chat ? "Bắt buộc" : "Khuyến khích"}
                        </StatusChip>
                        <StatusChip>{it.pham_vi === "ca_nhan" ? "Cá nhân" : "Nhóm ca"}</StatusChip>
                        {it.muc_do_uu_tien === "cao" ? <StatusChip tone="warn">Ưu tiên cao</StatusChip> : null}
                        <StatusChip tone={it.do_tin_cay >= 0.9 ? "ok" : it.do_tin_cay >= 0.75 ? "warn" : "danger"}>
                          {Math.round(it.do_tin_cay * 100)}% tin cậy
                        </StatusChip>
                      </div>

                      {it.noi_dung_chi_tiet ? (
                        <div className="nq-meeting-action__detail">
                          <strong>Chi tiết:</strong> {it.noi_dung_chi_tiet}
                        </div>
                      ) : null}

                      <div className="nq-meeting-action__fields">
                        {it.ten_nguoi_giao ? (
                          <span>
                            Giao từ: <strong>{it.ten_nguoi_giao}</strong>
                          </span>
                        ) : null}
                        <label className="flex items-center gap-1.5">
                          Giao cho:
                          <input
                            type="text"
                            className={`${inputClassName} nq-input--compact w-32`}
                            value={it.ten_nguoi_nhan}
                            onChange={(e) => onUpdateAssignee(it.id, e.target.value)}
                          />
                        </label>
                        {it.thoi_gian_bat_dau ? (
                          <span>
                            Bắt đầu: <strong>{it.thoi_gian_bat_dau}</strong>
                          </span>
                        ) : null}
                        <label className="flex items-center gap-1.5">
                          Hạn chót:
                          <input
                            type="text"
                            className={`${inputClassName} nq-input--compact w-28`}
                            value={it.han_chot || ""}
                            onChange={(e) => onUpdateDue(it.id, e.target.value)}
                          />
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </MeetingSection>
      ) : null}

      {tab === "coaching" ? (
        <div className="space-y-5">
          {meeting.gop_y_luu_y && meeting.gop_y_luu_y.length > 0 ? (
            <MeetingSection title="Góp ý & lưu ý nội bộ" count={meeting.gop_y_luu_y.length}>
              <MeetingList>
                {meeting.gop_y_luu_y.map((fb) => (
                  <MeetingListItem
                    key={fb.id}
                    title={fb.noi_dung}
                    badge={
                      <>
                        <StatusChip>{fbLabel(fb.tinh_chat)}</StatusChip>
                        <StatusChip>{fbTopic(fb.chu_de)}</StatusChip>
                      </>
                    }
                    meta={
                      <>
                        {fb.nguoi_gop_y ? `Từ: ${fb.nguoi_gop_y}` : null}
                        {fb.nguoi_nhan ? ` · Gửi đến: ${fb.nguoi_nhan}` : null}
                        {fb.ghi_chu ? ` · ${fb.ghi_chu}` : null}
                      </>
                    }
                  />
                ))}
              </MeetingList>
            </MeetingSection>
          ) : (
            <Empty>Chưa có góp ý nội bộ từ cuộc họp.</Empty>
          )}

          {meeting.huan_luyen_quan_ly ? (
            <MeetingSection
              title="Huấn luyện quản lý"
              hint={meeting.huan_luyen_quan_ly.phong_cach_dieu_hanh || "Phong cách điều hành ca"}
            >
              <div className="nq-meeting-ratio">
                <div className="nq-meeting-ratio__labels">
                  <span>
                    Quản lý nói: <strong>{meeting.huan_luyen_quan_ly.ty_le_noi_quan_ly_pct}%</strong>
                  </span>
                  <span>
                    Nhân viên: <strong>{meeting.huan_luyen_quan_ly.ty_le_noi_nhan_vien_pct}%</strong>
                  </span>
                </div>
                <div className="nq-meeting-ratio__bar">
                  <div
                    className="nq-meeting-ratio__bar-mgr h-full"
                    style={{ width: `${meeting.huan_luyen_quan_ly.ty_le_noi_quan_ly_pct}%` }}
                  />
                  <div
                    className="nq-meeting-ratio__bar-staff h-full"
                    style={{ width: `${meeting.huan_luyen_quan_ly.ty_le_noi_nhan_vien_pct}%` }}
                  />
                </div>
                <p className="mt-2 mb-0 text-xs text-[var(--nq-ink-muted)]">
                  {meeting.huan_luyen_quan_ly.ty_le_noi_quan_ly_pct > 85
                    ? "Quản lý đang nói quá nhiều (>85%). Nên đặt thêm câu hỏi cho nhân viên."
                    : meeting.huan_luyen_quan_ly.ty_le_noi_quan_ly_pct < 50
                    ? "Quản lý nói ít (<50%). Cần dẫn dắt mục tiêu ca rõ hơn."
                    : "Tỷ lệ giao tiếp cân bằng giữa giao việc và lắng nghe."}
                </p>
              </div>

              <div className="grid gap-2 sm:grid-cols-2 mt-3">
                <div className="nq-meeting-panel flex items-center justify-between gap-3">
                  <div>
                    <p className="m-0 text-sm font-semibold">Tương tác 2 chiều</p>
                    <p className="m-0 mt-1 text-xs text-[var(--nq-ink-muted)]">Hỏi han & lắng nghe</p>
                  </div>
                  <StatusChip>{meeting.huan_luyen_quan_ly.diem_tuong_tac_2_chieu}/10</StatusChip>
                </div>
                <div className="nq-meeting-panel flex items-center justify-between gap-3">
                  <div>
                    <p className="m-0 text-sm font-semibold">Truyền cảm hứng</p>
                    <p className="m-0 mt-1 text-xs text-[var(--nq-ink-muted)]">Khen ngợi & động viên</p>
                  </div>
                  <StatusChip>{meeting.huan_luyen_quan_ly.diem_truyen_cam_hung}/10</StatusChip>
                </div>
              </div>

              {meeting.huan_luyen_quan_ly.loi_khuyen_ai_coaching &&
              meeting.huan_luyen_quan_ly.loi_khuyen_ai_coaching.length > 0 ? (
                <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">
                  {meeting.huan_luyen_quan_ly.loi_khuyen_ai_coaching.map((tip, idx) => (
                    <li key={idx}>{tip}</li>
                  ))}
                </ul>
              ) : null}
            </MeetingSection>
          ) : null}
        </div>
      ) : null}

      {meeting.khong_lien_quan ? (
        <p className="text-sm text-[var(--nq-ink-muted)]">
          Nội dung bóc băng không liên quan vận hành quán. AI không tạo việc giao — vui lòng kiểm tra nguồn âm thanh.
        </p>
      ) : null}

      <div className="nq-meeting-footer">
        <p className="nq-meeting-footer__note">
          Sau khi duyệt, việc được chọn sẽ đẩy vào OpsEngine (việc treo ca); đề xuất cẩm nang ghi vào Playbook.
        </p>
        <Btn variant="primary" onClick={onApply} disabled={busy || !manager}>
          {manager ? "Duyệt & phân công vào ca" : "Cần quyền quản lý để duyệt"}
        </Btn>
      </div>
    </div>
  );
}

function BroadcastCard({ title, items, empty }: { title: string; items?: string[]; empty: string }) {
  return (
    <article className="nq-meeting-broadcast-card">
      <h5>{title}</h5>
      {items && items.length > 0 ? (
        <ul>
          {items.map((v, i) => (
            <li key={i}>{v}</li>
          ))}
        </ul>
      ) : (
        <p className="m-0 text-xs text-[var(--nq-ink-muted)] italic">{empty}</p>
      )}
    </article>
  );
}
