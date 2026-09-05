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
  agent_mode?: string | null;
  timestamp: string;
}

export type Mode = "pane" | "page";

const STORAGE_KEY = "ag_copilot_history_v1";
const MAX_HISTORY = 200;
const TYPING_CHARS_PER_TICK = 2;
const TYPING_TICK_MS = 30;
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Tách key theo mode để pane và /copilot page không ghi đè lịch sử nhau.
function storageKey(mode: Mode): string {
  return `${STORAGE_KEY}_${mode}`;
}

function loadHistory(mode: Mode): ChatMessage[] | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(storageKey(mode));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ChatMessage[];
    return Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function saveHistory(messages: ChatMessage[], mode: Mode) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      storageKey(mode),
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
    const saved = loadHistory(mode);
    if (saved && saved.length > 0) setMessages(saved);
    setHydrated(true);
  }, [mode]);

  // Lưu lịch sử
  useEffect(() => {
    if (!hydrated) return;
    saveHistory(messages, mode);
  }, [messages, hydrated, mode]);

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
        const payload = JSON.stringify({
          message: text,
          channel: mode === "page" ? "web-page" : "web",
          recent_messages: recent,
        });

        // Ưu tiên SSE streaming; nếu thất bại fallback về POST /message (JSON).
        const streamed = await streamCopilot(payload, token, (delta) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === copilotId
                ? { ...m, text: (m.text || "") + delta }
                : m
            )
          );
        });

        if (streamed.ok) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === copilotId
                ? {
                    ...m,
                    action_proposal: streamed.action_proposal ?? null,
                    citations: streamed.citations,
                    agent_mode: streamed.agent_mode ?? null,
                  }
                : m
            )
          );
          return;
        }

        // Fallback: POST /message (không stream).
        const res = await fetch(`${API_BASE}/api/v1/copilot/message`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: payload,
        });

        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || "Không thể kết nối với trợ lý vận hành");
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
                  agent_mode: data.agent_mode ?? null,
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
    const ok = window.confirm("Xoá toàn bộ lịch sử hội thoại với trợ lý vận hành?");
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

// ── SSE streaming helper ────────────────────────────────────────────────────
interface StreamResult {
  ok: boolean;
  action_proposal?: ActionProposalData | null;
  citations?: string[] | null;
  agent_mode?: string | null;
}

/** Đọc SSE từ /api/v1/copilot/message/stream và gọi onDelta cho từng chunk text. */
async function streamCopilot(
  payload: string,
  token: string,
  onDelta: (delta: string) => void
): Promise<StreamResult> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/copilot/message/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: payload,
    });

    if (!res.ok || !res.body) {
      return { ok: false };
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let meta: { action_proposal?: ActionProposalData | null; citations?: string[] | null; agent_mode?: string | null } = {};

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // Mỗi event SSE kết thúc bằng "\n\n".
      let idx: number;
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        const rawEvent = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        const lines = rawEvent.split("\n");
        let eventName = "message";
        for (const line of lines) {
          if (line.startsWith("event:")) eventName = line.slice(6).trim();
          else if (line.startsWith("data:")) {
            const dataStr = line.slice(5).trim();
            try {
              const data = JSON.parse(dataStr);
              if (eventName === "meta") {
                meta = {
                  action_proposal: data.action_proposal ?? null,
                  citations: Array.isArray(data.citations) ? data.citations : null,
                  agent_mode: data.agent_mode ?? null,
                };
              } else if (eventName === "delta") {
                onDelta(data.text || "");
              }
            } catch {
              /* bỏ qua chunk không parse được */
            }
          }
        }
      }
    }
    return { ok: true, ...meta };
  } catch {
    return { ok: false };
  }
}