"use client";

import React from "react";
import { Icon } from "../icons";

interface LightboxModalProps {
  url: string | null;
  onClose: () => void;
}

export function LightboxModal({ url, onClose }: LightboxModalProps) {
  if (!url) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4 animate-fade-in"
      onClick={onClose}
    >
      <div className="relative max-w-4xl max-h-[90vh] flex flex-col items-center" onClick={(e) => e.stopPropagation()}>
        <div className="absolute top-2 right-2 flex items-center gap-2 z-10">
          <a
            href={url}
            download
            target="_blank"
            rel="noreferrer"
            className="p-2 rounded-full bg-black/60 text-white hover:bg-black/90 transition shadow"
            title="Tải ảnh về"
          >
            <Icon name="download" size={20} />
          </a>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-full bg-black/60 text-white hover:bg-black/90 transition shadow"
            title="Đóng"
          >
            <Icon name="close" size={20} />
          </button>
        </div>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={url}
          alt="Preview"
          className="max-w-full max-h-[85vh] object-contain rounded-xl shadow-2xl border border-white/10"
        />
      </div>
    </div>
  );
}
