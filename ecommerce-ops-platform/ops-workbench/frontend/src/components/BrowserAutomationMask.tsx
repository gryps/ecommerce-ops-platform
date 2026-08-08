import { useState } from "react";
import { LoaderCircle, Square } from "lucide-react";
import type { BrowserSession } from "../types";

export function BrowserAutomationMask({ session, onExit }: { session: BrowserSession; onExit: () => Promise<void> }) {
  const [stopping, setStopping] = useState(false);
  return <div className="browser-automation-mask" role="dialog" aria-modal="true" aria-labelledby="browser-automation-title">
    <section className="browser-automation-panel">
      <LoaderCircle className="spin" />
      <div><b id="browser-automation-title">浏览器自动化正在运行</b><span>平台浏览器已独立打开。请在其中完成登录；系统不会绕过验证码、风控或二次确认。</span><small>{session.platform_url}</small></div>
      <button type="button" className="human-danger" disabled={stopping} onClick={async () => { setStopping(true); try { await onExit(); } finally { setStopping(false); } }}><Square />{stopping ? "正在退出…" : "退出自动化"}</button>
    </section>
  </div>;
}
