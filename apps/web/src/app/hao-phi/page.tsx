"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { matchSearch, matchTime, TIME_FILTER_OPTIONS, uniqueSorted, type TimeFilter } from "../../lib/list-filters";
import {
  formatLuc,
  lossBasisLabel,
  lossLevelLabel,
  lossLevelTone,
  lossNgay,
  lossThieuVeLabel,
  matHangLabel,
  nguyenNhanLabel,
  safeText,
  thuLabel,
} from "../../lib/present";
import { getToken, isManager } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  Empty,
  Field,
  FixtureChip,
  inputClassName,
  Loading,
  NextSteps,
  Notice,
  Num,
  OpsCard,
  PageHeader,
  Stat,
  StatGrid,
  StatusChip,
} from "../../ui/kit";
import { FilteredEmpty, ListToolbar } from "../../ui/list-filters";
import { DayOfWeekSelect } from "../../ui/ops-pickers";

/* ── Kiểu dữ liệu từ máy chủ ── */

type LossLine = {
  mat_hang: string;
  ten: string;
  don_vi: string;
  ly_thuyet: number | null;
  thuc_te: number | null;
  lech: number | null;
  ty_le_phan_tram: number | null;
  muc_do: string;
  nguong_phan_tram: number;
  co_so: string;
  thieu_ve: string[];
  ghi_chu: string;
};

type LossCause = {
  nguyen_nhan: string;
  ten: string;
  so_lan: number;
  mat_hang_lien_quan: string[];
  ty_le_tong: number;
};

type LossSummary = {
  ky: string;
  tong_dong: number;
  so_nghiem_trong: number;
  so_canh_bao: number;
  so_thieu_du_lieu: number;
  ty_le_trung_binh: number | null;
  dong: LossLine[];
  nguyen_nhan_hang_dau: LossCause[];
  co_du_lieu_mau?: boolean;
};

type Cluster = { cau?: string; thu?: string; n?: number; created_at?: string };

type GhiChu = {
  id?: string;
  thu?: string;
  ghi_chu?: string;
  mat_hang?: string;
  so_luong?: number;
  don_vi?: string;
  nguyen_nhan?: string;
  luc?: string;
  created_at?: string;
  ngay?: string;
  at?: string;
};

type Ky = "hom_nay" | "tuan" | "thang" | "all";

const KY_OPTIONS: Array<{ value: Ky; label: string }> = [
  { value: "hom_nay", label: "Hôm nay" },
  { value: "tuan", label: "Tuần này" },
  { value: "thang", label: "Tháng này" },
  { value: "all", label: "Toàn bộ" },
];

/** Nguyên nhân hay gặp ở quán — dùng cho ô chọn khi ghi. */
const NGUYEN_NHAN_GOI_Y = [
  "het_han",
  "roi_do",
  "pha_sai",
  "dem_sai_dau_ca",
  "quen_tat_may",
  "khach_doi_mon",
  "hong_tu_lanh",
  "bay_hoi",
];

const DON_VI_GOI_Y = ["g", "ml", "cái", "hộp", "kg", "chai", "ly", "lát"];

function clusterHaystack(it: Cluster): string {
  return [it.cau, it.thu, String(it.n ?? "")].filter(Boolean).join(" ");
}

/**
 * Một cột số: `null` in gạch, `0` in số 0.
 *
 * Đây là ràng buộc chính của mặt này. `null` là máy chủ **chưa có dữ liệu**;
 * `0` là có dữ liệu và bằng không. In `null` thành "0" là bịa số, và người đọc
 * sẽ tưởng quán không hao hụt trong khi thật ra chưa ai gõ phiếu kiểm kê.
 */
function O({ value, digits = 1 }: { value: number | null; digits?: number }) {
  if (value === null || value === undefined) {
    return (
      <span className="font-mono text-[var(--nq-dim)]" title="Chưa có dữ liệu">
        —
      </span>
    );
  }
  return <Num value={value} digits={digits} />;
}

