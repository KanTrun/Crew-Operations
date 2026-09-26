"use client";

/**
 * Nhật ký thay đổi ca — "ai đổi ca với ai", đọc được bằng mắt thường.
 *
 * Vì sao tách thành component riêng: cùng một câu hỏi được hỏi ở hai chỗ —
 * `/lich-tuan` (sau khi xếp tự động) và `/doi-ca` (sau khi chốt phiếu đổi ca).
 * Hai nơi tự vẽ thì sẽ có hai cách trình bày khác nhau cho cùng một dữ liệu, và
 * người dùng phải học lại cách đọc ở mỗi trang.
 *
 * Nguyên tắc trình bày (theo đúng phàn nàn của người dùng):
 *  - In TÊN người, không in mã `nv_xx`.
 *  - Phân biệt RÕ ba chuyện khác nhau: CA đổi người · NGƯỜI chuyển ca · LƯỢT
 *    vào/ra lẻ. Gộp chúng lại thành "3 thay đổi" là vô nghĩa với người đọc.
 *  - Không có gì đổi thì nói thẳng "không có gì đổi", đừng hiện bảng rỗng.
 *  - Thiếu dữ liệu thì nói "chưa đủ dữ liệu", KHÔNG nói "không có gì đổi".
 */

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import { getToken } from "../../lib/session";
import { Empty, Loading, StatusChip } from "../../ui/kit";
import type { Diff } from "./shift-change-types";

export type { Diff, ChuyenCa, DongThayDoi, HoanDoi } from "./shift-change-types";

type BanGhi = {
  luc: string;
  nguon: string;
  tuan_iso: string;
  diff: Diff;
  tom_tat?: string;
};

const NGUON_LABEL: Record<string, string> = {
  xep_tu_dong: "Xếp tự động",
  tkb: "Lịch bận (TKB)",
  doi_ca: "Chợ đổi ca",
  cu_bi: "Trực dự bị",
};

function gioHienThi(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Bảng chứng minh đổi ca cho MỘT bản ghi diff. */
export function ShiftChangeDiff({ diff }: { diff: Diff }) {
  if (diff.khong_so_sanh_duoc) {
    return (
      <p className="nq-shiftdiff__empty">
        Chưa đủ dữ liệu để so sánh hai bản phân công (một bên chưa có lịch).
      </p>
    );
  }
  const rong =
    diff.hoan_doi.length === 0 &&
    diff.doi_giua_hai_ca.length === 0 &&
    diff.them.length === 0 &&
    diff.bot.length === 0;

  if (rong) {
    return <p className="nq-shiftdiff__empty">Không có ca nào thay đổi.</p>;
  }

  return (
    <div className="nq-shiftdiff">
      {diff.hoan_doi.length > 0 ? (
        <section className="nq-shiftdiff__block">
          <h4 className="nq-shiftdiff__title">Ca đổi người</h4>
          <ul className="nq-shiftdiff__list">
            {diff.hoan_doi.map((h) => (
              <li key={h.ca.ca_id} className="nq-shiftdiff__row">
                <span className="nq-shiftdiff__when">
                  {h.ca.thu} · {h.ca.gio}
                </span>
                <span className="nq-shiftdiff__who">
                  <span className="nq-shiftdiff__out">{h.ra.map((r) => r.ten).join(", ")}</span>
                  <span className="nq-shiftdiff__arrow">ra</span>
                  <span className="nq-shiftdiff__in">{h.vao.map((v) => v.ten).join(", ")}</span>
                  <span className="nq-shiftdiff__arrow">vào</span>
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {diff.doi_giua_hai_ca.length > 0 ? (
        <section className="nq-shiftdiff__block">
          <h4 className="nq-shiftdiff__title">Người chuyển sang ca khác (không mất ca)</h4>
          <ul className="nq-shiftdiff__list">
            {diff.doi_giua_hai_ca.map((c) => (
              <li key={c.nv_id} className="nq-shiftdiff__row">
                <span className="nq-shiftdiff__who">
                  <strong>{c.ten}</strong>
                  <span className="nq-shiftdiff__arrow">
                    {c.tu_ca.map((t) => `${t.thu} ${t.gio}`).join(", ")} →{" "}
                    {c.den_ca.map((d) => `${d.thu} ${d.gio}`).join(", ")}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {diff.bot.length > 0 || diff.them.length > 0 ? (
        <section className="nq-shiftdiff__block">
          <h4 className="nq-shiftdiff__title">Lượt vào / ra ca</h4>
          <ul className="nq-shiftdiff__tags">
            {diff.bot.map((b) => (
              <li key={`ra-${b.ca.ca_id}-${b.nv_id}`} data-chieu="ra">
                {b.ten} ra khỏi {b.ca.thu} {b.ca.gio}
              </li>
            ))}
            {diff.them.map((t) => (
              <li key={`vao-${t.ca.ca_id}-${t.nv_id}`} data-chieu="vao">
                {t.ten} vào {t.ca.thu} {t.ca.gio}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <p className="nq-shiftdiff__keep">
        Giữ nguyên {diff.giu_nguyen} lượt phân công không đổi.
      </p>
    </div>
  );
}

/**
 * Panel nhật ký: tự tải `/api/v1/lich-tuan/thay-doi` cho một tuần.
 *
 * `compact` dùng cho chỗ chật (trang /doi-ca) — chỉ hiện bản mới nhất.
 * Chỉ quản lý/chủ mới gọi được endpoint; nhân viên sẽ nhận 403 và panel tự ẩn
 * (không hiện lỗi đỏ vì đây không phải hành động của họ).
 */
export function ShiftChangeLog({
  tuanIso,
  compact = false,
}: {
  tuanIso: string;
  compact?: boolean;
}) {
  const [items, setItems] = useState<BanGhi[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [hidden, setHidden] = useState(false);

  const load = useCallback(() => {
    if (!getToken() || !tuanIso) return;
    setLoading(true);
    apiGet<{ items?: BanGhi[] }>(`/api/v1/lich-tuan/thay-doi?tuan_iso=${encodeURIComponent(tuanIso)}`)
      .then((d) => setItems(d.items ?? []))
      .catch(() => setHidden(true))
      .finally(() => setLoading(false));
  }, [tuanIso]);

  useEffect(() => {
    load();
  }, [load]);

  if (hidden) return null;
  if (loading && items === null) return <Loading skeleton="rows">Đang tải nhật ký…</Loading>;
  if (!items || items.length === 0) {
    if (compact) return null;
    return (
      <Empty>
        Tuần {tuanIso} chưa có lần xếp lịch nào ghi lại thay đổi. Nhật ký xuất hiện sau
        khi xếp lịch tự động hoặc xếp lại vì lịch bận.
      </Empty>
    );
  }

  const hienThi = compact ? items.slice(0, 1) : items;

  return (
    <div className="nq-shiftlog">
      {hienThi.map((b) => (
        <article key={`${b.luc}-${b.tom_tat ?? ""}`} className="nq-shiftlog__entry">
          <header className="nq-shiftlog__head">
            <StatusChip tone="info">{NGUON_LABEL[b.nguon] ?? b.nguon}</StatusChip>
            <span className="nq-shiftlog__time">{gioHienThi(b.luc)}</span>
          </header>
          {b.tom_tat ? <p className="nq-shiftlog__summary">{b.tom_tat}</p> : null}
          {b.diff ? <ShiftChangeDiff diff={b.diff} /> : null}
        </article>
      ))}
      {compact && items.length > 1 ? (
        <p className="nq-shiftlog__more">Còn {items.length - 1} lần thay đổi khác trong tuần này.</p>
      ) : null}
    </div>
  );
}
