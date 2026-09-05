"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Alert,
  AuthGate,
  Btn,
  FixedBottomBar,
  inputClassName,
  OpsCard,
  PageHeader,
  ProgressBar,
  StepDone,
  Textarea,
} from "../../ui/kit";
import { CopilotPane } from "../../ui/copilot/CopilotPane";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type MauPhieu = { ma: string; ten: string };

type BuocDef = {
  ma: string;
  ten: string;
  loai: "text" | "photo" | "confirm" | string;
  bat_buoc?: boolean;
};

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

export default function PhieuPage() {
  const [token, setToken] = useState("");
  const [mauList, setMauList] = useState<MauPhieu[]>([]);
  const [phieu, setPhieu] = useState<PhieuData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [treoText, setTreoText] = useState("");
  const [showTreo, setShowTreo] = useState(false);
  const [inputVal, setInputVal] = useState("");
  const [done, setDone] = useState(false);
  const [copilotOpen, setCopilotOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const t = sessionStorage.getItem("nq_token");
    if (t) setToken(t);
  }, []);

  const authHeader = useCallback(
    () => ({ Authorization: `Bearer ${token}` }),
    [token],
  );

  // Load mau list
  useEffect(() => {
    fetch(`${API}/api/v1/phieu/mau`, { headers: authHeader() })
      .then(async (r) => {
        if (!r.ok) throw new Error("load_mau");
        return r.json() as Promise<MauPhieu[] | { items: MauPhieu[] }>;
      })
      .then((d) => setMauList(Array.isArray(d) ? d : d.items ?? []))
      .catch(() => setMauList([{ ma: "mo_quan", ten: "Mở quán" }]));
  }, [authHeader]);

  async function startPhieu(ma: string) {
    setBusy(true);
    setError(null);
    try {
      const checkin = await fetch(`${API}/api/v1/diem-danh`, {
        method: "POST",
        headers: authHeader(),
      });
      if (!checkin.ok) throw new Error("chua_diem_danh");
      const r = await fetch(`${API}/api/v1/phieu/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader() },
        body: JSON.stringify({ mau: ma }),
      });
      if (!r.ok) throw new Error("start_failed");
      const data = (await r.json()) as PhieuData;
      setPhieu(data);
      setDone(false);
    } catch {
      setError("Không tạo được phiếu.");
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
      const r = await fetch(`${API}/api/v1/phieu/${phieu.id}/buoc`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader() },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error("buoc_failed");
      const updated = (await r.json()) as PhieuData;
      setPhieu(updated);
      setInputVal("");
      if (updated.trang_thai === "hoan_thanh") setDone(true);
    } catch {
      setError("Không hoàn thành được bước.");
    } finally {
      setBusy(false);
    }
  }

  async function sendPhoto(buocMa: string, dataUrl: string) {
    if (!phieu) return;
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(`${API}/api/v1/phieu/${phieu.id}/minh-chung`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader() },
        body: JSON.stringify({ buoc_ma: buocMa, data_url: dataUrl }),
      });
      if (!r.ok) throw new Error("photo_failed");
      const updated = (await r.json()) as PhieuData;
      setPhieu(updated);
      if (updated.trang_thai === "hoan_thanh") setDone(true);
      setBusy(false);
    } catch {
      setError("Không gửi được ảnh.");
      setBusy(false);
    }
  }

  async function handleTreo() {
    if (!phieu || !treoText.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(`${API}/api/v1/phieu/${phieu.id}/treo`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader() },
        body: JSON.stringify({ noi_dung: treoText }),
      });
      if (!r.ok) throw new Error("treo_failed");
      const updated = (await r.json()) as PhieuData;
      setPhieu(updated);
      setTreoText("");
      setShowTreo(false);
    } catch {
      setError("Không treo được phiếu.");
    } finally {
      setBusy(false);
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>, buocMa: string) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setError("Cần ảnh thật, không nhận file khác.");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      sendPhoto(buocMa, dataUrl);
    };
    reader.readAsDataURL(file);
  }

  const currentBuocIndex = phieu
    ? phieu.buocs.findIndex((b) => !b.hoan_thanh)
    : -1;
  const currentBuoc = currentBuocIndex >= 0 ? phieu!.buocs[currentBuocIndex] : null;
  const completed = phieu ? phieu.buocs.filter((b) => b.hoan_thanh).length : 0;
  const total = phieu ? phieu.buocs.length : 0;

  if (!token) return <AuthGate />;

  if (done || phieu?.trang_thai === "hoan_thanh") {
    return (
      <div className="nq-page nq-page--center">
        <PageHeader kicker="Xong phiếu" title="Hoàn thành" meta={`Phiếu ${phieu?.id ?? ""} đã xong.`} />
        <Btn variant="ghost" onClick={() => setCopilotOpen(true)}>
          Hỏi trợ lý vận hành
        </Btn>
        <Btn variant="primary" onClick={() => { setPhieu(null); setDone(false); }}>
          Tạo phiếu mới
        </Btn>
        <CopilotPane open={copilotOpen} onClose={() => setCopilotOpen(false)} />
      </div>
    );
  }

  return (
    <div className="nq-page nq-page--run-has-bar">
      <PageHeader
        kicker="Một tay · một bước"
        title={phieu ? `Phiếu ${phieu.mau}` : "Mở phiếu"}
        meta={phieu ? `Bước ${completed + 1} / ${total}` : "Chọn mẫu phiếu. Hệ thống điểm danh trước khi mở."}
      />
      <Btn variant="ghost" onClick={() => setCopilotOpen(true)}>
        Hỏi trợ lý vận hành
      </Btn>

      {error ? <Alert>{error}</Alert> : null}

      {!phieu ? (
        <OpsCard eyebrow="Bước 1" title="Chọn mẫu phiếu">
          <div className="flex flex-col gap-3">
            {mauList.map((m) => (
              <Btn key={m.ma} variant="primary" block disabled={busy} onClick={() => startPhieu(m.ma)}>
                {m.ten || m.ma}
              </Btn>
            ))}
            {mauList.length === 0 ? (
              <Btn variant="primary" block disabled={busy} onClick={() => startPhieu("mo_quan")}>
                Mở quán
              </Btn>
            ) : null}
          </div>
        </OpsCard>
      ) : null}

      {phieu && !done ? (
        <>
          <OpsCard eyebrow="Tiến độ" title="Các bước đã qua">
            <ProgressBar value={completed} max={total} className="mb-6" />
            {phieu.buocs.filter((b) => b.hoan_thanh).map((b) => (
              <StepDone key={b.ma} label={b.ten} timingMs={phieu.signals?.timing_ms?.[b.ma]} />
            ))}
          </OpsCard>

          {currentBuoc ? (
            <OpsCard eyebrow={currentBuoc.loai || "bước"} title={currentBuoc.ten}>
              {(currentBuoc.loai === "text" || currentBuoc.loai === "nhap") && (
                <input
                  type="text"
                  className={inputClassName}
                  value={inputVal}
                  onChange={(e) => setInputVal(e.target.value)}
                  placeholder="Nhập giá trị…"
                />
              )}
              {currentBuoc.loai === "photo" && (
                <>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    capture="environment"
                    className="hidden"
                    onChange={(e) => handleFileChange(e, currentBuoc.ma)}
                  />
                  <Btn variant="ghost" disabled={busy} onClick={() => fileInputRef.current?.click()}>
                    Chụp ảnh minh chứng
                  </Btn>
                </>
              )}
            </OpsCard>
          ) : null}

          {showTreo ? (
            <OpsCard eyebrow="Ngoại lệ" title="Để việc treo">
              <Textarea
                className="min-h-[6rem]"
                value={treoText}
                onChange={(e) => setTreoText(e.target.value)}
                placeholder="Mô tả vấn đề cần treo lại…"
                rows={4}
              />
              <div className="flex flex-wrap gap-2 mt-4">
                <Btn variant="danger" disabled={busy || !treoText.trim()} onClick={handleTreo}>
                  Treo phiếu
                </Btn>
                <Btn variant="ghost" onClick={() => setShowTreo(false)}>
                  Hủy
                </Btn>
              </div>
            </OpsCard>
          ) : null}
        </>
      ) : null}

      {phieu && !done && currentBuoc ? (
        <FixedBottomBar>
          {currentBuoc.loai !== "photo" ? (
            <Btn
              variant="primary"
              block
              busy={busy}
              busyLabel="Đang xử lý…"
              onClick={() =>
                completeBuoc(
                  currentBuoc.ma,
                  currentBuoc.loai === "text" || currentBuoc.loai === "nhap" ? inputVal || undefined : undefined,
                )
              }
            >
              Xong bước này
            </Btn>
          ) : null}
          <Btn variant="ghost" onClick={() => setShowTreo((s) => !s)} title="Để việc treo">
            Treo
          </Btn>
        </FixedBottomBar>
      ) : null}
      <CopilotPane open={copilotOpen} onClose={() => setCopilotOpen(false)} />
    </div>
  );
}
