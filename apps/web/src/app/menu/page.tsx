"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { viError } from "../../lib/present";
import { getToken } from "../../lib/session";
import { Alert, Btn, Empty, Field, Loading, PageHeader, StatusChip } from "../../ui/kit";

type Mon = { id: string; ten: string; gia: number; an: boolean; bom: Record<string, number> };

const EMPTY = { id: "", ten: "", gia: "", an: false, bom: "{\"ly\": 1}" };

export default function MenuPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<Mon[]>([]);
  const [form, setForm] = useState(EMPTY);
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
  useEffect(() => { if (token) void load(); }, [load, token]);

  function edit(mon: Mon) {
    setForm({ id: mon.id, ten: mon.ten, gia: String(mon.gia), an: mon.an, bom: JSON.stringify(mon.bom) });
    setMsg(null);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    let bom: Record<string, number>;
    try {
      bom = JSON.parse(form.bom) as Record<string, number>;
    } catch {
      setError("BOM cần là JSON hợp lệ, ví dụ {\"cafe_g\": 18, \"ly\": 1}.");
      return;
    }
    const gia = Number(form.gia);
    if (!Number.isInteger(gia) || gia < 0) {
      setError("Giá cần là số nguyên không âm.");
      return;
    }
    setBusy(true);
    try {
      await apiSend(`/api/v1/menu/${form.id.trim()}`, { ten: form.ten, gia, an: form.an, bom }, "PUT");
      setMsg("Đã lưu món. Menu này chỉ dùng tại quầy nội bộ.");
      setForm(EMPTY);
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
      <PageHeader kicker="Admin quán" title="Menu & giá" meta="Chủ quán cấu hình món, giá và BOM ước lượng. Không có định giá tự động hoặc menu khách." />
      {error ? <Alert>{error}</Alert> : null}
      {msg ? <Alert kind="ok">{msg}</Alert> : null}
      <form className="nq-item" onSubmit={(e) => void submit(e)}>
        <h2>{form.id ? "Sửa món" : "Thêm món"}</h2>
        <Field label="Mã món">
          <input value={form.id} onChange={(e) => setForm({ ...form, id: e.target.value.toLowerCase() })} placeholder="tra_chanh" required />
        </Field>
        <Field label="Tên món">
          <input value={form.ten} onChange={(e) => setForm({ ...form, ten: e.target.value })} required />
        </Field>
        <Field label="Giá (đồng)">
          <input value={form.gia} onChange={(e) => setForm({ ...form, gia: e.target.value })} inputMode="numeric" required />
        </Field>
        <Field label="BOM ước lượng (JSON)">
          <textarea value={form.bom} onChange={(e) => setForm({ ...form, bom: e.target.value })} rows={3} />
        </Field>
        <label><input type="checkbox" checked={form.an} onChange={(e) => setForm({ ...form, an: e.target.checked })} /> Ẩn món khỏi quầy</label>
        <p><Btn type="submit" busy={busy}>Lưu món</Btn></p>
      </form>
      <h2>Toàn bộ menu</h2>
      {loading ? <Loading skeleton="list">Đang tải menu…</Loading> : null}
      {!loading && items.length === 0 ? <Empty>Chưa có món nào.</Empty> : null}
      <div className="nq-list">
        {items.map((mon) => (
          <article key={mon.id} className="nq-item">
            <div><strong>{mon.ten}</strong><p className="nq-muted">{mon.id} · {mon.gia.toLocaleString("vi-VN")}đ · BOM {JSON.stringify(mon.bom)}</p></div>
            <div className="flex gap-2"><StatusChip tone={mon.an ? "warn" : "ok"}>{mon.an ? "đang ẩn" : "đang bán"}</StatusChip><Btn variant="ghost" onClick={() => edit(mon)}>Sửa</Btn></div>
          </article>
        ))}
      </div>
    </section>
  );
}
