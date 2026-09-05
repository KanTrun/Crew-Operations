"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { luatLabel, luatTone, safeText, vfRuleLyDo, viError } from "../../lib/present";
import { matchSearch } from "../../lib/list-filters";
import { getRole, getToken, isChuQuan, isManager } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  BtnLink,
  Empty,
  Field,
  Input,
  Loading,
  Notice,
  PageHeader,
  ProgressBar,
  StatusChip,
  Summary,
  TechnicalDrawer,
} from "../../ui/kit";
import { CopilotPane } from "../../ui/copilot/CopilotPane";

type Luat = {
  id: string;
  cau?: string;
  trang_thai: string;
  tap_su_dung?: number;
  ap_dung?: number;
  ghi_de?: number;
  vf_rule?: string;
  bang_chung?: string[];
  mau_minh_hoa?: boolean;
};

type Pipeline = {
  so_sua_that: number;
  so_mau_san_sang: number;
  so_luat_that_quan: number;
  so_hieu_luc: number;
  so_cho_chot: number;
  so_mau_minh_hoa: number;
  can_chay_8_buoc: boolean;
  insight: { severity: string; message: string };
};

const LOC_TRANG_THAI = [
  { value: "all", label: "Mọi trạng thái" },
  { value: "hieu_luc", label: "Đang hiệu lực" },
  { value: "de_xuat", label: "Mới đề xuất" },
  { value: "qua_vf_rule", label: "Qua vòng kiểm" },
  { value: "cho_chu_quan", label: "Chờ chủ quán" },
];

