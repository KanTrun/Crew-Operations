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
      className="flex flex-col h-full bg-zinc-950 text-zinc-100"
      style={{ ["--accent" as any]: profile.accent }}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-zinc-800 bg-zinc-900/60 shrink-0">
        <div className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm border"
            style={{
              background: `color-mix(in srgb, ${profile.accent} 20%, transparent)`,
              borderColor: `color-mix(in srgb, ${profile.accent} 40%, transparent)`,
              color: profile.accent,
            }}
          >
            ✨
          </div>
          <div>
            <h3 className="text-sm font-semibold text-zinc-100">{profile.label}</h3>
            <p className="text-[11px] text-emerald-400 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>{" "}
              Trực tuyến · Điều hành 1-Click
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          {onClearHistory ? (
            <button
              onClick={onClearHistory ?? clearHistory}
              title="Xoá lịch sử hội thoại"
              className="p-1.5 rounded-lg text-zinc-400 hover:text-rose-400 hover:bg-zinc-800 transition text-xs"
            >
              🗑
            </button>
          ) : null}
          {onOpenFullPage ? (
            <button
              onClick={onOpenFullPage}
              title="Mở trang riêng AG-COPILOT"
              className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition text-xs"
            >
              ⤢
            </button>
          ) : null}
          {onClose ? (
            <button
              onClick={onClose}
              title="Đóng"
              className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition text-sm"
            >
              ✕
            </button>
          ) : null}
        </div>
      </div>

      {/* Empty role */}
      {profile.quickPrompts.length === 0 ? (
        <div className="flex-1 flex items-center justify-center p-8 text-center text-sm text-zinc-400">
          {profile.emptyMessage ?? profile.greeting}
        </div>
      ) : (
        <>
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex flex-col ${
                  msg.sender === "user" ? "items-end" : "items-start"
                }`}
              >
                <div
                  className={`max-w-[85%] p-3 rounded-2xl ${
                    msg.sender === "user"
                      ? "bg-amber-600 text-white rounded-br-none"
                      : "bg-zinc-900 border border-zinc-800 text-zinc-200 rounded-bl-none"
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
                <span className="text-[9px] text-zinc-500 mt-1 px-1">{msg.timestamp}</span>
              </div>
            ))}
            {loading && (
              <div className="flex items-center gap-2 text-zinc-400 text-xs italic bg-zinc-900/60 p-2 rounded-xl border border-zinc-800 w-fit">
                <span className="animate-spin" style={{ color: profile.accent }}>
                  ⏳
                </span>{" "}
                AG-COPILOT đang suy nghĩ…
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Prompts */}
          <div className="px-4 py-2 border-t border-zinc-900 bg-zinc-900/30 overflow-x-auto flex gap-1.5 shrink-0">
            {profile.quickPrompts.map((qp, idx) => (
              <button
                key={idx}
                onClick={() => send(qp)}
                disabled={loading || Boolean(streamingId)}
                className="whitespace-nowrap text-[11px] px-2.5 py-1 rounded-full bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-100 hover:border-zinc-600 transition disabled:opacity-50"
              >
                {qp}
              </button>
            ))}
          </div>

          {/* Input */}
          <div className="p-3 border-t border-zinc-800 bg-zinc-900/40 shrink-0">
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
                className="flex-1 px-3.5 py-2 text-xs bg-zinc-900 border border-zinc-700 rounded-xl text-zinc-100 placeholder-zinc-500 focus:outline-none disabled:opacity-50"
                style={{ borderColor: "var(--accent)" }}
              />
              <button
                type="submit"
                disabled={loading || Boolean(streamingId) || !input.trim()}
                className="px-3.5 py-2 rounded-xl font-semibold text-xs transition disabled:opacity-40 disabled:cursor-not-allowed text-zinc-950"
                style={{ backgroundColor: profile.accent }}
              >
                Gửi
              </button>
            </form>
            <p className="mt-1.5 text-[10px] text-zinc-500 text-center">
              Ctrl/Cmd+K mở·đóng · Esc thoát
            </p>
          </div>
        </>
      )}
    </div>
  );
}