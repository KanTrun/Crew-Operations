"use client";

import { Btn, Input, Select } from "./kit";

export type BomRow = { key: string; qty: string };

/** Nguyên liệu phổ biến — key giữ nguyên cho API, nhãn dành cho quản lý. */
export const BOM_INGREDIENTS: Array<{ key: string; label: string; unit: string }> = [
  { key: "ca_phe_hat", label: "Cà phê hạt", unit: "g" },
  { key: "cafe_g", label: "Cà phê", unit: "g" },
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
  return BOM_INGREDIENTS.find((i) => i.key === key)?.unit ?? "đơn vị";
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
      onChange([{ key: "", qty: "" }]);
      return;
    }
    onChange(rows.filter((_, i) => i !== index));
  }

  return (
    <div className="nq-bom-editor">
      <p className="nq-bom-editor__intro">
        Mỗi dòng = một nguyên liệu cho <strong>1 ly / 1 phần</strong>. Khi bán xong ở quầy, hệ thống tự trừ kho theo
        bảng này.
      </p>

      <ul className="nq-bom-list">
        {rows.map((row, index) => {
          const preset = BOM_INGREDIENTS.some((i) => i.key === row.key);
          const isCustom = Boolean(row.key) && !preset;
          const selectValue = preset ? row.key : isCustom ? CUSTOM : "";
          const unit = row.key ? ingredientUnit(row.key) : "đơn vị";

          return (
            <li key={`bom-${index}`} className="nq-bom-card">
              <div className="nq-bom-card__head">
                <span className="nq-bom-card__num">Dòng {index + 1}</span>
                <button type="button" className="nq-bom-card__remove" onClick={() => removeRow(index)}>
                  Xóa dòng
                </button>
              </div>

              <div className="nq-bom-card__field">
                <label className="nq-bom-card__label" htmlFor={`bom-ing-${index}`}>
                  Chọn nguyên liệu
                </label>
                <Select
                  id={`bom-ing-${index}`}
                  value={selectValue}
                  onChange={(e) => {
                    const v = e.target.value;
                    if (v === CUSTOM) updateRow(index, { key: "" });
                    else if (v) updateRow(index, { key: v });
                    else updateRow(index, { key: "", qty: "" });
                  }}
                >
                  <option value="">— Chọn trong danh sách —</option>
                  {BOM_INGREDIENTS.map((ing) => (
                    <option key={ing.key} value={ing.key}>
                      {ing.label}
                    </option>
                  ))}
                  <option value={CUSTOM}>Nguyên liệu khác…</option>
                </Select>
              </div>

              {selectValue === CUSTOM ? (
                <div className="nq-bom-card__field">
                  <label className="nq-bom-card__label" htmlFor={`bom-key-${index}`}>
                    Tên nguyên liệu (ghi bằng tiếng Việt)
                  </label>
                  <Input
                    id={`bom-key-${index}`}
                    value={row.key.replace(/_/g, " ")}
                    onChange={(e) =>
                      updateRow(index, {
                        key: e.target.value
                          .trim()
                          .toLowerCase()
                          .normalize("NFD")
                          .replace(/[\u0300-\u036f]/g, "")
                          .replace(/đ/g, "d")
                          .replace(/[^a-z0-9]+/g, "_")
                          .replace(/^_+|_+$/g, ""),
                      })
                    }
                    placeholder="Ví dụ: Syrup vải"
                  />
                </div>
              ) : null}

              <div className="nq-bom-card__field">
                <label className="nq-bom-card__label" htmlFor={`bom-qty-${index}`}>
                  Số lượng dùng ({unit})
                </label>
                <Input
                  id={`bom-qty-${index}`}
                  value={row.qty}
                  onChange={(e) => updateRow(index, { qty: e.target.value })}
                  inputMode="decimal"
                  placeholder={`Nhập số, đơn vị: ${unit}`}
                />
              </div>
            </li>
          );
        })}
      </ul>

      <Btn type="button" variant="ghost" block onClick={() => onChange([...rows, { key: "", qty: "" }])}>
        + Thêm dòng nguyên liệu
      </Btn>
    </div>
  );
}
