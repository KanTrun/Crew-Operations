"use client";

/**
 * Cẩm nang quán — 12 luật, năm loại, năm chặng đời.
 *
 * Hồ sơ §9.3 đòi mỗi luật hiện đủ bốn thứ, và trước đây trang này chỉ hiện thứ
 * nhất rưỡi:
 *  1. **Câu luật** viết bằng tiếng Việt.
 *  2. **Nguồn gốc bấm xem được** — luật này sinh từ mấy lần sửa thật, thuộc mẫu
 *     lặp lại nào, dừng ở bước nào trong tám bước. Để trong `<details>` vì đó là
 *     thứ người ta chỉ mở khi cần kiểm, không phải thứ đọc mỗi lần.
 *  3. **Kết quả tập sự** — máy đề xuất và người làm thật khớp nhau bao nhiêu lượt
 *     trên tổng số lượt cần.
 *  4. **Số lần áp dụng và số lần bị ghi đè** — luật được dùng bao nhiêu, bị người
 *     bỏ qua bao nhiêu. Tỉ lệ ghi đè cao là lý do luật tự tắt.
 *
 * Luật bị vòng kiểm loại và luật tự tắt nằm ở nhóm riêng, viền trái đổi màu, kèm
 * một câu nói vì sao — trộn chung với luật đang hiệu lực là mời người đọc tin vào
 * một luật đã chết.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import {
  loaiLuatLabel,
  luatLabel,
  luatTone,
  safeNumber,
  safeText,
  vfRuleLyDo,
  viError,
} from "../../lib/present";
import { getToken, isManager } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  BtnLink,
  Empty,
  Loading,
  NextSteps,
  Notice,
  PageHeader,
  StatusChip,
  Summary,
  TechnicalDrawer,
  Toasts,
  useToasts,
} from "../../ui/kit";

type Luat = {
  id: string;
  cau?: string;
  loai?: string;
  loai_ho_so?: string;
  trang_thai: string;
  buoc?: number;
  vf_rule?: string;
  bang_chung?: string[];
  tap_su_dung?: number;
  tap_su_tong?: number;
  ap_dung?: number;
  ghi_de?: number;
  ti_le_dung?: number;
  nguoi_duyet?: string;
  ly_do_tu_choi?: string;
};

type Mau = { mau?: string; loai_luat?: string; n?: number; nguon?: string };

type CamNang = { items?: Luat[]; mau?: Mau[] };

/**
 * Ba họ luật, theo việc người đọc cần làm với chúng.
 *
 * Không nhóm theo loại luật (ngưỡng tồn / bước phiếu…) vì loại không nói được
 * luật còn sống hay đã chết — mà đó chính là câu hỏi đầu tiên khi mở cẩm nang.
 */
const HO: Array<{
  ma: string;
  ten: string;
  vi_sao: string;
  trang_thai: string[];
}> = [
  {
    ma: "song",
    ten: "Luật đang chạy trong quán",
    vi_sao:
      "Đã qua vòng kiểm và đủ lượt tập sự. Hệ thống dùng những luật này khi xếp lịch và khi sinh bước phiếu.",
    trang_thai: ["hieu_luc"],
  },
  {
    ma: "cho",
    ten: "Đang trên đường vào cẩm nang",
    vi_sao:
      "Mới đề xuất hoặc mới qua vòng kiểm, chưa đủ lượt tập sự nên chưa có hiệu lực. Chạy 8 bước để đẩy tiếp.",
    trang_thai: ["de_xuat", "qua_vf_rule", "du_tap_su", "truot_tap_su"],
  },
  {
    ma: "chet",
    ten: "Đã dừng — bị loại, bị từ chối, hoặc tự tắt",
    vi_sao:
      "Giữ lại để tra, nhưng hệ thống không dùng. Luật bị vòng kiểm loại kèm lý do; luật tự tắt là luật lâu không ai theo.",
    trang_thai: ["loai", "tu_choi", "tu_tat"],
  },
];

function hoCuaLuat(tt: string): string {
  for (const h of HO) if (h.trang_thai.includes(tt)) return h.ma;
  return "cho";
}

