"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "./api";
import { viError } from "./present";

export type StaffOption = { id: string; ten: string };
export type ShiftOption = {
  id: string;
  label: string;
  thu?: string;
  bat_dau?: string;
  ket_thuc?: string;
  vi_tri?: string;
};

export type OpsPickers = {
  nhan_vien: StaffOption[];
  ca: ShiftOption[];
  me_nv_id?: string | null;
};

type State = {
  data: OpsPickers | null;
  loading: boolean;
  error: string | null;
};

let cache: OpsPickers | null = null;
let inflight: Promise<OpsPickers> | null = null;

async function fetchPickers(): Promise<OpsPickers> {
  if (cache) return cache;
  if (inflight) return inflight;
  inflight = apiGet<OpsPickers>("/api/v1/ops/pickers").then((d) => {
    cache = {
      nhan_vien: d.nhan_vien ?? [],
      ca: d.ca ?? [],
      me_nv_id: d.me_nv_id,
    };
    return cache;
  });
  try {
    return await inflight;
  } finally {
    inflight = null;
  }
}

/** Xóa cache sau khi đổi lịch / đăng xuất. */
export function invalidateOpsPickers() {
  cache = null;
}

export function useOpsPickers(enabled = true) {
  const [state, setState] = useState<State>({ data: cache, loading: !cache && enabled, error: null });

  const load = useCallback(() => {
    if (!enabled) return;
    setState((s) => ({ ...s, loading: true, error: null }));
    fetchPickers()
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((e) =>
        setState({
          data: null,
          loading: false,
          error: viError(e, { doing: "tải được danh sách người và ca" }),
        }),
      );
  }, [enabled]);

  useEffect(() => {
    if (enabled) load();
  }, [enabled, load]);

  return { ...state, reload: load };
}
