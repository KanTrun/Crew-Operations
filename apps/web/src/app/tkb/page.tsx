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
const THU_TEN: Record<string, string> = {
  T2: "Thứ Hai",
  T3: "Thứ Ba",
  T4: "Thứ Tư",
  T5: "Thứ Năm",
  T6: "Thứ Sáu",
  T7: "Thứ Bảy",
  CN: "Chủ Nhật",
};

const TIME_PATTERN = /^([01]\d|2[0-3]):[0-5]\d$/;

function isoWeekDates(tuanIso: string): Record<string, string> {
  const match = /^(\d{4})-W(\d{2})$/.exec(tuanIso);
  if (!match) return {};

  const year = Number(match[1]);
  const week = Number(match[2]);
  const januaryFourth = new Date(Date.UTC(year, 0, 4));
  const monday = new Date(januaryFourth);
  monday.setUTCDate(
    januaryFourth.getUTCDate() - ((januaryFourth.getUTCDay() + 6) % 7) + (week - 1) * 7,
  );

  return Object.fromEntries(
    THU.map((thu, index) => {
      const date = new Date(monday);
      date.setUTCDate(monday.getUTCDate() + index);
      return [
        thu,
        new Intl.DateTimeFormat("vi-VN", {
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
          timeZone: "UTC",
        }).format(date),
      ];
    }),
  );
}

function validateRows(rows: Khoang[]): string[][] {
  const errors = rows.map(() => [] as string[]);
  const hasValidTimeRange = rows.map(
    (row) => TIME_PATTERN.test(row.start) && TIME_PATTERN.test(row.end) && row.start < row.end,
  );

  rows.forEach((row, index) => {
    if (!THU.includes(row.thu as (typeof THU)[number])) {
      errors[index].push("Ngày không hợp lệ.");
    }
    if (!TIME_PATTERN.test(row.start) || !TIME_PATTERN.test(row.end)) {
      errors[index].push("Nhập đủ giờ bắt đầu và kết thúc theo định dạng HH:mm.");
    } else if (row.start >= row.end) {
      errors[index].push("Giờ kết thúc phải sau giờ bắt đầu.");
    }
  });

  rows.forEach((row, index) => {
    if (!hasValidTimeRange[index]) return;
    rows.slice(index + 1).forEach((other, offset) => {
      const otherIndex = index + offset + 1;
      if (
        hasValidTimeRange[otherIndex] &&
        row.thu === other.thu &&
        row.start < other.end &&
        other.start < row.end
      ) {
        errors[index].push("Khung giờ bị trùng trong cùng ngày.");
        errors[otherIndex].push("Khung giờ bị trùng trong cùng ngày.");
      }
    });
  });

  return errors;
}

function nextISOWeek(): string {
  const now = new Date();
  now.setDate(now.getDate() + 7);
  now.setHours(0, 0, 0, 0);
  now.setDate(now.getDate() + 3 - ((now.getDay() + 6) % 7));
  const week1 = new Date(now.getFullYear(), 0, 4);
  const week =
    1 +
    Math.round(
      ((now.getTime() - week1.getTime()) / 86400000 -
        3 +
        ((week1.getDay() + 6) % 7)) /
        7,
    );
  return `${now.getFullYear()}-W${String(week).padStart(2, "0")}`;
}

