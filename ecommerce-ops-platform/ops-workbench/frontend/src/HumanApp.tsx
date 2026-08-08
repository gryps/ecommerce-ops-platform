import {
  BookOpenText,
  Boxes,
  CheckCircle2,
  Film,
  Image as ImageIcon,
  LoaderCircle,
  LogOut,
  Music2,
  PanelLeftClose,
  PanelLeftOpen,
  Play,
  RefreshCw,
  Settings,
  ShoppingBag,
  Upload,
  WandSparkles,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
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
  useEffect(() => { localStorage.setItem("human_sidebar_collapsed", sidebarCollapsed ? "1" : "0"); }, [sidebarCollapsed]);
  useEffect(() => { localStorage.setItem("platform_module", module); }, [module]);
  const act = async (work: () => Promise<unknown>, success: string) => {
    setError(""); setNotice("");
    try { await work(); setNotice(success); await refresh(); return true; }
    catch (reason) { setError(reason instanceof Error ? reason.message : "操作失败"); return false; }
  };

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
      <header><div><small>{module === "video" ? "电商运营平台 · 视频生产" : module === "images" ? "电商运营平台 · 图片生产" : "电商运营平台 · 模型配置"}</small><h1>{activeTitle}</h1></div>
        <button className="human-secondary" onClick={refresh} disabled={loading}><RefreshCw className={loading ? "spin" : ""} />刷新</button>
      </header>
      <div className={`human-banner ${error ? "error" : "success"}${error || notice ? "" : " is-empty"}`} role={error ? "alert" : "status"} aria-live="polite" aria-hidden={!error && !notice}>{error || notice}</div>
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
