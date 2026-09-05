"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React, { useState } from "react";
import { useChatClient } from "../../lib/useChatClient";
import { getToken } from "../../lib/session";

export function FloatingChatHead() {
  const pathname = usePathname();
  const token = getToken();
  const [isOpen, setIsOpen] = useState(false);
  const [selectedConvId, setSelectedConvId] = useState<string>("");

  const {
    conversations,
    messages,
    unreadTotal,
    sendMessage,
  } = useChatClient(selectedConvId);

  const [input, setInput] = useState("");

  // Không hiển thị widget nếu chưa đăng nhập hoặc đang ở chính trang /chat
  if (!token || pathname === "/chat" || pathname === "/login") {
    return null;
  }

  const activeConv = conversations.find((c) => c.id === selectedConvId) || conversations[0];

  const handleQuickSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !activeConv) return;
    sendMessage(activeConv.id, input.trim());
    setInput("");
  };

  return (
    <div className="fixed bottom-20 md:bottom-6 right-4 md:right-6 z-40 flex flex-col items-end">
      {/* Cửa sổ Chat Head Popup */}
      {isOpen && (
        <div className="mb-3 w-[360px] sm:w-[380px] h-[500px] bg-[var(--nq-card)] border border-[var(--nq-dim)] rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-fade-in">
          {/* Header */}
          <div className="p-3 bg-[var(--nq-copper)] text-white flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-base">💬</span>
              <div>
                <h4 className="font-bold text-xs truncate max-w-[200px]">{activeConv ? activeConv.display_name : "Chat Nội Bộ"}</h4>
                <p className="text-[10px] opacity-80">NHỊP QUÁN Messenger</p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <Link
                href="/chat"
                onClick={() => setIsOpen(false)}
                className="p-1 rounded hover:bg-white/20 text-xs text-white"
                title="Mở toàn màn hình"
              >
                ⤢
              </Link>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="p-1 rounded hover:bg-white/20 text-xs text-white"
                title="Thu nhỏ"
              >
                ✕
              </button>
            </div>
          </div>

          {/* Chọn nhanh hội thoại */}
          <div className="flex gap-1.5 p-2 bg-[var(--nq-bg)] border-b border-[var(--nq-dim)] overflow-x-auto">
            {conversations.slice(0, 5).map((conv) => (
              <button
                key={conv.id}
                type="button"
                onClick={() => setSelectedConvId(conv.id)}
                className={`px-2 py-1 rounded-lg text-[10px] font-bold truncate max-w-[100px] transition ${
                  (activeConv && activeConv.id === conv.id)
                    ? "bg-[var(--nq-copper)] text-white"
                    : "bg-[var(--nq-card)] text-[var(--nq-muted)] hover:text-[var(--nq-fg)]"
                }`}
              >
                {conv.type === "general" ? "☕ Chung" : conv.display_name}
              </button>
            ))}
          </div>

          {/* Vùng tin nhắn thu nhỏ */}
          <div className="flex-1 p-3 overflow-y-auto space-y-2 bg-[var(--nq-bg)]/50 text-xs">
            {messages.slice(-20).map((msg) => {
              const isSystem = msg.sender_id === "system";
              if (isSystem) {
                return (
                  <div key={msg.id} className="text-center text-[10px] text-[var(--nq-muted)] italic my-1">
                    {msg.content}
                  </div>
                );
              }
              return (
                <div key={msg.id} className="p-2 rounded-xl bg-[var(--nq-card)] border border-[var(--nq-dim)]">
                  <div className="flex justify-between text-[10px] text-[var(--nq-muted)] mb-0.5">
                    <span className="font-bold text-[var(--nq-copper)]">{msg.sender_name || msg.sender_id}</span>
                    <span>{new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                  </div>
                  <p className="text-[11px] text-[var(--nq-fg)] break-words">{msg.content}</p>
                </div>
              );
            })}
          </div>

          {/* Ô nhập tin nhắn */}
          <form onSubmit={handleQuickSend} className="p-2 border-t border-[var(--nq-dim)] bg-[var(--nq-card)] flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Nhắn nhanh…"
              className="flex-1 px-3 py-1.5 rounded-xl bg-[var(--nq-bg)] border border-[var(--nq-dim)] text-xs text-[var(--nq-fg)] outline-none focus:border-[var(--nq-copper)]"
            />
            <button
              type="submit"
              disabled={!input.trim()}
              className="px-3 py-1.5 rounded-xl bg-[var(--nq-copper)] text-white font-bold text-xs hover:opacity-90 disabled:opacity-40 transition"
            >
              ➤
            </button>
          </form>
        </div>
      )}

      {/* Nút Chat Head Tròn Nổi */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-13 h-13 rounded-full bg-[var(--nq-copper)] text-white shadow-xl hover:scale-105 active:scale-95 transition-all flex items-center justify-center relative p-3.5 border-2 border-white/20"
        title="Chat nội bộ nhân viên"
      >
        <svg className="w-6 h-6 fill-current" viewBox="0 0 24 24">
          <path d="M12 2C6.477 2 2 6.145 2 11.258c0 2.909 1.455 5.512 3.736 7.172v3.57c0 .545.6.89 1.05.584l3.96-2.64c.405.07.82.114 1.254.114 5.523 0 10-4.145 10-9.258C22 6.145 17.523 2 12 2zm1 13h-2v-2h2v2zm0-4h-2V7h2v4z" />
        </svg>
        {unreadTotal > 0 && (
          <span className="absolute -top-1 -right-1 min-w-5 h-5 px-1 rounded-full bg-red-500 text-white text-[10px] font-extrabold flex items-center justify-center shadow">
            {unreadTotal > 9 ? "9+" : unreadTotal}
          </span>
        )}
      </button>
    </div>
  );
}
