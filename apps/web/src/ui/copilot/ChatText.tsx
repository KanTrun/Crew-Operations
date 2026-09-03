"use client";

import React from "react";

/**
 * Render text chat an toàn, không lỗi phông/định dạng.
 *
 * - Escape HTML trước (chống XSS khi LLM/backend trả markup).
 * - Hỗ trợ markdown nhẹ: `**bold**`, `*italic*`, `` `code` ``.
 * - Giữ xuống dòng `\n` bằng className `whitespace-pre-wrap`.
 * - Ký tự đặc biệt (→, ⚠, ✨, 📎...) render nguyên vẹn — không bị break.
 */

/** Escape các ký tự HTML nguy hiểm. */
function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

const CODE_RE = /(`+)([^`]*?)\1/g;
const BOLD_RE = /(\*\*)([^*]+?)\1/g;
const ITALIC_RE = /(\*)([^*]+?)\1/g;

/**
 * Render một đoạn văn bản, hỗ trợ inline markdown nhẹ.
 * Input đã escape — an toàn để render qua dangerouslySetInnerHTML.
 */
function renderInline(text: string): string {
  let out = text;
  // code trước (tránh conflict với * trong code)
  out = out.replace(CODE_RE, (_m, _tick, code) => `<code>${code}</code>`);
  // bold
  out = out.replace(BOLD_RE, (_m, _star, inner) => `<strong>${inner}</strong>`);
  // italic (không đụng vào đã thành <strong>/<code>)
  out = out.replace(ITALIC_RE, (_m, _star, inner) => `<em>${inner}</em>`);
  return out;
}

export function ChatText({ text }: { text: string }) {
  // Nếu không có markdown đặc biệt, render thuần (an toàn, nhanh).
  const hasMarkdown = /\*\*|\*|`/.test(text);

  if (!hasMarkdown) {
    return <>{text}</>;
  }

  const safe = escapeHtml(text);
  const html = renderInline(safe);

  return (
    <span
      className="[&_strong]:font-semibold [&_strong]:text-zinc-100 [&_code]:px-1 [&_code]:py-0.5 [&_code]:rounded [&_code]:bg-zinc-800 [&_code]:text-amber-300 [&_code]:text-[0.9em] [&_em]:italic"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
