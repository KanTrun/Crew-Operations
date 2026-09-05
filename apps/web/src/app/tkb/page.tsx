"use client";

/**
 * Thời khoá biểu từ ảnh — upload → AI đọc → sửa → xác nhận gắn NV.
 */

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiSend, apiUpload } from "../../lib/api";
import { nvTenHienThi, safeText, viError } from "../../lib/present";
import { getToken, isManager } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  Empty,
  Field,
  inputClassName,
  Loading,
  Notice,
  OpsCard,
  PageHeader,
  StatusChip,
  Toasts,
  useToasts,
} from "../../ui/kit";
import { CopilotPane } from "../../ui/copilot/CopilotPane";

type Khoang = { thu: string; start: string; end: string };

type ExtractOut = {
  rows: Khoang[];
  spans: Array<{ day: string; start: string; end: string }>;
  confidence: number;
  blur: boolean;
  escalate: boolean;
  reason?: string;
  provider?: string;
  mode?: string;
  source_id?: string;
  upload_id?: string;
  agent_mode?: string;
};

type Nv = { id: string; ten: string };

const THU = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"] as const;

export default function TkbPage() {
  const [token, setToken] = useState("");
  const [manager, setManager] = useState(false);
  const [myNv, setMyNv] = useState("");
  const [staff, setStaff] = useState<Nv[]>([]);
  const [nvId, setNvId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [result, setResult] = useState<ExtractOut | null>(null);
  const [rows, setRows] = useState<Khoang[]>([]);
  const [saved, setSaved] = useState<Khoang[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hint, setHint] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [copilotOpen, setCopilotOpen] = useState(false);
  const { toasts, push, dismiss } = useToasts();

  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
    setMyNv(sessionStorage.getItem("nq_nv") || "");
    if (!getToken()) setLoading(false);
  }, []);

  const loadMine = useCallback(() => {
    if (!getToken()) return;
    setLoading(true);
    Promise.all([
      apiGet<{ nv_id: string; item: { khoang_ban?: Khoang[] } | null }>("/api/v1/tkb/mine"),
      apiGet<{ nhan_vien?: Nv[] }>("/api/v1/lich-tuan?tuan=2026-W34").catch(() => ({ nhan_vien: [] })),
    ])
      .then(([mine, lich]) => {
        setMyNv(mine.nv_id || sessionStorage.getItem("nq_nv") || "");
        setNvId((prev) => prev || mine.nv_id || "");
        setSaved(mine.item?.khoang_ban ?? null);
        setStaff(lich.nhan_vien ?? []);
        setError(null);
      })
      .catch((e) => setError(viError(e, { doing: "mở được trang thời khoá biểu" })))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) loadMine();
  }, [token, loadMine]);

  useEffect(() => {
    if (!file) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  async function chayExtract(fixture?: string) {
    setBusy(true);
    setError(null);
    setHint(null);
    try {
      const form = new FormData();
      if (fixture) {
        form.append("fixture_id", fixture);
      } else if (file) {
        form.append("file", file);
      } else {
        setError("Chọn ảnh thời khoá biểu, hoặc thử ảnh mẫu.");
        return;
      }
      const out = await apiUpload<ExtractOut>("/api/v1/tkb/upload", form);
      setResult(out);
      const khoang =
        out.rows?.length > 0
          ? out.rows
          : (out.spans ?? []).map((s) => ({ thu: s.day, start: s.start, end: s.end }));
      setRows(khoang.length ? khoang : [{ thu: "T2", start: "07:30", end: "11:00" }]);
      if (out.escalate || !khoang.length) {
        // Inline — không dùng toast đáy màn (đè nút Xác nhận).
        setHint("Máy đọc chưa chắc. Sửa các khung giờ bên dưới rồi bấm Xác nhận gắn TKB.");
      } else {
        setHint(null);
        push(`Đã đọc ${khoang.length} khung · độ tin ${(out.confidence * 100).toFixed(0)}%.`);
      }
    } catch (e) {
      setError(viError(e, { doing: "đọc được ảnh thời khoá biểu" }));
    } finally {
      setBusy(false);
    }
  }

  async function xacNhan() {
    setBusy(true);
    setError(null);
    try {
      const target = manager ? nvId || myNv : myNv;
      await apiSend("/api/v1/tkb/confirm", {
        nv_id: target,
        khoang_ban: rows,
        source_id: result?.source_id || "",
        upload_id: result?.upload_id || "",
      });
      setSaved(rows);
      setHint(null);
      push("Đã gắn thời khoá biểu. Lượt xếp lịch tới sẽ tránh các khung này.");
      loadMine();
    } catch (e) {
      setError(viError(e, { doing: "xác nhận được thời khoá biểu" }));
    } finally {
      setBusy(false);
    }
  }

  function updateRow(i: number, patch: Partial<Khoang>) {
    setRows((prev) => prev.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  }

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page nq-page--tkb">
      <PageHeader
        kicker="Lịch cá nhân · tránh xếp trùng ca"
        title="Tải ảnh lịch bận"
        meta="Chụp hoặc chọn ảnh lịch học, kiểm tra các khung giờ được đọc rồi xác nhận. Lần xếp ca tiếp theo sẽ tránh các giờ này."
      />
      <Btn variant="ghost" onClick={() => setCopilotOpen(true)}>
        Hỏi trợ lý vận hành
      </Btn>
      <Toasts toasts={toasts} onDismiss={dismiss} />
      {error ? <Alert kind="err">{error}</Alert> : null}
      {loading ? <Loading skeleton="list">Đang tải…</Loading> : null}

      <Notice>
        Ảnh thật cần <span className="font-mono text-[var(--nq-fg)]">CA_AGENT_MODE=live</span> và key
        Gemini. Có thể bấm <strong className="text-[var(--nq-fg)]">Thử ảnh mẫu</strong> ngay không cần
        Gemini.
      </Notice>

      {saved && saved.length > 0 ? (
        <OpsCard eyebrow="Đã lưu" title="Khoảng bận của bạn" count={saved.length} countLabel="khung">
          <ul className="nq-tkb-list">
            {saved.map((k, i) => (
              <li key={`${k.thu}-${k.start}-${i}`}>
                {k.thu} · {k.start}–{k.end}
              </li>
            ))}
          </ul>
        </OpsCard>
      ) : null}

      <OpsCard eyebrow="Bước 1" title="Tải ảnh & đọc">
        <div className="mb-4">
          <span className="mb-2 block text-sm font-bold uppercase tracking-widest text-[var(--nq-dim)]">
            Ảnh thời khoá biểu
          </span>
          <label className="nq-tkb-file">
            <span className="nq-tkb-file-btn">Chọn ảnh</span>
            <span className="nq-tkb-file-name">
              {file ? file.name : "Chưa chọn — PNG, JPG hoặc chụp màn hình"}
            </span>
            <input
              type="file"
              accept="image/*,.svg"
              className="sr-only"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </label>
        </div>
        {preview ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={preview} alt="Xem trước TKB" className="nq-tkb-preview" />
        ) : null}
        {manager ? (
          <Field label="Gắn cho nhân viên">
            <select className={inputClassName} value={nvId} onChange={(e) => setNvId(e.target.value)}>
              <option value={myNv}>Tôi ({myNv || "—"})</option>
              {staff.map((nv) => (
                <option key={nv.id} value={nv.id}>
                  {nvTenHienThi(nv.ten, nv.id)}
                </option>
              ))}
            </select>
          </Field>
        ) : (
          <p className="text-sm text-[var(--nq-fg)]">
            Gắn vào tài khoản của bạn ({safeText(myNv, "…")})
          </p>
        )}
        <div className="mt-4 flex flex-wrap gap-2">
          <Btn variant="primary" disabled={busy || !file} onClick={() => chayExtract()}>
            {busy ? "Đang đọc…" : "Đọc ảnh"}
          </Btn>
          <Btn variant="ghost" disabled={busy} onClick={() => chayExtract("tkb_01")}>
            Thử ảnh mẫu
          </Btn>
        </div>
      </OpsCard>

      {result ? (
        <OpsCard eyebrow="Bước 2" title="Sửa & xác nhận" count={rows.length} countLabel="khung">
          <div className="mb-3 flex flex-wrap gap-2">
            <StatusChip tone={result.escalate ? "warn" : "ok"}>
              {result.escalate ? "Cần sửa tay" : "Đọc được"}
            </StatusChip>
            <StatusChip>
              {(result.confidence * 100).toFixed(0)}% · {safeText(result.provider, "—")} ·{" "}
              {safeText(result.mode, "")}
            </StatusChip>
          </div>
          {hint ? <Alert kind="info">{hint}</Alert> : null}
          <div className="nq-tkb-edit">
            {rows.map((r, i) => (
              <div key={i} className="nq-tkb-row">
                <select className={inputClassName} value={r.thu} onChange={(e) => updateRow(i, { thu: e.target.value })}>
                  {THU.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
                <input
                  className={inputClassName}
                  type="time"
                  value={r.start}
                  onChange={(e) => updateRow(i, { start: e.target.value })}
                />
                <span className="text-[var(--nq-fg)]">→</span>
                <input
                  className={inputClassName}
                  type="time"
                  value={r.end}
                  onChange={(e) => updateRow(i, { end: e.target.value })}
                />
                <Btn
                  variant="ghost"
                  onClick={() => setRows((prev) => prev.filter((_, j) => j !== i))}
                >
                  Xóa
                </Btn>
              </div>
            ))}
            <Btn
              variant="ghost"
              onClick={() => setRows((prev) => [...prev, { thu: "T2", start: "13:00", end: "17:00" }])}
            >
              Thêm khung
            </Btn>
          </div>
          <div className="mt-6 pb-24 md:pb-8">
            <Btn variant="primary" disabled={busy || rows.length === 0} onClick={xacNhan}>
              Xác nhận gắn TKB
            </Btn>
          </div>
        </OpsCard>
      ) : (
        !loading && (
          <Empty>Chưa có kết quả đọc. Chọn ảnh rồi bấm Đọc ảnh, hoặc thử ảnh mẫu.</Empty>
        )
      )}
      <CopilotPane open={copilotOpen} onClose={() => setCopilotOpen(false)} />
    </div>
  );
}
