"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { API, apiGet, apiSend } from "./api";
import { chatSounds } from "./chat-sound";
import { getName, getNvId, getToken } from "./session";

export type ChatMessage = {
  id: string;
  conversation_id: string;
  sender_id: string;
  type: "text" | "image" | "file" | "voice" | "system" | "ops_card";
  content: string;
  reply_to_id?: string | null;
  reply_snippet?: {
    id: string;
    sender_id: string;
    content: string;
    type: string;
    sender_name: string;
  } | null;
  is_unsent: boolean;
  edited_at?: string | null;
  metadata?: Record<string, any>;
  created_at: string;
  sender_name?: string;
  sender_role?: string;
  reactions?: Record<string, { nv_id: string; name: string }[]>;
  status?: "sending" | "sent" | "error";
};

export type ChatConversation = {
  id: string;
  store_id: string;
  type: "general" | "direct" | "group";
  display_name: string;
  avatar_url?: string;
  is_locked: boolean;
  created_at: string;
  updated_at: string;
  muted?: boolean;
  unread_count?: number;
  last_message?: {
    id: string;
    sender_id: string;
    type: string;
    content: string;
    created_at: string;
    is_unsent?: boolean;
    sender_name?: string;
  } | null;
  participants: {
    nv_id: string;
    role: string;
    status: string;
    muted: boolean;
    display_name: string;
    user_role: string;
  }[];
  other_user?: {
    nv_id: string;
    display_name: string;
    user_role: string;
  };
};

export type ReadReceipt = {
  nv_id: string;
  display_name: string;
  last_read_message_id: string;
  read_at: string;
  role: string;
};

