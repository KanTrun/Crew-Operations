"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiGet, apiSend, apiUpload } from "../../lib/api";
import { menuImageUrl } from "../../lib/menu-image";
import { viError } from "../../lib/present";
import { getToken } from "../../lib/session";
import { BomEditor, bomToRows, rowsToBom, type BomRow } from "../../ui/bom-editor";
import { Alert, Btn, Empty, Field, Input, Loading, PageHeader } from "../../ui/kit";

type Mon = { id: string; ten: string; gia: number; an: boolean; bom: Record<string, number>; hinh_url?: string };

type FormState = {
  id: string;
  ten: string;
  gia: string;
  an: boolean;
  bomRows: BomRow[];
  hinh_url: string;
};

const EMPTY: FormState = {
  id: "",
  ten: "",
  gia: "",
  an: false,
  bomRows: bomToRows({ ly: 1 }),
  hinh_url: "",
};

function MenuThumb({ mon, selected }: { mon: Mon; selected: boolean }) {
  const [err, setErr] = useState(false);
  const src = menuImageUrl(mon.id, mon.hinh_url);
  return (
    <div className="relative aspect-square w-full overflow-hidden rounded-[var(--nq-radius-bubble)] border border-[var(--nq-line)] bg-[var(--nq-surface-hi)]">
      {!err ? (
        <img src={src} alt="" className="h-full w-full object-cover" onError={() => setErr(true)} />
      ) : (
        <div className="flex h-full items-center justify-center text-xs font-mono uppercase tracking-widest text-[var(--nq-dim)]">
          {mon.ten.slice(0, 2)}
        </div>
      )}
      {selected ? (
        <span className="absolute inset-x-0 bottom-0 bg-[var(--nq-copper)] py-0.5 text-center text-[10px] font-bold uppercase text-black">
          Đang sửa
        </span>
      ) : null}
    </div>
  );
}

export default function MenuPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<Mon[]>([]);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!getToken()) return;
    setLoading(true);
    try {
      const out = await apiGet<{ items: Mon[] }>("/api/v1/menu/quan-tri");
      setItems(out.items ?? []);
      setError(null);
    } catch (e) {
      setError(viError(e, { doing: "mở menu quản trị" }));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => setToken(getToken()), []);
  useEffect(() => {
    if (token) void load();
  }, [load, token]);

  function select(mon: Mon) {
    setForm({
      id: mon.id,
      ten: mon.ten,
      gia: String(mon.gia),
      an: mon.an,
      bomRows: bomToRows(mon.bom),
      hinh_url: mon.hinh_url ?? "",
    });
    setMsg(null);
  }

  function resetForm() {
    setForm(EMPTY);
    setMsg(null);
  }

  async function onImage(file: File | null) {
    if (!file || !form.id.trim()) {
      setError("Lưu mã món trước khi tải ảnh.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const out = await apiUpload<{ hinh_url?: string }>(`/api/v1/menu/${form.id.trim()}/anh`, fd);
      setForm((f) => ({ ...f, hinh_url: out.hinh_url ?? f.hinh_url }));
      setMsg("Đã tải ảnh món.");
      await load();
    } catch (e) {
      setError(viError(e, { doing: "tải ảnh món" }));
    } finally {
      setBusy(false);
    }
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const bom = rowsToBom(form.bomRows);
    if (Object.keys(bom).length === 0) {
      setError("Thêm ít nhất một nguyên liệu với số lượng lớn hơn 0.");
      return;
    }
    const gia = Number(form.gia);
    if (!Number.isInteger(gia) || gia < 0) {
      setError("Giá cần là số nguyên không âm.");
      return;
    }
    setBusy(true);
    try {
      await apiSend(
        `/api/v1/menu/${form.id.trim()}`,
        { ten: form.ten, gia, an: form.an, bom, hinh_url: form.hinh_url },
        "PUT",
      );
      setMsg("Đã lưu món. Menu này chỉ dùng tại quầy nội bộ.");
      await load();
    } catch (err) {
      setError(viError(err, { doing: "lưu món" }));
    } finally {
      setBusy(false);
    }
  }

  if (!token) return null;

  return (
    <section className="nq-page">
      <PageHeader
        kicker="Admin quán"
        title="Menu & giá"
        meta="Chọn món bên trái, chỉnh tên – giá – ảnh – nguyên liệu ước lượng bên phải. Không cần biết lập trình."
      />
      {error ? <Alert>{error}</Alert> : null}
      {msg ? <Alert kind="ok">{msg}</Alert> : null}

      <div className="nq-split">
        <div>
          <h2 className="mb-4 text-sm font-mono uppercase tracking-widest text-[var(--nq-dim)]">Danh mục món</h2>
          {loading ? <Loading skeleton="list">Đang tải menu…</Loading> : null}
          {!loading && items.length === 0 ? <Empty>Chưa có món nào.</Empty> : null}
          <div className="nq-card-grid">
            {items.map((mon) => (
              <button
                key={mon.id}
                type="button"
                className={`nq-menu-card ${form.id === mon.id ? "nq-menu-card--on" : ""}`}
                onClick={() => select(mon)}
              >
                <MenuThumb mon={mon} selected={form.id === mon.id} />
                <div>
                  <strong className="block text-sm">{mon.ten}</strong>
                  <p className="nq-muted text-xs font-mono">
                    {mon.gia.toLocaleString("vi-VN")}đ · {mon.an ? "ẩn" : "bán"}
                  </p>
                </div>
              </button>
            ))}
          </div>
        </div>

        <aside className="nq-sticky-panel nq-item space-y-4">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-sm font-mono uppercase tracking-widest">{form.id ? "Sửa món" : "Thêm món"}</h2>
            {form.id ? (
              <Btn variant="ghost" onClick={resetForm}>
                Mới
              </Btn>
            ) : null}
          </div>
          <form className="space-y-4" onSubmit={(e) => void submit(e)}>
            <Field label="Mã món" hint="Chữ thường, không dấu — dùng nội bộ, nhân viên không cần nhớ.">
              <Input
                value={form.id}
                onChange={(e) => setForm({ ...form, id: e.target.value.toLowerCase() })}
                placeholder="tra_dao"
                required
                readOnly={Boolean(form.id && items.some((m) => m.id === form.id))}
              />
            </Field>
            <Field label="Tên món">
              <Input value={form.ten} onChange={(e) => setForm({ ...form, ten: e.target.value })} required />
            </Field>
            <Field label="Giá bán (đồng)">
              <Input value={form.gia} onChange={(e) => setForm({ ...form, gia: e.target.value })} inputMode="numeric" required />
            </Field>
            <Field label="Ảnh món">
              <input
                type="file"
                className="nq-input"
                accept="image/jpeg,image/png,image/webp,image/gif"
                onChange={(e) => void onImage(e.target.files?.[0] ?? null)}
                disabled={!form.id.trim() || busy}
              />
              <p className="nq-muted mt-1 text-xs">JPG/PNG/WebP, tối đa 4MB. Lưu mã món trước khi tải.</p>
            </Field>
            <Field label="Nguyên liệu ước lượng (mỗi ly / phần)">
              <BomEditor rows={form.bomRows} onChange={(bomRows) => setForm({ ...form, bomRows })} />
            </Field>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.an} onChange={(e) => setForm({ ...form, an: e.target.checked })} />
              Ẩn món khỏi quầy
            </label>
            <Btn type="submit" busy={busy} block>
              Lưu món
            </Btn>
          </form>
        </aside>
      </div>
    </section>
  );
}
