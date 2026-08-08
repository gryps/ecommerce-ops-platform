import {
  BookOpenText,
  Boxes,
  CheckCircle2,
  Film,
  Image as ImageIcon,
  KeyRound,
  LoaderCircle,
  LogOut,
  Music2,
  PanelLeftClose,
  PanelLeftOpen,
  Play,
  Settings,
  ShoppingBag,
  Upload,
  UserCircle,
  WandSparkles,
  X,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, clearToken, storedToken } from "./api";
import { Auth } from "./components/Auth";
import { BusinessModelSettings } from "./modules/model-config/BusinessModelSettings";
import { ImageProduction } from "./modules/image-production/ImageProduction";
import { Flow, Materials, CopyLibrary, MusicLibrary, DraftProduction } from "./modules/video-production/VideoProduction";
import type {
  ClassifiedMaterial,
  CopyItem,
  ImageView,
  JianyingDraft,
  MusicResource,
  Narration,
  PlatformModule,
  Product,
  User,
  View,
} from "./types";

export default function HumanApp() {
  const [initialized, setInitialized] = useState<boolean | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [module, setModule] = useState<PlatformModule>(() => {
    const stored = localStorage.getItem("platform_module");
    return stored === "images" || stored === "models" ? stored : "video";
  });
  const [view, setView] = useState<View>("flow");
  const [imageView, setImageView] = useState<ImageView>("overview");
  const [products, setProducts] = useState<Product[]>([]);
  const [materials, setMaterials] = useState<ClassifiedMaterial[]>([]);
  const [copies, setCopies] = useState<CopyItem[]>([]);
  const [narrations, setNarrations] = useState<Narration[]>([]);
  const [music, setMusic] = useState<MusicResource[]>([]);
  const [drafts, setDrafts] = useState<JianyingDraft[]>([]);
  const [error, setError] = useState(""); const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => localStorage.getItem("human_sidebar_collapsed") === "1");
  const [accountOpen, setAccountOpen] = useState(false);
  const [profileName, setProfileName] = useState("");
  const [profilePhone, setProfilePhone] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [accountBusy, setAccountBusy] = useState(false);
  const [passwordBusy, setPasswordBusy] = useState(false);
  const [accountMessage, setAccountMessage] = useState("");
  const [accountError, setAccountError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [me, productRows, materialRows, copyRows, narrationRows, musicRows, draftRows] = await Promise.all([
        api<User>("/auth/me"), api<Product[]>("/products"),
        api<ClassifiedMaterial[]>("/human/classified-materials"),
        api<{ items: CopyItem[] }>("/human/copies/library?limit=200"), api<Narration[]>("/human/narrations"),
        api<MusicResource[]>("/music-resources"), api<JianyingDraft[]>("/human/jianying-drafts"),
      ]);
      setUser(me); setProducts(productRows); setMaterials(materialRows);
      setCopies(copyRows.items); setNarrations(narrationRows); setMusic(musicRows); setDrafts(draftRows);
    } catch (reason) {
      if (!storedToken()) setUser(null);
      else setError(reason instanceof Error ? reason.message : "加载失败");
    } finally { setLoading(false); }
  }, []);
  useEffect(() => {
    api<{ initialized: boolean }>("/auth/status", {}, false).then(value => {
      setInitialized(value.initialized); if (value.initialized && storedToken()) refresh();
    }).catch(() => setInitialized(false));
  }, [refresh]);
  useEffect(() => {
    if (!user) return;
    setProfileName(user.display_name || user.username);
    setProfilePhone(user.phone || "");
  }, [user]);
  useEffect(() => { localStorage.setItem("human_sidebar_collapsed", sidebarCollapsed ? "1" : "0"); }, [sidebarCollapsed]);
  useEffect(() => { localStorage.setItem("platform_module", module); }, [module]);
  const act = async (work: () => Promise<unknown>, success: string) => {
    setError(""); setNotice("");
    try { await work(); setNotice(success); await refresh(); return true; }
    catch (reason) { setError(reason instanceof Error ? reason.message : "操作失败"); return false; }
  };
  async function saveAccountProfile(event: FormEvent) {
    event.preventDefault();
    setAccountBusy(true); setAccountError(""); setAccountMessage(""); setError(""); setNotice("");
    try {
      const updated = await api<User>("/auth/me", { method: "PATCH", body: JSON.stringify({ display_name: profileName, phone: profilePhone }) });
      setUser(updated);
      setAccountMessage("用户信息已更新");
      setNotice("用户信息已更新");
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "用户信息保存失败";
      setAccountError(message); setError(message);
    } finally { setAccountBusy(false); }
  }
  async function savePassword(event: FormEvent) {
    event.preventDefault();
    setPasswordBusy(true); setAccountError(""); setAccountMessage(""); setError(""); setNotice("");
    if (newPassword !== confirmPassword) {
      setAccountError("两次输入的新密码不一致");
      setPasswordBusy(false);
      return;
    }
    try {
      await api("/auth/me/password", { method: "POST", body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }) });
      setCurrentPassword(""); setNewPassword(""); setConfirmPassword("");
      setAccountMessage("密码已更新");
      setNotice("密码已更新");
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "密码修改失败";
      setAccountError(message); setError(message);
    } finally { setPasswordBusy(false); }
  }

  if (initialized === null) return <main className="human-loading"><LoaderCircle className="spin" /> 正在启动</main>;
  if (!user) return <Auth initialized={initialized} done={value => { setUser(value); refresh(); }} />;
  const nav: Array<[View, string, typeof Film]> = [
    ["flow", "生产总览", Film], ["materials", "素材归类", Boxes],
    ["copy", "内容文库", BookOpenText], ["music", "背景音乐", Music2], ["production", "剪映草稿", Play],
  ];
  const imageNav: Array<[ImageView, string, typeof Film]> = [
    ["overview", "生产总览", Film], ["batches", "拍摄分组", Boxes],
    ["products", "产品资料", BookOpenText], ["plans", "出图方案", WandSparkles],
    ["review", "结果审核", CheckCircle2], ["delivery", "导出上传", Upload],
  ];
  const activeTitle = module === "video" ? nav.find(item => item[0] === view)?.[1] : module === "images" ? imageNav.find(item => item[0] === imageView)?.[1] : "模型配置";
  const operationMessage = error || notice || (loading ? "正在刷新数据" : "空闲");
  const operationTone = error ? "error" : loading ? "busy" : notice ? "success" : "idle";
  const userDisplayName = user.display_name || user.username;
  return <div className={`human-shell ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
    <aside>
      <div className="human-brand"><ShoppingBag /><span>电商运营平台<small>Commerce Operations</small></span></div>
      <button type="button" className="human-sidebar-toggle" onClick={() => setSidebarCollapsed(value => !value)}>
        {sidebarCollapsed ? <PanelLeftOpen /> : <PanelLeftClose />}
      </button>
      <div className="platform-module-switch" aria-label="业务模块">
        <button type="button" title={sidebarCollapsed ? "电商视频生产" : undefined} className={module === "video" ? "active" : ""} onClick={() => setModule("video")}><Film /><span>电商视频生产</span></button>
        <button type="button" title={sidebarCollapsed ? "电商图片生产" : undefined} className={module === "images" ? "active" : ""} onClick={() => setModule("images")}><ImageIcon /><span>电商图片生产</span></button>
        <button type="button" title={sidebarCollapsed ? "模型配置" : undefined} className={module === "models" ? "active" : ""} onClick={() => setModule("models")}><Settings /><span>模型配置</span></button>
      </div>
      {module === "video" && <nav>{nav.map(([key, label, Icon]) => <button key={key} title={sidebarCollapsed ? label : undefined} className={view === key ? "active" : ""} onClick={() => setView(key)}><Icon /><span>{label}</span></button>)}</nav>}
      {module === "images" && <nav>{imageNav.map(([key, label, Icon]) => <button key={key} title={sidebarCollapsed ? label : undefined} className={imageView === key ? "active" : ""} onClick={() => setImageView(key)}><Icon /><span>{label}</span></button>)}</nav>}
      <button className="human-logout" onClick={() => { clearToken(); setUser(null); }}><LogOut /><span>退出 {user.username}</span></button>
    </aside>
    <main>
      <header><div className="human-title-block"><small>{module === "video" ? "电商运营平台 · 视频生产" : module === "images" ? "电商运营平台 · 图片生产" : "电商运营平台 · 模型配置"}</small><h1>{activeTitle}</h1></div>
        <div className={`human-operation-status ${operationTone}`} role={error ? "alert" : "status"} aria-live="polite">
          <b>操作状态</b><span title={operationMessage}>{operationMessage}</span>
        </div>
        <button type="button" className="human-user-summary" onClick={() => { setAccountOpen(true); setAccountError(""); setAccountMessage(""); }}>
          <UserCircle /><span title={userDisplayName}>{userDisplayName}</span>
        </button>
      </header>
      {accountOpen && <div className="account-dialog-backdrop" role="presentation">
        <section className="account-dialog" role="dialog" aria-modal="true" aria-labelledby="account-dialog-title">
          <div className="account-dialog-title"><div><b id="account-dialog-title">当前用户</b><span>{user.username}</span></div><button type="button" className="human-secondary" onClick={() => setAccountOpen(false)}><X />关闭</button></div>
          <form className="account-form" onSubmit={saveAccountProfile}>
            <label>姓名<input value={profileName} onChange={event => setProfileName(event.target.value)} maxLength={80} placeholder={user.username} /></label>
            <label>手机号<input value={profilePhone} onChange={event => setProfilePhone(event.target.value)} maxLength={40} placeholder="未填写" /></label>
            <button type="submit" disabled={accountBusy}>{accountBusy && <LoaderCircle className="spin" />}保存用户信息</button>
          </form>
          <form className="account-form password" onSubmit={savePassword}>
            <div><KeyRound /><b>更改密码</b></div>
            <label>当前密码<input type="password" value={currentPassword} onChange={event => setCurrentPassword(event.target.value)} required /></label>
            <label>新密码<input type="password" value={newPassword} onChange={event => setNewPassword(event.target.value)} required minLength={10} /></label>
            <label>确认新密码<input type="password" value={confirmPassword} onChange={event => setConfirmPassword(event.target.value)} required minLength={10} /></label>
            <button type="submit" disabled={passwordBusy}>{passwordBusy && <LoaderCircle className="spin" />}确认修改密码</button>
          </form>
          {(accountError || accountMessage) && <p className={`account-dialog-message ${accountError ? "error" : ""}`}>{accountError || accountMessage}</p>}
        </section>
      </div>}
      {module === "video" && view === "flow" && <Flow materials={materials} copies={copies} music={music} drafts={drafts} />}
      {module === "video" && view === "materials" && <Materials products={products} act={act} />}
      {module === "video" && view === "copy" && <CopyLibrary copies={copies} narrations={narrations} act={act} reload={refresh} />}
      {module === "video" && view === "music" && <MusicLibrary music={music} act={act} />}
      {module === "video" && view === "production" && <DraftProduction copies={copies} narrations={narrations} music={music} drafts={drafts} act={act} />}
      {module === "images" && <ImageProduction view={imageView} onError={setError} onNotice={setNotice} />}
      {module === "models" && <BusinessModelSettings onError={setError} onNotice={setNotice} />}
    </main>
  </div>;
}
