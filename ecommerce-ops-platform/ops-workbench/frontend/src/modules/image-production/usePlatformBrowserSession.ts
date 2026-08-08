import { useEffect, useState } from "react";
import { api } from "../../api";
import type { BrowserSession } from "../../types";

export function usePlatformBrowserSession({
  onError,
  onNotice,
}: {
  onError: (value: string) => void;
  onNotice: (value: string) => void;
}) {
  const [platformUrl, setPlatformUrl] = useState("");
  const [browserSession, setBrowserSession] = useState<BrowserSession | null>(null);

  async function startBrowserAutomation() {
    if (!platformUrl.trim()) {
      onError("请先填写已登录后用于发布商品的平台页面地址。");
      return;
    }
    try {
      onError("");
      onNotice("");
      const session = await api<BrowserSession>("/images/browser-sessions", { method: "POST", body: JSON.stringify({ platform_url: platformUrl }) });
      setBrowserSession(session);
    } catch (reason) {
      onError(reason instanceof Error ? reason.message : "无法启动平台浏览器");
    }
  }

  async function stopBrowserAutomation() {
    if (!browserSession) return;
    try {
      await api(`/images/browser-sessions/${browserSession.id}`, { method: "DELETE" });
      setBrowserSession(null);
      onNotice("已退出平台浏览器自动化会话。");
    } catch (reason) {
      setBrowserSession(null);
      onError(reason instanceof Error ? reason.message : "浏览器会话退出失败");
    }
  }

  useEffect(() => {
    if (!browserSession) return undefined;
    let cancelled = false;
    const timer = window.setInterval(async () => {
      try {
        const current = await api<BrowserSession>(`/images/browser-sessions/${browserSession.id}`);
        if (!cancelled && current.status !== "running") {
          setBrowserSession(null);
          onNotice("平台浏览器已关闭，自动化会话已结束。");
        }
      } catch {
        if (!cancelled) setBrowserSession(null);
      }
    }, 1500);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [browserSession, onNotice]);

  return {
    platformUrl,
    browserSession,
    setPlatformUrl,
    startBrowserAutomation,
    stopBrowserAutomation,
  };
}
