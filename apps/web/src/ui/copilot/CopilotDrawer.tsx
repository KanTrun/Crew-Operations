"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { getToken } from "../../lib/session";
import { ActionProposalCard, ActionProposalData } from "./ActionProposalCard";
import { motion, AnimatePresence } from "framer-motion";

interface ChatMessage {
  id: string;
  sender: "user" | "copilot";
  text: string;
  action_proposal?: ActionProposalData | null;
  citations?: string[] | null;
  timestamp: string;
}

const QUICK_PROMPTS = [
  "Xếp lịch tuần sau, ưu tiên Lan ca sáng",
  "Tóm tắt bản tin sáng hôm nay",
  "Kiểm tra tồn kho và cảnh báo hết hàng",
  "Quy trình mở quán gồm các bước nào?",
  "Báo cáo hao hụt sữa hôm nay",
];

const STORAGE_KEY = "ag_copilot_history_v1";
const MAX_HISTORY = 200;
const TYPING_CHARS_PER_TICK = 2; // số ký tự / 30ms — mô phỏng streaming
const TYPING_TICK_MS = 30;

function loadHistory(): ChatMessage[] | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ChatMessage[];
    if (!Array.isArray(parsed)) return null;
    return parsed;
  } catch {
    return null;
  }
}

function saveHistory(messages: ChatMessage[]) {
  if (typeof window === "undefined") return;
  try {
    const trimmed = messages.slice(-MAX_HISTORY);
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
  } catch {
    // hết quota hoặc bị chặn — bỏ qua, không vỡ UI
  }
}

const WELCOME_MSG: ChatMessage = {
  id: "welcome",
  sender: "copilot",
  text: "Xin chào! Em là AG-COPILOT — Trợ lý điều hành ảo của quán. Anh/chị cần em hỗ trợ xếp lịch, duyệt ca hay kiểm tra vận hành gì ạ? (Bấm Ctrl+K để mở/đóng, Esc để thoát)",
  timestamp: "Bây giờ",
};

interface CopilotDrawerProps {
  /** Controlled mode — nếu truyền, drawer dùng giá trị này thay vì tự quản lý. */
  open?: boolean;
  /** Controlled mode — callback khi đóng (backdrop / Esc / nút ✕). */
  onClose?: () => void;
}