/** Một luật, đủ hồ sơ §9.3. */
function TheLuat({ luat, mau }: { luat: Luat; mau: Mau[] }) {
  const tt = safeText(luat.trang_thai, "");
  const tone = luatTone(tt);
  const bangChung = (luat.bang_chung ?? []).length;
  const tapSu = typeof luat.tap_su_dung === "number" ? luat.tap_su_dung : 0;
  const tapSuTong = typeof luat.tap_su_tong === "number" && luat.tap_su_tong > 0 ? luat.tap_su_tong : 5;
  const apDung = typeof luat.ap_dung === "number" ? luat.ap_dung : 0;
  const ghiDe = typeof luat.ghi_de === "number" ? luat.ghi_de : 0;
  const loai = safeText(luat.loai_ho_so, safeText(luat.loai, ""));
  // Mẫu lặp lại đã sinh ra loại luật này — đây là "nguồn gốc" theo nghĩa §9.3.
  const mauNguon = mau.filter((m) => safeText(m.loai_luat, "") === loai);
  const biLoai = tt === "loai";
  const tuTat = tt === "tu_tat";
  const tuChoi = tt === "tu_choi";

  return (
    <article className="nq-rule" data-tone={tone}>
      <div className="nq-rule-head">
        <StatusChip tone={tone}>{luatLabel(tt)}</StatusChip>
        <StatusChip>{loaiLuatLabel(loai)}</StatusChip>
        {typeof luat.buoc === "number" ? (
          <span className="nq-count">bước {luat.buoc} / 8</span>
        ) : null}
      </div>

      <p className="nq-rule-cau">{safeText(luat.cau, "Luật chưa có câu diễn giải")}</p>

      {biLoai ? <p className="nq-rule-why">{vfRuleLyDo(luat.vf_rule)}</p> : null}
      {tuChoi ? (
        <p className="nq-rule-why">
          Quản lý từ chối luật này{luat.ly_do_tu_choi ? `: ${safeText(luat.ly_do_tu_choi)}` : "."} Muốn
          dùng lại thì đề xuất lần nữa kèm bằng chứng mới.
        </p>
      ) : null}
      {tuTat ? (
        <p className="nq-rule-why">
          Luật tự tắt vì bị ghi đè {ghiDe} lần trên {apDung} lần áp dụng — người trong quán làm khác nó
          đủ nhiều để nó không còn phản ánh cách quán chạy.
        </p>
      ) : null}

      <div className="nq-rule-facts">
        <div>
          <span className="nq-fact-k">Kết quả tập sự</span>
          <span className="nq-fact-v">
            {tapSu} / {tapSuTong}
          </span>
          <span className="nq-fact-note">
            {tapSu >= tapSuTong
              ? "Máy đề xuất khớp việc người làm thật đủ số lượt cần."
              : tapSu === 0
                ? "Chưa vào tập sự."
                : `Còn ${tapSuTong - tapSu} lượt nữa mới đủ.`}
          </span>
        </div>
        <div>
          <span className="nq-fact-k">Đã áp dụng</span>
          <span className="nq-fact-v">{apDung}</span>
          <span className="nq-fact-note">lần hệ thống dùng luật này khi xếp lịch hoặc sinh bước</span>
        </div>
        <div>
          <span className="nq-fact-k">Bị ghi đè</span>
          <span className="nq-fact-v">{ghiDe}</span>
          <span className="nq-fact-note">
            {typeof luat.ti_le_dung === "number"
              ? `tỉ lệ theo luật ${safeNumber(luat.ti_le_dung * 100, 0)}%`
              : "lần người trong quán làm khác luật"}
          </span>
        </div>
      </div>

      <details className="nq-src">
        <summary>Xem nguồn gốc luật này</summary>
        <dl className="nq-src-body">
          <dt>Bằng chứng</dt>
          <dd>
            {bangChung > 0
              ? `${bangChung} lần sửa thật trong sổ ghi nhận đã dẫn tới luật này. Bốn lần cùng một mẫu là ngưỡng hệ thống bắt đầu đề xuất.`
              : "Chưa có lần sửa nào làm bằng chứng — luật này chưa đứng được."}
          </dd>
          <dt>Mẫu lặp lại</dt>
          <dd>
            {mauNguon.length > 0
              ? mauNguon
                  .map((m) => `${loaiLuatLabel(m.loai_luat)}: ${typeof m.n === "number" ? m.n : 0} lần lặp`)
                  .join(" · ")
              : "Không tìm thấy mẫu lặp lại tương ứng trong lượt gom gần nhất."}
          </dd>
          <dt>Chặng đã đi</dt>
          <dd>
            Dừng ở bước {typeof luat.buoc === "number" ? luat.buoc : "chưa rõ"} trong tám bước xét luật.
            Vòng kiểm nói: {vfRuleLyDo(luat.vf_rule)}
          </dd>
          <dt>Người chốt</dt>
          <dd>
            {luat.nguoi_duyet === "chu_quan"
              ? "Chủ quán đã chốt luật này."
              : luat.nguoi_duyet === "quan_ly"
                ? "Quản lý đã chốt luật này."
                : "Chưa có người chốt — luật còn trong quy trình."}
          </dd>
        </dl>
      </details>
    </article>
  );
}

