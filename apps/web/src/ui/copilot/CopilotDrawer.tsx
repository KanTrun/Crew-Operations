"use client";

import React, { useState, useRef, useEffect } from "react";
import { getToken, getName, getRole } from "../../lib/session";
import { ActionProposalCard, ActionProposalData } from "./ActionProposalCard";
import { motion, AnimatePresence } from "framer-motion";

interface ChatMessage {
  id: string;
  sender: "user" | "copilot";
  text: string;
  action_proposal?: ActionProposalData | null;
  timestamp: string;
}

const QUICK_PROMPTS = [
  "Xếp lịch tuần sau, ưu tiên Lan ca sáng",
  "Tóm tắt bản tin sáng hôm nay",
  "Kiểm tra tồn kho và cảnh báo hết hàng",
  "Quy trình mở quán gồm các bước nào?",
  "Báo cáo hao hụt sữa hôm nay",
];

export function CopilotDrawer() {
  const [isOpen, setIsOpen] = useState(false);
  const [inputMessage, setInputMessage] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      sender: "copilot",
      text: "Xin chào! Em là AG-COPILOT — Trợ lý điều hành ảo của quán. Anh/chị cần em hỗ trợ xếp lịch, duyệt ca hay kiểm tra vận hành gì ạ?",
      timestamp: "Bây giờ",
    },
  ]);
  const [loading, setLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isOpen]);

  async function handleSendMessage(textToSend?: string) {
    const text = (textToSend || inputMessage).trim();
    if (!text || loading) return;

    const userMsg: ChatMessage = {
      id: `user_${Date.now()}`,
      sender: "user",
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInputMessage("");
    setLoading(true);

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

      const copilotMsg: ChatMessage = {
        id: `copilot_${Date.now()}`,
        sender: "copilot",
        text: data.reply_text || "Dạ em đã xử lý xong yêu cầu của anh/chị.",
        action_proposal: data.action_proposal,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, copilotMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `err_${Date.now()}`,
        sender: "copilot",
        text: `⚠️ Lỗi: ${err.message || "Không thể xử lý yêu cầu."}`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMsg]);
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
        onClick={() => setIsOpen(!isOpen)}
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
              onClick={() => setIsOpen(false)}
              className="absolute inset-0 bg-black/40 backdrop-blur-sm pointer-events-auto"
            />

            {/* Chat Drawer */}
            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 250 }}
              className="relative w-full max-w-md bg-zinc-950 border-l border-zinc-800 shadow-2xl flex flex-col h-full pointer-events-auto"
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
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Trực tuyến · Điều hành 1-Click
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-1 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition text-sm"
                >
                  ✕
                </button>
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
                      <p className="whitespace-pre-wrap leading-relaxed">{msg.text}</p>
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
                    disabled={loading}
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
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    placeholder="Nhập lệnh hoặc hỏi quy trình..."
                    disabled={loading}
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
                    disabled={loading || !inputMessage.trim()}
                    className="px-3.5 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-zinc-950 font-semibold text-xs transition disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    Gửi
                  </button>
                </form>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
}
