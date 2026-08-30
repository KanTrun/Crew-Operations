"use client";

import { Btn, Field, Input, Select } from "./kit";

export type BomRow = { key: string; qty: string };

/** Nguyên liệu phổ biến — key giữ nguyên cho API, nhãn dành cho quản lý. */
export const BOM_INGREDIENTS: Array<{ key: string; label: string; unit: string }> = [
  { key: "ca_phe_hat", label: "Cà phê hạt", unit: "g" },
  { key: "cafe_g", label: "Cà phê (g)", unit: "g" },
  { key: "sua_tuoi", label: "Sữa tươi", unit: "ml" },
  { key: "tra", label: "Trà", unit: "g" },
  { key: "matcha", label: "Matcha", unit: "g" },
  { key: "dao", label: "Đào / topping trái", unit: "g" },
  { key: "da", label: "Đá", unit: "g" },
  { key: "banh", label: "Bánh kèm", unit: "cái" },
  { key: "ly", label: "Ly / cốc dùng một lần", unit: "cái" },
  { key: "nuoc_dong_chai", label: "Nước đóng chai", unit: "chai" },
];

const CUSTOM = "__custom__";

export function ingredientLabel(key: string): string {
  const hit = BOM_INGREDIENTS.find((i) => i.key === key);
  if (hit) return hit.label;
  return key.replace(/_/g, " ");
}

export function ingredientUnit(key: string): string {
  return BOM_INGREDIENTS.find((i) => i.key === key)?.unit ?? "đv";
}

export function bomToRows(bom: Record<string, number>): BomRow[] {
  const entries = Object.entries(bom ?? {});
  if (entries.length === 0) return [{ key: "ly", qty: "1" }];
  return entries.map(([key, qty]) => ({ key, qty: String(qty) }));
}

export function rowsToBom(rows: BomRow[]): Record<string, number> {
  const out: Record<string, number> = {};
  for (const row of rows) {
    const key = row.key.trim();
    const qty = Number(row.qty);
    if (!key || !Number.isFinite(qty) || qty <= 0) continue;
    out[key] = qty;
  }
  return out;
}

type BomEditorProps = {
  rows: BomRow[];
  onChange: (rows: BomRow[]) => void;
};

export function BomEditor({ rows, onChange }: BomEditorProps) {
  function updateRow(index: number, patch: Partial<BomRow>) {
    onChange(rows.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }

  function removeRow(index: number) {
    if (rows.length <= 1) {
      onChange([{ key: "ly", qty: "1" }]);
      return;
    }
    onChange(rows.filter((_, i) => i !== index));
  }

  return (
    <div className="nq-bom-editor space-y-3">
      <p className="text-xs leading-relaxed text-[var(--nq-ink-muted)]">
        Ghi rõ nguyên liệu dùng cho <strong>một ly / một phần</strong>. Khi hoàn tất đơn ở quầy, hệ thống tự trừ kho theo
        bảng này — không cần nhập mã JSON.
      </p>

      <ul className="space-y-2">
        {rows.map((row, index) => {
          const preset = BOM_INGREDIENTS.some((i) => i.key === row.key);
          const selectValue = preset ? row.key : row.key ? CUSTOM : "";
          const unit = ingredientUnit(row.key);

          return (
            <li key={`bom-${index}`} className="nq-bom-row">
              <div className="nq-bom-row__field">
                <label className="nq-bom-row__label" htmlFor={`bom-ing-${index}`}>
                  Nguyên liệu
                </label>
                <Select
                  id={`bom-ing-${index}`}
                  value={selectValue}
                  onChange={(e) => {
                    const v = e.target.value;
                    if (v === CUSTOM) updateRow(index, { key: "" });
                    else updateRow(index, { key: v });
                  }}
                >
                  <option value="">— Chọn —</option>
                  {BOM_INGREDIENTS.map((ing) => (
                    <option key={ing.key} value={ing.key}>
                      {ing.label}
                    </option>
                  ))}
                  <option value={CUSTOM}>Khác (tự nhập)…</option>
                </Select>
              </div>

              {!preset ? (
                <div className="nq-bom-row__field">
                  <label className="nq-bom-row__label" htmlFor={`bom-key-${index}`}>
                    Tên nguyên liệu
                  </label>
                  <Input
                    id={`bom-key-${index}`}
                    value={row.key}
                    onChange={(e) => updateRow(index, { key: e.target.value.toLowerCase().replace(/\s+/g, "_") })}
                    placeholder="vd: siro_vai"
                  />
                </div>
              ) : null}

              <div className="nq-bom-row__field nq-bom-row__field--qty">
                <label className="nq-bom-row__label" htmlFor={`bom-qty-${index}`}>
                  Số lượng ({unit})
                </label>
                <Input
                  id={`bom-qty-${index}`}
                  value={row.qty}
                  onChange={(e) => updateRow(index, { qty: e.target.value })}
                  inputMode="decimal"
                  placeholder="0"
                />
              </div>

              <Btn type="button" variant="ghost" className="nq-bom-row__remove" onClick={() => removeRow(index)}>
                Xóa
              </Btn>
            </li>
          );
        })}
      </ul>

      <Btn
        type="button"
        variant="ghost"
        onClick={() => onChange([...rows, { key: "", qty: "" }])}
      >
        + Thêm nguyên liệu
      </Btn>
    </div>
  );
}