export default function CamNangPage() {
  const [token, setToken] = useState("");
  const [manager, setManager] = useState(false);
  const [items, setItems] = useState<Luat[]>([]);
  const [mau, setMau] = useState<Mau[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [soThat, setSoThat] = useState<number | null>(null);
  const [chiTiet, setChiTiet] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const { toasts, push, dismiss } = useToasts();

  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    setLoading(true);
    apiGet<CamNang>("/api/v1/cam-nang")
      .then((d) => {
        setItems((d.items ?? []).filter((x) => x && typeof x.id === "string"));
        setMau(d.mau ?? []);
        setError(null);
      })
      .catch((e) => setError(viError(e, { doing: "mở được cẩm nang quán" })))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  async function chay() {
    setError(null);
    setBusy(true);
    try {
      const d = await apiSend<{ bi_loai?: { vf_rule?: string }; so_luat_that_quan?: number }>(
        "/api/v1/cam-nang/chay-8-buoc",
      );
      const that = typeof d.so_luat_that_quan === "number" ? d.so_luat_that_quan : 0;
      setSoThat(that);
      push(
        that > 0
          ? `Đã chạy đủ 8 bước. Quán đang có ${that} luật sinh từ người thật.`
          : "Đã chạy đủ 8 bước. Chưa có luật nào sinh từ người quán thật — cần thêm lần sửa có bằng chứng.",
      );
      // Mã cổng VF là chi tiết kỹ thuật: để trong ngăn, không phơi lên thân trang.
      setChiTiet([`Cổng loại luật: ${safeText(d.bi_loai?.vf_rule, "không có luật nào bị loại")}`]);
      load();
    } catch (e) {
      setError(
        viError(e, {
          doing: "chạy được 8 bước cẩm nang",
          forbidden: "Chỉ quản lý hoặc chủ quán chạy được 8 bước.",
          conflict: "Chưa đủ lần sửa có bằng chứng để chạy 8 bước. Ghi thêm lần sửa rồi chạy lại.",
        }),
      );
    } finally {
      setBusy(false);
    }
  }

  const nhom = useMemo(() => {
    const m = new Map<string, Luat[]>();
    for (const l of items) {
      const k = hoCuaLuat(safeText(l.trang_thai, ""));
      m.set(k, [...(m.get(k) ?? []), l]);
    }
    return HO.filter((h) => (m.get(h.ma) ?? []).length > 0).map(
      (h) => [h, m.get(h.ma) ?? []] as const,
    );
  }, [items]);

  const demHo = useCallback(
    (ma: string) => items.filter((l) => hoCuaLuat(safeText(l.trang_thai, "")) === ma).length,
    [items],
  );

  const soLoai = useMemo(
    () => new Set(items.map((l) => safeText(l.loai_ho_so, safeText(l.loai, "khac")))).size,
    [items],
  );

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page">
      <PageHeader
        kicker="Cẩm nang sống"
        title="Cẩm nang quán"
        meta="Luật của quán chỉ có hiệu lực khi đủ bằng chứng từ lần sửa thật và qua được vòng kiểm. Mỗi thẻ dưới đây mở ra được nguồn gốc của luật."
      />

      {items.length > 0 ? (
        <Summary
          cells={[
            { n: items.length, k: "luật trong cẩm nang" },
            { n: demHo("song"), k: "đang chạy", tone: "ok" },
            { n: demHo("cho"), k: "đang xét", tone: "warn" },
            { n: demHo("chet"), k: "đã dừng", tone: "danger" },
            { n: soLoai, k: "loại luật" },
            ...(soThat != null ? [{ n: soThat, k: "sinh từ người thật" as const }] : []),
          ]}
        />
      ) : null}

      {manager ? (
        <Btn variant="primary" busy={busy} busyLabel="Đang chạy 8 bước…" onClick={chay}>
          Chạy 8 bước xét luật
        </Btn>
      ) : (
        <Notice>Bạn xem được luật quán. Quản lý hoặc chủ quán mới chạy 8 bước xét luật.</Notice>
      )}
      {error ? <Alert>{error}</Alert> : null}
      {chiTiet.length > 0 ? <TechnicalDrawer lines={chiTiet} /> : null}

      {loading ? <Loading skeleton="card" rows={3}>Đang mở cẩm nang…</Loading> : null}
      {!loading && !error && items.length === 0 ? (
        <Empty>Chưa có luật nào. Luật sinh ra từ lần sửa có bằng chứng trong ca.</Empty>
      ) : null}

      {!loading &&
        nhom.map(([ho, list]) => (
          <section key={ho.ma} className="nq-rule-group">
            <div className="nq-rule-group-head">
              <h2 className="nq-rule-group-title">{ho.ten}</h2>
              <span className="nq-count">{list.length} luật</span>
            </div>
            <p className="nq-rule-group-why">{ho.vi_sao}</p>
            {list.map((l) => (
              <TheLuat key={l.id} luat={l} mau={mau} />
            ))}
          </section>
        ))}

      <NextSteps note="Luật lớn lên từ việc thật: mỗi lần ghim ca, nhả ca hay sửa lịch đều là một bằng chứng.">
        <BtnLink href="/treo">Xem sổ lần sửa</BtnLink>
        <BtnLink href="/sop" variant="ghost">
          Hỏi cẩm nang một câu
        </BtnLink>
        <Btn variant="ghost" onClick={load}>
          Tải lại cẩm nang
        </Btn>
      </NextSteps>

      <Toasts toasts={toasts} onDismiss={dismiss} />
    </div>
  );
}