export default function TkbPage() {
  const [token, setToken] = useState("");
  const [manager, setManager] = useState(false);
  const [myNv, setMyNv] = useState("");
  const [staff, setStaff] = useState<Nv[]>([]);
  const [nvId, setNvId] = useState("");
  const [tuanIso, setTuanIso] = useState(nextISOWeek);
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
  const datesByDay = isoWeekDates(tuanIso);
  const rowErrors = validateRows(rows);
  const hasInvalidRows = rowErrors.some((messages) => messages.length > 0);
  const unrecognizedDayRows = rows
    .map((row, index) => ({ ...row, _i: index }))
    .filter((row) => !THU.includes(row.thu as (typeof THU)[number]));

  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
    setMyNv(sessionStorage.getItem("nq_nv") || "");
    if (!getToken()) setLoading(false);
  }, []);

  const loadMine = useCallback(() => {
    if (!getToken()) return;
    setLoading(true);
    // Danh sách nhân viên lấy từ /ops/pickers (mọi role) — không dùng
    // /lich-tuan (chỉ quản lý) kèm tuần hardcode cũ đã gây lỗi tải → nút
    // duyệt TKB không chạy sau khi lọc.
    Promise.all([
      apiGet<{ nv_id: string; item: { tuan_iso?: string; khoang_ban?: Khoang[] } | null }>(
        `/api/v1/tkb/mine?tuan_iso=${encodeURIComponent(tuanIso)}`,
      ),
      apiGet<{ nhan_vien?: Nv[] }>("/api/v1/ops/pickers").catch(() => ({ nhan_vien: [] })),
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
  }, [tuanIso]);

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
      setRows(khoang);
      if (out.escalate || !khoang.length) {
        // Inline — không dùng toast đáy màn (đè nút Xác nhận).
        setHint(
          khoang.length
            ? "Máy đọc chưa chắc. Kiểm tra và sửa các khung giờ bên dưới trước khi xác nhận."
            : "Không nhận diện được khung giờ bận nào. Ảnh có thể chưa đủ rõ; hãy thêm khung thủ công theo từng ngày.",
        );
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
    if (rows.length === 0 || hasInvalidRows) {
      setError("Kiểm tra và sửa các khung giờ chưa hợp lệ trước khi xác nhận.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const target = manager ? nvId || myNv : myNv;
      await apiSend("/api/v1/tkb/confirm", {
        nv_id: target,
        tuan_iso: tuanIso,
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
        <OpsCard
          eyebrow="Đã lưu"
          title="Lưới lịch bận đã gắn"
          count={saved.length}
          countLabel="khung bận"
        >
          <p className="mb-3 text-sm text-[var(--nq-fg)]">
            Các khung bên dưới sẽ được AvoidConflict khi xếp lịch lần tới — bấm «Xóa khung» để bỏ.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {THU.map((t) => {
              const khungTrongNgay = saved.filter((k) => k.thu === t);
              if (khungTrongNgay.length === 0) {
                return (
                  <div
                    key={t}
                    className="rounded-lg border border-[var(--nq-line)] bg-[var(--nq-bg)] p-3 opacity-70"
                  >
                    <p className="text-xs font-bold uppercase tracking-wide text-[var(--nq-ink)]">
                      {THU_TEN[t]}
                    </p>
                    <p className="mt-1 text-xs text-[var(--nq-ink-muted)]">Rảnh cả ngày</p>
                  </div>
                );
              }
              return (
                <div key={t} className="rounded-lg border border-[color-mix(in_srgb,var(--nq-st-warn)_46%,var(--nq-line))] bg-[var(--nq-st-warn-soft)] p-3">
                  <p className="text-xs font-bold uppercase tracking-wide text-[var(--nq-st-warn-ink)]">
                    {THU_TEN[t]}
                  </p>
                  <ul className="mt-1.5 space-y-1">
                    {khungTrongNgay.map((k, i) => (
                      <li
                        key={`${k.thu}-${k.start}-${i}`}
                        className="rounded bg-[var(--nq-bg-elevated)] px-2 py-1 font-mono text-xs text-[var(--nq-ink)]"
                      >
                        {k.start} – {k.end}
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>
        </OpsCard>
      ) : null}

      <OpsCard eyebrow="Bước 1" title="Tải ảnh & đọc">
        <Field label="Tuần áp dụng">
          <input
            className={inputClassName}
            type="week"
            value={tuanIso}
            onChange={(e) => setTuanIso(e.target.value)}
          />
        </Field>
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
            <StatusChip tone={result.escalate || rows.length === 0 ? "warn" : "ok"}>
              {rows.length === 0
                ? "Không nhận diện được khung"
                : result.escalate
                  ? "Kết quả chưa chắc chắn"
                  : "Đã nhận diện"}
            </StatusChip>
            <StatusChip>
              {(result.confidence * 100).toFixed(0)}% · {safeText(result.provider, "—")} ·{" "}
              {safeText(result.mode, "")}
            </StatusChip>
          </div>
          {hint ? <Alert kind="info">{hint}</Alert> : null}
          <p className="mb-3 text-sm text-[var(--nq-fg)]">
            Kết quả nhận diện cho tuần <strong>{tuanIso}</strong>. Mỗi khung bên dưới hiển thị rõ
            ngày và giờ bận; bạn có thể thêm, sửa hoặc xóa trước khi xác nhận.
          </p>
          {hasInvalidRows ? (
            <Alert kind="err">Có khung giờ chưa hợp lệ hoặc bị trùng. Hãy sửa các mục được đánh dấu.</Alert>
          ) : null}

          {unrecognizedDayRows.map((row) => (
            <div
              key={row._i}
              className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-[color-mix(in_srgb,var(--nq-st-danger)_46%,var(--nq-line))] bg-[var(--nq-st-danger-soft)] p-3"
            >
              <span className="text-sm text-[var(--nq-st-danger-ink)]">
                Không nhận diện được ngày “{safeText(row.thu, "trống")}” cho khung {safeText(row.start, "—")}–
                {safeText(row.end, "—")}.
              </span>
              <select
                className={`${inputClassName} w-auto text-xs`}
                value=""
                aria-label={`Chọn lại ngày cho khung ${row.start}–${row.end}`}
                onChange={(event) => updateRow(row._i, { thu: event.target.value })}
              >
                <option value="">Chọn ngày</option>
                {THU.map((thu) => (
                  <option key={thu} value={thu}>
                    {THU_TEN[thu]} · {datesByDay[thu]}
                  </option>
                ))}
              </select>
              <Btn
                variant="ghost"
                title="Xóa khung không nhận diện được ngày"
                onClick={() => setRows((prev) => prev.filter((_, index) => index !== row._i))}
              >
                Xóa
              </Btn>
            </div>
          ))}

          {/* Lưới chi tiết theo ngày — mỗi khung hiện đầy đủ thứ, giờ, nút xóa */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {THU.map((t) => {
              const khungTrongNgay = rows.map((r, i) => ({ ...r, _i: i })).filter((r) => r.thu === t);
              return (
                <div
                  key={t}
                  className={`rounded-lg border p-3 space-y-2 ${
                    khungTrongNgay.length > 0
                      ? "border-[color-mix(in_srgb,var(--nq-st-warn)_46%,var(--nq-line))] bg-[var(--nq-st-warn-soft)]"
                      : "border-[var(--nq-line)] bg-[var(--nq-bg)]"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-bold uppercase tracking-wide text-[var(--nq-fg)]">
                        {THU_TEN[t]}
                      </p>
                      <p className="mt-0.5 text-xs text-[var(--nq-dim)]">{datesByDay[t]}</p>
                    </div>
                    <button
                      type="button"
                      className="rounded px-1.5 py-0.5 text-2xs font-bold text-[var(--nq-st-warn-ink)] hover:bg-[var(--nq-st-warn)]"
                      title={`Thêm khung bận cho ${THU_TEN[t]}`}
                      onClick={() => setRows((prev) => [...prev, { thu: t, start: "", end: "" }])}
                    >
                      + Thêm khung
                    </button>
                  </div>
                  {khungTrongNgay.length === 0 ? (
                    <p className="text-xs text-[var(--nq-ink-muted)]">Không có khung bận</p>
                  ) : (
                    khungTrongNgay.map((r) => (
                      <div key={r._i}>
                        <div className="flex items-center gap-1.5">
                          <input
                            className="nq-input w-full text-xs"
                            type="time"
                            value={r.start}
                            aria-invalid={rowErrors[r._i].length > 0}
                            onChange={(e) => updateRow(r._i, { start: e.target.value })}
                            aria-label={`Giờ bắt đầu bận ${THU_TEN[t]} ${datesByDay[t]}`}
                          />
                          <span className="text-[var(--nq-fg)] text-xs">đến</span>
                          <input
                            className="nq-input w-full text-xs"
                            type="time"
                            value={r.end}
                            aria-invalid={rowErrors[r._i].length > 0}
                            onChange={(e) => updateRow(r._i, { end: e.target.value })}
                            aria-label={`Giờ kết thúc bận ${THU_TEN[t]} ${datesByDay[t]}`}
                          />
                          <Btn
                            variant="ghost"
                            title={`Xóa khung bận ${THU_TEN[t]} ${r.start}–${r.end}`}
                            onClick={() => setRows((prev) => prev.filter((_, j) => j !== r._i))}
                          >
                            Xóa
                          </Btn>
                        </div>
                        {rowErrors[r._i].map((message) => (
                          <p key={message} className="mt-1 text-xs text-[var(--nq-st-danger-ink)]" role="alert">
                            {message}
                          </p>
                        ))}
                      </div>
                    ))
                  )}
                </div>
              );
            })}
          </div>

          <div className="mt-6 pb-24 md:pb-8">
            <Btn
              variant="primary"
              disabled={busy || rows.length === 0 || hasInvalidRows}
              onClick={xacNhan}
            >
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