export default function HaoPhiPage() {
  const [token, setToken] = useState("");
  const [quanLy, setQuanLy] = useState(false);
  const [ky, setKy] = useState<Ky>("hom_nay");
  const [summary, setSummary] = useState<LossSummary | null>(null);
  const [coMau, setCoMau] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Khu ghi chú cũ — giữ nguyên chức năng
  const [items, setItems] = useState<Cluster[]>([]);
  const [ghiChu, setGhiChu] = useState<GhiChu[]>([]);
  const [thu, setThu] = useState("T2");
  const [ghi, setGhi] = useState("");
  const [search, setSearch] = useState("");
  const [thuF, setThuF] = useState("all");
  const [timeF, setTimeF] = useState<TimeFilter>("all");

  // Khu ghi hao hụt có mặt hàng + nguyên nhân
  const [matHang, setMatHang] = useState("");
  const [soLuong, setSoLuong] = useState("");
  const [donVi, setDonVi] = useState("g");
  const [nguyenNhan, setNguyenNhan] = useState("het_han");
  const [ghiChuMoi, setGhiChuMoi] = useState("");  const [dangGhi, setDangGhi] = useState(false);
  const [xong, setXong] = useState<string | null>(null);
  const [danhMuc, setDanhMuc] = useState<string[]>([]);

  useEffect(() => {
    setToken(getToken());
    setQuanLy(isManager());
    if (!getToken()) setLoading(false);
  }, []);

  const loadSummary = useCallback(() => {
    if (!getToken()) return;
    setLoading(true);
    apiGet<LossSummary>(`/api/v1/hao-hut?ky=${ky}`)
      .then((d) => {
        setSummary(d);
        setCoMau(d.co_du_lieu_mau === true);
        setError(null);
      })
      .catch(() => {
        setSummary(null);
        setError("Không đọc được bảng hao hụt.");
      })
      .finally(() => setLoading(false));
  }, [ky]);

  const loadGhiChu = useCallback(() => {
    if (!getToken()) return;
    apiGet<{ items: Cluster[]; ghi_chu?: GhiChu[]; co_du_lieu_mau?: boolean }>("/api/v1/waste")
      .then((d) => {
        setItems(d.items ?? []);
        setGhiChu(d.ghi_chu ?? []);
        if (d.co_du_lieu_mau === true) setCoMau(true);
      })
      .catch(() => setError("Không đọc được ghi chú hao phí."));
  }, []);

  useEffect(() => {
    if (token) loadSummary();
  }, [token, loadSummary]);

  useEffect(() => {
    if (token) loadGhiChu();
  }, [token, loadGhiChu]);

  // Danh mục gợi ý: chỉ quản lý đọc được, và chỉ là tiện ích nên lỗi thì bỏ qua.
  useEffect(() => {
    if (!token || !quanLy) return;
    apiGet<{ items: string[] }>("/api/v1/hao-hut/danh-muc")
      .then((d) => setDanhMuc(d.items ?? []))
      .catch(() => setDanhMuc([]));
  }, [token, quanLy]);

  const dong = useMemo(() => summary?.dong ?? [], [summary]);
  const nghiemTrong = useMemo(() => dong.filter((d) => d.muc_do === "nghiem_trong"), [dong]);
  const canhBao = useMemo(() => dong.filter((d) => d.muc_do === "canh_bao"), [dong]);
  const thieuDuLieu = useMemo(() => dong.filter((d) => d.muc_do === "thieu_du_lieu"), [dong]);
  /** Xếp hạng nguyên nhân từ máy chủ — khác `nguyenNhan` (ô chọn khi ghi). */
  const hangNguyenNhan = useMemo(() => summary?.nguyen_nhan_hang_dau ?? [], [summary]);

  const thuOptions = useMemo(
    () => [
      { value: "all", label: "Mọi thứ" },
      ...uniqueSorted(items.map((i) => i.thu)).map((v) => ({ value: v, label: thuLabel(v) })),
    ],
    [items],
  );

  const filtered = useMemo(() => {
    return items.filter((it) => {
      if (!matchSearch(clusterHaystack(it), search)) return false;
      if (thuF !== "all" && (it.thu ?? "") !== thuF) return false;
      if (!matchTime(it.created_at, timeF)) return false;
      return true;
    });
  }, [items, search, thuF, timeF]);

  const filterActive = search.length > 0 || thuF !== "all" || timeF !== "all";

  const ghiChuGanDay = useMemo(
    () => [...ghiChu].sort((a, b) => lossNgay(b).localeCompare(lossNgay(a))).slice(0, 6),
    [ghiChu],
  );

  function clearFilters() {
    setSearch("");
    setThuF("all");
    setTimeF("all");
  }

  async function onSubmitGhiChu(e: FormEvent) {
    e.preventDefault();
    if (!ghi.trim()) {
      setError("Ghi nội dung ghi chú trước khi lưu.");
      return;
    }
    try {
      await apiSend("/api/v1/waste", { thu, ghi_chu: ghi.trim() });
      setGhi("");
      setError(null);
      loadGhiChu();
      loadSummary();
    } catch {
      setError("Không ghi được ghi chú hao phí.");
    }
  }

  async function onSubmitHaoHut(e: FormEvent) {
    e.preventDefault();
    const sl = Number(soLuong);
    if (!matHang.trim()) {
      setError("Chọn hoặc gõ tên nguyên liệu bị hao.");
      return;
    }
    if (!Number.isFinite(sl) || sl <= 0) {
      setError("Số lượng hao phải là số lớn hơn 0.");
      return;
    }
    setDangGhi(true);
    setError(null);
    try {
      await apiSend("/api/v1/hao-hut", {
        mat_hang: matHang.trim(),
        so_luong: sl,
        don_vi: donVi,
        nguyen_nhan: nguyenNhan,
        ghi_chu: ghiChuMoi.trim(),
        thu,
      });
      setSoLuong("");
      setGhiChuMoi("");
      setXong(`Đã ghi hao hụt: ${matHangLabel(matHang)} ${sl}${donVi}.`);
      loadSummary();
      loadGhiChu();
    } catch {
      setError("Không ghi được hao hụt. Tải lại trang rồi thử lại.");
    } finally {
      setDangGhi(false);
    }
  }

  if (!token) return <AuthGate />;

  const kyLabel = KY_OPTIONS.find((o) => o.value === ky)?.label ?? "Hôm nay";

  return (
    <div className="nq-page">
      <PageHeader
        kicker="Hao hụt · tiêu thụ"
        title="Hao phí"
        meta="Đối chiếu lượng nguyên liệu lẽ ra phải dùng (theo công thức món × số phần đã bán) với lượng thực tế đã dùng (theo phiếu kiểm kê). Chỗ nào lệch nhiều là chỗ có chuyện."
      />
      {error ? <Alert>{error}</Alert> : null}
      {xong ? <Alert kind="ok">{xong}</Alert> : null}

      <div className="flex flex-wrap gap-2 mb-8" role="group" aria-label="Chọn kỳ xem">
        {KY_OPTIONS.map((o) => (
          <button
            key={o.value}
            type="button"
            onClick={() => setKy(o.value)}
            aria-pressed={ky === o.value}
            className={`nq-modebtn${ky === o.value ? " nq-modebtn--on" : ""}`}
          >
            {o.label}
          </button>
        ))}
      </div>

      <StatGrid>
        <Stat value={dong.length} label="Nguyên liệu có dòng" />
        <Stat
          value={
            summary?.ty_le_trung_binh === null || summary?.ty_le_trung_binh === undefined
              ? "—"
              : `${summary.ty_le_trung_binh}%`
          }
          label="Hao hụt trung bình"
        />
        <Stat value={nghiemTrong.length} label="Vượt ngưỡng nặng" tone={nghiemTrong.length > 0 ? "danger" : "default"} />
        <Stat value={canhBao.length} label="Cần xem lại" tone={canhBao.length > 0 ? "warn" : "default"} />
      </StatGrid>

      {thieuDuLieu.length > 0 ? (
        <Alert kind="info">
          {thieuDuLieu.length} nguyên liệu chưa kết luận được vì thiếu một vế — chưa gõ phiếu kiểm kê hoặc chưa có đơn
          quầy nào trong kỳ. Hệ thống để trống chứ không đoán số.
        </Alert>
      ) : null}

      <OpsCard
        eyebrow={`Kỳ ${kyLabel.toLowerCase()}`}
        title="Hao hụt theo nguyên liệu"
        count={dong.length}
        countLabel="nguyên liệu"
      >
        {coMau ? (
          <p className="mb-4">
            <FixtureChip />
          </p>
        ) : null}
        {loading ? (
          <Loading skeleton="table" rows={4}>
            Đang tính hao hụt…
          </Loading>
        ) : null}

        {!loading && dong.length === 0 ? (
          <Empty title="Chưa có dữ liệu để đối chiếu">
            Cần hai vế mới tính được: phiếu kiểm kê (mặt Hàng tồn) và đơn quầy đã xong. Có một vế thì hệ thống vẫn hiện
            dòng, nhưng để trống số chứ không đoán.
          </Empty>
        ) : null}

        {!loading && dong.length > 0 ? (
          <>
            <div className="nq-table-wrap hidden md:block">
              <table className="nq-table w-full">
                <caption className="sr-only">
                  Hao hụt theo từng nguyên liệu: lượng theo công thức, lượng đã dùng thật, độ lệch và mức độ.
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Nguyên liệu</th>
                    <th scope="col" className="text-right">
                      Theo công thức
                    </th>
                    <th scope="col" className="text-right">
                      Đã dùng thật
                    </th>
                    <th scope="col" className="text-right">
                      Lệch
                    </th>
                    <th scope="col" className="text-right">
                      Tỷ lệ
                    </th>
                    <th scope="col">Mức độ</th>
                    <th scope="col">Nguồn số</th>
                  </tr>
                </thead>
                <tbody>
                  {dong.map((d) => (
                    <tr key={d.mat_hang} data-mat-hang={d.mat_hang} data-muc-do={d.muc_do}>
                      <th scope="row" className="font-bold">
                        {safeText(d.ten, matHangLabel(d.mat_hang))}
                        {d.ghi_chu ? (
                          <span className="block text-xs font-normal text-[var(--nq-dim)]">{d.ghi_chu}</span>
                        ) : null}
                      </th>
                      <td className="text-right">
                        <O value={d.ly_thuyet} />
                        <span className="text-xs text-[var(--nq-dim)] ml-1">{d.don_vi}</span>
                      </td>
                      <td className="text-right">
                        <O value={d.thuc_te} />
                        <span className="text-xs text-[var(--nq-dim)] ml-1">{d.don_vi}</span>
                      </td>
                      <td className="text-right">
                        <O value={d.lech} />
                      </td>
                      <td className="text-right">
                        {d.ty_le_phan_tram === null ? (
                          <span className="font-mono text-[var(--nq-dim)]">—</span>
                        ) : (
                          <Num value={d.ty_le_phan_tram} digits={1} unit="%" />
                        )}
                      </td>
                      <td>
                        <StatusChip tone={lossLevelTone(d.muc_do)}>{lossLevelLabel(d.muc_do)}</StatusChip>
                        {d.thieu_ve.length > 0 ? (
                          <span className="block text-xs text-[var(--nq-dim)] mt-1">{lossThieuVeLabel(d.thieu_ve)}</span>
                        ) : null}
                      </td>
                      <td className="text-xs text-[var(--nq-dim)]">
                        {lossBasisLabel(d.co_so)}
                        <span className="block">ngưỡng {d.nguong_phan_tram}%</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="nq-list md:hidden">
              {dong.map((d) => (
                <article key={d.mat_hang} className="nq-item" data-mat-hang={d.mat_hang} data-muc-do={d.muc_do}>
                  <div className="flex items-start justify-between gap-2">
                    <p className="nq-item-title">{safeText(d.ten, matHangLabel(d.mat_hang))}</p>
                    <StatusChip tone={lossLevelTone(d.muc_do)}>{lossLevelLabel(d.muc_do)}</StatusChip>
                  </div>
                  <p className="nq-item-sub font-mono">
                    công thức <O value={d.ly_thuyet} /> · thật <O value={d.thuc_te} /> · lệch <O value={d.lech} />{" "}
                    {d.don_vi}
                  </p>
                  {d.thieu_ve.length > 0 ? <p className="nq-item-sub">{lossThieuVeLabel(d.thieu_ve)}</p> : null}
                  {d.ghi_chu ? <p className="nq-item-sub">{d.ghi_chu}</p> : null}
                </article>
              ))}
            </div>
          </>
        ) : null}
      </OpsCard>

      <OpsCard
        eyebrow="Từ ghi chú trong ca"
        title="Nguyên nhân lặp lại"
        count={hangNguyenNhan.length}
        countLabel="nguyên nhân"
      >
        {!loading && hangNguyenNhan.length === 0 ? (
          <Empty title="Chưa có nguyên nhân nào được ghi">
            Khi ghi hao hụt, chọn nguyên nhân ở ô bên dưới. Hệ thống đếm dần để thấy nguyên nhân nào đang lặp lại nhiều
            nhất — đó thường là chỗ sửa được.
          </Empty>
        ) : null}
        <div className="nq-list">
          {hangNguyenNhan.map((c) => (
            <article key={c.nguyen_nhan} className="nq-item" data-nguyen-nhan={c.nguyen_nhan}>
              <div className="flex items-start justify-between gap-2">
                <p className="nq-item-title">{safeText(c.ten, nguyenNhanLabel(c.nguyen_nhan))}</p>
                <span className="font-mono text-sm text-[var(--nq-copper)]">
                  {c.so_lan} lần · {c.ty_le_tong}%
                </span>
              </div>
              {c.mat_hang_lien_quan.length > 0 ? (
                <p className="nq-item-sub">
                  Hay đi cùng: {c.mat_hang_lien_quan.map((m) => matHangLabel(m)).join(", ")}
                </p>
              ) : null}
            </article>
          ))}
        </div>
      </OpsCard>

      <OpsCard eyebrow="Khu vực 1" title="Ghi một lần hao hụt">
        <p className="mb-4 text-sm text-[var(--nq-dim)]">
          Ghi rõ nguyên liệu, số lượng và nguyên nhân. Đây là vế nuôi bảng nguyên nhân ở trên — ghi chung chung thì bảng
          không đếm được gì.
        </p>
        <form onSubmit={onSubmitHaoHut}>
          <Field label="Nguyên liệu" hint="Chọn từ gợi ý hoặc gõ mã nguyên liệu của quán.">
            <input
              className={inputClassName}
              value={matHang}
              onChange={(e) => setMatHang(e.target.value)}
              list="mat-hang-goi-y"
              placeholder="Ví dụ: sua_tuoi"
            />
            <datalist id="mat-hang-goi-y">
              {danhMuc.map((m) => (
                <option key={m} value={m} label={matHangLabel(m)} />
              ))}
            </datalist>
          </Field>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Số lượng hao">
              <input
                className={inputClassName}
                value={soLuong}
                onChange={(e) => setSoLuong(e.target.value)}
                inputMode="decimal"
                placeholder="Ví dụ: 2"
              />
            </Field>
            <Field label="Đơn vị">
              <select className={inputClassName} value={donVi} onChange={(e) => setDonVi(e.target.value)}>
                {DON_VI_GOI_Y.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          <Field label="Nguyên nhân" hint="Chọn lý do gần nhất. Không rõ thì để nguyên và ghi ở ô bên dưới.">
            <select className={inputClassName} value={nguyenNhan} onChange={(e) => setNguyenNhan(e.target.value)}>
              {NGUYEN_NHAN_GOI_Y.map((n) => (
                <option key={n} value={n}>
                  {nguyenNhanLabel(n)}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Ghi chú thêm">
            <input
              className={inputClassName}
              value={ghiChuMoi}
              onChange={(e) => setGhiChuMoi(e.target.value)}
              placeholder="Ví dụ: hộp mở từ sáng, tới chiều chua phải bỏ"
            />
          </Field>

          <Btn type="submit" variant="primary" busy={dangGhi} busyLabel="Đang ghi…">
            Ghi hao hụt
          </Btn>
        </form>
      </OpsCard>

      <OpsCard eyebrow="Khu vực 2" title="Ghi chú trong ca">
        <form onSubmit={onSubmitGhiChu}>
          <DayOfWeekSelect value={thu} onChange={setThu} />
          <Field label="Ghi chú">
            <input
              className={inputClassName}
              value={ghi}
              onChange={(e) => setGhi(e.target.value)}
              placeholder="Mô tả hao phí trong ca…"
            />
          </Field>
          <Btn type="submit" variant="primary">
            Ghi chú
          </Btn>
        </form>
      </OpsCard>

      {ghiChuGanDay.length > 0 ? (
        <OpsCard eyebrow="Sổ ghi chú" title="Ghi chú gần đây" count={ghiChu.length} countLabel="ghi chú">
          <div className="nq-list">
            {ghiChuGanDay.map((g, i) => (
              <article key={g.id ?? i} className="nq-item">
                <p className="nq-item-title">{safeText(g.ghi_chu, "Ghi chú không có nội dung")}</p>
                <p className="nq-item-sub">
                  {g.mat_hang ? `${matHangLabel(g.mat_hang)} · ` : ""}
                  {g.nguyen_nhan ? `${nguyenNhanLabel(g.nguyen_nhan)} · ` : ""}
                  {formatLuc(lossNgay(g))}
                </p>
              </article>
            ))}
          </div>
        </OpsCard>
      ) : null}

      <OpsCard eyebrow="Gom cụm theo thứ" title="Cụm đã gom" count={filtered.length} countLabel="cụm">
        <ListToolbar
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Tìm nội dung cụm, thứ…"
          status={thuF}
          onStatusChange={setThuF}
          statusOptions={thuOptions}
          statusLabel="Thứ trong tuần"
          time={timeF}
          onTimeChange={(v) => setTimeF(v as TimeFilter)}
          timeOptions={TIME_FILTER_OPTIONS}
          shown={filtered.length}
          total={items.length}
          filtered={filterActive}
        />
        {!loading && items.length === 0 ? <Empty title="Chưa có cụm">Chưa có ghi chú để gom cụm.</Empty> : null}
        {!loading && items.length > 0 && filtered.length === 0 ? <FilteredEmpty onClear={clearFilters} /> : null}
        <div className="nq-list">
          {filtered.map((it, i) => (
            <article key={i} className="nq-item">
              <p className="nq-item-title">{it.cau ?? "Chưa đủ mẫu để gom cụm"}</p>
              <p className="nq-item-sub">
                {thuLabel(it.thu)} · {it.n ?? 0} lần
              </p>
            </article>
          ))}
        </div>
        {!quanLy ? (
          <Notice>Bạn xem được bảng hao hụt và ghi hao hụt. Danh mục gợi ý là phần của quản lý.</Notice>
        ) : null}
      </OpsCard>

      <NextSteps title="Làm gì tiếp" note="Hao hụt chỉ sửa được khi biết chỗ nào lệch">
        <Link href="/tieu-thu" className="nq-btn nq-btn-ghost">
          Gõ phiếu kiểm kê
        </Link>
        <Link href="/menu" className="nq-btn nq-btn-ghost">
          Xem công thức món
        </Link>
        <Link href="/sop" className="nq-btn nq-btn-ghost">
          Hỏi quy trình xử lý
        </Link>
      </NextSteps>
    </div>
  );
}
