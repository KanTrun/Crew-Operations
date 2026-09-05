// UI body chat (header + messages + quick prompts + input) dùng chung cho
// CopilotPane (floating) và trang /copilot (full-page).
//
// Props:
//  - chat: state từ useCopilotChat
//  - onClose?: callback cho header nút ✕ (pane)
//  - onOpenFullPage?: callback mở /copilot trong tab/cửa sổ mới (pane)
//  - showHeaderAccent: true = pane (có nút expand), false = page (chỉ header)

"use client";

import React, { useEffect, useRef } from "react";
import { Icon } from "../icons";
import { ActionProposalCard } from "./ActionProposalCard";
import { ChatText } from "./ChatText";
import type { ChatMessage, Mode } from "./useCopilotChat";

interface Props {
  chat: ReturnType<typeof import("./useCopilotChat").useCopilotChat>;
  mode: Mode;
  onClose?: () => void;
  onOpenFullPage?: () => void;
  onClearHistory?: () => void;
}

export function CopilotBody({ chat, mode, onClose, onOpenFullPage, onClearHistory }: Props) {
  const {
    profile,
    messages,
    input,
    setInput,
    loading,
    streamingId,
    send,
    updateProposal,
    clearHistory,
  } = chat;

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Focus input khi mở
  useEffect(() => {
    const t = window.setTimeout(() => inputRef.current?.focus(), 200);
    return () => window.clearTimeout(t);
  }, []);

  return (
    <div
      className="flex h-full flex-col bg-[var(--nq-bg)] text-[var(--nq-fg)]"
      style={{ ["--accent" as any]: profile.accent }}
    >
      {/* Header */}
      <div className="flex shrink-0 items-center justify-between border-b-2 border-[var(--nq-dim)] bg-[var(--nq-surface)] p-4">
        <div className="flex items-center gap-2.5">
          <div
            className="flex h-8 w-8 items-center justify-center border-2"
            style={{
              borderColor: "var(--nq-copper)",
              color: "var(--nq-copper)",
            }}
          >
            <Icon name="cam-nang" size={18} />
          </div>
          <div>
            <h3 className="text-sm font-bold uppercase text-[var(--nq-fg)]">🤖 {profile.label}</h3>
            <p className="flex items-center gap-1 text-[11px] text-[var(--nq-dim)]">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              Sẵn sàng hỗ trợ · AI trả lời kèm đề xuất, người duyệt mới áp dụng
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          {onClearHistory ? (
            <button
              onClick={onClearHistory ?? clearHistory}
              title="Xoá lịch sử hội thoại"
              className="border border-transparent px-2 py-1 text-[10px] font-bold uppercase text-[var(--nq-dim)] transition hover:border-[var(--nq-red)] hover:text-[var(--nq-red)]"
            >
              Xoá
            </button>
          ) : null}
          {onOpenFullPage ? (
            <button
              onClick={onOpenFullPage}
              title="Mở trợ lý ở trang riêng"
              className="border border-transparent px-2 py-1 text-[10px] font-bold uppercase text-[var(--nq-dim)] transition hover:border-[var(--nq-copper)] hover:text-[var(--nq-copper)]"
            >
              Mở rộng
            </button>
          ) : null}
          {onClose ? (
            <button
              onClick={onClose}
              title="Đóng"
              className="border border-transparent px-2 py-1 text-[10px] font-bold uppercase text-[var(--nq-dim)] transition hover:border-[var(--nq-copper)] hover:text-[var(--nq-fg)]"
            >
              Đóng
            </button>
          ) : null}
        </div>
      </div>

      {/* Empty role */}
      {profile.quickPrompts.length === 0 ? (
        <div className="flex flex-1 items-center justify-center p-8 text-center text-sm text-[var(--nq-dim)]">
          {profile.emptyMessage ?? profile.greeting}
        </div>
      ) : (
        <>
          {/* Messages */}
          <div className="flex-1 space-y-4 overflow-y-auto p-4 text-xs">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex flex-col ${
                  msg.sender === "user" ? "items-end" : "items-start"
                }`}
              >
                <div
                  className={`max-w-[88%] border p-3 ${
                    msg.sender === "user"
                      ? "border-[var(--nq-copper)] bg-[var(--nq-copper)] text-[#0e0c0a]"
                      : "border-[var(--nq-dim)] bg-[var(--nq-surface)] text-[var(--nq-fg)]"
                  }`}
                >
                  <p className="whitespace-pre-wrap leading-relaxed">
                    <ChatText text={msg.text} />
                    {streamingId === msg.id && (
                      <span className="ml-0.5 inline-block w-1.5 h-3 align-middle bg-amber-400 animate-pulse" />
                    )}
                  </p>

                  {msg.sender === "copilot" &&
                    msg.id === "welcome" &&
                    profile.capabilities.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-zinc-800/80">
                        <p className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1">
                          Em làm được gì cho anh/chị
                        </p>
                        <ul className="flex flex-wrap gap-1">
                          {profile.capabilities.map((cap, i) => (
                            <li
                              key={`cap-${i}`}
                              className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800/80 border border-emerald-500/20 text-emerald-300"
                            >
                              ✓ {cap}
                            </li>
                          ))}
                        </ul>
                        {profile.deniedNote ? (
                          <p className="text-[10px] text-zinc-500 mt-1.5 italic">
                            ⚠ {profile.deniedNote}
                          </p>
                        ) : null}
                      </div>
                    )}

                  {msg.sender === "copilot" &&
                    msg.citations &&
                    msg.citations.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-zinc-800/80">
                        <p className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1">
                          Nguồn tham chiếu
                        </p>
                        <ul className="flex flex-wrap gap-1">
                          {msg.citations.map((c, i) => (
                            <li
                              key={`${msg.id}-cit-${i}`}
                              className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800/80 border"
                              style={{
                                color: profile.accent,
                                borderColor: `color-mix(in srgb, ${profile.accent} 20%, transparent)`,
                              }}
                            >
                              📎 {c}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                  {msg.action_proposal && profile.allowActionApproval && (
                    <ActionProposalCard
                      proposal={msg.action_proposal}
                      onExecuted={(updated) => updateProposal(msg.id, updated)}
                    />
                  )}
                  {msg.action_proposal && !profile.allowActionApproval && (
                    <div className="mt-2 pt-2 border-t border-zinc-800/80 text-[11px] text-zinc-400 italic">
                      Đề xuất: {msg.action_proposal.intent} — nhờ quản lý duyệt trong
                      <a className="underline ml-1" href="/inbox">
                        Hộp thư
                      </a>
                      .
                    </div>
                  )}
                </div>
                <span className="mt-1 px-1 text-[9px] text-[var(--nq-dim)]">{msg.timestamp}</span>
              </div>
            ))}
            {loading && (
              <div className="flex w-fit items-center gap-2 border border-[var(--nq-dim)] bg-[var(--nq-surface)] p-2 text-xs italic text-[var(--nq-dim)]">
                <span className="h-2 w-2 animate-pulse rounded-full bg-[var(--nq-copper)]" />
                Đang xử lý yêu cầu…
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Prompts */}
          <div className="flex shrink-0 gap-1.5 overflow-x-auto border-t border-[var(--nq-dim)] bg-[var(--nq-surface)] px-4 py-2">
            {profile.quickPrompts.map((qp, idx) => (
              <button
                key={idx}
                onClick={() => send(qp)}
                disabled={loading || Boolean(streamingId)}
                className="whitespace-nowrap border border-[var(--nq-dim)] bg-[var(--nq-bg)] px-2.5 py-1 text-[11px] text-[var(--nq-dim)] transition hover:border-[var(--nq-copper)] hover:text-[var(--nq-fg)] disabled:opacity-50"
              >
                {qp}
              </button>
            ))}
          </div>

          {/* Input */}
          <div className="shrink-0 border-t-2 border-[var(--nq-dim)] bg-[var(--nq-surface)] p-3">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                send();
              }}
              className="flex items-center gap-2"
            >
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Nhập lệnh hoặc hỏi quy trình..."
                disabled={loading || Boolean(streamingId)}
                className="flex-1 border-2 bg-[var(--nq-bg)] px-3.5 py-2 text-xs text-[var(--nq-fg)] placeholder:text-[var(--nq-dim)] focus:outline-none disabled:opacity-50"
                style={{ borderColor: "var(--accent)" }}
              />
              <button
                type="submit"
                disabled={loading || Boolean(streamingId) || !input.trim()}
                className="border-2 border-[var(--nq-copper)] bg-[var(--nq-copper)] px-3.5 py-2 text-xs font-bold uppercase text-[#0e0c0a] transition disabled:cursor-not-allowed disabled:opacity-40"
              >
                Gửi
              </button>
            </form>
            <p className="mt-1.5 text-center text-[10px] text-[var(--nq-dim)]">
              Ctrl/Cmd+K mở hoặc đóng · Esc thu nhỏ
            </p>
          </div>
        </>
      )}
    </div>
  );
}