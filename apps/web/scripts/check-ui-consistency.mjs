#!/usr/bin/env node
/**
 * check-ui-consistency.mjs — chặn lệch chuẩn kit/motion trên src/app.
 * Chạy: node scripts/check-ui-consistency.mjs
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "src", "app");
const ALLOW = new Set([
  // Kit và shell được phép định nghĩa chuyển động
]);

const rules = [
  {
    id: "inline-transition",
    re: /transition=\{\{/,
    msg: "Dùng presets từ ui/motion/presets.ts thay vì transition={{...}} rời",
  },
  {
    id: "z-arbitrary",
    re: /\bz-\[(\d+)\]/,
    msg: "Dùng token --nq-z-* thay vì z-[n]",
  },
  {
    id: "json-stringify-jsx",
    re: /\{JSON\.stringify\(/,
    msg: "Không JSON.stringify trong JSX — dùng DataList / formatFieldValue",
    // Chỉ báo khi nằm gần return/JSX (heuristic: dòng có JSX braces + stringify)
  },
];

/** Bỏ qua haystack / log nội bộ không render UI */
const IGNORE_LINE = /rowHaystack|console\.|\/\/|join\(/;

/** @type {{file:string,line:number,id:string,msg:string,sample:string}[]} */
const hits = [];

function walk(dir) {
  for (const name of fs.readdirSync(dir)) {
    const p = path.join(dir, name);
    const st = fs.statSync(p);
    if (st.isDirectory()) walk(p);
    else if (/\.(tsx|ts|jsx|js)$/.test(name)) scan(p);
  }
}

function scan(file) {
  const rel = path.relative(root, file).replace(/\\/g, "/");
  if (ALLOW.has(rel)) return;
  const text = fs.readFileSync(file, "utf8");
  const lines = text.split(/\r?\n/);
  lines.forEach((line, i) => {
    if (IGNORE_LINE.test(line)) return;
    for (const rule of rules) {
      if (rule.re.test(line)) {
        hits.push({
          file: rel,
          line: i + 1,
          id: rule.id,
          msg: rule.msg,
          sample: line.trim().slice(0, 120),
        });
      }
    }
  });
}

walk(root);

if (hits.length === 0) {
  console.log("check-ui-consistency: OK");
  process.exit(0);
}

console.error(`check-ui-consistency: ${hits.length} vấn đề\n`);
for (const h of hits) {
  console.error(`[${h.id}] ${h.file}:${h.line}`);
  console.error(`  ${h.msg}`);
  console.error(`  ${h.sample}\n`);
}
process.exit(1);