export function CopilotDrawer({ open, onClose }: CopilotDrawerProps = {}) {
  const isControlled = open !== undefined;
  const [internalOpen, setInternalOpen] = useState(false);
  const isOpen = isControlled ? Boolean(open) : internalOpen;

  const setOpen = useCallback(
    (v: boolean | ((prev: boolean) => boolean)) => {
      if (isControlled) {
        // Trong controlled mode, chỉ phản hồi "đóng" lên parent.
        if (!v) onClose?.();
        return;
      }
      setInternalOpen((prev) => (typeof v === "function" ? v(prev) : v));
    },
    [isControlled, onClose]
  );

  const [inputMessage, setInputMessage] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MSG]);
  const [hydrated, setHydrated] = useState(false);
  const [loading, setLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [streamingId, setStreamingId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const typingTimers = useRef<Record<string, number>>({});

  // Khôi phục lịch sử từ localStorage khi mount
  useEffect(() => {
    const saved = loadHistory();
    if (saved && saved.length > 0) {
      setMessages(saved);
    }
    setHydrated(true);
  }, []);

  // Lưu lịch sử mỗi khi messages thay đổi (sau khi đã hydrate)
  useEffect(() => {
    if (!hydrated) return;
    saveHistory(messages);
  }, [messages, hydrated]);

  // Auto-scroll khi mở hoặc có tin nhắn mới
  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isOpen]);

  // Phím tắt: Ctrl/Cmd+K mở/đóng, Esc đóng
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const isToggle = (e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k";
      if (isToggle) {
        e.preventDefault();
        // Controlled: chỉ cho phép mở (parent quyết đóng)
        if (isControlled) {
          if (!isOpen) onClose?.();
          return;
        }
        setOpen((v) => !v);
        return;
      }
      if (e.key === "Escape" && isOpen) {
        setOpen(false);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen, isControlled, onClose, setOpen]);

  // Focus input khi mở drawer
  useEffect(() => {
    if (isOpen) {
      const t = window.setTimeout(() => inputRef.current?.focus(), 250);
      return () => window.clearTimeout(t);
    }
  }, [isOpen]);

  const clearHistory = useCallback(() => {
    if (typeof window === "undefined") return;
    const ok = window.confirm("Xoá toàn bộ lịch sử hội thoại với AG-COPILOT?");
    if (!ok) return;
    setMessages([WELCOME_MSG]);
  }, []);

  // Streaming "typing" cho 1 message: tách text theo ký tự rồi nạp dần
  const startTyping = useCallback((msgId: string, fullText: string) => {
    setStreamingId(msgId);
    const chars = Array.from(fullText);
    let i = 0;
    const tick = () => {
      i = Math.min(chars.length, i + TYPING_CHARS_PER_TICK);
      const partial = chars.slice(0, i).join("");
      setMessages((prev) =>
        prev.map((m) => (m.id === msgId ? { ...m, text: partial } : m))
      );
      if (i < chars.length) {
        typingTimers.current[msgId] = window.setTimeout(tick, TYPING_TICK_MS);
      } else {
        setStreamingId((cur) => (cur === msgId ? null : cur));
        delete typingTimers.current[msgId];
      }
    };
    typingTimers.current[msgId] = window.setTimeout(tick, TYPING_TICK_MS);
  }, []);

  useEffect(() => {
    return () => {
      // cleanup timers khi unmount
      Object.values(typingTimers.current).forEach((t) => window.clearTimeout(t));
      typingTimers.current = {};
    };
  }, []);

  async function handleSendMessage(textToSend?: string) {
    const text = (textToSend || inputMessage).trim();
    if (!text || loading || streamingId) return;

    const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const userMsg: ChatMessage = {
      id: `user_${Date.now()}`,
      sender: "user",
      text,
      timestamp: now,
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInputMessage("");
    setLoading(true);

    // Tạo placeholder message cho copilot (text="") để typing effect có chỗ ghi vào
    const copilotId = `copilot_${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      { id: copilotId, sender: "copilot", text: "", timestamp: now },
    ]);

    try {
      const token = getToken();
      const res = await fetch("http://localhost:8000/api/v1/copilot/message", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: text,
          channel: "web",
          recent_messages: messages.slice(-3).map((m) => m.text),
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Không thể kết nối với AG-COPILOT");
      }

      const replyText: string =
        data.reply_text || "Dạ em đã xử lý xong yêu cầu của anh/chị.";
      const citations: string[] | null = Array.isArray(data.citations)
        ? data.citations
        : null;

      // Cập nhật action_proposal + citations cho message placeholder
      setMessages((prev) =>
        prev.map((m) =>
          m.id === copilotId
            ? { ...m, action_proposal: data.action_proposal ?? null, citations }
            : m
        )
      );

      // Bắt đầu typing
      startTyping(copilotId, replyText);
    } catch (err: any) {
      const errText = `⚠️ Lỗi: ${err.message || "Không thể xử lý yêu cầu."}`;
      // Nếu lỗi thì ghi thẳng, không cần typing
      setMessages((prev) =>
        prev.map((m) =>
          m.id === copilotId ? { ...m, text: errText } : m
        )
      );
    } finally {
      setLoading(false);
    }
  }

  function handleVoiceInput() {
    const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRec) {
      alert("Trình duyệt không hỗ trợ nhận diện giọng nói (Web Speech API).");
      return;
    }

    if (isListening) {
      setIsListening(false);
      return;
    }

    try {
      const recognition = new SpeechRec();
      recognition.lang = "vi-VN";
      recognition.continuous = false;
      recognition.interimResults = false;

      recognition.onstart = () => setIsListening(true);
      recognition.onend = () => setIsListening(false);
      recognition.onerror = () => setIsListening(false);

      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        if (transcript) {
          setInputMessage(transcript);
        }
      };

      recognition.start();
    } catch (e) {
      setIsListening(false);
    }
  }

  return (
    <>
      {/* Floating Trigger Button */}
      <button
        onClick={() => setOpen(!isOpen)}
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2 px-4 py-2.5 rounded-full bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-zinc-950 font-bold shadow-lg shadow-amber-500/20 transition transform hover:scale-105 active:scale-95"
        title="Mở Trợ lý AG-COPILOT"
      >
        <span className="text-lg">✨</span>
        <span className="text-sm font-semibold tracking-wide">AG-COPILOT</span>
      </button>

      {/* Drawer Overlay & Panel */}
      <AnimatePresence>
        {isOpen && (
          <div className="fixed inset-0 z-50 flex justify-end pointer-events-none">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setOpen(false)}
              className="absolute inset-0 bg-black/40 backdrop-blur-sm pointer-events-auto"
            />

            {/* Chat Drawer */}
            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 250 }}
              className="relative w-full md:max-w-md bg-zinc-950 md:border-l border-zinc-800 shadow-2xl flex flex-col h-full pointer-events-auto"
            >
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-zinc-800 bg-zinc-900/60">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-full bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400 font-bold text-sm">
                    ✨
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-zinc-100">AG-COPILOT</h3>
                    <p className="text-[11px] text-emerald-400 flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>{" "}
                      Trực tuyến · Điều hành 1-Click
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={clearHistory}
                    title="Xoá lịch sử hội thoại"
                    className="p-1.5 rounded-lg text-zinc-400 hover:text-rose-400 hover:bg-zinc-800 transition text-xs"
                  >
                    🗑
                  </button>
                  <button
                    onClick={() => setOpen(false)}
                    title="Đóng (Esc)"
                    className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition text-sm"
                  >
                    ✕
                  </button>
                </div>
              </div>

              {/* Messages Body */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex flex-col ${msg.sender === "user" ? "items-end" : "items-start"}`}
                  >
                    <div
                      className={`max-w-[85%] p-3 rounded-2xl ${
                        msg.sender === "user"
                          ? "bg-amber-600 text-white rounded-br-none"
                          : "bg-zinc-900 border border-zinc-800 text-zinc-200 rounded-bl-none"
                      }`}
                    >
                      <p className="whitespace-pre-wrap leading-relaxed">
                        {msg.text}
                        {streamingId === msg.id && (
                          <span className="ml-0.5 inline-block w-1.5 h-3 align-middle bg-amber-400 animate-pulse" />
                        )}
                      </p>

                      {/* Citation/nguồn trích dẫn — slot sẵn, render nếu có */}
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
                                  className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800/80 text-amber-300 border border-amber-500/20"
                                >
                                  📎 {c}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                      {msg.action_proposal && (
                        <ActionProposalCard
                          proposal={msg.action_proposal}
                          onExecuted={(updated) => {
                            setMessages((prev) =>
                              prev.map((m) =>
                                m.id === msg.id ? { ...m, action_proposal: updated } : m
                              )
                            );
                          }}
                        />
                      )}
                    </div>
                    <span className="text-[9px] text-zinc-500 mt-1 px-1">{msg.timestamp}</span>
                  </div>
                ))}
                {loading && (
                  <div className="flex items-center gap-2 text-zinc-400 text-xs italic bg-zinc-900/60 p-2 rounded-xl border border-zinc-800 w-fit">
                    <span className="animate-spin text-amber-400">⏳</span> AG-COPILOT đang suy nghĩ và kiểm tra solver...
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Quick Prompts */}
              <div className="px-4 py-2 border-t border-zinc-900 bg-zinc-900/30 overflow-x-auto flex gap-1.5 no-scrollbar">
                {QUICK_PROMPTS.map((qp, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(qp)}
                    disabled={loading || Boolean(streamingId)}
                    className="whitespace-nowrap text-[11px] px-2.5 py-1 rounded-full bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-amber-300 hover:border-amber-500/40 transition disabled:opacity-50"
                  >
                    {qp}
                  </button>
                ))}
              </div>

              {/* Input Footer */}
              <div className="p-3 border-t border-zinc-800 bg-zinc-900/40">
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    handleSendMessage();
                  }}
                  className="flex items-center gap-2"
                >
                  <input
                    ref={inputRef}
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    placeholder="Nhập lệnh hoặc hỏi quy trình..."
                    disabled={loading || Boolean(streamingId)}
                    className="flex-1 px-3.5 py-2 text-xs bg-zinc-900 border border-zinc-700 rounded-xl text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-amber-500 disabled:opacity-50"
                  />
                  <button
                    type="button"
                    onClick={handleVoiceInput}
                    title="Nhập bằng giọng nói"
                    className={`p-2 rounded-xl border transition ${
                      isListening
                        ? "bg-rose-500 text-white border-rose-400 animate-pulse"
                        : "bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border-zinc-700"
                    }`}
                  >
                    🎙️
                  </button>
                  <button
                    type="submit"
                    disabled={loading || Boolean(streamingId) || !inputMessage.trim()}
                    className="px-3.5 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-zinc-950 font-semibold text-xs transition disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    Gửi
                  </button>
                </form>
                <p className="mt-1.5 text-[10px] text-zinc-500 text-center">
                  Ctrl/Cmd+K mở·đóng · Esc thoát
                </p>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
}
