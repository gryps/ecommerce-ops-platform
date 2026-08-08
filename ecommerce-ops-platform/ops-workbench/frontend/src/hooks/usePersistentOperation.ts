import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { TrackedOperationStatus } from "../types";

export function usePersistentOperation(kind: "material_classification" | "copy_generation", onSettled: (status: TrackedOperationStatus) => void | Promise<void>) {
  const storageKey = `workbench_operation_${kind}`;
  const [operationId, setOperationId] = useState(() => localStorage.getItem(storageKey) ?? "");
  const activeIdRef = useRef(operationId);
  const settledRef = useRef(onSettled);
  settledRef.current = onSettled;

  const clear = useCallback((expectedId: string) => {
    if (activeIdRef.current !== expectedId) return;
    localStorage.removeItem(storageKey);
    activeIdRef.current = "";
    setOperationId("");
  }, [storageKey]);
  const begin = useCallback(() => {
    if (activeIdRef.current) return null;
    const id = crypto.randomUUID().replaceAll("-", "");
    localStorage.setItem(storageKey, id);
    activeIdRef.current = id;
    setOperationId(id);
    return id;
  }, [storageKey]);

  useEffect(() => {
    if (!operationId) return undefined;
    let cancelled = false;
    let timer = 0;
    let unknownCount = 0;
    const poll = async () => {
      try {
        const state = await api<TrackedOperationStatus>(`/human/operation-status/${operationId}`);
        if (cancelled) return;
        if (state.status === "processing" || (state.status === "unknown" && unknownCount++ < 3)) {
          timer = window.setTimeout(poll, 1200);
          return;
        }
        const settled = state.status === "unknown"
          ? { ...state, status: "failed" as const, detail: "服务已重启或操作状态已失效，请先核对当前结果再重新提交。" }
          : state;
        clear(operationId);
        await settledRef.current(settled);
      } catch {
        if (!cancelled) timer = window.setTimeout(poll, 1500);
      }
    };
    poll();
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [clear, operationId]);

  return { busy: Boolean(operationId), begin, clear };
}
