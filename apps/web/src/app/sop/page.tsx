"use client";

/**
 * Hỏi SOP — "AI hướng dẫn" của quán, và nó có thật.
 *
 * AG-SOP chỉ đọc hai nguồn: mẫu phiếu quán đang dùng và luật cẩm nang đã vào
 * hiệu lực. Không khớp được thì nó trả `chua_co` và nói thẳng là chưa có trong
 * cẩm nang — không đoán, không viết văn. Vì thế mọi câu trả lời đều kiểm được,
 * và trang này in trích dẫn ngay dưới câu trả lời chứ không giấu.
 *
 * Hai chi tiết đáng ghi lại:
 *  1. Trích dẫn máy chủ trả về là mã (`phieu:nhiet_do_tu_lanh`). In mã lên UI là
 *     vi phạm mục Disclosure rules, nên trang tải bảng mẫu phiếu + cẩm nang rồi
 *     tra ra tên bước và câu luật. Tra không được thì in loại nguồn, vẫn không
 *     in mã.
 *  2. Câu hỏi có thể tới từ `?q=` (tour hướng dẫn và trang /huong-dan bấm sang).
 *     Đọc từ `window.location.search` trong effect thay vì `useSearchParams` để
 *     trang không cần biên giới Suspense lúc dựng tĩnh.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { safeText, trichDanTach, viError } from "../../lib/present";
import { getToken } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  Empty,
  Field,
  Loading,
  OpsCard,
  PageHeader,
  textareaStyle,
} from "../../ui/kit";

type Ans = { cau_tra_loi: string; trich_dan: string[]; chua_co: boolean };

type MauPhieu = { ma: string; ten?: string; buoc?: Array<{ ma?: string; ten?: string }> };
type Luat = { id: string; cau?: string; trang_thai?: string };

const GOI_Y = [
  "Nhiệt độ tủ lạnh bao nhiêu là được?",
  "Ca sáng phải kiểm kê mấy mặt hàng?",
  "Bàn giao ca gồm những bước nào?",
];

export default function SopPage() {
  const [token, setToken] = useState("");
  const [q, setQ] = useState(GOI_Y[0]);
  const [a, setA] = useState<Ans | null>(null);
  const [daHoi, setDaHoi] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [tenBuoc, setTenBuoc] = useState<Record<string, string>>({});
  const [cauLuat, setCauLuat] = useState<Record<string, string>>({});
  const tuDong = useRef(false);

  useEffect(() => {
    setToken(getToken());
  }, []);

  const hoi = useCallback(async (cau: string) => {
    const text = cau.trim();
    setError(null);
    if (!text) {
      setError("Nhập câu hỏi trước khi bấm hỏi.");
      return;
    }
    setBusy(true);
    try {
      const d = await apiSend<Ans>("/api/v1/sop", { question: text });
      setA(d);
      setDaHoi(text);
    } catch (e) {
      setError(viError(e, { doing: "hỏi được cẩm nang quán" }));
    } finally {
      setBusy(false);
    }
  }, []);

  // Bảng tra tên: để trích dẫn hiện tên bước và câu luật thay vì mã nội bộ.
  useEffect(() => {
    if (!token) return;
    apiGet<{ items?: MauPhieu[] }>("/api/v1/phieu/mau")
      .then((d) => {
        const map: Record<string, string> = {};
        for (const m of d.items ?? []) {
          for (const b of m.buoc ?? []) {
            const ma = safeText(b.ma, "");
            if (ma && !map[ma]) {
              map[ma] = `${safeText(b.ten, "bước trong phiếu")} — phiếu ${safeText(m.ten, "ca")}`;
            }
          }
        }
        setTenBuoc(map);
      })
      .catch(() => setTenBuoc({}));
    apiGet<{ items?: Luat[] }>("/api/v1/cam-nang")
      .then((d) => {
        const map: Record<string, string> = {};
        for (const l of d.items ?? []) {
          const id = safeText(l.id, "");
          if (id) map[id] = safeText(l.cau, "luật trong cẩm nang");
        }
        setCauLuat(map);
      })
      .catch(() => setCauLuat({}));
  }, [token]);

  // Câu hỏi tới từ tour hoặc trang hướng dẫn: điền sẵn rồi hỏi luôn một lần.
  useEffect(() => {
    if (!token || tuDong.current) return;
    const raw = new URLSearchParams(window.location.search).get("q");
    const cau = (raw ?? "").trim().slice(0, 200);
    if (!cau) return;
    tuDong.current = true;
    setQ(cau);
    void hoi(cau);
  }, [token, hoi]);

  if (!token) return <AuthGate />;

  const trichDan = (a?.trich_dan ?? []).map((x) => safeText(x, "")).filter(Boolean);

  return (
    <div className="nq-page nq-page--run">
      <PageHeader
        kicker="Chỉ trả lời từ phiếu và luật đã duyệt"
        title="Hỏi SOP"
        meta="Đặt câu bằng tiếng Việt thường ngày. Hệ thống dẫn lại phiếu và luật của quán kèm nguồn; không có căn cứ thì nói thẳng là chưa có trong cẩm nang."
      />

      <OpsCard eyebrow="Câu hỏi" title="Hỏi cẩm nang quán">
        <Field label="Bạn muốn biết gì">
          <textarea
            value={q}
            onChange={(e) => setQ(e.target.value)}
            rows={3}
            style={textareaStyle}
            aria-label="Bạn muốn biết gì"
          />
        </Field>
        <Btn variant="primary" busy={busy} busyLabel="Đang tra cẩm nang…" onClick={() => void hoi(q)}>
          Hỏi cẩm nang
        </Btn>
        <div className="nq-tour-asks">
          <p className="nq-tour-asks-k">Câu hay hỏi:</p>
          {GOI_Y.map((c) => (
            <button
              key={c}
              type="button"
              className="nq-ask"
              disabled={busy}
              onClick={() => {
                setQ(c);
                void hoi(c);
              }}
            >
              {c}
            </button>
          ))}
        </div>
      </OpsCard>

      {error ? <Alert>{error}</Alert> : null}
      {busy && !a ? <Loading skeleton="card">Đang tra cẩm nang…</Loading> : null}

      {a ? (
        <OpsCard eyebrow={`Đã hỏi: ${daHoi}`} title="Cẩm nang trả lời">
          <p style={{ margin: 0, lineHeight: 1.6, maxWidth: "64ch" }}>
            {safeText(a.cau_tra_loi, "Cẩm nang chưa có câu trả lời cho câu này.")}
          </p>
          {a.chua_co ? (
            <Alert kind="info">
              Chưa có trong cẩm nang quán. Làm theo cách quán đang làm, rồi nhờ quản lý ghi thành luật
              — vài lần sửa giống nhau là hệ thống tự đề xuất.
            </Alert>
          ) : null}
          {trichDan.length > 0 ? (
            <ul className="nq-cites">
              {trichDan.map((raw) => {
                const t = trichDanTach(raw);
                const ten =
                  t.loai === "phieu"
                    ? tenBuoc[t.ma]
                    : t.loai === "luat"
                      ? cauLuat[t.ma]
                      : undefined;
                return (
                  <li key={raw}>
                    <span className="nq-cite-k">{t.nguon}</span>
                    <span>
                      {ten ??
                        (t.loai === "phieu"
                          ? "một bước trong mẫu phiếu quán"
                          : "một luật đang hiệu lực trong cẩm nang")}
                    </span>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="nq-table-note">
              Câu này không dẫn được về phiếu hay luật nào, nên cẩm nang không nhận là đã trả lời.
            </p>
          )}
        </OpsCard>
      ) : (
        !busy && !error && <Empty>Chưa có câu trả lời — đặt câu hỏi để tra cẩm nang.</Empty>
      )}
    </div>
  );
}