export function useChatClient(activeConvId?: string) {
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [messagesByConv, setMessagesByConv] = useState<Record<string, ChatMessage[]>>({});
  const [onlineUsers, setOnlineUsers] = useState<Set<string>>(new Set());
  const [typingByConv, setTypingByConv] = useState<Record<string, { nv_id: string; is_typing: boolean }>>({});
  const [receiptsByConv, setReceiptsByConv] = useState<Record<string, ReadReceipt[]>>({});
  const [isConnected, setIsConnected] = useState(false);
  const [loadingConv, setLoadingConv] = useState(true);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const backoffRef = useRef(1000);
  const activeConvIdRef = useRef(activeConvId);
  activeConvIdRef.current = activeConvId;

  const currentNvId = getNvId();

  // 1. Tải danh sách hội thoại
  const loadConversations = useCallback(async () => {
    try {
      setLoadingConv(true);
      const res = await apiGet<{ items: ChatConversation[]; unread_total: number }>("/api/v1/chat/conversations");
      setConversations(res.items || []);
    } catch {
      // Ignored
    } finally {
      setLoadingConv(false);
    }
  }, []);

  // 2. Tải tin nhắn của hội thoại
  const loadMessages = useCallback(async (convId: string) => {
    if (!convId) return;
    try {
      const res = await apiGet<{ items: ChatMessage[] }>(`/api/v1/chat/conversations/${convId}/messages?limit=60`);
      setMessagesByConv((prev) => ({ ...prev, [convId]: res.items || [] }));
    } catch {}
  }, []);

  // 3. Tải danh sách online
  const loadOnline = useCallback(async () => {
    try {
      const res = await apiGet<{ online_users: string[] }>("/api/v1/chat/online");
      setOnlineUsers(new Set(res.online_users || []));
    } catch {}
  }, []);

  // 4. Kết nối WebSocket với First-Message Authentication
  const connectWebSocket = useCallback(() => {
    if (typeof window === "undefined") return;
    const token = getToken();
    if (!token) return;

    if (socketRef.current && (socketRef.current.readyState === WebSocket.OPEN || socketRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const wsUrl = `${API.replace(/^http/, "ws")}/ws/chat`;
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      // Gửi ngay message xác thực đầu tiên
      ws.send(JSON.stringify({ event: "auth", token }));
    };

    ws.onmessage = (e) => {
      try {
        const packet = JSON.parse(e.data);
        const event = packet.event;
        const data = packet.data;

        if (event === "auth:ack") {
          setIsConnected(true);
          backoffRef.current = 1000;
          return;
        }

        if (event == "message:new") {
          const msg = data as ChatMessage;
          const cid = msg.conversation_id;

          setMessagesByConv((prev) => {
            const list = prev[cid] || [];
            if (list.some((m) => m.id === msg.id)) return prev;
            return { ...prev, [cid]: [...list, msg] };
          });

          // Cập nhật last_message và unread trong danh sách hội thoại
          setConversations((prev) =>
            prev.map((c) => {
              if (c.id === cid) {
                const isCurrentActive = activeConvIdRef.current === cid;
                const isFromMe = msg.sender_id === currentNvId;
                if (!isFromMe && !c.muted) {
                  chatSounds.playMessageTing();
                }
                return {
                  ...c,
                  updated_at: msg.created_at,
                  last_message: {
                    id: msg.id,
                    sender_id: msg.sender_id,
                    type: msg.type,
                    content: msg.content,
                    created_at: msg.created_at,
                    sender_name: msg.sender_name,
                  },
                  unread_count: isCurrentActive || isFromMe ? 0 : (c.unread_count || 0) + 1,
                };
              }
              return c;
            })
          );
          return;
        }

        if (event === "message:updated") {
          const updated = data as ChatMessage;
          const cid = updated.conversation_id;
          setMessagesByConv((prev) => {
            const list = prev[cid] || [];
            return {
              ...prev,
              [cid]: list.map((m) => (m.id === updated.id ? updated : m)),
            };
          });
          return;
        }

        if (event === "message:typing") {
          const { conversation_id, nv_id, is_typing } = data;
          setTypingByConv((prev) => ({
            ...prev,
            [conversation_id]: { nv_id, is_typing },
          }));
          return;
        }

        if (event === "message:read") {
          const { conversation_id, receipts } = data;
          if (receipts) {
            setReceiptsByConv((prev) => ({ ...prev, [conversation_id]: receipts }));
          }
          return;
        }

        if (event === "user:online") {
          setOnlineUsers((prev) => new Set([...prev, data.nv_id]));
          return;
        }

        if (event === "user:offline") {
          setOnlineUsers((prev) => {
            const next = new Set(prev);
            next.delete(data.nv_id);
            return next;
          });
          return;
        }

        if (event === "conversation:created") {
          loadConversations();
          return;
        }
      } catch {}
    };

    ws.onclose = () => {
      setIsConnected(false);
      socketRef.current = null;
      // Exponential backoff reconnect
      const delay = Math.min(backoffRef.current, 10000);
      backoffRef.current *= 1.5;
      reconnectTimeoutRef.current = setTimeout(connectWebSocket, delay);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [currentNvId, loadConversations]);

  // Ping interval giữ kết nối
  useEffect(() => {
    const timer = setInterval(() => {
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({ event: "ping" }));
      }
    }, 15000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    loadConversations();
    loadOnline();
    connectWebSocket();

    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (socketRef.current) socketRef.current.close();
    };
  }, [loadConversations, loadOnline, connectWebSocket]);

  useEffect(() => {
    if (activeConvId) {
      loadMessages(activeConvId);
    }
  }, [activeConvId, loadMessages]);

  // Actions
  const sendMessage = useCallback(
    async (convId: string, content: string, msgType: ChatMessage["type"] = "text", metadata: Record<string, any> = {}, replyToId?: string) => {
      if (!convId || (!content.trim() && !metadata.url)) return;

      // Optimistic update
      const tempId = `temp_${Date.now()}`;
      const optimisticMsg: ChatMessage = {
        id: tempId,
        conversation_id: convId,
        sender_id: currentNvId,
        type: msgType,
        content: content.trim(),
        reply_to_id: replyToId,
        is_unsent: false,
        metadata,
        created_at: new Date().toISOString(),
        sender_name: getName() || currentNvId,
        status: "sending",
      };

      setMessagesByConv((prev) => ({
        ...prev,
        [convId]: [...(prev[convId] || []), optimisticMsg],
      }));

      // Thử gửi qua WebSocket trước
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.send(
          JSON.stringify({
            event: "message:send",
            data: {
              conversation_id: convId,
              content: content.trim(),
              msg_type: msgType,
              metadata,
              reply_to_id: replyToId,
            },
          })
        );
      } else {
        // Fallback REST
        try {
          const sent = await apiSend<ChatMessage>(`/api/v1/chat/conversations/${convId}/messages`, {
            content: content.trim(),
            msg_type: msgType,
            metadata,
            reply_to_id: replyToId,
          });
          setMessagesByConv((prev) => ({
            ...prev,
            [convId]: (prev[convId] || []).map((m) => (m.id === tempId ? sent : m)),
          }));
        } catch {
          setMessagesByConv((prev) => ({
            ...prev,
            [convId]: (prev[convId] || []).map((m) => (m.id === tempId ? { ...m, status: "error" } : m)),
          }));
        }
      }
    },
    [currentNvId]
  );

  const editMessage = useCallback(async (messageId: string, newContent: string) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          event: "message:edit",
          data: { message_id: messageId, content: newContent },
        })
      );
    } else {
      await apiSend(`/api/v1/chat/messages/${messageId}`, { content: newContent }, "PATCH");
    }
  }, []);

  const deleteMessage = useCallback(async (messageId: string, convId?: string) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          event: "message:delete",
          data: { message_id: messageId, conversation_id: convId },
        })
      );
    } else {
      await apiSend(`/api/v1/chat/messages/${messageId}`, {}, "DELETE");
    }
  }, []);

  const reactMessage = useCallback(async (messageId: string, convId: string, emoji: string) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          event: "message:react",
          data: { message_id: messageId, conversation_id: convId, emoji },
        })
      );
    } else {
      await apiSend(`/api/v1/chat/messages/${messageId}/reactions`, { emoji });
    }
  }, []);

  const sendTyping = useCallback((convId: string, isTyping: boolean) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          event: "message:typing",
          data: { conversation_id: convId, is_typing: isTyping },
        })
      );
    }
  }, []);

  const markRead = useCallback(async (convId: string, messageId: string) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          event: "message:read",
          data: { conversation_id: convId, message_id: messageId },
        })
      );
    } else {
      await apiSend(`/api/v1/chat/conversations/${convId}/read?message_id=${messageId}`);
    }
    // Xóa unread badge
    setConversations((prev) =>
      prev.map((c) => (c.id === convId ? { ...c, unread_count: 0 } : c))
    );
  }, []);

  const muteConversation = useCallback(async (convId: string, muted: boolean) => {
    await apiSend(`/api/v1/chat/conversations/${convId}/mute`, { muted });
    setConversations((prev) =>
      prev.map((c) => (c.id === convId ? { ...c, muted } : c))
    );
  }, []);

  const uploadMedia = useCallback(async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const token = getToken();
    const res = await fetch(`${API}/api/v1/chat/upload`, {
      method: "POST",
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Lỗi tải tệp lên");
    }
    return (await res.json()) as { url: string; filename: string; size: number; mime_type: string };
  }, []);

  const pinMessage = useCallback(async (messageId: string, pinned: boolean = true) => {
    await apiSend(`/api/v1/chat/messages/${messageId}/pin`, { pinned });
  }, []);

  const unreadTotal = conversations.reduce((sum, c) => sum + (c.unread_count || 0), 0);

  return {
    conversations,
    messages: (activeConvId ? messagesByConv[activeConvId] : []) || [],
    messagesByConv,
    onlineUsers,
    typing: activeConvId ? typingByConv[activeConvId] : undefined,
    receipts: activeConvId ? receiptsByConv[activeConvId] : undefined,
    isConnected,
    loadingConv,
    unreadTotal,
    loadConversations,
    loadMessages,
    sendMessage,
    editMessage,
    deleteMessage,
    reactMessage,
    pinMessage,
    sendTyping,
    markRead,
    muteConversation,
    uploadMedia,
  };
}