export default function CamNangPage() {
  const [token, setToken] = useState("");
  const [manager, setManager] = useState(false);
  const [chuQuan, setChuQuan] = useState(false);
  const [items, setItems] = useState<Luat[]>([]);
  const [pipeline, setPipeline] = useState<Pipeline | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusF, setStatusF] = useState("all");
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [chiTiet, setChiTiet] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [copilotOpen, setCopilotOpen] = useState(false);

  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
    setChuQuan(isChuQuan(getRole()));
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    setLoading(true);
    apiGet<{ items: Luat[]; pipeline?: Pipeline; so_luat_that_quan?: number }>("/api/v1/cam-nang")
      .then((d) => {
        setItems((d.items ?? []).filter((x) => x && typeof x.id === "string"));
        if (d.pipeline) setPipeline(d.pipeline);
        setError(null);
      })
      .catch((e) => setError(viError(e, { doing: "mở được cẩm nang quán" })))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  const filtered = useMemo(() => {
    return items.filter((luat) => {
      const text = safeText(luat.cau, "");
      if (!matchSearch(text, search)) return false;
      if (statusF !== "all" && luat.trang_thai !== statusF) return false;
      return true;
    });
  }, [items, search, statusF]);

  const soThat = pipeline?.so_luat_that_quan ?? 0;
  const canChay = pipeline?.can_chay_8_buoc ?? false;

  async function chay() {
    setError(null);
    setMsg(null);
    setBusy(true);
    try {
      const d = await apiSend<{
        bi_loai?: { vf_rule?: string };
        so_luat_that_quan?: number;
        pipeline?: Pipeline;
      }>("/api/v1/cam-nang/chay-8-buoc");
      if (d.pipeline) setPipeline(d.pipeline);
      const that = typeof d.so_luat_that_quan === "number" ? d.so_luat_that_quan : 0;
      setMsg(
        that > 0
          ? `Đã hoàn tất đề xuất và tập sự. Quán có ${that} luật sinh từ sửa thật — chủ quán chốt để hiệu lực.`
          : "Đã hoàn tất đề xuất và tập sự. Chủ quán cần chốt riêng trước khi luật có hiệu lực.",
      );
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

  async function chot(id: string) {
    setBusy(true);
    setError(null);
    try {
      await apiSend("/api/v1/cam-nang/duyet", { id, ok: true });
      setMsg("Chủ quán đã chốt luật có hiệu lực — luật sẽ ảnh hưởng lần xếp lịch kế tiếp.");
      load();
    } catch (e) {
      setError(viError(e, { doing: "chốt luật có hiệu lực" }));
    } finally {
      setBusy(false);
    }
  }

  async function goLuat(id: string) {
    setBusy(true);
    setError(null);
    try {
      await apiSend("/api/v1/cam-nang/go", { id });
      setMsg("Đã gỡ luật khỏi hiệu lực.");
      load();
    } catch (e) {
      setError(viError(e, { doing: "gỡ luật" }));
    } finally {
      setBusy(false);
    }
  }

  if (!token) return <AuthGate />;

  const insight = pipeline?.insight;

  return (
    <div className="nq-page nq-page--cam-nang">
      <PageHeader
        kicker="Cẩm nang sống"
        title="Cẩm nang quán"
        meta={`Luật học từ lần sửa thật trong ca. Luật sinh từ quán: ${soThat > 0 ? soThat : "chưa có"}.`}
      />

      {!loading && pipeline ? (
        <Summary
          cells={[
            { n: pipeline.so_sua_that, k: "Lần sửa thật" },
            { n: pipeline.so_mau_san_sang, k: "Mẫu sẵn sàng", tone: pipeline.so_mau_san_sang > 0 ? "ok" : undefined },
            { n: pipeline.so_hieu_luc, k: "Đang hiệu lực", tone: "ok" },
            { n: pipeline.so_cho_chot, k: "Chờ chốt", tone: "warn" },
          ]}
        />
      ) : null}

      {insight ? (
        <div
          className={`nq-nguoi-insight nq-nguoi-insight--${insight.severity} mb-4`}
          role="status"
          aria-live="polite"
        >
          <p className="nq-nguoi-insight__label">Pipeline 8 bước</p>
          <p className="nq-nguoi-insight__text">{insight.message}</p>
        </div>
      ) : null}

      <div className="mb-6 flex flex-wrap items-center gap-3">
        {manager ? (
          <Btn variant="primary" disabled={busy || !canChay} onClick={chay} title={!canChay ? insight?.message : undefined}>
            {busy ? "Đang chạy…" : "Chạy 8 bước xét luật"}
          </Btn>
        ) : (
          <Notice>Bạn xem được luật quán. Quản lý hoặc chủ quán mới chạy 8 bước xét luật.</Notice>
        )}
        <BtnLink href="/sop" variant="ghost">
          Hỏi quy trình
        </BtnLink>
        <Btn variant="ghost" onClick={() => setCopilotOpen(true)}>
          Hỏi trợ lý vận hành
        </Btn>
      </div>

      <div className="flex flex-wrap gap-3 mb-4">
        <div className="flex-1 min-w-[200px]">
          <Field label="Tìm luật">
            <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Tìm theo nội dung…" />
          </Field>
        </div>
        <Field label="Trạng thái">
          <select className="nq-input" value={statusF} onChange={(e) => setStatusF(e.target.value)}>
            {LOC_TRANG_THAI.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </Field>
      </div>

      {msg ? <Alert kind="ok">{msg}</Alert> : null}
      {error ? <Alert>{error}</Alert> : null}
      {chiTiet.length > 0 ? <TechnicalDrawer lines={chiTiet} /> : null}
      {loading ? <Loading skeleton="list">Đang mở cẩm nang…</Loading> : null}
      {!loading && !error && filtered.length === 0 ? (
        <Empty>Chưa có luật phù hợp bộ lọc. Luật sinh ra từ lần sửa có bằng chứng trong ca.</Empty>
      ) : null}
      <div className="nq-card-grid">
        {filtered.map((luat) => {
          const open = expanded === luat.id;
          const text = safeText(luat.cau, "Luật chưa có câu diễn giải");
          const tapSu = typeof luat.tap_su_dung === "number" ? luat.tap_su_dung : 0;
          const apDung = typeof luat.ap_dung === "number" ? luat.ap_dung : 0;
          return (
            <article key={luat.id} className="nq-item flex flex-col gap-3">
              <p className={open ? "nq-item-title" : "nq-item-title nq-clamp-3"}>{text}</p>
              {text.length > 120 ? (
                <button
                  type="button"
                  className="self-start text-xs font-mono uppercase tracking-widest text-[var(--nq-copper)] underline"
                  onClick={() => setExpanded(open ? null : luat.id)}
                >
                  {open ? "Thu gọn" : "Xem thêm"}
                </button>
              ) : null}
              <p className="nq-item-sub flex flex-wrap items-center gap-2">
                <StatusChip tone={luatTone(luat.trang_thai)}>{luatLabel(luat.trang_thai)}</StatusChip>
                {luat.mau_minh_hoa ? (
                  <StatusChip tone="default">Mẫu minh họa</StatusChip>
                ) : null}
              </p>
              {tapSu > 0 || apDung > 0 ? (
                <div>
                  <p className="text-xs text-[var(--nq-dim)] mb-1">
                    Tập sự {tapSu} · Áp dụng {apDung}
                  </p>
                  <ProgressBar value={Math.min(apDung, 10)} max={10} />
                </div>
              ) : null}
              {open && luat.vf_rule ? (
                <p className="text-sm text-[var(--nq-ink-muted)]">{vfRuleLyDo(luat.vf_rule)}</p>
              ) : null}
              {open && (luat.bang_chung?.length ?? 0) > 0 ? (
                <p className="text-xs text-[var(--nq-dim)]">Bằng chứng: {luat.bang_chung?.length} lần sửa</p>
              ) : null}
              <div className="flex flex-wrap gap-2">
                {chuQuan && luat.trang_thai === "cho_chu_quan" ? (
                  <Btn busy={busy} onClick={() => void chot(luat.id)}>
                    Chốt hiệu lực
                  </Btn>
                ) : null}
                {chuQuan && luat.trang_thai === "hieu_luc" && !luat.mau_minh_hoa ? (
                  <Btn variant="ghost" busy={busy} onClick={() => void goLuat(luat.id)}>
                    Gỡ luật
                  </Btn>
                ) : null}
              </div>
            </article>
          );
        })}
      </div>

      <CopilotPane open={copilotOpen} onClose={() => setCopilotOpen(false)} />
    </div>
  );
}
