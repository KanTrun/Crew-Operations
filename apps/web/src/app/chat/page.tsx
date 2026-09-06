"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { API, apiSend } from "../../lib/api";
import { ChatConversation, ChatMessage, useChatClient } from "../../lib/useChatClient";
import { getName, getNvId, getRole } from "../../lib/session";
import { VoicePlayer, VoiceRecorder } from "../../ui/chat/VoiceRecorder";
import { LightboxModal } from "../../ui/chat/LightboxModal";
import { NewGroupModal } from "../../ui/chat/NewGroupModal";
import { Loading, PageHeader } from "../../ui/kit";

const QUICK_EMOJIS = ["❤️", "👍", "😂", "😮", "😢", "😡"];

export default function ChatPage() {
  const currentNvId = getNvId();
  const currentName = getName();

  const [activeConvId, setActiveConvId] = useState<string>("");
  const [inputText, setInputText] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [filterTab, setFilterTab] = useState<"all" | "unread" | "groups">("all");
  const [replyingTo, setReplyingTo] = useState<ChatMessage | null>(null);
  const [editingMsg, setEditingMsg] = useState<ChatMessage | null>(null);
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [isNewGroupOpen, setIsNewGroupOpen] = useState(false);
  const [showMemberDrawer, setShowMemberDrawer] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const {
    conversations,
    messages,
    onlineUsers,
    typing,
    receipts,
    isConnected,
    loadingConv,
    sendMessage,
    editMessage,
    deleteMessage,
    reactMessage,
    pinMessage,
    sendTyping,
    markRead,
    muteConversation,
    uploadMedia,
    loadConversations,
  } = useChatClient(activeConvId);

  const pinnedMessages = useMemo(() => {
    return messages.filter((m) => !m.is_unsent && m.metadata?.pinned);
  }, [messages]);

  // Chọn hội thoại mặc định: luôn ưu tiên nhóm chung "conv_general_quan_01"
  useEffect(() => {
    if (!activeConvId && conversations.length > 0) {
      const general = conversations.find((c) => c.type === "general");
      setActiveConvId(general ? general.id : conversations[0].id);
    }
  }, [conversations, activeConvId]);

  // Đánh dấu đã đọc khi mở hội thoại hoặc có tin nhắn mới
  useEffect(() => {
    if (activeConvId && messages.length > 0) {
      const last = messages[messages.length - 1];
      if (last && last.id && !last.id.startsWith("temp_")) {
        markRead(activeConvId, last.id);
      }
    }
  }, [activeConvId, messages, markRead]);

  // Tự động cuộn xuống cuối khi có tin mới
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typing]);

  const activeConv = useMemo(() => {
    return conversations.find((c) => c.id === activeConvId);
  }, [conversations, activeConvId]);

  // Bộ lọc hội thoại
  const filteredConversations = useMemo(() => {
    return conversations.filter((c) => {
      const matchSearch =
        !searchTerm.trim() ||
        c.display_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (c.last_message?.content || "").toLowerCase().includes(searchTerm.toLowerCase());

      if (!matchSearch) return false;

      if (filterTab === "unread") return (c.unread_count || 0) > 0;
      if (filterTab === "groups") return c.type === "group" || c.type === "general";
      return true;
    });
  }, [conversations, searchTerm, filterTab]);

  const handleSend = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim() || !activeConvId) return;

    if (editingMsg) {
      await editMessage(editingMsg.id, inputText.trim());
      setEditingMsg(null);
      setInputText("");
      return;
    }

    const replyId = replyingTo ? replyingTo.id : undefined;
    await sendMessage(activeConvId, inputText.trim(), "text", {}, replyId);
    setInputText("");
    setReplyingTo(null);
    sendTyping(activeConvId, false);
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputText(e.target.value);
    if (activeConvId) {
      sendTyping(activeConvId, e.target.value.length > 0);
    }
    // Auto resize
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !activeConvId) return;
    try {
      const res = await uploadMedia(file);
      const isImg = file.type.startsWith("image/");
      const msgType = isImg ? "image" : "file";
      const fullUrl = `${API}${res.url}`;
      await sendMessage(activeConvId, isImg ? "" : res.filename, msgType, {
        url: fullUrl,
        size: res.size,
        mime: res.mime_type,
        filename: res.filename,
      });
    } catch (err: any) {
      alert(err?.message || "Lỗi tải tệp lên");
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleVoiceSend = async (blob: Blob, durationSec: number) => {
    if (!activeConvId) return;
    const file = new File([blob], `voice_${Date.now()}.webm`, { type: "audio/webm" });
    const res = await uploadMedia(file);
    const fullUrl = `${API}${res.url}`;
    await sendMessage(activeConvId, "", "voice", {
      url: fullUrl,
      duration: durationSec,
    });
  };

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] overflow-hidden bg-[var(--nq-bg)]">
      {/* Container chính: 2 cột (Sidebar & Chat Area) */}
      <div className="flex flex-1 overflow-hidden">
        {/* CỘT TRÁI: DANH SÁCH HỘI THOẠI */}
        <div
          className={`${
            activeConvId ? "hidden md:flex" : "flex"
          } w-full md:w-80 lg:w-96 flex-col border-r border-[var(--nq-dim)] bg-[var(--nq-card)] shrink-0`}
        >
          {/* Header Sidebar */}
          <div className="p-4 border-b border-[var(--nq-dim)] flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="relative">
                <div className="w-9 h-9 rounded-full bg-[var(--nq-copper)] text-white font-bold flex items-center justify-center text-sm shadow">
                  {(currentName || "NV").charAt(0).toUpperCase()}
                </div>
                <span
                  className={`absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-[var(--nq-card)] ${
                    isConnected ? "bg-green-500" : "bg-gray-400"
                  }`}
                  title={isConnected ? "Đã kết nối" : "Mất kết nối"}
                />
              </div>
              <div>
                <h2 className="font-bold text-base text-[var(--nq-fg)] leading-tight">Trò chuyện</h2>
                <p className="text-[11px] text-[var(--nq-muted)] flex items-center gap-1">
                  <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? "bg-green-500" : "bg-amber-500"}`} />
                  {isConnected ? "Trực tuyến" : "Đang kết nối lại…"}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setIsNewGroupOpen(true)}
              className="p-2 rounded-xl bg-[var(--nq-bg)] border border-[var(--nq-dim)] hover:border-[var(--nq-copper)] text-[var(--nq-fg)] hover:text-[var(--nq-copper)] transition shadow-sm"
              title="Tạo nhóm chat mới"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
            </button>
          </div>

          {/* Ô tìm kiếm */}
          <div className="p-3 border-b border-[var(--nq-dim)]">
            <div className="relative">
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Tìm người hoặc tin nhắn…"
                className="w-full pl-8 pr-3 py-1.5 rounded-xl bg-[var(--nq-bg)] border border-[var(--nq-dim)] focus:border-[var(--nq-copper)] outline-none text-xs text-[var(--nq-fg)] placeholder-[var(--nq-muted)]"
              />
              <svg
                className="w-4 h-4 absolute left-2.5 top-2 text-[var(--nq-muted)]"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            {/* Filter Tabs */}
            <div className="flex gap-1 mt-2">
              <button
                type="button"
                onClick={() => setFilterTab("all")}
                className={`flex-1 py-1 text-[11px] font-bold rounded-lg transition ${
                  filterTab === "all" ? "bg-[var(--nq-copper)] text-white" : "text-[var(--nq-muted)] hover:bg-[var(--nq-bg)]"
                }`}
              >
                Tất cả
              </button>
              <button
                type="button"
                onClick={() => setFilterTab("unread")}
                className={`flex-1 py-1 text-[11px] font-bold rounded-lg transition ${
                  filterTab === "unread" ? "bg-[var(--nq-copper)] text-white" : "text-[var(--nq-muted)] hover:bg-[var(--nq-bg)]"
                }`}
              >
                Chưa đọc
              </button>
              <button
                type="button"
                onClick={() => setFilterTab("groups")}
                className={`flex-1 py-1 text-[11px] font-bold rounded-lg transition ${
                  filterTab === "groups" ? "bg-[var(--nq-copper)] text-white" : "text-[var(--nq-muted)] hover:bg-[var(--nq-bg)]"
                }`}
              >
                Nhóm
              </button>
            </div>
          </div>

          {/* Danh sách hội thoại */}
          <div className="flex-1 overflow-y-auto divide-y divide-[var(--nq-dim)]/40">
            {loadingConv && conversations.length === 0 ? (
              <div className="p-6 text-center text-xs text-[var(--nq-muted)]">Đang tải hội thoại…</div>
            ) : filteredConversations.length === 0 ? (
              <div className="p-6 text-center text-xs text-[var(--nq-muted)] italic">Không tìm thấy cuộc trò chuyện nào.</div>
            ) : (
              filteredConversations.map((conv) => {
                const isActive = conv.id === activeConvId;
                const isGeneral = conv.type === "general";
                const otherNvId = conv.type === "direct" ? conv.other_user?.nv_id : undefined;
                const isUserOnline = otherNvId ? onlineUsers.has(otherNvId) : false;

                return (
                  <div
                    key={conv.id}
                    onClick={() => setActiveConvId(conv.id)}
                    className={`p-3 cursor-pointer flex items-center gap-3 transition ${
                      isActive ? "bg-[var(--nq-copper-dim)]/20 border-l-4 border-[var(--nq-copper)]" : "hover:bg-[var(--nq-bg)]"
                    }`}
                  >
                    {/* Avatar */}
                    <div className="relative shrink-0">
                      {isGeneral ? (
                        <div className="w-11 h-11 rounded-2xl bg-amber-500/20 text-amber-500 font-bold flex items-center justify-center text-lg border border-amber-500/30">
                          ☕
                        </div>
                      ) : conv.type === "group" ? (
                        <div className="w-11 h-11 rounded-2xl bg-[var(--nq-dim)] text-[var(--nq-copper)] font-bold flex items-center justify-center text-base">
                          👥
                        </div>
                      ) : (
                        <div className="w-11 h-11 rounded-full bg-[var(--nq-dim)] text-[var(--nq-fg)] font-bold flex items-center justify-center text-sm">
                          {conv.display_name.charAt(0).toUpperCase()}
                        </div>
                      )}
                      {conv.type === "direct" && (
                        <span
                          className={`absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-[var(--nq-card)] ${
                            isUserOnline ? "bg-green-500" : "bg-gray-400"
                          }`}
                        />
                      )}
                    </div>

                    {/* Content Snippet */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1 mb-0.5">
                        <span className="font-bold text-xs text-[var(--nq-fg)] truncate flex items-center gap-1.5">
                          {conv.display_name}
                          {isGeneral && (
                            <span className="bg-amber-500/20 text-amber-600 dark:text-amber-400 text-[9px] font-extrabold px-1.5 py-0.2 rounded uppercase">
                              Toàn quán
                            </span>
                          )}
                        </span>
                        {conv.last_message?.created_at && (
                          <span className="text-[10px] text-[var(--nq-muted)] whitespace-nowrap">
                            {new Date(conv.last_message.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center justify-between gap-1">
                        <p className="text-[11px] text-[var(--nq-muted)] truncate">
                          {conv.last_message ? (
                            conv.last_message.is_unsent ? (
                              <span className="italic">Tin nhắn đã thu hồi</span>
                            ) : conv.last_message.type === "image" ? (
                              "📷 Đã gửi một ảnh"
                            ) : conv.last_message.type === "voice" ? (
                              "🎤 Tin nhắn thoại"
                            ) : (
                              `${conv.last_message.sender_name ? `${conv.last_message.sender_name}: ` : ""}${conv.last_message.content}`
                            )
                          ) : (
                            <span className="italic">Bắt đầu trò chuyện…</span>
                          )}
                        </p>
                        {(conv.unread_count || 0) > 0 && (
                          <span className="w-5 h-5 rounded-full bg-[var(--nq-copper)] text-white text-[10px] font-bold flex items-center justify-center shrink-0">
                            {conv.unread_count}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* CỘT PHẢI: KHUNG CHAT CHÍNH */}
        {activeConv ? (
          <div
            className={`${
              activeConvId ? "flex" : "hidden md:flex"
            } flex-1 flex-col bg-[var(--nq-bg)] h-full overflow-hidden`}
          >
            {/* Header Chat */}
            <div className="p-3.5 border-b border-[var(--nq-dim)] bg-[var(--nq-card)] flex items-center justify-between shadow-sm">
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setActiveConvId("")}
                  className="md:hidden p-1.5 text-[var(--nq-muted)] hover:text-[var(--nq-fg)]"
                >
                  ◀
                </button>
                <div className="w-9 h-9 rounded-full bg-[var(--nq-dim)] flex items-center justify-center font-bold text-sm text-[var(--nq-copper)]">
                  {activeConv.type === "general" ? "☕" : activeConv.type === "group" ? "👥" : activeConv.display_name.charAt(0)}
                </div>
                <div>
                  <h3 className="font-bold text-sm text-[var(--nq-fg)] flex items-center gap-2">
                    {activeConv.display_name}
                    {activeConv.is_locked && (
                      <span className="text-[10px] bg-amber-500/20 text-amber-500 px-1.5 py-0.5 rounded font-mono">CHUNG</span>
                    )}
                  </h3>
                  <p className="text-[11px] text-[var(--nq-muted)]">
                    {activeConv.type === "direct" ? (
                      activeConv.other_user && onlineUsers.has(activeConv.other_user.nv_id) ? (
                        <span className="text-green-500 font-medium">● Đang hoạt động</span>
                      ) : (
                        "Ngoại tuyến"
                      )
                    ) : (
                      `${activeConv.participants.length} thành viên`
                    )}
                  </p>
                </div>
              </div>

              {/* Actions Header */}
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => muteConversation(activeConv.id, !activeConv.muted)}
                  className={`p-2 rounded-xl border transition ${
                    activeConv.muted
                      ? "bg-amber-500/10 text-amber-500 border-amber-500/30"
                      : "text-[var(--nq-muted)] hover:text-[var(--nq-fg)] border-transparent"
                  }`}
                  title={activeConv.muted ? "Bật thông báo" : "Tắt thông báo"}
                >
                  {activeConv.muted ? "🔕" : "🔔"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowMemberDrawer(!showMemberDrawer)}
                  className="p-2 rounded-xl text-[var(--nq-muted)] hover:text-[var(--nq-fg)] transition"
                  title="Danh sách thành viên"
                >
                  ℹ️
                </button>
              </div>
            </div>

            {/* Banner tin nhắn đã ghim (Pinned Banner) */}
            {pinnedMessages.length > 0 && (
              <div className="bg-[var(--nq-copper)]/10 border-b border-[var(--nq-copper)]/30 px-4 py-2 flex items-center justify-between text-xs text-[var(--nq-copper)] shrink-0">
                <div className="flex items-center gap-2 truncate">
                  <span>📌</span>
                  <span className="font-bold">Đã ghim:</span>
                  <span className="truncate">{pinnedMessages[pinnedMessages.length - 1].content}</span>
                </div>
                <button
                  type="button"
                  onClick={() => pinMessage(pinnedMessages[pinnedMessages.length - 1].id, false)}
                  className="text-[10px] underline hover:opacity-80 shrink-0 ml-2"
                >
                  Bỏ ghim
                </button>
              </div>
            )}

            {/* Dòng thời gian tin nhắn (Message Stream) */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {messages.map((msg, index) => {
                const isMe = msg.sender_id === currentNvId;
                const isSystem = msg.sender_id === "system" || msg.type === "system";

                if (isSystem) {
                  return (
                    <div key={msg.id || index} className="flex justify-center my-3">
                      <span className="px-3 py-1 rounded-full bg-[var(--nq-dim)]/40 text-[var(--nq-muted)] text-xs font-medium max-w-md text-center">
                        {msg.content}
                      </span>
                    </div>
                  );
                }

                return (
                  <div key={msg.id || index} className={`flex flex-col ${isMe ? "items-end" : "items-start"}`}>
                    {!isMe && (
                      <span className="text-[10px] text-[var(--nq-muted)] ml-1 mb-0.5 font-medium">
                        {msg.sender_name || msg.sender_id}
                      </span>
                    )}

                    <div className="relative group max-w-[80%] sm:max-w-[70%]">
                      {/* Trích dẫn trả lời (Reply quote) */}
                      {msg.reply_snippet && (
                        <div
                          className={`text-[11px] p-2 rounded-t-xl border-b opacity-80 mb-[-4px] ${
                            isMe ? "bg-[var(--nq-copper)]/80 text-white border-white/20" : "bg-[var(--nq-dim)] text-[var(--nq-fg)] border-black/10"
                          }`}
                        >
                          <span className="font-bold block text-[10px]">{msg.reply_snippet.sender_name}</span>
                          <span className="truncate block">{msg.reply_snippet.content}</span>
                        </div>
                      )}

                      {/* Bong bóng chat chính */}
                      <div
                        className={`p-3 rounded-2xl text-xs break-words shadow-sm ${
                          isMe
                            ? "bg-[var(--nq-copper)] text-white rounded-br-none"
                            : "bg-[var(--nq-card)] text-[var(--nq-fg)] border border-[var(--nq-dim)] rounded-bl-none"
                        } ${msg.is_unsent ? "italic opacity-60" : ""}`}
                      >
                        {msg.is_unsent ? (
                          <span>Tin nhắn đã được thu hồi</span>
                        ) : (
                          <>
                            {msg.type === "image" && msg.metadata?.url && (
                              <div className="mb-2 rounded-xl overflow-hidden cursor-pointer" onClick={() => setPreviewImage(msg.metadata?.url)}>
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img
                                  src={msg.metadata.url}
                                  alt="Media"
                                  className="max-h-60 rounded-xl object-cover hover:opacity-95 transition"
                                />
                              </div>
                            )}

                            {msg.type === "voice" && msg.metadata?.url && (
                              <VoicePlayer url={msg.metadata.url} durationSec={msg.metadata.duration} />
                            )}

                            {msg.type === "ops_card" && (
                              <div className="my-2 p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl space-y-2 max-w-sm text-left">
                                <div className="flex items-center gap-2 text-amber-500 font-bold text-xs uppercase tracking-wider">
                                  <span>⚡</span>
                                  <span>{msg.metadata?.proposal?.title || "Đề xuất tác vụ vận hành"}</span>
                                </div>
                                <p className="text-xs opacity-90">{msg.metadata?.proposal?.summary || msg.content}</p>
                                <div className="flex items-center gap-2 pt-1 border-t border-amber-500/20 text-[11px]">
                                  <Link
                                    href="/contracts"
                                    className="px-2.5 py-1 bg-amber-500 text-black font-semibold rounded hover:bg-amber-400 transition inline-block"
                                  >
                                    Xem và duyệt trong Hộp thư
                                  </Link>
                                </div>
                              </div>
                            )}

                            {msg.content && (
                              <p className="leading-relaxed whitespace-pre-wrap">
                                {msg.content.split(/(@\S+)/g).map((part, i) =>
                                  part.startsWith("@") ? (
                                    <span key={i} className="font-semibold text-amber-500 bg-amber-500/15 px-1 py-0.5 rounded">
                                      {part}
                                    </span>
                                  ) : (
                                    part
                                  )
                                )}
                              </p>
                            )}

                            {msg.edited_at && <span className="text-[9px] opacity-75 ml-1 italic">(đã sửa)</span>}
                          </>
                        )}
                      </div>

                      {/* Reactions gắn chân tin nhắn */}
                      {msg.reactions && Object.keys(msg.reactions).length > 0 && (
                        <div
                          className={`flex items-center gap-1 mt-[-6px] px-1.5 py-0.5 rounded-full bg-[var(--nq-card)] border border-[var(--nq-dim)] shadow-sm text-[11px] ${
                            isMe ? "float-right mr-2" : "float-left ml-2"
                          }`}
                        >
                          {Object.entries(msg.reactions).map(([emoji, users]) => (
                            <span key={emoji} title={users.map((u) => u.name).join(", ")} className="cursor-pointer">
                              {emoji} {users.length > 1 && <span className="text-[9px] font-bold">{users.length}</span>}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Menu hành động khi hover (Reactions, Reply, Pin, Edit, Delete) */}
                      {!msg.is_unsent && (
                        <div
                          className={`absolute top-0 hidden group-hover:flex items-center gap-1 bg-[var(--nq-card)] border border-[var(--nq-dim)] p-1 rounded-xl shadow-md z-10 ${
                            isMe ? "right-full mr-2" : "left-full ml-2"
                          }`}
                        >
                          {QUICK_EMOJIS.slice(0, 3).map((emoji) => (
                            <button
                              key={emoji}
                              type="button"
                              onClick={() => reactMessage(msg.id, activeConv.id, emoji)}
                              className="hover:scale-125 transition text-xs p-1"
                            >
                              {emoji}
                            </button>
                          ))}
                          <button
                            type="button"
                            onClick={() => pinMessage(msg.id, !msg.metadata?.pinned)}
                            className="text-[var(--nq-muted)] hover:text-[var(--nq-copper)] p-1 text-xs"
                            title={msg.metadata?.pinned ? "Bỏ ghim" : "Ghim tin nhắn"}
                          >
                            📌
                          </button>
                          <button
                            type="button"
                            onClick={() => setReplyingTo(msg)}
                            className="text-[var(--nq-muted)] hover:text-[var(--nq-fg)] p-1 text-xs"
                            title="Trả lời"
                          >
                            ↩
                          </button>
                          {isMe && (
                            <>
                              <button
                                type="button"
                                onClick={() => {
                                  setEditingMsg(msg);
                                  setInputText(msg.content);
                                  textareaRef.current?.focus();
                                }}
                                className="text-[var(--nq-muted)] hover:text-[var(--nq-fg)] p-1 text-xs"
                                title="Sửa tin nhắn"
                              >
                                ✎
                              </button>
                              <button
                                type="button"
                                onClick={() => deleteMessage(msg.id, activeConv.id)}
                                className="text-[var(--nq-muted)] hover:text-red-500 p-1 text-xs"
                                title="Thu hồi"
                              >
                                ✕
                              </button>
                            </>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Timestamp & Status */}
                    <div className="flex items-center gap-1 mt-0.5 text-[10px] text-[var(--nq-muted)]">
                      <span>{new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                      {isMe && msg.status === "sending" && <span>• Đang gửi…</span>}
                    </div>

                    {/* Avatars người đã xem (Seen avatars) dưới tin nhắn */}
                    {receipts && receipts.some((r) => r.last_read_message_id === msg.id && r.nv_id !== currentNvId) && (
                      <div className="flex items-center gap-1 mt-1">
                        {receipts
                          .filter((r) => r.last_read_message_id === msg.id && r.nv_id !== currentNvId)
                          .map((r) => (
                            <div
                              key={r.nv_id}
                              title={`Đã xem bởi ${r.display_name}`}
                              className="w-4 h-4 rounded-full bg-[var(--nq-copper)] text-white text-[8px] font-bold flex items-center justify-center border border-[var(--nq-card)]"
                            >
                              {r.display_name.charAt(0)}
                            </div>
                          ))}
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Typing indicator */}
              {typing && typing.is_typing && typing.nv_id !== currentNvId && (
                <div className="flex items-center gap-2 text-xs text-[var(--nq-muted)] italic">
                  <div className="flex gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--nq-copper)] animate-bounce" />
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--nq-copper)] animate-bounce delay-100" />
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--nq-copper)] animate-bounce delay-200" />
                  </div>
                  <span>Đồng nghiệp đang soạn tin…</span>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Banner đang trả lời / đang sửa */}
            {(replyingTo || editingMsg) && (
              <div className="px-4 py-2 bg-[var(--nq-card)] border-t border-[var(--nq-dim)] flex items-center justify-between text-xs">
                <div className="truncate">
                  {editingMsg ? (
                    <span className="text-[var(--nq-copper)] font-bold">Đang sửa tin nhắn…</span>
                  ) : (
                    <span>
                      Đang trả lời <strong className="text-[var(--nq-copper)]">{replyingTo?.sender_name}</strong>:{" "}
                      <span className="text-[var(--nq-muted)] truncate">{replyingTo?.content}</span>
                    </span>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setReplyingTo(null);
                    setEditingMsg(null);
                    setInputText("");
                  }}
                  className="text-[var(--nq-muted)] hover:text-[var(--nq-fg)] ml-2"
                >
                  ✕
                </button>
              </div>
            )}

            {/* Mention Suggestions Bar */}
            {inputText.includes("@") && (
              <div className="px-3 py-1.5 bg-[var(--nq-surface-hi)] border-t border-[var(--nq-dim)] flex items-center gap-1.5 overflow-x-auto text-xs shrink-0">
                <span className="text-[10px] text-[var(--nq-muted)] font-medium shrink-0">Gợi ý tag:</span>
                <button
                  type="button"
                  onClick={() => {
                    const lastAtIndex = inputText.lastIndexOf("@");
                    setInputText(inputText.substring(0, lastAtIndex) + "@copilot ");
                    textareaRef.current?.focus();
                  }}
                  className="px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-500 hover:bg-amber-500/30 text-[11px] font-semibold shrink-0 transition"
                >
                  🤖 @copilot
                </button>
                <button
                  type="button"
                  onClick={() => {
                    const lastAtIndex = inputText.lastIndexOf("@");
                    setInputText(inputText.substring(0, lastAtIndex) + "@agent_lich ");
                    textareaRef.current?.focus();
                  }}
                  className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-500 hover:bg-emerald-500/30 text-[11px] font-semibold shrink-0 transition"
                >
                  📅 @agent_lich
                </button>
                {activeConv?.participants.slice(0, 6).map((p) => (
                  <button
                    key={p.nv_id}
                    type="button"
                    onClick={() => {
                      const lastAtIndex = inputText.lastIndexOf("@");
                      setInputText(inputText.substring(0, lastAtIndex) + `@${p.display_name || p.nv_id} `);
                      textareaRef.current?.focus();
                    }}
                    className="px-2 py-0.5 rounded-full bg-[var(--nq-dim)] text-[var(--nq-fg)] hover:bg-[var(--nq-copper)]/20 hover:text-[var(--nq-copper)] text-[11px] shrink-0 transition"
                  >
                    @{p.display_name || p.nv_id}
                  </button>
                ))}
              </div>
            )}

            {/* Action Input Bar */}
            <div className="p-3 border-t border-[var(--nq-dim)] bg-[var(--nq-card)] flex items-end gap-2">
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileUpload}
                accept="image/*,application/pdf"
                className="hidden"
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="p-2 text-[var(--nq-muted)] hover:text-[var(--nq-copper)] rounded-full transition shrink-0"
                title="Đính kèm ảnh hoặc tài liệu"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                </svg>
              </button>

              <VoiceRecorder onSendVoice={handleVoiceSend} />

              <div className="flex-1 bg-[var(--nq-bg)] border border-[var(--nq-dim)] focus-within:border-[var(--nq-copper)] rounded-2xl px-3 py-1.5 flex items-center">
                <textarea
                  ref={textareaRef}
                  value={inputText}
                  onChange={handleInputChange}
                  onKeyDown={handleKeyDown}
                  placeholder={editingMsg ? "Sửa nội dung tin nhắn…" : "Nhập tin nhắn (Enter để gửi)…"}
                  rows={1}
                  className="w-full bg-transparent outline-none text-xs text-[var(--nq-fg)] resize-none placeholder-[var(--nq-muted)] max-h-28"
                />
              </div>

              <button
                type="button"
                onClick={() => handleSend()}
                disabled={!inputText.trim()}
                className="p-2.5 rounded-full bg-[var(--nq-copper)] text-white hover:opacity-90 disabled:opacity-40 transition shrink-0 shadow-md"
                title="Gửi tin nhắn"
              >
                <svg className="w-4 h-4 translate-x-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
              </button>
            </div>
          </div>
        ) : (
          <div className="hidden md:flex flex-1 items-center justify-center text-[var(--nq-muted)] text-sm italic">
            Chọn một cuộc trò chuyện để bắt đầu
          </div>
        )}

        {/* Drawer danh sách thành viên */}
        {showMemberDrawer && activeConv && (
          <div className="w-64 border-l border-[var(--nq-dim)] bg-[var(--nq-card)] p-4 flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-[var(--nq-dim)] pb-3">
              <h4 className="font-bold text-xs uppercase tracking-wider text-[var(--nq-fg)]">Thành viên ({activeConv.participants.length})</h4>
              <button type="button" onClick={() => setShowMemberDrawer(false)} className="text-[var(--nq-muted)] hover:text-[var(--nq-fg)]">✕</button>
            </div>
            <div className="flex-1 overflow-y-auto space-y-2">
              {activeConv.participants.map((p) => (
                <div key={p.nv_id} className="flex items-center gap-2.5 p-2 rounded-xl bg-[var(--nq-bg)]">
                  <div className="w-7 h-7 rounded-full bg-[var(--nq-copper)] text-white text-xs font-bold flex items-center justify-center">
                    {p.display_name.charAt(0)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="text-xs font-bold text-[var(--nq-fg)] block truncate">{p.display_name}</span>
                    <span className="text-[10px] text-[var(--nq-muted)] block capitalize">{p.role === "admin" ? "Quản trị viên" : "Thành viên"}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Modals */}
      <LightboxModal url={previewImage} onClose={() => setPreviewImage(null)} />
      <NewGroupModal
        isOpen={isNewGroupOpen}
        onClose={() => setIsNewGroupOpen(false)}
        onCreated={(id) => {
          loadConversations();
          setActiveConvId(id);
        }}
      />
    </div>
  );
}
