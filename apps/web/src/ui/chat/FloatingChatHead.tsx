"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React, { useEffect, useState } from "react";
import { useChatClient } from "../../lib/useChatClient";
import { getNvId, getToken } from "../../lib/session";

export function FloatingChatHead() {
  const pathname = usePathname();
  const token = getToken();
  const currentNvId = getNvId();
  const [isOpen, setIsOpen] = useState(false);
  const [selectedConvId, setSelectedConvId] = useState<string>("");
  const [notification, setNotification] = useState<string | null>(null);
  const notificationTimerRef = React.useRef<number | null>(null);

  const {
    conversations,
    messages,
    unreadTotal,
    sendMessage,
  } = useChatClient(selectedConvId);

  const [input, setInput] = useState("");

  useEffect(() => {
    function onNotification(event: Event) {
      const message = (event as CustomEvent<{ sender_name?: string; content?: string }>).detail;
      setNotification(`${message.sender_name || "Tin nhắn mới"}: ${message.content || ""}`);
      if (notificationTimerRef.current !== null) window.clearTimeout(notificationTimerRef.current);
      notificationTimerRef.current = window.setTimeout(() => setNotification(null), 5000);
    }
    window.addEventListener("nq:chat-notification", onNotification);
    return () => {
      window.removeEventListener("nq:chat-notification", onNotification);
      if (notificationTimerRef.current !== null) window.clearTimeout(notificationTimerRef.current);
    };
  }, []);

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
      {notification ? (
        <div role="status" className="mb-2 max-w-[min(360px,calc(100vw-2rem))] rounded-lg border border-[var(--nq-copper)] bg-[var(--nq-bg-elevated)] px-3 py-2 text-xs text-[var(--nq-fg)] shadow-xl">
          {notification}
        </div>
      ) : null}
      {/* Cửa sổ Chat Head Popup */}
      {isOpen && (
        <div className="mb-3 flex h-[min(500px,calc(100vh-7rem))] w-[calc(100vw-2rem)] max-w-[380px] flex-col overflow-hidden rounded-2xl border border-[var(--nq-dim)] bg-[var(--nq-bg-elevated)] shadow-2xl animate-fade-in">
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
          <div className="flex-1 space-y-2 overflow-y-auto bg-[var(--nq-bg)] p-3 text-xs">
            {messages.slice(-20).map((msg) => {
              const isSystem = msg.sender_id === "system";
              const isMine = msg.sender_id === currentNvId;
              if (isSystem) {
                return (
                  <div key={msg.id} className="text-center text-[10px] text-[var(--nq-muted)] italic my-1">
                    {msg.content}
                  </div>
                );
              }
              return (
                <div key={msg.id} className={`flex ${isMine ? "justify-end" : "justify-start"}`}>
                  <div className={`w-fit max-w-[82%] rounded-xl border p-2 ${isMine ? "border-[var(--nq-copper)] bg-[var(--nq-copper)] text-[#0e0c0a]" : "border-[var(--nq-dim)] bg-[var(--nq-card)] text-[var(--nq-fg)]"}`}>
                    <div className={`mb-0.5 flex gap-3 text-[10px] ${isMine ? "justify-end text-[#0e0c0a]/70" : "justify-between text-[var(--nq-muted)]"}`}>
                      {!isMine ? <span className="font-bold text-[var(--nq-copper)]">{msg.sender_name || msg.sender_id}</span> : null}
                      <span>{new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                    </div>
                    <p className="break-words text-[11px] leading-relaxed">{msg.content}</p>
                  </div>
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
