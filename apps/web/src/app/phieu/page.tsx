"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { apiGet, apiSend } from "../../lib/api";
import { loaiBuocLabel, safeText, viError } from "../../lib/present";
import { getToken } from "../../lib/session";
import {
  Alert,
  Btn,
  Empty,
  Field,
  FixedBottomBar,
  InlineActions,
  inputStyle,
  Loading,
  OpsCard,
  PageHeader,
  ProgressBar,
  StepDone,
  TechnicalDrawer,
  textareaStyle,
} from "../../ui/kit";

type MauPhieu = { ma: string; ten: string };

type BuocState = {
  ma: string;
  ten: string;
  loai: string;
  hoan_thanh: boolean;
  gia_tri?: string;
  timing_ms?: number;
};

type PhieuData = {
  id: string;
  mau: string;
  trang_thai: "dang_lam" | "hoan_thanh" | "treo" | string;
  buoc_hien_tai?: string;
  buocs: BuocState[];
  signals?: { timing_ms?: Record<string, number> };
};

const MAU_MO_QUAN: MauPhieu = { ma: "mo_quan", ten: "Mở quán" };

export default function PhieuPage() {
  const router = useRouter();
  const [token, setToken] = useState("");
  const [mauList, setMauList] = useState<MauPhieu[]>([]);
  const [mauLoading, setMauLoading] = useState(true);
  const [phieu, setPhieu] = useState<PhieuData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [treoText, setTreoText] = useState("");
  const [showTreo, setShowTreo] = useState(false);
  const [inputVal, setInputVal] = useState("");
  const [done, setDone] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setToken(getToken());
  }, []);

  const loadMau = useCallback(() => {
    if (!getToken()) return;
    setMauLoading(true);
    apiGet<MauPhieu[] | { items: MauPhieu[] }>("/api/v1/phieu/mau")
      .then((d) => {
        const list = Array.isArray(d) ? d : d.items ?? [];
        setMauList(list.length > 0 ? list : [MAU_MO_QUAN]);
      })
      .catch(() => setMauList([MAU_MO_QUAN]))
      .finally(() => setMauLoading(false));
  }, []);

  useEffect(() => {
    if (token) loadMau();
  }, [token, loadMau]);

  const tenMau = useCallback(
    (ma?: string) => {
      const found = mauList.find((m) => m.ma === ma);
      if (found) return safeText(found.ten, "Phiếu ca");
      return ma === MAU_MO_QUAN.ma ? MAU_MO_QUAN.ten : "Phiếu ca";
    },
    [mauList],
  );

  async function startPhieu(ma: string) {
    setBusy(true);
    setError(null);
    try {
      await apiSend("/api/v1/diem-danh");
    } catch (e) {
      setError(
        viError(e, {
          doing: "điểm danh để mở phiếu",
          forbidden: "Bạn chưa có ca hôm nay nên chưa điểm danh được. Nhờ quản lý gán ca rồi mở lại phiếu.",
        }),
      );
      setBusy(false);
      return;
    }
    try {
      const data = await apiSend<PhieuData>("/api/v1/phieu/start", { mau: ma });
      setPhieu(data);
      setDone(false);
    } catch (e) {
      setError(viError(e, { doing: "mở được phiếu mới" }));
    } finally {
      setBusy(false);
    }
  }

  async function completeBuoc(ma: string, gia_tri?: string) {
    if (!phieu) return;
    setBusy(true);
    setError(null);
    try {
      const body: Record<string, unknown> = { ma };
      if (gia_tri !== undefined) body.gia_tri = gia_tri;
      const updated = await apiSend<PhieuData>(`/api/v1/phieu/${phieu.id}/buoc`, body);
      setPhieu(updated);
      setInputVal("");
      if (updated.trang_thai === "hoan_thanh") setDone(true);
    } catch (e) {
      setError(viError(e, { doing: "đóng được bước này" }));
    } finally {
      setBusy(false);
    }
  }

  async function sendPhoto(buocMa: string, dataUrl: string) {
    if (!phieu) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await apiSend<PhieuData>(`/api/v1/phieu/${phieu.id}/minh-chung`, {
        buoc_ma: buocMa,
        data_url: dataUrl,
      });
      setPhieu(updated);
      if (updated.trang_thai === "hoan_thanh") setDone(true);
    } catch (e) {
      setError(viError(e, { doing: "gửi được ảnh minh chứng" }));
    } finally {
      setBusy(false);
    }
  }

  async function handleTreo() {
    if (!phieu || !treoText.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await apiSend<PhieuData>(`/api/v1/phieu/${phieu.id}/treo`, {
        noi_dung: treoText,
      });
      setPhieu(updated);
      setTreoText("");
      setShowTreo(false);
    } catch (e) {
      setError(viError(e, { doing: "treo được phiếu này" }));
    } finally {
      setBusy(false);
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>, buocMa: string) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setError("Cần một tấm ảnh. Chụp lại bằng camera hoặc chọn ảnh trong máy.");
      return;
    }
    const reader = new FileReader();
    reader.onerror = () => setError("Không đọc được ảnh vừa chọn. Chụp lại một tấm khác.");
    reader.onload = () => sendPhoto(buocMa, String(reader.result ?? ""));
    reader.readAsDataURL(file);
  }

  const buocs = phieu?.buocs ?? [];
  const currentBuocIndex = buocs.findIndex((b) => !b.hoan_thanh);
  const currentBuoc = currentBuocIndex >= 0 ? buocs[currentBuocIndex] : null;
  const completed = buocs.filter((b) => b.hoan_thanh).length;
  const total = buocs.length;
  const activeRun = Boolean(phieu && !done && currentBuoc);

  if (!token) {
    return (
      <div className="nq-page nq-page--run">
        <PageHeader
          kicker="Một tay · một bước"
          title="Phiếu mở quán"
          meta="Phiếu chạy theo phiên của bạn, nên cần đăng nhập trước."
        />
        <Btn variant="primary" block onClick={() => router.push("/login")}>
          Đăng nhập để mở phiếu
        </Btn>
      </div>
    );
  }

  if (done || phieu?.trang_thai === "hoan_thanh") {
    return (
      <div className="nq-page nq-page--run nq-page--center">
        <PageHeader
          kicker="Xong phiếu"
          title="Hoàn thành"
          meta={`Đã đóng đủ ${total} bước của ${tenMau(phieu?.mau)}. Việc treo (nếu có) đã sang trang Việc treo.`}
        />
        <Btn
          variant="primary"
          block
          onClick={() => {
            setPhieu(null);
            setDone(false);
          }}
        >
          Mở phiếu tiếp theo
        </Btn>
      </div>
    );
  }

  return (
    <div className={`nq-page nq-page--run${activeRun ? " nq-page--run-has-bar" : ""}`}>
      <PageHeader
        kicker="Một tay · một bước"
        title="Phiếu mở quán"
        meta={
          !phieu
            ? "Chọn mẫu phiếu để bắt đầu. Hệ thống điểm danh giúp bạn trước khi mở bước đầu."
            : "Làm từng bước một. Kẹt ở đâu thì treo lại, quản lý thấy ngay trên bảng hôm nay."
        }
      />

      {error ? <Alert>{error}</Alert> : null}

      {!phieu && (
        <>
          {mauLoading ? <Loading skeleton="list">Đang lấy danh sách mẫu phiếu…</Loading> : null}
          {!mauLoading && mauList.length === 0 ? (
            <Empty>Quán chưa cài mẫu phiếu nào. Nhờ quản lý thêm mẫu trong cẩm nang.</Empty>
          ) : null}
          {!mauLoading && mauList.length > 0 ? (
            <div className="nq-stack">
              {mauList.map((m) => (
                <Btn key={m.ma} variant="primary" block disabled={busy} onClick={() => startPhieu(m.ma)}>
                  Bắt đầu {safeText(m.ten, "phiếu ca").toLowerCase()}
                </Btn>
              ))}
            </div>
          ) : null}
        </>
      )}

      {phieu && !done && (
        <>
          <div style={{ marginBottom: "1.25rem" }}>
            <div className="nq-run-meta">
              <span>
                Bước {Math.min(completed + 1, Math.max(total, 1))} / {total}
              </span>
              <span>{tenMau(phieu.mau)}</span>
            </div>
            <ProgressBar value={completed} max={total} />
          </div>

          {buocs
            .filter((b) => b.hoan_thanh)
            .map((b) => (
              <StepDone
                key={b.ma}
                label={safeText(b.ten, "Bước đã xong")}
                timingMs={phieu.signals?.timing_ms?.[b.ma]}
              />
            ))}

          {currentBuoc ? (
            <OpsCard eyebrow={loaiBuocLabel(currentBuoc.loai)} title={safeText(currentBuoc.ten, "Bước tiếp theo")}>
              {(currentBuoc.loai === "text" || currentBuoc.loai === "nhap") && (
                <Field label="Số liệu đọc được">
                  <input
                    type="text"
                    value={inputVal}
                    onChange={(e) => setInputVal(e.target.value)}
                    placeholder="Ví dụ: 4 độ C"
                    style={inputStyle}
                  />
                </Field>
              )}
              {currentBuoc.loai === "photo" && (
                <>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    capture="environment"
                    style={{ display: "none" }}
                    onChange={(e) => handleFileChange(e, currentBuoc.ma)}
                  />
                  <Btn variant="ghost" block disabled={busy} onClick={() => fileInputRef.current?.click()}>
                    Chụp ảnh minh chứng
                  </Btn>
                </>
              )}
            </OpsCard>
          ) : null}

          {showTreo ? (
            <OpsCard title="Để lại việc treo">
              <Field label="Kẹt ở đâu">
                <textarea
                  value={treoText}
                  onChange={(e) => setTreoText(e.target.value)}
                  placeholder="Ví dụ: máy pha không lên áp, đã tắt nguồn chờ thợ"
                  rows={3}
                  style={textareaStyle}
                />
              </Field>
              <InlineActions>
                <Btn variant="danger" disabled={busy || !treoText.trim()} onClick={handleTreo}>
                  Gửi việc treo
                </Btn>
                <Btn variant="ghost" onClick={() => setShowTreo(false)}>
                  Quay lại phiếu
                </Btn>
              </InlineActions>
            </OpsCard>
          ) : null}

          <TechnicalDrawer
            lines={[`Mã lần chạy: ${safeText(phieu.id)}`, `Mã mẫu: ${safeText(phieu.mau)}`]}
          />
        </>
      )}

      {activeRun && currentBuoc ? (
        <FixedBottomBar>
          {currentBuoc.loai !== "photo" ? (
            <Btn
              variant="primary"
              disabled={busy}
              onClick={() =>
                completeBuoc(
                  currentBuoc.ma,
                  currentBuoc.loai === "text" || currentBuoc.loai === "nhap" ? inputVal || undefined : undefined,
                )
              }
            >
              {busy ? "Đang xử lý…" : "Xong bước này"}
            </Btn>
          ) : null}
          <Btn variant="ghost" title="Để lại việc treo" onClick={() => setShowTreo((s) => !s)}>
            Treo lại
          </Btn>
        </FixedBottomBar>
      ) : null}
    </div>
  );
}
