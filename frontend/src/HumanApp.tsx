import {
  BookOpenText,
  Boxes,
  ChevronDown,
  Film,
  FolderOpen,
  LoaderCircle,
  LogOut,
  Music2,
  PanelLeftClose,
  PanelLeftOpen,
  Play,
  RefreshCw,
  Settings,
  Sparkles,
  Upload,
  Volume2,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import {
  api,
  apiBlob,
  clearToken,
  ModelProfile,
  ModelProfilesResponse,
  saveToken,
  storedToken,
  User,
} from "./api";

type View = "flow" | "materials" | "copy" | "music" | "production" | "models";
type Product = {
  id: number; system_code: string; name: string; status: string; asset_count: number;
};
type Tag = { id: string; name: string; category: string; category_id: string; product_id?: number };
type TagCategory = { id: string; name: string };
type SourceVideo = { name: string; relative_path: string; path: string };
type ClassifiedMaterial = {
  id: string; product_id: number; product_name: string; filename: string; source_path: string;
  status: string; duration_seconds: number; width: number; height: number; tags: Tag[];
};
type CopyItem = {
  id: string; content: string; product_id: number | null; product_name?: string;
  source: string;
};
type CopyCandidate = { id: string; content: string; status: string; rejection_reason?: string; library_content_id?: string | null };
type CopyBatch = { id: string; sequence_number: number; created_at: string; copies: CopyCandidate[] };
type CopyAnalysis = {
  id: string; source_mode: "input" | "adopted_history"; source_text: string;
  language_analysis: Record<string, string>; audience_analysis: Record<string, string>;
  expert_role: string; created_at: string; batches: CopyBatch[];
};
type VoiceCatalogItem = { sequence: number; name: string; voice: string; gender: string; age: string; trait: string; scenario: string; language: string; preview_filename: string; preview_ready?: boolean };
type Narration = {
  id: string; approved_text: string; recognized_text: string; voice_source: "human" | "model";
  text_source: "human" | "model"; subtitle_cues: Array<Record<string, unknown>>; status: string;
};
type MusicResource = {
  id: string; name: string; status: string; duration_seconds: number; source_type: string;
  custom_tags: string[]; error?: string;
};
type JianyingDraft = {
  id: string; name: string; draft_path: string; status: string; created_at: string; error: string;
  copy_content_id?: string | null; narration_asset_id?: string | null; music_resource_id?: string | null;
  snapshot?: Record<string, unknown>;
};
type DraftDirectory = { path: string; windows_path: string; source: string; exists: boolean };

function Auth({ initialized, done }: { initialized: boolean; done: (user: User) => void }) {
  const [setup, setSetup] = useState(!initialized);
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      if (setup) {
        await api("/auth/bootstrap", { method: "POST", body: JSON.stringify({ username, password }) }, false);
        setSetup(false); setPassword("");
      } else {
        const result = await api<{ token: string; user: User }>("/auth/login", {
          method: "POST", body: JSON.stringify({ username, password }),
        }, false);
        saveToken(result.token); done(result.user);
      }
    } catch (reason) { setError(reason instanceof Error ? reason.message : "操作失败"); }
    finally { setBusy(false); }
  }
  return <main className="human-auth"><form onSubmit={submit}>
    <div className="human-logo"><Film /> 本地视频生产工作台</div>
    <h1>{setup ? "初始化管理员" : "管理员登录"}</h1>
    <label>账号<input value={username} onChange={event => setUsername(event.target.value)} required /></label>
    <label>密码<input type="password" value={password} onChange={event => setPassword(event.target.value)} required minLength={setup ? 10 : 1} /></label>
    {error && <p className="human-error">{error}</p>}
    <button disabled={busy}>{busy && <LoaderCircle className="spin" />}{setup ? "完成初始化" : "登录"}</button>
  </form></main>;
}

const statusText: Record<string, string> = {
  active: "使用中", classified: "已归类", pending: "待审核", adopted: "已采纳",
  not_adopted: "未采纳", approved: "已确认", pending_review: "待确认", ready: "可使用",
  processing: "处理中", failed: "失败", generating: "生成中", disabled: "已停用",
};
function Pill({ value }: { value: string }) {
  return <span className={`human-pill ${value}`}>{statusText[value] ?? value}</span>;
}

function fuzzyScore(query: string, value: string) {
  const needle = query.trim().toLocaleLowerCase().replace(/\s+/g, "");
  const haystack = value.toLocaleLowerCase().replace(/\s+/g, "");
  if (!needle) return 1;
  if (haystack.includes(needle)) return 3 + needle.length / Math.max(1, haystack.length);
  const common = [...new Set(needle)].filter(char => haystack.includes(char)).length;
  return common / Math.max(new Set(needle).size, new Set(haystack).size, 1);
}

function fuzzyRows<T>(rows: T[], query: string, label: (item: T) => string, limit = 20) {
  return rows.map(item => ({ item, score: fuzzyScore(query, label(item)) }))
    .filter(row => !query.trim() || row.score >= 0.35)
    .sort((left, right) => right.score - left.score || label(left.item).localeCompare(label(right.item)))
    .slice(0, limit).map(row => row.item);
}

type DeleteConfirmation = { title: string; message: string; onConfirm: () => Promise<boolean | void> };
type TrackedOperationStatus = { operation_id: string; kind: string; status: "unknown" | "processing" | "completed" | "failed"; detail: string };

