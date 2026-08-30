"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
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

function slugFromName(name: string): string {
  return name
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 48);
}

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

  const isExisting = useMemo(
    () => Boolean(form.id && items.some((m) => m.id === form.id)),
    [form.id, items],
  );

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
    if (!file || !isExisting) {
      setError("Lưu món lần đầu trước, sau đó mới tải ảnh được.");
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

    const ten = form.ten.trim();
    if (!ten) {
      setError("Nhập tên món.");
      return;
    }

    const id = isExisting ? form.id.trim() : slugFromName(ten);
    if (!id) {
      setError("Tên món cần có ít nhất một chữ hoặc số.");
      return;
    }

    const bom = rowsToBom(form.bomRows);
    if (Object.keys(bom).length === 0) {
      setError("Thêm ít nhất một nguyên liệu và nhập số lượng lớn hơn 0.");
      return;
    }

    const gia = Number(form.gia);
    if (!Number.isInteger(gia) || gia < 0) {
      setError("Giá bán cần là số nguyên (ví dụ: 35000).");
      return;
    }

    setBusy(true);
    try {
      await apiSend(`/api/v1/menu/${id}`, { ten, gia, an: form.an, bom, hinh_url: form.hinh_url }, "PUT");
      setForm((f) => ({ ...f, id }));
      setMsg(isExisting ? "Đã cập nhật món." : "Đã thêm món mới. Bạn có thể tải ảnh ngay bên dưới.");
      await load();
    } catch (err) {
      setError(viError(err, { doing: "lưu món" }));
    } finally {
      setBusy(false);
    }
  }

  if (!token) return null;

  return (
    <section className="nq-page nq-page--wide">
      <PageHeader
        kicker="Admin quán"
        title="Menu & giá"
        meta="Chọn món bên trái để sửa, hoặc điền form bên phải để thêm món mới."
      />
      {error ? <Alert>{error}</Alert> : null}
      {msg ? <Alert kind="ok">{msg}</Alert> : null}

      <div className="nq-split nq-split--menu">
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
                  <p className="nq-muted text-xs">
                    {mon.gia.toLocaleString("vi-VN")}đ · {mon.an ? "ẩn trên quầy" : "đang bán"}
                  </p>
                </div>
              </button>
            ))}
          </div>
        </div>

        <aside className="nq-sticky-panel nq-menu-form space-y-4">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-sm font-mono uppercase tracking-widest">{isExisting ? "Sửa món" : "Thêm món mới"}</h2>
            {form.ten || form.id ? (
              <Btn variant="ghost" onClick={resetForm}>
                Làm mới
              </Btn>
            ) : null}
          </div>

          <form className="space-y-5" onSubmit={(e) => void submit(e)}>
            <Field label="Tên món hiển thị" hint="Tên khách và nhân viên thấy trên quầy.">
              <Input
                value={form.ten}
                onChange={(e) => setForm({ ...form, ten: e.target.value })}
                placeholder="Ví dụ: Trà đào"
                required
              />
            </Field>

            <Field label="Giá bán" hint="Nhập số tiền bằng đồng, không cần dấu chấm.">
              <Input
                value={form.gia}
                onChange={(e) => setForm({ ...form, gia: e.target.value.replace(/\D/g, "") })}
                inputMode="numeric"
                placeholder="35000"
                required
              />
            </Field>

            {isExisting ? (
              <p className="text-xs text-[var(--nq-ink-muted)]">
                Mã trong hệ thống: <span className="font-mono text-[var(--nq-ink)]">{form.id}</span>
              </p>
            ) : null}

            <section className="nq-menu-form__section" aria-labelledby="menu-bom-title">
              <h3 id="menu-bom-title" className="nq-menu-form__section-title">
                Nguyên liệu ước lượng
              </h3>
              <BomEditor rows={form.bomRows} onChange={(bomRows) => setForm({ ...form, bomRows })} />
            </section>

            <Field label="Ảnh món">
              <input
                type="file"
                className="nq-input"
                accept="image/jpeg,image/png,image/webp,image/gif"
                onChange={(e) => void onImage(e.target.files?.[0] ?? null)}
                disabled={!isExisting || busy}
              />
              <p className="nq-muted mt-1 text-xs">
                {isExisting
                  ? "JPG/PNG/WebP, tối đa 4MB."
                  : "Lưu món lần đầu trước, sau đó quay lại để tải ảnh."}
              </p>
            </Field>

            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.an} onChange={(e) => setForm({ ...form, an: e.target.checked })} />
              Ẩn món khỏi quầy (khách không đặt được)
            </label>

            <Btn type="submit" busy={busy} block>
              {isExisting ? "Cập nhật món" : "Thêm món"}
            </Btn>
          </form>
        </aside>
      </div>
    </section>
  );
}
