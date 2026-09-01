// Logic chat chung cho cả Drawer (pane) và /copilot page.
// Tách ra để 2 nơi cùng dùng: role-aware, streaming, history, action proposal.

import { useCallback, useEffect, useRef, useState } from "react";
import { getRole, getToken } from "../../lib/session";
import { getCopilotProfile } from "./profile";
import type { ActionProposalData } from "./ActionProposalCard";

export interface ChatMessage {
  id: string;
  sender: "user" | "copilot";
  text: string;
  action_proposal?: ActionProposalData | null;
  citations?: string[] | null;
  timestamp: string;
}

export type Mode = "pane" | "page";

const STORAGE_KEY = "ag_copilot_history_v1";
const MAX_HISTORY = 200;
const TYPING_CHARS_PER_TICK = 2;
const TYPING_TICK_MS = 30;
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function loadHistory(): ChatMessage[] | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ChatMessage[];
    return Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function saveHistory(messages: ChatMessage[]) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify(messages.slice(-MAX_HISTORY))
    );
  } catch {
    /* quota / blocked — bỏ qua */
  }
}

export function useCopilotChat(mode: Mode = "pane") {
  const profile = getCopilotProfile(getRole() as any);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      sender: "copilot",
      text: profile.greeting,
      timestamp: "Bây giờ",
    },
  ]);
  const [hydrated, setHydrated] = useState(false);
  const [loading, setLoading] = useState(false);
  const [streamingId, setStreamingId] = useState<string | null>(null);
  const typingTimers = useRef<Record<string, number>>({});
  const messagesRef = useRef<ChatMessage[]>(messages);

  // Cập nhật ref mỗi render để handleSendMessage có state mới nhất
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  // Khi đổi role (logout/login), reset messages + greeting mới
  useEffect(() => {
    if (!hydrated) return;
    setMessages([
      {
        id: "welcome",
        sender: "copilot",
        text: profile.greeting,
        timestamp: "Bây giờ",
      },
    ]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile.role]);

  // Khôi phục lịch sử
  useEffect(() => {
    const saved = loadHistory();
    if (saved && saved.length > 0) setMessages(saved);
    setHydrated(true);
  }, []);

  // Lưu lịch sử
  useEffect(() => {
    if (!hydrated) return;
    saveHistory(messages);
  }, [messages, hydrated]);

  // Cleanup timers khi unmount
  useEffect(() => {
    const timers = typingTimers.current;
    return () => {
      Object.values(timers).forEach((t) => window.clearTimeout(t));
      Object.keys(timers).forEach((k) => delete timers[k]);
    };
  }, []);

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

  const send = useCallback(
    async (textToSend?: string) => {
      const text = (textToSend ?? input).trim();
      if (!text || loading || streamingId) return;

      const now = new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
      const userMsg: ChatMessage = {
        id: `user_${Date.now()}`,
        sender: "user",
        text,
        timestamp: now,
      };

      setMessages((prev) => [...prev, userMsg]);
      if (!textToSend) setInput("");
      setLoading(true);

      const copilotId = `copilot_${Date.now()}`;
      setMessages((prev) => [
        ...prev,
        { id: copilotId, sender: "copilot", text: "", timestamp: now },
      ]);

      try {
        const token = getToken();
        const recent = messagesRef.current.slice(-3).map((m) => m.text);
        const res = await fetch(`${API_BASE}/api/v1/copilot/message`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            message: text,
            channel: mode === "page" ? "web-page" : "web",
            recent_messages: recent,
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

        setMessages((prev) =>
          prev.map((m) =>
            m.id === copilotId
              ? {
                  ...m,
                  action_proposal: data.action_proposal ?? null,
                  citations,
                }
              : m
          )
        );

        startTyping(copilotId, replyText);
      } catch (err: any) {
        const errText = `⚠️ Lỗi: ${err.message || "Không thể xử lý yêu cầu."}`;
        setMessages((prev) =>
          prev.map((m) => (m.id === copilotId ? { ...m, text: errText } : m))
        );
      } finally {
        setLoading(false);
      }
    },
    [input, loading, streamingId, mode, startTyping]
  );

  const clearHistory = useCallback(() => {
    if (typeof window === "undefined") return;
    const ok = window.confirm("Xoá toàn bộ lịch sử hội thoại với AG-COPILOT?");
    if (!ok) return;
    setMessages([
      {
        id: "welcome",
        sender: "copilot",
        text: profile.greeting,
        timestamp: "Bây giờ",
      },
    ]);
  }, [profile.greeting]);

  const updateProposal = useCallback(
    (msgId: string, updated: ActionProposalData) => {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === msgId ? { ...m, action_proposal: updated } : m
        )
      );
    },
    []
  );

  return {
    profile,
    messages,
    setMessages,
    input,
    setInput,
    loading,
    streamingId,
    send,
    clearHistory,
    updateProposal,
  };
}