function usePersistentOperation(kind: "material_classification" | "copy_generation", onSettled: (status: TrackedOperationStatus) => void | Promise<void>) {
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

function ConfirmDeleteDialog({ confirmation, close }: { confirmation: DeleteConfirmation | null; close: () => void }) {
  const [deleting, setDeleting] = useState(false);
  if (!confirmation) return null;
  return <div className="confirm-dialog-backdrop" role="presentation">
    <section className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="confirm-delete-title">
      <div><b id="confirm-delete-title">{confirmation.title}</b><span>{confirmation.message}</span></div>
      <div><button type="button" className="human-secondary" disabled={deleting} onClick={close}>取消</button><button type="button" className="human-danger" disabled={deleting} onClick={async () => { setDeleting(true); try { const succeeded = await confirmation.onConfirm(); if (succeeded !== false) close(); } finally { setDeleting(false); } }}>{deleting ? <LoaderCircle className="spin" /> : null}确认删除</button></div>
    </section>
  </div>;
}

function ClassificationDropdown({ value, options, placeholder, disabled = false, onChange, onSelect }: {
  value: string;
  options: Array<{ id: string; name: string }>;
  placeholder: string;
  disabled?: boolean;
  onChange: (value: string) => void;
  onSelect: (item: { id: string; name: string }) => void;
}) {
  const [open, setOpen] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const rows = showAll ? options.slice(0, 50) : fuzzyRows(options, value, item => item.name, 50);
  return <div className="classification-combobox">
    <input value={value} placeholder={placeholder} disabled={disabled} autoComplete="off" onFocus={() => { setOpen(true); setShowAll(false); }} onChange={event => { onChange(event.target.value); setOpen(true); setShowAll(false); }} onBlur={() => {
      const exact = options.find(item => item.name.trim().toLocaleLowerCase() === value.trim().toLocaleLowerCase());
      if (exact) onSelect(exact);
      window.setTimeout(() => setOpen(false), 100);
    }} />
    <button type="button" className="classification-combobox-toggle human-secondary" aria-label="展开下拉列表" aria-expanded={open} disabled={disabled} onMouseDown={event => event.preventDefault()} onClick={() => { setShowAll(true); setOpen(current => !current || !showAll); }}><ChevronDown /></button>
    {open && <div className="classification-combobox-options">
      {rows.map(item => <button type="button" key={item.id} className={item.name === value ? "selected" : ""} onMouseDown={event => event.preventDefault()} onClick={() => { onSelect(item); setOpen(false); setShowAll(false); }}>{item.name}</button>)}
      {rows.length === 0 && <span>没有匹配项，可输入后单独保存</span>}
    </div>}
  </div>;
}

export default function HumanApp() {
  const [initialized, setInitialized] = useState<boolean | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [view, setView] = useState<View>("flow");
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
    ["models", "模型配置", Settings],
  ];
  return <div className={`human-shell ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
    <aside>
      <div className="human-brand"><Film /><span>视频生产工作台<small>Jianying Draft Workflow</small></span></div>
      <button type="button" className="human-sidebar-toggle" onClick={() => setSidebarCollapsed(value => !value)}>
        {sidebarCollapsed ? <PanelLeftOpen /> : <PanelLeftClose />}
      </button>
      <nav>{nav.map(([key, label, Icon]) => <button key={key} title={sidebarCollapsed ? label : undefined} className={view === key ? "active" : ""} onClick={() => setView(key)}><Icon /><span>{label}</span></button>)}</nav>
      <button className="human-logout" onClick={() => { clearToken(); setUser(null); }}><LogOut /><span>退出 {user.username}</span></button>
    </aside>
    <main>
      <header><div><small>本地项目 · 剪映草稿生产</small><h1>{nav.find(item => item[0] === view)?.[1]}</h1></div>
        <button className="human-secondary" onClick={refresh} disabled={loading}><RefreshCw className={loading ? "spin" : ""} />刷新</button>
      </header>
      {(error || notice) && <div className={error ? "human-banner error" : "human-banner success"} role={error ? "alert" : "status"} aria-live="polite">{error || notice}</div>}
      {view === "flow" && <Flow materials={materials} copies={copies} music={music} drafts={drafts} />}
      {view === "materials" && <Materials products={products} act={act} />}
      {view === "copy" && <CopyLibrary copies={copies} narrations={narrations} act={act} reload={refresh} />}
      {view === "music" && <MusicLibrary music={music} act={act} />}
      {view === "production" && <DraftProduction copies={copies} narrations={narrations} music={music} drafts={drafts} act={act} />}
      {view === "models" && <BusinessModelSettings onError={setError} onNotice={setNotice} />}
    </main>
  </div>;
}

function ProductManager({ products, act }: {
  products: Product[];
  act: (work: () => Promise<unknown>, success: string) => Promise<boolean>;
}) {
  const [name, setName] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState("");
  const [page, setPage] = useState(0);
  const [confirmation, setConfirmation] = useState<DeleteConfirmation | null>(null);
  const activeProducts = products.filter(item => item.status === "active");
  const visibleProducts = activeProducts;
  const pageProducts = visibleProducts.slice(page * 20, page * 20 + 20);

  async function create(event: FormEvent) {
    event.preventDefault();
    const nextName = name.trim();
    if (!nextName) return;
    await act(
      () => api("/products", { method: "POST", body: JSON.stringify({ name: nextName }) }),
      "产品名称已添加",
    );
    setName("");
  }

  async function saveName(product: Product) {
    const nextName = editingName.trim();
    if (!nextName || nextName === product.name) { setEditingId(null); return; }
    await act(
      () => api(`/products/${product.id}`, { method: "PATCH", body: JSON.stringify({ name: nextName }) }),
      "产品名称已更新",
    );
    setEditingId(null);
  }

  return <div className="human-card product-library-card">
      <div className="human-card-title"><h2>产品名称</h2><span>用于素材归类文件夹、文件名及剪映草稿归属</span></div>
      <div className="product-manager product-library-manager">
        <div className="product-manager-heading"><b>新增产品名称</b><span>名称不可重复，后续可以修改</span></div>
        <form onSubmit={create}>
          <input list="master-product-hints" value={name} onChange={event => setName(event.target.value)} placeholder="输入新名称或模糊查询已有产品" maxLength={160} required /><datalist id="master-product-hints">{fuzzyRows(activeProducts, name, item => item.name).map(item => <option key={item.id} value={item.name} />)}</datalist>
          <button>添加产品</button>
        </form>
      </div>
      <div className="product-library-summary">
        <span>共 {visibleProducts.length} 个产品</span>
      </div>
      <div className="product-manager-list product-library-list">
        {pageProducts.map(product => <div key={product.id}>
          <span>
            {editingId === product.id
              ? <input autoFocus value={editingName} maxLength={160} onChange={event => setEditingName(event.target.value)} onKeyDown={event => {
                if (event.key === "Escape") setEditingId(null);
                if (event.key === "Enter") { event.preventDefault(); saveName(product); }
              }} />
              : <b>{product.name || "未命名产品"}</b>}
            <small>{product.system_code} · {product.asset_count} 条素材</small>
          </span>
          <div>
            {editingId === product.id ? <>
              <button type="button" onClick={() => saveName(product)}>保存</button>
              <button type="button" className="human-secondary" onClick={() => setEditingId(null)}>取消</button>
            </> : <button type="button" className="human-secondary" onClick={() => { setEditingId(product.id); setEditingName(product.name); }}>改名</button>}
            <button type="button" className="human-secondary danger" onClick={() => setConfirmation({ title: `删除产品“${product.name || product.system_code}”？`, message: "将删除产品及其数据库关联，磁盘上的视频不会移动或改名。", onConfirm: async () => { await act(() => api(`/human/products/${product.id}`, { method: "DELETE" }), "产品已删除"); } })}>删除</button>
          </div>
        </div>)}
        {visibleProducts.length === 0 && <div className="product-library-empty">还没有产品名称，请先添加一个。</div>}
      </div>
      {visibleProducts.length > 20 && <div className="resource-pagination"><button className="human-secondary" disabled={page === 0} onClick={() => setPage(value => value - 1)}>上一页</button><span>{page + 1} / {Math.ceil(visibleProducts.length / 20)}</span><button className="human-secondary" disabled={(page + 1) * 20 >= visibleProducts.length} onClick={() => setPage(value => value + 1)}>下一页</button></div>}
      <ConfirmDeleteDialog confirmation={confirmation} close={() => setConfirmation(null)} />
  </div>;
}

function TagManager({ categories, tags, reload, act }: {
  categories: TagCategory[]; tags: Tag[]; reload: () => Promise<void>;
  act: (work: () => Promise<unknown>, success: string) => Promise<boolean>;
}) {
  const [categoryName, setCategoryName] = useState(""); const [tagName, setTagName] = useState("");
  const [categoryId, setCategoryId] = useState(""); const [page, setPage] = useState(0);
  const [editingCategory, setEditingCategory] = useState<string | null>(null); const [editingTag, setEditingTag] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [confirmation, setConfirmation] = useState<DeleteConfirmation | null>(null);
  const scopedTags = tags.filter(tag => !categoryId || tag.category_id === categoryId);
  const shown = scopedTags;
  const run = async (work: () => Promise<unknown>, message: string) => { await act(work, message); await reload(); };
  return <div className="master-tag-column">
    <div className="human-card"><div className="human-card-title"><h2>标签分类</h2><span>分类名称可手动输入、查询和选择</span></div>
      <form className="inline-library-form compact" onSubmit={event => { event.preventDefault(); run(() => api("/human/tag-categories", { method: "POST", body: JSON.stringify({ name: categoryName }) }), "标签分类已保存").then(() => setCategoryName("")); }}>
        <input list="master-category-hints" value={categoryName} onChange={event => setCategoryName(event.target.value)} placeholder="输入或查询标签分类" required /><datalist id="master-category-hints">{fuzzyRows(categories, categoryName, item => item.name).map(item => <option key={item.id} value={item.name} />)}</datalist><button>单独保存</button>
      </form>
      <div className="product-manager-list">{categories.slice(0, 20).map(item => <div key={item.id}><span>{editingCategory === item.id ? <input autoFocus value={editName} onChange={event => setEditName(event.target.value)} /> : <b>{item.name}</b>}<small>{tags.filter(tag => tag.category_id === item.id).length} 个标签</small></span><div>{editingCategory === item.id ? <button onClick={() => run(() => api(`/human/tag-categories/${item.id}`, { method: "PATCH", body: JSON.stringify({ name: editName }) }), "标签分类已修改").then(() => setEditingCategory(null))}>保存</button> : <button className="human-secondary" onClick={() => { setEditingCategory(item.id); setEditName(item.name); }}>修改</button>}<button className="human-secondary danger" onClick={() => setConfirmation({ title: `删除标签分类“${item.name}”？`, message: `将同时删除该分类下的 ${tags.filter(tag => tag.category_id === item.id).length} 个标签及视频标签关系。`, onConfirm: () => run(() => api(`/human/tag-categories/${item.id}`, { method: "DELETE" }), "标签分类及其标签已删除") })}>删除</button></div></div>)}</div>
    </div>
    <div className="human-card"><div className="human-card-title"><h2>标签名称</h2><span>同一名称可存在于不同分类</span></div>
      <form className="master-tag-create" onSubmit={event => { event.preventDefault(); run(() => api("/human/tags", { method: "POST", body: JSON.stringify({ category_id: categoryId, name: tagName }) }), "标签已保存").then(() => setTagName("")); }}>
        <select value={categoryId} onChange={event => { setCategoryId(event.target.value); setPage(0); }} required><option value="">选择标签分类</option>{categories.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
        <input list="master-tag-hints" value={tagName} onChange={event => setTagName(event.target.value)} placeholder="输入或查询标签名称" required /><datalist id="master-tag-hints">{fuzzyRows(tags.filter(item => item.category_id === categoryId), tagName, item => item.name).map(item => <option key={item.id} value={item.name} />)}</datalist><button disabled={!categoryId}>单独保存</button>
      </form>
      <div className="product-library-summary"><span>{categoryId ? `${categories.find(item => item.id === categoryId)?.name ?? ""}分类` : "全部分类"} · {shown.length} 个标签</span></div>
      <div className="product-manager-list">{shown.slice(page * 20, page * 20 + 20).map(tag => <div key={tag.id}><span>{editingTag === tag.id ? <input autoFocus value={editName} onChange={event => setEditName(event.target.value)} /> : <b>{tag.name}</b>}<small>{tag.category}</small></span><div>{editingTag === tag.id ? <button onClick={() => run(() => api(`/human/tags/${tag.id}`, { method: "PATCH", body: JSON.stringify({ name: editName }) }), "标签名称已修改").then(() => setEditingTag(null))}>保存</button> : <button className="human-secondary" onClick={() => { setEditingTag(tag.id); setEditName(tag.name); }}>修改</button>}<button className="human-secondary danger" onClick={() => setConfirmation({ title: `删除标签“${tag.name}”？`, message: `该标签属于“${tag.category}”，删除后将同时移除相关视频标签关系。`, onConfirm: () => run(() => api(`/human/tags/${tag.id}`, { method: "DELETE" }), "标签已删除") })}>删除</button></div></div>)}</div>
      {shown.length > 20 && <div className="resource-pagination"><button className="human-secondary" disabled={page === 0} onClick={() => setPage(value => value - 1)}>上一页</button><span>{page + 1} / {Math.ceil(shown.length / 20)}</span><button className="human-secondary" disabled={(page + 1) * 20 >= shown.length} onClick={() => setPage(value => value + 1)}>下一页</button></div>}
      <ConfirmDeleteDialog confirmation={confirmation} close={() => setConfirmation(null)} />
    </div>
  </div>;
}

function Flow({ materials, copies, music, drafts }: { materials: ClassifiedMaterial[]; copies: CopyItem[]; music: MusicResource[]; drafts: JianyingDraft[] }) {
  const steps = [
    ["1", "素材归类", "维护产品与标签，选择原视频后按产品和标签移动重命名，供后续在剪映中手动取用。"],
    ["2", "内容文库", "沉淀已采纳文案，使用音频转文案补充内容，并在旁白与字幕中按音色序号生成可用配音。"],
    ["3", "背景音乐", "上传本地音频或从短视频链接提取音频，试听后维护名称和自定义标签。"],
    ["4", "剪映草稿", "确认剪映草稿目录，选择文案、字幕/旁白和背景音乐，生成无视频轨道的半成品草稿。"],
    ["5", "剪映精修", "打开生成的草稿目录，在剪映专业版中添加视频、裁剪排列并完成后续编辑。"],
  ];
  return <section className="human-page">
    <div className="human-metrics">
      <article><b>{materials.length}</b><span>已归类原视频</span></article>
      <article><b>{copies.length}</b><span>可用内容</span></article>
      <article><b>{music.filter(item => item.status === "ready").length}</b><span>可用背景音乐</span></article>
      <article><b>{drafts.filter(item => item.status === "ready").length}</b><span>剪映草稿</span></article>
    </div>
    <div className="human-card"><div className="human-card-title"><h2>当前生产流程</h2><span>按模块准备物料并生成剪映半成品草稿</span></div>
      <div className="human-flow">{steps.map(([number, title, detail]) => <article key={number}><i>{number}</i><div><b>{title}</b><span>{detail}</span></div></article>)}</div>
    </div>
  </section>;
}

function Materials({ products, act }: { products: Product[]; act: (work: () => Promise<unknown>, success: string) => Promise<boolean> }) {
  const activeProducts = products.filter(item => item.status === "active");
  const [tab, setTab] = useState<"master" | "classify">("classify");
  const [productId, setProductId] = useState(0); const [productInput, setProductInput] = useState("");
  const [sourceDir, setSourceDir] = useState(""); const [videos, setVideos] = useState<SourceVideo[]>([]);
  const [tags, setTags] = useState<Tag[]>([]); const [categories, setCategories] = useState<TagCategory[]>([]);
  const [selectedTags, setSelectedTags] = useState<Record<string, string[]>>({}); const [selectedVideos, setSelectedVideos] = useState<string[]>([]);
  const [categoryId, setCategoryId] = useState(""); const [categoryInput, setCategoryInput] = useState(""); const [tagInput, setTagInput] = useState("");
  const [selecting, setSelecting] = useState(false);
  const [classificationResult, setClassificationResult] = useState<ClassifiedMaterial[]>([]);
  const [classificationMessage, setClassificationMessage] = useState("");
  const classificationOperation = usePersistentOperation("material_classification", state => {
    setClassificationMessage(state.status === "completed" ? (state.detail || "原视频归类已完成。") : `原视频归类未完成：${state.detail}`);
  });
  const loadMaster = useCallback(async () => {
    const [categoryRows, tagRows] = await Promise.all([api<{ items: TagCategory[] }>("/human/tag-categories?limit=5000"), api<{ items: Tag[] }>("/human/tags?limit=5000")]);
    setCategories(categoryRows.items); setTags(tagRows.items);
  }, []);
  useEffect(() => { loadMaster().catch(() => { setCategories([]); setTags([]); }); }, [loadMaster]);
  async function chooseVideos() {
    setSelecting(true);
    try {
      const result = await api<{ path: string; cancelled: boolean; videos: SourceVideo[] }>("/human/source-directory/select", { method: "POST", body: JSON.stringify({ initial_path: sourceDir }) });
      if (!result.cancelled) { setSourceDir(result.path); setVideos(result.videos); setSelectedTags({}); setSelectedVideos([]); }
    } finally { setSelecting(false); }
  }
  function toggleVideo(path: string) { setSelectedVideos(value => value.includes(path) ? value.filter(item => item !== path) : [...value, path]); }
  function toggleTag(tagId: string) {
    if (!selectedVideos.length) return;
    const selectedTag = tags.find(item => item.id === tagId);
    if (!selectedTag) return;
    setSelectedTags(value => {
      const allHave = selectedVideos.every(path => (value[path] ?? []).includes(tagId));
      const next = { ...value };
      selectedVideos.forEach(path => {
        const current = next[path] ?? [];
        const otherCategories = current.filter(id => tags.find(item => item.id === id)?.category_id !== selectedTag.category_id);
        next[path] = allHave ? otherCategories : [...otherCategories, tagId];
      });
      return next;
    });
  }
  const ready = productId > 0 && videos.length > 0 && videos.every(video => (selectedTags[video.path] ?? []).length > 0);
  async function classify() {
    const operationId = classificationOperation.begin();
    if (!operationId) return;
    let completed = false;
    let movedAssets: ClassifiedMaterial[] = [];
    await act(() => api<{ assets: ClassifiedMaterial[] }>("/human/material-classifications", {
      method: "POST", headers: { "X-Operation-Id": operationId }, body: JSON.stringify({
        product_id: productId, source_dir: sourceDir,
        items: videos.map(video => ({ source_path: video.path, tag_ids: selectedTags[video.path] ?? [] })),
      }),
    }).then(value => { movedAssets = value.assets; completed = true; return value; }), "");
    classificationOperation.clear(operationId);
    if (completed) {
      setClassificationMessage("");
      setClassificationResult(movedAssets); setVideos([]); setSelectedTags({}); setSelectedVideos([]);
    }
  }
  const productMatches = fuzzyRows(activeProducts, productInput, item => item.name);
  const availableCategoryTags = tags.filter(item => item.category_id === categoryId);
  const categoryTags = fuzzyRows(availableCategoryTags, tagInput, item => item.name);
  const saveProduct = async () => { const value = productInput.trim(); if (!value) return; await act(() => api("/products", { method: "POST", body: JSON.stringify({ name: value }) }), "产品名称已单独保存"); setProductInput(""); setProductId(0); };
  const saveCategory = async () => { const value = categoryInput.trim(); if (!value) return; await act(() => api("/human/tag-categories", { method: "POST", body: JSON.stringify({ name: value }) }), "标签分类已单独保存"); await loadMaster(); setCategoryInput(""); setCategoryId(""); };
  const saveTag = async () => { const value = tagInput.trim(); if (!value || !categoryId) return; await act(() => api("/human/tags", { method: "POST", body: JSON.stringify({ category_id: categoryId, name: value }) }), "标签已单独保存"); await loadMaster(); setTagInput(""); };
  return <section className="human-page material-classification-page">
    <div className="material-tabs full"><button className={tab === "master" ? "active" : ""} onClick={() => setTab("master")}>产品与标签管理</button><button className={tab === "classify" ? "active" : ""} onClick={() => setTab("classify")}>素材归类</button></div>
    {tab === "master" && <>
      <div className="master-data-layout full"><ProductManager products={products} act={act} /><TagManager categories={categories} tags={tags} reload={loadMaster} act={act} /></div>
    </>}
    {tab === "classify" && <>
      {classificationMessage && <div className="human-note classification-result-note full" role="status"><Boxes /><div><b>归类操作状态</b><span>{classificationMessage}</span></div></div>}
      {classificationResult.length > 0 && <div className="human-note classification-result-note full"><Boxes /><div><b>本次归类成功</b><span>{classificationResult[0].product_name} · 已移动并重命名 {classificationResult.length} 个原视频</span><small title={classificationResult.map(item => item.filename).join("、")}>{classificationResult.map(item => item.filename).join("、")}</small></div></div>}
      <div className="human-card full"><div className="human-card-title"><h2>产品名称与视频</h2></div>
        <div className="classification-master-inputs">
          <label>产品名称<div><input list="classify-product-hints" value={productInput} onChange={event => { setProductInput(event.target.value); setProductId(0); }} onBlur={() => { const match = activeProducts.find(item => item.name === productInput.trim()); if (match) setProductId(match.id); }} placeholder="输入可模糊查询" /><datalist id="classify-product-hints">{productMatches.map(item => <option key={item.id} value={item.name} />)}</datalist><button className="human-secondary" onMouseDown={event => event.preventDefault()} onClick={saveProduct}>新增并保存</button></div><small>{productId ? `已选择：${activeProducts.find(item => item.id === productId)?.name}` : "请选择已保存的产品"}</small></label>
          <label>选择视频<div className="source-directory-field"><input value={sourceDir} readOnly placeholder="选择同一产品的一组视频" /><button type="button" className="human-secondary" disabled={selecting} onClick={chooseVideos}>{selecting ? <LoaderCircle className="spin" /> : <FolderOpen />}{selecting ? "等待窗口" : "选择视频"}</button></div><small>{videos.length > 0 ? `已选择 ${videos.length} 个视频` : "请选择同一产品的一组视频"}</small></label>
        </div>
      </div>
      <div className="human-card full"><div className="human-card-title"><h2>批量选择与打标签</h2><span>未打标签的视频不能归类</span></div>
        <div className="classification-toolbar"><button className="human-secondary" onClick={() => setSelectedVideos(videos.map(item => item.path))}>全选</button><button className="human-secondary" onClick={() => setSelectedVideos([])}>取消全选</button><span>已选择 {selectedVideos.length}/{videos.length} 个视频</span></div>
        <div className="classification-tag-inputs">
          <label>标签分类<div><ClassificationDropdown value={categoryInput} options={categories} placeholder="输入可模糊查询，或展开列表" onChange={value => { setCategoryInput(value); setCategoryId(""); setTagInput(""); }} onSelect={item => { setCategoryInput(item.name); setCategoryId(item.id); setTagInput(""); }} /><button className="human-secondary" onMouseDown={event => event.preventDefault()} onClick={saveCategory}>新增并保存</button></div></label>
          <label>标签名称<div><ClassificationDropdown value={tagInput} options={availableCategoryTags} placeholder={categoryId ? "输入可模糊查询，或展开列表" : "先选择标签分类"} disabled={!categoryId} onChange={setTagInput} onSelect={item => setTagInput(item.name)} /><button className="human-secondary" onClick={saveTag} disabled={!categoryId}>新增并保存</button></div></label>
        </div>
        <div className="tag-picker classification-tags">{categoryId && categoryTags.map(tag => { const count = selectedVideos.filter(path => (selectedTags[path] ?? []).includes(tag.id)).length; return <button type="button" key={tag.id} disabled={!selectedVideos.length} className={count === selectedVideos.length && count > 0 ? "on" : count > 0 ? "partial" : ""} onClick={() => toggleTag(tag.id)}>{tag.name}{count > 0 && <small>{count}/{selectedVideos.length}</small>}</button>; })}</div>
        {videos.length > 0 && <div className="classification-video-list">{videos.map(video => <article key={video.path} className={selectedVideos.includes(video.path) ? "selected" : ""} onClick={() => toggleVideo(video.path)}><input type="checkbox" checked={selectedVideos.includes(video.path)} onChange={() => toggleVideo(video.path)} onClick={event => event.stopPropagation()} /><div><b>{video.name}</b><small>{video.relative_path}</small><div className="video-applied-tags">{(selectedTags[video.path] ?? []).map(id => tags.find(item => item.id === id)).filter(Boolean).map(tag => <span key={tag!.id}>{tag!.category} / {tag!.name}</span>)}{!(selectedTags[video.path] ?? []).length && <em>未打标签</em>}</div></div></article>)}</div>}
        <button type="button" className="human-wide" disabled={!ready || classificationOperation.busy} onClick={classify}>{classificationOperation.busy && <LoaderCircle className="spin" />}{classificationOperation.busy ? "正在校验、移动并重命名原视频…" : `确认归类并移动 ${videos.length || ""} 个原视频`}</button>
        {classificationOperation.busy && <div className="copy-generation-progress" role="status" aria-live="polite"><LoaderCircle className="spin" /><div><b>原视频归类正在执行</b><span>刷新页面后仍会保持此状态，完成前请勿重复提交或移动这些文件。</span></div></div>}
      </div>
    </>}
  </section>;
}

function CopyLibrary({ copies, narrations, act, reload }: {
  copies: CopyItem[]; narrations: Narration[];
  act: (work: () => Promise<unknown>, success: string) => Promise<boolean>;
  reload: () => Promise<void>;
}) {
  const [tab, setTab] = useState<"copies" | "voices" | "narrations">("copies");
  const [reference, setReference] = useState("");
  const [activeRecord, setActiveRecord] = useState<CopyAnalysis | null>(null);
  const [history, setHistory] = useState<CopyAnalysis[]>([]); const [historyTotal, setHistoryTotal] = useState(0); const [historyPage, setHistoryPage] = useState(1);
  const [generationError, setGenerationError] = useState(""); const [generationNotice, setGenerationNotice] = useState("");
  const [narrationText, setNarrationText] = useState(""); const [selectedCopyId, setSelectedCopyId] = useState("");
  const [copySearch, setCopySearch] = useState(""); const [copySearchOpen, setCopySearchOpen] = useState(false); const [copySearchBusy, setCopySearchBusy] = useState(false); const [copySuggestions, setCopySuggestions] = useState<CopyItem[]>([]); const [selectedNarrationCopy, setSelectedNarrationCopy] = useState<CopyItem | null>(null);
  const [narrationBusy, setNarrationBusy] = useState(false); const [narrationError, setNarrationError] = useState("");
  const [transcriptionLink, setTranscriptionLink] = useState(""); const [transcriptionFile, setTranscriptionFile] = useState<File | null>(null); const [transcriptionText, setTranscriptionText] = useState(""); const [transcriptionBusy, setTranscriptionBusy] = useState(false); const [transcriptionError, setTranscriptionError] = useState("");
  const [previewingVoice, setPreviewingVoice] = useState(""); const [previewLoading, setPreviewLoading] = useState(false); const [voicePreviewError, setVoicePreviewError] = useState("");
  const [voiceSequenceInput, setVoiceSequenceInput] = useState(""); const [selectedCatalogVoice, setSelectedCatalogVoice] = useState<VoiceCatalogItem | null>(null); const [voiceSequenceError, setVoiceSequenceError] = useState("");
  const [voiceCatalog, setVoiceCatalog] = useState<VoiceCatalogItem[]>([]); const [voiceCatalogTotal, setVoiceCatalogTotal] = useState(0); const [voiceCatalogPage, setVoiceCatalogPage] = useState(1); const [voiceCatalogQuery, setVoiceCatalogQuery] = useState(""); const [voiceCatalogGender, setVoiceCatalogGender] = useState(""); const [voiceCatalogAge, setVoiceCatalogAge] = useState(""); const [voiceCatalogScenario, setVoiceCatalogScenario] = useState("");
  const [voiceCatalogGenders, setVoiceCatalogGenders] = useState<string[]>([]); const [voiceCatalogAges, setVoiceCatalogAges] = useState<string[]>([]); const [voiceCatalogScenarios, setVoiceCatalogScenarios] = useState<string[]>([]);
  const voicePlayerRef = useRef<HTMLAudioElement | null>(null); const voiceAudioUrlRef = useRef(""); const voicePreviewRequestRef = useRef(0);
  const [playingNarrationId, setPlayingNarrationId] = useState(""); const narrationPlayerRef = useRef<HTMLAudioElement | null>(null); const narrationAudioUrlRef = useRef("");
  const [editingCopyId, setEditingCopyId] = useState<string | null>(null); const [editingCopy, setEditingCopy] = useState("");
  const [hiddenCopyIds, setHiddenCopyIds] = useState<string[]>([]);
  const [confirmation, setConfirmation] = useState<DeleteConfirmation | null>(null);
  const visibleCopies = copies.filter(item => !hiddenCopyIds.includes(item.id));
  useEffect(() => { setHiddenCopyIds(ids => ids.filter(id => copies.some(item => item.id === id))); }, [copies]);
  useEffect(() => {
    if (!copySearchOpen || narrationBusy) return undefined;
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setCopySearchBusy(true);
      try {
        const params = new URLSearchParams({ search: copySearch.trim(), limit: "10" });
        const result = await api<{ items: CopyItem[] }>(`/human/copies/library?${params}`);
        if (!cancelled) setCopySuggestions(result.items);
      } catch { if (!cancelled) setCopySuggestions([]); }
      finally { if (!cancelled) setCopySearchBusy(false); }
    }, 220);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [copySearch, copySearchOpen, narrationBusy]);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams({ page: String(voiceCatalogPage), page_size: "20" });
      if (voiceCatalogQuery.trim()) params.set("q", voiceCatalogQuery.trim());
      if (voiceCatalogGender) params.set("gender", voiceCatalogGender);
      if (voiceCatalogAge) params.set("age", voiceCatalogAge);
      if (voiceCatalogScenario) params.set("scenario", voiceCatalogScenario);
      api<{ total: number; items: VoiceCatalogItem[]; genders?: string[]; ages?: string[]; scenarios?: string[] }>(`/human/voice-catalog?${params}`).then(value => { setVoiceCatalog(value.items); setVoiceCatalogTotal(value.total); setVoiceCatalogGenders(value.genders ?? ["女", "男"]); setVoiceCatalogAges(value.ages ?? []); setVoiceCatalogScenarios(value.scenarios ?? []); }).catch(() => { setVoiceCatalog([]); setVoiceCatalogTotal(0); });
    }, 250);
    return () => window.clearTimeout(timer);
  }, [voiceCatalogPage, voiceCatalogQuery, voiceCatalogGender, voiceCatalogAge, voiceCatalogScenario]);
  useEffect(() => {
    setSelectedCatalogVoice(null); setVoiceSequenceError("");
    const raw = voiceSequenceInput.trim();
    if (!raw) return undefined;
    if (!/^\d+$/.test(raw)) { setVoiceSequenceError("请输入 1 至 597 的整数序号"); return undefined; }
    const timer = window.setTimeout(() => {
      api<VoiceCatalogItem>(`/human/voice-catalog/${Number(raw)}`).then(item => { setSelectedCatalogVoice(item); setVoiceSequenceError(""); setVoicePreviewError(""); stopVoicePreview(); }).catch(reason => { setSelectedCatalogVoice(null); setVoiceSequenceError(reason instanceof Error ? reason.message : "音色序号不存在"); });
    }, 250);
    return () => window.clearTimeout(timer);
  }, [voiceSequenceInput]);
  function stopVoicePreview(updateState = true) {
    voicePreviewRequestRef.current += 1;
    if (voicePlayerRef.current) { voicePlayerRef.current.pause(); voicePlayerRef.current.currentTime = 0; voicePlayerRef.current = null; }
    if (voiceAudioUrlRef.current) { URL.revokeObjectURL(voiceAudioUrlRef.current); voiceAudioUrlRef.current = ""; }
    if (updateState) { setPreviewingVoice(""); setPreviewLoading(false); }
  }
  useEffect(() => () => stopVoicePreview(false), []);
  async function previewVoice(targetVoice: string, voiceSequence: number) {
    if (previewingVoice === targetVoice && !previewLoading) { stopVoicePreview(); return; }
    stopVoicePreview();
    const requestId = voicePreviewRequestRef.current;
    setPreviewingVoice(targetVoice); setPreviewLoading(true); setVoicePreviewError("");
    try {
      const blob = await apiBlob("/human/voice-preview", { method: "POST", body: JSON.stringify({ voice_sequence: voiceSequence }) });
      if (requestId !== voicePreviewRequestRef.current) return;
      const url = URL.createObjectURL(blob); const player = new Audio(url);
      voiceAudioUrlRef.current = url; voicePlayerRef.current = player; setPreviewLoading(false);
      player.onended = () => { if (voicePlayerRef.current === player) stopVoicePreview(); };
      await player.play();
    } catch (reason) {
      if (requestId === voicePreviewRequestRef.current) { stopVoicePreview(); setVoicePreviewError(reason instanceof Error ? reason.message : "音色试听失败"); }
    }
  }
  function stopNarration(updateState = true) {
    if (narrationPlayerRef.current) { narrationPlayerRef.current.pause(); narrationPlayerRef.current.currentTime = 0; narrationPlayerRef.current = null; }
    if (narrationAudioUrlRef.current) { URL.revokeObjectURL(narrationAudioUrlRef.current); narrationAudioUrlRef.current = ""; }
    if (updateState) setPlayingNarrationId("");
  }
  useEffect(() => () => stopNarration(false), []);
  async function listenNarration(item: Narration) {
    if (playingNarrationId === item.id) { stopNarration(); return; }
    stopNarration(); stopVoicePreview(); setPlayingNarrationId(item.id);
    try {
      const blob = await apiBlob(`/human/narrations/${item.id}/audio`); const url = URL.createObjectURL(blob); const player = new Audio(url);
      narrationAudioUrlRef.current = url; narrationPlayerRef.current = player;
      player.onended = () => { if (narrationPlayerRef.current === player) stopNarration(); };
      await player.play();
    } catch { stopNarration(); }
  }
  const loadHistory = useCallback(async (page: number) => {
    const result = await api<{ total: number; items: CopyAnalysis[] }>(`/human/copies/iterations?page=${page}&page_size=10`);
    setHistory(result.items); setHistoryTotal(result.total);
    return result;
  }, []);
  const generationOperation = usePersistentOperation("copy_generation", async state => {
    if (state.status === "completed") {
      const result = await loadHistory(1);
      setHistoryPage(1);
      setActiveRecord(result.items[0] ?? null);
      setGenerationNotice(state.detail || "文案生成已完成。");
      await reload();
    } else {
      setGenerationError(state.detail || "文案分析与生成未完成");
    }
  });
  useEffect(() => { loadHistory(historyPage).catch(() => undefined); }, [historyPage, loadHistory]);
  function replaceRecord(record: CopyAnalysis) {
    setActiveRecord(record); setHistory(rows => rows.map(item => item.id === record.id ? record : item));
  }
  async function generateCopies(event: FormEvent) {
    event.preventDefault();
    const operationId = generationOperation.begin();
    if (!operationId) return;
    setGenerationError(""); setGenerationNotice(""); setActiveRecord(null);
    try {
      const record = await api<CopyAnalysis>("/human/copies/iterations", { method: "POST", headers: { "X-Operation-Id": operationId }, body: JSON.stringify({ reference_text: reference }) });
      setActiveRecord(record); setHistoryPage(1); await Promise.all([loadHistory(1), reload()]);
    } catch (reason) {
      setGenerationError(reason instanceof Error ? reason.message : "文案分析与生成失败");
    } finally { generationOperation.clear(operationId); }
  }
  async function review(record: CopyAnalysis, item: CopyCandidate, status: "adopted" | "not_adopted") {
    let reason = "";
    if (status === "not_adopted") { reason = window.prompt("请填写不采纳原因，后续迭代会据此改进")?.trim() ?? ""; if (!reason) return; }
    const ok = await act(() => api(`/human/copies/${item.id}/review`, { method: "PATCH", body: JSON.stringify({ status, reason }) }), status === "adopted" ? "文案已采纳并加入内容文库" : "已记录不采纳原因");
    if (!ok) return;
    replaceRecord({ ...record, batches: record.batches.map(batch => ({ ...batch, copies: batch.copies.map(copy => copy.id === item.id ? { ...copy, status, rejection_reason: reason } : copy) })) });
  }
  async function continueIteration(record: CopyAnalysis) {
    const operationId = generationOperation.begin();
    if (!operationId) return;
    setGenerationError(""); setGenerationNotice("");
    try { const updated = await api<CopyAnalysis>(`/human/copies/iterations/${record.id}/continue`, { method: "POST", headers: { "X-Operation-Id": operationId } }); replaceRecord(updated); await loadHistory(historyPage); }
    catch (reason) { setGenerationError(reason instanceof Error ? reason.message : "继续迭代失败"); }
    finally { generationOperation.clear(operationId); }
  }
  function AnalysisView({ record }: { record: CopyAnalysis }) {
    const latest = record.batches[record.batches.length - 1];
    const pending = latest?.copies.some(item => item.status === "pending") ?? true;
    const labels: Record<string, string> = { language_style: "语言风格", word_preference: "用词偏好", emotional_tone: "情感基调", appeal_focus: "诉求重点", age: "年龄", gender: "性别", interests: "兴趣", spending_level: "消费水平", psychological_state: "心理状态" };
    return <>
      <div className="copy-analysis-grid"><article><h3>文案感官分析</h3>{Object.entries(record.language_analysis).map(([key, value]) => <p key={key}><b>{labels[key] ?? key}</b><span>{value}</span></p>)}</article><article><h3>目标受众推断</h3>{Object.entries(record.audience_analysis).map(([key, value]) => <p key={key}><b>{labels[key] ?? key}</b><span>{value}</span></p>)}</article><article><h3>模型专家角色</h3><p><span>{record.expert_role}</span></p></article></div>
      <div className="copy-batches">{record.batches.map(batch => <section key={batch.id}><div className="human-card-title"><h3>第 {batch.sequence_number} 轮迭代</h3><span>5 条分别审核</span></div>{batch.copies.map((item, index) => <article className="copy-candidate" key={item.id}><div><small>{index + 1}</small><b>{item.content}</b>{item.rejection_reason && <em>不采纳原因：{item.rejection_reason}</em>}</div><div>{item.status === "pending" ? <><button onClick={() => review(record, item, "adopted")}>采纳</button><button className="human-secondary" onClick={() => review(record, item, "not_adopted")}>不采纳</button></> : <Pill value={item.status} />}</div></article>)}</section>)}</div>
      <button type="button" className="human-wide" disabled={generationOperation.busy || pending} onClick={() => continueIteration(record)}>{generationOperation.busy ? <LoaderCircle className="spin" /> : <Sparkles />}{pending ? "请先审核本轮全部文案" : generationOperation.busy ? "正在继续迭代 5 条…" : "继续迭代 5 条"}</button>
    </>;
  }
  async function transcribeToCopy(event: FormEvent) {
    event.preventDefault(); setTranscriptionBusy(true); setTranscriptionError("");
    const form = new FormData();
    if (transcriptionFile) form.append("media", transcriptionFile);
    else form.append("share_url", transcriptionLink.trim());
    try {
      const result = await api<{ text: string }>("/human/copies/audio-to-text", { method: "POST", body: form });
      setTranscriptionText(result.text);
    } catch (reason) { setTranscriptionError(reason instanceof Error ? reason.message : "音频转文案失败"); }
    finally { setTranscriptionBusy(false); }
  }
  async function generateNarration() {
    if (narrationBusy || !narrationText.trim() || !selectedCatalogVoice) return;
    setNarrationBusy(true); setNarrationError("");
    try {
      const success = await act(() => api("/human/narrations/model-voice", { method: "POST", body: JSON.stringify({ approved_text: narrationText.trim(), text_source: selectedCopyId ? "model" : "human", voice_sequence: selectedCatalogVoice.sequence }) }), "旁白配音已生成");
      if (!success) setNarrationError("旁白配音生成失败，请查看页面上方的错误提示。");
    } finally { setNarrationBusy(false); }
  }
  return <section className="human-page copy-library-page">
    <div className="material-tabs copy-library-tabs full"><button className={tab === "copies" ? "active" : ""} onClick={() => setTab("copies")}>文案（{copies.length}）</button><button className={tab === "voices" ? "active" : ""} onClick={() => setTab("voices")}>音色库（597）</button><button className={tab === "narrations" ? "active" : ""} onClick={() => setTab("narrations")}>旁白与字幕（{narrations.length}）</button></div>
    {tab === "copies" && <>
      <div className="human-card full"><div className="human-card-title"><h2>音频转文案</h2><span>抖音短链接、本地视频或本地音频</span></div>
        <form className="human-form audio-to-copy-form" onSubmit={transcribeToCopy}><label>抖音视频短链接<textarea value={transcriptionLink} disabled={transcriptionBusy || Boolean(transcriptionFile)} onChange={event => setTranscriptionLink(event.target.value)} placeholder="粘贴抖音分享内容或短链接；与本地文件二选一" /></label><label>本地视频或音频<input type="file" accept="audio/*,video/*" disabled={transcriptionBusy || Boolean(transcriptionLink.trim())} onChange={event => setTranscriptionFile(event.target.files?.[0] ?? null)} /></label><button disabled={transcriptionBusy || (!transcriptionLink.trim() && !transcriptionFile)}>{transcriptionBusy ? <LoaderCircle className="spin" /> : <Upload />}{transcriptionBusy ? "正在转换…" : "转换成文案"}</button>{transcriptionBusy && <div className="copy-generation-progress" role="status" aria-live="polite"><LoaderCircle className="spin" /><div><b>音频正在转换为文案</b><span>系统正在提取音频并调用语音识别模型，完成前请勿重复提交。</span></div></div>}</form>
        {transcriptionError && <div className="copy-generation-progress error" role="alert"><div><b>转换失败</b><span>{transcriptionError}</span></div></div>}
        {transcriptionText && <div className="human-form transcribed-copy-editor"><label>转换结果<textarea value={transcriptionText} onChange={event => setTranscriptionText(event.target.value)} /><small>可修改后保存到内容文库。</small></label><button disabled={!transcriptionText.trim()} onClick={() => act(() => api("/human/copies", { method: "POST", body: JSON.stringify({ content: transcriptionText.trim(), product_id: null }) }), "转换文案已保存到内容文库").then(ok => { if (ok) { setTranscriptionText(""); setTranscriptionLink(""); setTranscriptionFile(null); } })}>保存到内容文库</button></div>}
      </div>
      <div className="human-card full"><div className="human-card-title"><h2>文案分析与迭代</h2><span>自动分析后一次生成 5 条</span></div>
        <form className="human-form copy-generation-form" onSubmit={generateCopies}><label>参考文案<textarea value={reference} onChange={event => setReference(event.target.value)} placeholder="粘贴一条短标题或长口播稿；留空时将根据全局已采纳文案推荐" disabled={generationOperation.busy} /><small>输入内容会自动作为已采纳文案保存；模型保持内容类型和大致长度。</small></label><button disabled={generationOperation.busy}>{generationOperation.busy ? <LoaderCircle className="spin" /> : <Sparkles />}{generationOperation.busy ? "正在分析并生成 5 条…" : reference.trim() ? "分析并迭代 5 条" : "根据已采纳文案推荐"}</button></form>
        {generationOperation.busy && <div className="copy-generation-progress" role="status" aria-live="polite"><LoaderCircle className="spin" /><div><b>正在分析语言、受众和专家角色</b><span>刷新页面后仍会保持此状态；分析完成后自动生成 5 条文案，请勿重复提交。</span></div></div>}
        {generationNotice && <div className="copy-generation-progress" role="status"><div><b>生成完成</b><span>{generationNotice}</span></div></div>}
        {generationError && <div className="copy-generation-progress error" role="alert"><div><b>生成失败</b><span>{generationError}</span></div></div>}
      </div>
      <div className="human-card full"><div className="human-card-title"><h2>分析与迭代记录</h2><span>最新在前，每页 10 条</span></div><div className="copy-history-list">{history.map(item => <div className={`copy-history-entry ${activeRecord?.id === item.id ? "expanded" : ""}`} key={item.id}><article><div><b>{item.source_mode === "input" ? item.source_text : "根据全局已采纳文案推荐"}</b><span>{new Date(item.created_at).toLocaleString()} · {item.batches.length} 轮</span><small>{item.expert_role}</small></div><div><button className="human-secondary" aria-expanded={activeRecord?.id === item.id} onClick={() => setActiveRecord(current => current?.id === item.id ? null : item)}>{activeRecord?.id === item.id ? "收起" : "查看"}</button><button className="human-secondary danger" onClick={() => setConfirmation({ title: "删除这条分析与迭代记录？", message: "只删除分析、专家角色和迭代过程；已进入内容文库的原文和采纳文案会保留。", onConfirm: async () => { const ok = await act(() => api(`/human/copies/iterations/${item.id}`, { method: "DELETE" }), "分析与迭代记录已删除"); if (ok) { if (activeRecord?.id === item.id) setActiveRecord(null); await loadHistory(historyPage); } } })}>删除</button></div></article>{activeRecord?.id === item.id && <section className="copy-history-detail"><AnalysisView record={activeRecord} /></section>}</div>)}</div><div className="resource-pagination"><span>共 {historyTotal} 条，第 {historyPage} 页</span><div><button className="human-secondary" disabled={historyPage <= 1} onClick={() => setHistoryPage(value => value - 1)}>上一页</button><button className="human-secondary" disabled={historyPage * 10 >= historyTotal} onClick={() => setHistoryPage(value => value + 1)}>下一页</button></div></div></div>
      <div className="human-card full"><div className="human-card-title"><h2>文案内容</h2><span>{visibleCopies.length} 条</span></div>
        <div className="simple-resource-list copy-library-list">{visibleCopies.map(item => <article key={item.id}><div>{editingCopyId === item.id ? <textarea autoFocus value={editingCopy} onChange={event => setEditingCopy(event.target.value)} /> : <b>{item.content}</b>}<span>{item.product_name || "全局通用"} · {item.source === "model" ? "模型生成" : item.source === "original" ? "参考原文" : "人工录入"}</span></div><div>{editingCopyId === item.id ? <><button className="human-secondary" onClick={() => setEditingCopyId(null)}>取消</button><button disabled={!editingCopy.trim()} onClick={() => act(() => api(`/human/copies/${item.id}`, { method: "PUT", body: JSON.stringify({ content: editingCopy.trim(), product_id: item.product_id }) }), "文案已修改").then(ok => { if (ok) setEditingCopyId(null); })}>保存</button></> : <><button className="human-secondary" onClick={() => { setEditingCopyId(item.id); setEditingCopy(item.content); }}>修改</button><button className="human-secondary danger" onClick={() => setConfirmation({ title: "删除这条文案？", message: "文案将从当前内容文库移除；已经生成的剪映草稿仍保留创建时冻结的内容。", onConfirm: async () => { const ok = await act(() => api(`/human/copies/${item.id}`, { method: "DELETE" }), "文案已删除"); if (ok) setHiddenCopyIds(ids => [...ids, item.id]); return ok; } })}>删除</button></>}</div></article>)}</div>
        <ConfirmDeleteDialog confirmation={confirmation} close={() => setConfirmation(null)} />
      </div>
    </>}
    {tab === "voices" && <>
      <div className="human-card full voice-catalog-card"><div className="human-card-title"><h2>音色库</h2><span>qwen-audio-3.0-tts-plus · 官方 597 条基础音色</span></div><div className="voice-catalog-toolbar"><input value={voiceCatalogQuery} onChange={event => { setVoiceCatalogQuery(event.target.value); setVoiceCatalogPage(1); }} placeholder="查询序号、名称、voice 参数、特质、语种或预览文件名" /><select value={voiceCatalogGender} onChange={event => { setVoiceCatalogGender(event.target.value); setVoiceCatalogPage(1); }}><option value="">全部性别</option>{voiceCatalogGenders.map(value => <option key={value} value={value}>{value}</option>)}</select><select value={voiceCatalogAge} onChange={event => { setVoiceCatalogAge(event.target.value); setVoiceCatalogPage(1); }}><option value="">全部年龄</option>{voiceCatalogAges.map(value => <option key={value} value={value}>{value} 岁</option>)}</select><select value={voiceCatalogScenario} onChange={event => { setVoiceCatalogScenario(event.target.value); setVoiceCatalogPage(1); }}><option value="">全部适用场景</option>{voiceCatalogScenarios.map(value => <option key={value} value={value}>{value}</option>)}</select></div><div className="voice-catalog-table-wrap"><table className="voice-catalog-table"><thead><tr><th>序号</th><th>名称</th><th>voice 参数</th><th>性别</th><th>年龄</th><th>特质</th><th>适用场景</th><th>音色试听</th></tr></thead><tbody>{voiceCatalog.map(item => <tr key={item.sequence}><td>{item.sequence}</td><td>{item.name}</td><td><code>{item.voice}</code></td><td>{item.gender}</td><td>{item.age}</td><td>{item.trait}</td><td>{item.scenario}</td><td><button type="button" className="human-secondary" disabled={previewLoading} onClick={() => previewVoice(item.voice, item.sequence)}>{previewLoading && previewingVoice === item.voice ? <LoaderCircle className="spin" /> : <Volume2 />}{previewingVoice === item.voice && !previewLoading ? "停止" : previewLoading && previewingVoice === item.voice ? "准备中" : item.preview_ready ? "试听" : "生成试听"}</button></td></tr>)}</tbody></table></div>{voicePreviewError && <div className="copy-generation-progress error" role="alert"><div><b>试听失败</b><span>{voicePreviewError}</span></div></div>}<div className="resource-pagination"><span>共 {voiceCatalogTotal} 条，第 {voiceCatalogPage} 页</span><div><button className="human-secondary" disabled={voiceCatalogPage <= 1} onClick={() => setVoiceCatalogPage(value => value - 1)}>上一页</button><button className="human-secondary" disabled={voiceCatalogPage * 20 >= voiceCatalogTotal} onClick={() => setVoiceCatalogPage(value => value + 1)}>下一页</button></div></div></div>
    </>}
    {tab === "narrations" && <>
      <div className="human-card full"><div className="human-card-title"><h2>字幕配音</h2><span>手动输入或从内容文库选择，按音色库序号生成</span></div>
        <div className="human-form narration-generation-form"><label>从内容文库选择<div className="copy-autocomplete"><input value={copySearch} disabled={narrationBusy} autoComplete="off" placeholder="输入文案中的关键词查询" onFocus={() => setCopySearchOpen(true)} onChange={event => { setCopySearch(event.target.value); setCopySearchOpen(true); }} onBlur={() => window.setTimeout(() => setCopySearchOpen(false), 120)} />{copySearchOpen && <div className="copy-autocomplete-options">{copySearchBusy ? <span><LoaderCircle className="spin" />正在查询内容文库…</span> : copySuggestions.length ? copySuggestions.map(item => <button type="button" key={item.id} onMouseDown={event => event.preventDefault()} onClick={() => { setSelectedCopyId(item.id); setSelectedNarrationCopy(item); setNarrationText(item.content); setCopySearch(""); setCopySearchOpen(false); }}>{item.content}<small>{item.product_name || "全局通用"} · {item.source === "model" ? "模型生成" : item.source === "original" ? "参考原文" : "人工录入"}</small></button>) : <span>没有匹配的文案</span>}</div>}</div>{selectedNarrationCopy && <span className="selected-copy-summary"><span><b>已选择文案</b>{selectedNarrationCopy.content}</span><button type="button" className="human-secondary" disabled={narrationBusy} onClick={() => { setSelectedCopyId(""); setSelectedNarrationCopy(null); }}>取消选择</button></span>}<small>输入关键词实时查询全部内容文库；不选择时可直接手动填写下方文案。</small></label><label>旁白文案<textarea value={narrationText} disabled={narrationBusy} onChange={event => { setNarrationText(event.target.value); setSelectedCopyId(""); setSelectedNarrationCopy(null); }} /></label><label>音色库序号<input inputMode="numeric" value={voiceSequenceInput} disabled={narrationBusy} onChange={event => setVoiceSequenceInput(event.target.value)} placeholder="输入 1–597" /><small className={voiceSequenceError ? "field-error" : ""}>{voiceSequenceError || (selectedCatalogVoice ? `已选择：${selectedCatalogVoice.sequence} · ${selectedCatalogVoice.name} · ${selectedCatalogVoice.voice}` : "请输入音色库序号")}</small></label><button disabled={narrationBusy || !narrationText.trim() || !selectedCatalogVoice} onClick={generateNarration}>{narrationBusy ? <LoaderCircle className="spin" /> : <Volume2 />}{narrationBusy ? "正在生成旁白配音…" : "生成旁白配音"}</button>{narrationBusy && <div className="copy-generation-progress" role="status" aria-live="polite"><LoaderCircle className="spin" /><div><b>旁白配音正在生成</b><span>系统正在调用字幕配音模型并生成音频与字幕时间轴，完成前请勿重复提交。</span></div></div>}{narrationError && !narrationBusy && <div className="copy-generation-progress error" role="alert"><div><b>生成失败</b><span>{narrationError}</span></div></div>}</div>
      </div>
      <div className="human-card full"><div className="human-card-title"><h2>旁白与字幕库</h2><span>{narrations.length} 条</span></div>
        <div className="simple-resource-list">{narrations.map(item => <article key={item.id}><div><b>{item.approved_text}</b><span>旁白配音 · {item.subtitle_cues.length} 条字幕</span></div><div><Pill value={item.status} /><button className="human-secondary" onClick={() => listenNarration(item)}>{playingNarrationId === item.id ? "停止试听" : "试听"}</button>{item.status !== "approved" && <button onClick={() => act(() => api(`/human/narrations/${item.id}/confirm`, { method: "PUT", body: JSON.stringify({ approved_text: item.approved_text, subtitle_cues: item.subtitle_cues }) }), "旁白与字幕已确认")}>确认</button>}<button className="human-secondary danger" onClick={() => setConfirmation({ title: "删除这条旁白配音？", message: "将删除旁白记录和音频文件；已经生成的剪映草稿仍保留其创建快照。", onConfirm: async () => { stopNarration(); return act(() => api(`/human/narrations/${item.id}`, { method: "DELETE" }), "旁白配音已删除"); } })}>删除</button></div></article>)}</div>
        <ConfirmDeleteDialog confirmation={confirmation} close={() => setConfirmation(null)} />
      </div>
    </>}
  </section>;
}

function MusicLibrary({ music, act }: { music: MusicResource[]; act: (work: () => Promise<unknown>, success: string) => Promise<boolean> }) {
  const [linkName, setLinkName] = useState(""); const [uploadName, setUploadName] = useState(""); const [shareUrl, setShareUrl] = useState(""); const [file, setFile] = useState<File | null>(null);
  const [extractBusy, setExtractBusy] = useState(false); const [uploadBusy, setUploadBusy] = useState(false);
  const [listeningId, setListeningId] = useState(""); const [listeningBusyId, setListeningBusyId] = useState(""); const [listenError, setListenError] = useState("");
  const [confirmation, setConfirmation] = useState<DeleteConfirmation | null>(null);
  const [tagEditor, setTagEditor] = useState<MusicResource | null>(null); const [tagInput, setTagInput] = useState(""); const [tagSaving, setTagSaving] = useState(false);
  const playerRef = useRef<HTMLAudioElement | null>(null); const audioUrlRef = useRef(""); const playRequestRef = useRef(0);
  function stopListening(updateState = true) {
    playRequestRef.current += 1;
    if (playerRef.current) { playerRef.current.pause(); playerRef.current.currentTime = 0; playerRef.current = null; }
    if (audioUrlRef.current) { URL.revokeObjectURL(audioUrlRef.current); audioUrlRef.current = ""; }
    if (updateState) { setListeningId(""); setListeningBusyId(""); }
  }
  useEffect(() => () => stopListening(false), []);
  async function extract(event: FormEvent) {
    event.preventDefault(); if (extractBusy) return; setExtractBusy(true);
    try {
      const success = await act(() => api("/music-resources/link", { method: "POST", body: JSON.stringify({ name: linkName, share_url: shareUrl, rights_confirmed: true }) }), "短视频音频已提取并入库");
      if (success) { setLinkName(""); setShareUrl(""); }
    } finally { setExtractBusy(false); }
  }
  async function upload(event: FormEvent) {
    event.preventDefault(); if (!file || uploadBusy) return; setUploadBusy(true);
    const form = new FormData(); form.append("music", file); form.append("name", uploadName); form.append("rights_confirmed", "true");
    try {
      const success = await act(() => api("/music-resources/upload", { method: "POST", body: form }), "背景音乐已上传并入库");
      if (success) { setUploadName(""); setFile(null); }
    } finally { setUploadBusy(false); }
  }
  async function listen(item: MusicResource) {
    if (listeningId === item.id) { stopListening(); return; }
    stopListening(); setListenError(""); const requestId = playRequestRef.current; setListeningBusyId(item.id);
    try {
      const blob = await apiBlob(`/music-resources/${item.id}/audio`);
      if (requestId !== playRequestRef.current) return;
      if (!blob.size) throw new Error("音乐文件为空");
      const url = URL.createObjectURL(blob); const player = new Audio();
      player.preload = "auto"; player.volume = 1; player.muted = false; player.src = url;
      audioUrlRef.current = url; playerRef.current = player;
      player.onended = () => { if (playerRef.current === player) stopListening(); };
      player.onerror = () => { if (playerRef.current === player) { setListenError(`“${item.name}”的音频格式无法播放或文件已损坏`); stopListening(); } };
      await player.play();
      if (requestId === playRequestRef.current) { setListeningBusyId(""); setListeningId(item.id); }
    } catch (reason) {
      if (requestId === playRequestRef.current) { setListenError(reason instanceof Error ? `“${item.name}”试听失败：${reason.message}` : `“${item.name}”试听失败`); stopListening(); }
    }
  }
  function editTags(item: MusicResource) { setTagEditor(item); setTagInput(item.custom_tags.join("，")); }
  async function saveTags() {
    if (!tagEditor || tagSaving) return; setTagSaving(true);
    const custom_tags = Array.from(new Set(tagInput.split(/[,，]/).map(value => value.trim()).filter(Boolean)));
    try {
      const success = await act(() => api(`/music-resources/${tagEditor.id}`, { method: "PATCH", body: JSON.stringify({ name: tagEditor.name, custom_tags }) }), "音乐标签已更新");
      if (success) setTagEditor(null);
    } finally { setTagSaving(false); }
  }
  return <section className="human-page music-library-page">
    <div className="human-card"><div className="human-card-title"><h2>短视频链接提取</h2><span>自动分离音频，失败时可改用上传</span></div><form className="human-form" onSubmit={extract}><label>音乐名称<input value={linkName} onChange={event => setLinkName(event.target.value)} /></label><label>短视频分享链接<textarea value={shareUrl} onChange={event => setShareUrl(event.target.value)} required /></label><button disabled={extractBusy}>{extractBusy && <LoaderCircle className="spin" />}{extractBusy ? "正在下载视频并提取音频…" : "提取背景音乐"}</button>{extractBusy && <div className="copy-generation-progress" role="status" aria-live="polite"><LoaderCircle className="spin" /><div><b>背景音乐正在提取</b><span>下载和音频分离可能需要一些时间，完成前请勿重复提交。</span></div></div>}</form></div>
    <div className="human-card"><div className="human-card-title"><h2>上传音乐</h2><span>支持常见音频和含音轨视频</span></div><form className="human-form" onSubmit={upload}><label>音乐名称<input value={uploadName} disabled={uploadBusy} onChange={event => setUploadName(event.target.value)} /></label><label>音频文件<input type="file" accept="audio/*,video/mp4,video/quicktime" disabled={uploadBusy} onChange={event => setFile(event.target.files?.[0] ?? null)} required /></label><button disabled={uploadBusy}><Upload />{uploadBusy ? "正在上传并处理…" : "上传到背景音乐"}</button>{uploadBusy && <div className="copy-generation-progress" role="status" aria-live="polite"><LoaderCircle className="spin" /><div><b>背景音乐正在上传并处理</b><span>系统正在读取媒体并提取有效音轨，完成前请勿重复提交。</span></div></div>}</form></div>
    <div className="human-card full"><div className="human-card-title"><h2>背景音乐库</h2><span>可试听、自定义标签和删除</span></div>{listenError && <div className="copy-generation-progress error" role="alert"><div><b>音乐试听失败</b><span>{listenError}</span></div></div>}<div className="music-resource-grid">{music.map(item => <article key={item.id}><div><b>{item.name}</b><span>{item.duration_seconds.toFixed(1)} 秒 · {item.source_type === "share_link" ? "链接提取" : "上传"}</span><div>{item.custom_tags.map(tag => <small key={tag}>{tag}</small>)}</div>{item.error && <em>{item.error}</em>}</div><Pill value={item.status} /><div><button className="human-secondary" aria-pressed={listeningId === item.id} disabled={item.status !== "ready" || Boolean(listeningBusyId && listeningBusyId !== item.id)} onClick={() => listen(item)}>{listeningBusyId === item.id ? <><LoaderCircle className="spin" />加载中</> : listeningId === item.id ? "停止试听" : "试听"}</button><button className="human-secondary" onClick={() => editTags(item)}>标签</button><button className="human-secondary danger" onClick={() => setConfirmation({ title: "删除这条背景音乐？", message: `将删除“${item.name}”的音乐记录和音频文件；如果已被剪映草稿引用，系统会阻止删除。`, onConfirm: async () => { if (listeningId === item.id || listeningBusyId === item.id) stopListening(); return act(() => api(`/music-resources/${item.id}`, { method: "DELETE" }), "背景音乐已删除"); } })}>删除</button></div></article>)}</div>{tagEditor && <div className="confirm-dialog-backdrop" role="presentation"><section className="confirm-dialog music-tag-dialog" role="dialog" aria-modal="true" aria-labelledby="music-tag-title"><div><b id="music-tag-title">设置背景音乐标签</b><span>“{tagEditor.name}”</span><label>音乐标签<input autoFocus value={tagInput} onChange={event => setTagInput(event.target.value)} onKeyDown={event => { if (event.key === "Enter") { event.preventDefault(); saveTags(); } }} placeholder="例如：轻快，治愈，产品展示" /><small>多个标签使用逗号分隔，清空后保存可移除全部标签。</small></label></div><div><button type="button" className="human-secondary" disabled={tagSaving} onClick={() => setTagEditor(null)}>取消</button><button type="button" className="music-tag-confirm" disabled={tagSaving} onClick={saveTags}>{tagSaving && <LoaderCircle className="spin" />}{tagSaving ? "正在保存…" : "保存标签"}</button></div></section></div>}<ConfirmDeleteDialog confirmation={confirmation} close={() => setConfirmation(null)} /></div>
  </section>;
}

function DraftProduction({ copies, narrations, music, drafts, act }: {
  copies: CopyItem[]; narrations: Narration[]; music: MusicResource[]; drafts: JianyingDraft[];
  act: (work: () => Promise<unknown>, success: string) => Promise<boolean>;
}) {
  const [copyId, setCopyId] = useState(""); const [narrationId, setNarrationId] = useState(""); const [musicId, setMusicId] = useState("");
  const [draftBusy, setDraftBusy] = useState(false); const [draftError, setDraftError] = useState("");
  const [directory, setDirectory] = useState<DraftDirectory | null>(null);
  const [manualDir, setManualDir] = useState("");
  const [dirBusy, setDirBusy] = useState(false);
  const [dirError, setDirError] = useState("");
  const [confirmation, setConfirmation] = useState<DeleteConfirmation | null>(null);
  const [copyPage, setCopyPage] = useState(0); const [narrationPage, setNarrationPage] = useState(0); const [musicPage, setMusicPage] = useState(0); const [draftPage, setDraftPage] = useState(0);
  const [copyQuery, setCopyQuery] = useState(""); const [narrationQuery, setNarrationQuery] = useState(""); const [musicQuery, setMusicQuery] = useState("");
  const [previewId, setPreviewId] = useState(""); const [previewBusyId, setPreviewBusyId] = useState(""); const [previewError, setPreviewError] = useState("");
  const [duplicatePrompt, setDuplicatePrompt] = useState<{ count: number } | null>(null);
  const draftPlayerRef = useRef<HTMLAudioElement | null>(null); const draftAudioUrlRef = useRef(""); const draftPlayRequestRef = useRef(0);
  const approvedNarrations = narrations.filter(item => item.status === "approved");
  const readyMusic = music.filter(item => item.status === "ready");
  const filteredCopies = fuzzyRows(copies, copyQuery, item => `${item.content} ${item.product_name || ""} ${item.source}`, copies.length);
  const filteredNarrations = fuzzyRows(approvedNarrations, narrationQuery, item => `${item.approved_text} ${item.voice_source} ${item.subtitle_cues.length}`, approvedNarrations.length);
  const filteredMusic = fuzzyRows(readyMusic, musicQuery, item => `${item.name} ${item.custom_tags.join(" ")} ${item.duration_seconds}`, readyMusic.length);
  const selectedCopy = copies.find(item => item.id === copyId);
  const selectedNarration = approvedNarrations.find(item => item.id === narrationId);
  const selectedMusic = readyMusic.find(item => item.id === musicId);
  const selectedCount = [copyId, narrationId, musicId].filter(Boolean).length;
  const pageSize = 20;
  const pageRows = <T,>(rows: T[], page: number) => rows.slice(page * pageSize, page * pageSize + pageSize);
  useEffect(() => {
    if (draftPage > 0 && draftPage * pageSize >= drafts.length) setDraftPage(Math.max(0, Math.ceil(drafts.length / pageSize) - 1));
  }, [draftPage, drafts.length]);
  const draftDuplicatePayload = () => ({ copy_content_id: copyId || null, narration_asset_id: narrationId || null, music_resource_id: musicId || null });
  function stopPreview(updateState = true) {
    draftPlayRequestRef.current += 1;
    if (draftPlayerRef.current) { draftPlayerRef.current.pause(); draftPlayerRef.current.currentTime = 0; draftPlayerRef.current = null; }
    if (draftAudioUrlRef.current) { URL.revokeObjectURL(draftAudioUrlRef.current); draftAudioUrlRef.current = ""; }
    if (updateState) { setPreviewId(""); setPreviewBusyId(""); }
  }
  useEffect(() => () => stopPreview(false), []);
  async function listenPreview(kind: "narration" | "music", item: Narration | MusicResource) {
    const targetId = `${kind}:${item.id}`;
    if (previewId === targetId && !previewBusyId) { stopPreview(); return; }
    stopPreview();
    const requestId = draftPlayRequestRef.current;
    setPreviewId(targetId); setPreviewBusyId(targetId); setPreviewError("");
    try {
      const blob = await apiBlob(kind === "narration" ? `/human/narrations/${item.id}/audio` : `/music-resources/${item.id}/audio`);
      if (requestId !== draftPlayRequestRef.current) return;
      const url = URL.createObjectURL(blob); const player = new Audio(url);
      draftAudioUrlRef.current = url; draftPlayerRef.current = player; setPreviewBusyId("");
      player.onended = () => { if (draftPlayerRef.current === player) stopPreview(); };
      await player.play();
    } catch (reason) {
      if (requestId === draftPlayRequestRef.current) {
        stopPreview();
        setPreviewError(reason instanceof Error ? reason.message : "试听失败");
      }
    }
  }
  async function loadDirectory() {
    setDirBusy(true); setDirError("");
    try {
      const value = await api<DraftDirectory>("/human/jianying-drafts/directory");
      setDirectory(value); setManualDir(value.path || "");
    } catch (reason) {
      setDirError(reason instanceof Error ? reason.message : "剪映草稿目录检测失败");
    } finally { setDirBusy(false); }
  }
  useEffect(() => { loadDirectory(); }, []);
  async function confirmDirectory() {
    if (dirBusy || !manualDir.trim()) return;
    setDirBusy(true); setDirError("");
    try {
      const value = await api<DraftDirectory>("/human/jianying-drafts/directory", { method: "PUT", body: JSON.stringify({ path: manualDir.trim() }) });
      setDirectory(value); setManualDir(value.path || "");
    } catch (reason) {
      setDirError(reason instanceof Error ? reason.message : "剪映草稿目录确认失败");
    } finally { setDirBusy(false); }
  }
  async function generateDraft() {
    if (draftBusy || !directory?.exists || !directory.path || selectedCount === 0) return;
    setDraftError("");
    const duplicate = await api<{ count: number }>("/human/jianying-drafts/duplicate-count", { method: "POST", body: JSON.stringify(draftDuplicatePayload()) });
    if (duplicate.count > 0) {
      setDuplicatePrompt({ count: duplicate.count });
      return;
    }
    await submitDraft();
  }
  async function resetDuplicateCounter() {
    if (draftBusy || selectedCount === 0) return;
    const success = await act(() => api("/human/jianying-drafts/duplicate-counter/reset", { method: "POST", body: JSON.stringify(draftDuplicatePayload()) }), "重复计数器已复位");
    if (success) setDuplicatePrompt(null);
  }
  async function submitDraft() {
    if (draftBusy || !directory?.exists || !directory.path || selectedCount === 0) return;
    setDuplicatePrompt(null);
    setDraftBusy(true); setDraftError("");
    try {
      const success = await act(() => api("/human/jianying-drafts", { method: "POST", body: JSON.stringify({ name: "", destination_dir: directory.path, copy_content_id: copyId || null, narration_asset_id: narrationId || null, music_resource_id: musicId || null }) }), "剪映草稿已生成到剪映草稿目录");
      if (!success) setDraftError("剪映草稿生成失败，请查看页面上方的错误提示。");
    } finally { setDraftBusy(false); }
  }
  function pager(total: number, page: number, setPage: (value: number) => void) {
    const pages = Math.max(1, Math.ceil(total / pageSize));
    return <div className="draft-library-pager"><button type="button" className="human-secondary" disabled={page <= 0} onClick={() => setPage(page - 1)}>上一页</button><span>{page + 1} / {pages}</span><button type="button" className="human-secondary" disabled={page + 1 >= pages} onClick={() => setPage(page + 1)}>下一页</button></div>;
  }
  return <section className="human-page draft-production-page">
    <div className="human-card full draft-directory-card"><div className="human-card-title"><h2>剪映草稿目录</h2><span>{directory?.exists ? "已确认" : "待确认"}</span></div><div className="human-form draft-directory-form">
        <label className="draft-directory-input">当前目录<input value={manualDir} disabled={dirBusy || draftBusy} onChange={event => setManualDir(event.target.value)} placeholder="未检测到时可手动填写完整目录" /></label>
        <button type="button" className="human-secondary draft-directory-detect" disabled={dirBusy || draftBusy} onClick={loadDirectory}><FolderOpen />{dirBusy ? "正在检测…" : "重新检测"}</button>
        <button type="button" className="draft-directory-confirm" disabled={dirBusy || draftBusy || !manualDir.trim()} onClick={confirmDirectory}>{dirBusy && <LoaderCircle className="spin" />}{dirBusy ? "正在确认…" : "确认目录"}</button>
        <small className="draft-directory-path" title={directory?.exists ? (directory.windows_path || directory.path) : ""}>{directory?.exists ? (directory.windows_path || directory.path) : "未确认有效目录"}</small>
        {dirError && <div className="copy-generation-progress error" role="alert"><div><b>目录不可用</b><span>{dirError}</span></div></div>}
      </div></div>
    <div className="human-card full draft-selection-card"><div className="human-card-title"><h2>物料清单</h2><span>{selectedCount} 项已选</span></div><div className="draft-selection-row">
        <article><b title="文案内容">文案内容</b><span title={selectedCopy?.content || "未选择"}>{selectedCopy?.content || "未选择"}</span>{selectedCopy && <button type="button" className="human-secondary" disabled={draftBusy} onClick={() => setCopyId("")}>取消</button>}</article>
        <article><b title="旁白与字幕">旁白与字幕</b><span title={selectedNarration?.approved_text || "未选择"}>{selectedNarration?.approved_text || "未选择"}</span>{selectedNarration && <button type="button" className="human-secondary" disabled={draftBusy} onClick={() => setNarrationId("")}>取消</button>}</article>
        <article><b title="背景音乐">背景音乐</b><span title={selectedMusic ? `${selectedMusic.name} · ${selectedMusic.duration_seconds.toFixed(1)} 秒` : "未选择"}>{selectedMusic ? `${selectedMusic.name} · ${selectedMusic.duration_seconds.toFixed(1)} 秒` : "未选择"}</span>{selectedMusic && <button type="button" className="human-secondary" disabled={draftBusy} onClick={() => setMusicId("")}>取消</button>}</article>
        <div className="draft-generate-box"><button disabled={draftBusy || !directory?.exists || !directory.path || selectedCount === 0} onClick={generateDraft}>{draftBusy ? <LoaderCircle className="spin" /> : <Sparkles />}{draftBusy ? "正在生成…" : "生成草稿"}</button><span>{directory?.exists ? "目录可用" : "目录未确认"}</span></div>
        {draftBusy && <div className="copy-generation-progress draft-progress" role="status" aria-live="polite"><LoaderCircle className="spin" /><div><b>剪映草稿正在生成</b><span>系统正在校验资源并写入剪映草稿目录，完成前请勿重复提交。</span></div></div>}
        {draftError && !draftBusy && <div className="copy-generation-progress error draft-progress" role="alert"><div><b>生成失败</b><span>{draftError}</span></div></div>}
      </div></div>
    <div className="draft-library-columns full">
      <div className="human-card draft-library-card"><div className="human-card-title"><h2>文案内容库</h2><span>{filteredCopies.length}/{copies.length} 条</span></div><input className="draft-library-search" value={copyQuery} onChange={event => { setCopyQuery(event.target.value); setCopyPage(0); }} placeholder="模糊查询文案、产品或来源" /><div className="draft-library-list">{pageRows(filteredCopies, copyPage).map(item => { const meta = `${item.product_name || "全局通用"} · ${item.source === "model" ? "模型生成" : item.source === "original" ? "参考原文" : "人工录入"}`; return <article key={item.id} className={copyId === item.id ? "selected" : ""}><button type="button" className="draft-library-select" disabled={draftBusy} onClick={() => setCopyId(item.id)}><b title={item.content}>{item.content}</b><span title={meta}>{meta}</span></button></article>; })}</div>{pager(filteredCopies.length, copyPage, setCopyPage)}</div>
      <div className="human-card draft-library-card"><div className="human-card-title"><h2>旁白与字幕库</h2><span>{filteredNarrations.length}/{approvedNarrations.length} 条</span></div><input className="draft-library-search" value={narrationQuery} onChange={event => { setNarrationQuery(event.target.value); setNarrationPage(0); }} placeholder="模糊查询旁白、字幕数量或来源" />{previewError && previewId.startsWith("narration:") && <div className="copy-generation-progress error draft-preview-error" role="alert"><div><b>旁白试听失败</b><span>{previewError}</span></div></div>}<div className="draft-library-list">{pageRows(filteredNarrations, narrationPage).map(item => { const meta = `${item.subtitle_cues.length} 条字幕 · ${item.voice_source === "model" ? "模型配音" : "人工资源"}`; return <article key={item.id} className={narrationId === item.id ? "selected" : ""}><button type="button" className="draft-library-select" disabled={draftBusy} onClick={() => setNarrationId(item.id)}><b title={item.approved_text}>{item.approved_text}</b><span title={meta}>{meta}</span></button><div className="draft-library-actions"><button type="button" className="human-secondary" disabled={Boolean(previewBusyId && previewBusyId !== `narration:${item.id}`)} onClick={() => listenPreview("narration", item)}>{previewBusyId === `narration:${item.id}` ? <LoaderCircle className="spin" /> : <Volume2 />}{previewId === `narration:${item.id}` && !previewBusyId ? "停止" : previewBusyId === `narration:${item.id}` ? "加载" : "试听"}</button></div></article>; })}</div>{pager(filteredNarrations.length, narrationPage, setNarrationPage)}</div>
      <div className="human-card draft-library-card"><div className="human-card-title"><h2>背景音乐库</h2><span>{filteredMusic.length}/{readyMusic.length} 条</span></div><input className="draft-library-search" value={musicQuery} onChange={event => { setMusicQuery(event.target.value); setMusicPage(0); }} placeholder="模糊查询名称、标签或时长" />{previewError && previewId.startsWith("music:") && <div className="copy-generation-progress error draft-preview-error" role="alert"><div><b>音乐试听失败</b><span>{previewError}</span></div></div>}<div className="draft-library-list">{pageRows(filteredMusic, musicPage).map(item => { const meta = `${item.duration_seconds.toFixed(1)} 秒 · ${item.custom_tags.length ? item.custom_tags.join(" / ") : "无标签"}`; return <article key={item.id} className={musicId === item.id ? "selected" : ""}><button type="button" className="draft-library-select" disabled={draftBusy} onClick={() => setMusicId(item.id)}><b title={item.name}>{item.name}</b><span title={meta}>{meta}</span></button><div className="draft-library-actions"><button type="button" className="human-secondary" disabled={Boolean(previewBusyId && previewBusyId !== `music:${item.id}`)} onClick={() => listenPreview("music", item)}>{previewBusyId === `music:${item.id}` ? <LoaderCircle className="spin" /> : <Volume2 />}{previewId === `music:${item.id}` && !previewBusyId ? "停止" : previewBusyId === `music:${item.id}` ? "加载" : "试听"}</button></div></article>; })}</div>{pager(filteredMusic.length, musicPage, setMusicPage)}</div>
    </div>
    <div className="human-card full"><div className="human-card-title"><h2>剪映草稿记录</h2><span>最新在前，每页 20 条，共 {drafts.length} 条</span></div><div className="simple-resource-list">{pageRows(drafts, draftPage).map(item => <article key={item.id}><div><b title={item.name}>{item.name}</b><span title={item.draft_path}>{item.draft_path || "未记录目录"} · {new Date(item.created_at).toLocaleString()}</span></div><div><Pill value={item.status} /><button className="human-secondary danger" onClick={() => setConfirmation({ title: `删除草稿记录“${item.name}”？`, message: "只删除工作台中的草稿记录，不删除磁盘上的剪映草稿文件夹。", onConfirm: () => act(() => api(`/human/jianying-drafts/${item.id}`, { method: "DELETE" }), "剪映草稿记录已删除") })}>删除</button></div></article>)}</div>{pager(drafts.length, draftPage, setDraftPage)}<ConfirmDeleteDialog confirmation={confirmation} close={() => setConfirmation(null)} />{duplicatePrompt && <div className="confirm-dialog-backdrop" role="presentation"><section className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="draft-duplicate-title"><div><b id="draft-duplicate-title">重复物料组合</b><span>当前选择的文案、旁白与字幕、背景音乐组合此前已生成 {duplicatePrompt.count} 次。系统不会阻止再次生成。</span></div><div><button type="button" className="human-secondary" disabled={draftBusy} onClick={() => setDuplicatePrompt(null)}>取消</button><button type="button" className="human-secondary" disabled={draftBusy} onClick={resetDuplicateCounter}>计数器复位</button><button type="button" disabled={draftBusy} onClick={submitDraft}>{draftBusy && <LoaderCircle className="spin" />}{draftBusy ? "正在生成…" : "继续生成"}</button></div></section></div>}</div>
  </section>;
}

function BusinessModelSettings({ onError, onNotice }: { onError: (value: string) => void; onNotice: (value: string) => void }) {
  const [profiles, setProfiles] = useState<ModelProfile[]>([]); const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(""); const [busy, setBusy] = useState(""); const [modelLists, setModelLists] = useState<Record<string, string[]>>({});
  useEffect(() => { api<ModelProfilesResponse>("/model-profiles").then(value => setProfiles(value.profiles)).catch(reason => onError(reason instanceof Error ? reason.message : "模型配置加载失败")).finally(() => setLoading(false)); }, [onError]);
  function update(stage: string, values: Partial<ModelProfile>) { setProfiles(rows => rows.map(item => item.stage === stage ? { ...item, ...values } : item)); }
  async function loadModels(profile: ModelProfile) { setBusy(profile.stage); try { const value = await api<{ models: string[] }>("/model-profiles/models", { method: "POST", body: JSON.stringify(profile) }); setModelLists(rows => ({ ...rows, [profile.stage]: value.models })); if (!value.models.includes(profile.model) && value.models[0]) update(profile.stage, { model: value.models[0] }); onNotice(profile.stage === "speech_recognition" ? `已读取 ${value.models.length} 个可用于音频转文案的非实时模型` : `已读取 ${value.models.length} 个百炼模型`); } catch (reason) { onError(reason instanceof Error ? reason.message : "连接失败"); } finally { setBusy(""); } }
  async function save(profile: ModelProfile) { setSaving(profile.stage); try { const stored = await api<ModelProfile>(`/model-profiles/${profile.stage}`, { method: "PUT", body: JSON.stringify(profile) }); update(profile.stage, stored); onNotice(`${profile.stage === "copywriting" ? "文案生成" : profile.stage === "speech_recognition" ? "语音识别" : "字幕配音"}配置已保存`); } catch (reason) { onError(reason instanceof Error ? reason.message : "保存失败"); } finally { setSaving(""); } }
  function card(stage: string, description: string) { const profile = profiles.find(item => item.stage === stage); if (!profile) return null; const listed = modelLists[stage] ?? []; const options = listed.length ? listed : [profile.model].filter(Boolean); const title = stage === "copywriting" ? "文案生成" : stage === "speech_recognition" ? "语音识别" : "字幕配音"; return <article className="human-card business-model-card" key={stage}><div><b>{title}</b><span>{description}</span></div><label>百炼兼容接口<input value={profile.base_url} onChange={event => update(stage, { base_url: event.target.value })} placeholder="https://.../compatible-mode/v1" /></label><label>API Key<input type="password" value={profile.api_key} onChange={event => update(stage, { api_key: event.target.value })} placeholder={profile.api_key_mask || "sk-..."} /></label><label>模型类别{listed.length ? <select value={profile.model} onChange={event => update(stage, { model: event.target.value })}><option value="">请选择模型类别</option>{options.map(value => <option key={value} value={value}>{value}</option>)}</select> : <input value={profile.model} onChange={event => update(stage, { model: event.target.value })} placeholder={stage === "speech_recognition" ? "请填写非实时 qwen3-asr-flash" : "读取列表后可下拉选择，也可手动填写"} />}</label>{stage === "speech_recognition" && <small>仅支持非实时 qwen3-asr-flash；realtime 和 filetrans 使用其他接口，不能用于这里。</small>}<div className="business-model-actions"><button type="button" className="human-secondary" disabled={busy === stage || saving === stage || !profile.base_url || (!profile.api_key && !profile.has_api_key)} onClick={() => loadModels(profile)}>{busy === stage && <LoaderCircle className="spin" />}{busy === stage ? "正在读取列表…" : "读取模型列表"}</button><button type="button" disabled={saving === stage || busy === stage} onClick={() => save(profile)}>{saving === stage && <LoaderCircle className="spin" />}{saving === stage ? "正在保存…" : "保存配置"}</button></div></article>; }
  if (loading) return <section className="human-page"><div className="human-empty"><LoaderCircle className="spin" />正在加载</div></section>;
  return <section className="human-page business-model-page"><div className="human-note"><Sparkles />三个功能分别配置百炼连接、读取模型列表和保存配置，互不影响。</div><div className="business-model-stack">{card("copywriting", "分析语言与受众并生成 5 条文案，也负责字幕文案生成")}{card("speech_recognition", "识别抖音视频、本地视频或本地音频并转换为文案")}{card("speech_synthesis", "按音色库序号将文案合成为旁白")}</div></section>;
}
