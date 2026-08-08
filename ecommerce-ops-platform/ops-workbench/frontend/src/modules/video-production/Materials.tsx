import { useCallback, useEffect, useState } from "react";
import { Boxes, FolderOpen, LoaderCircle } from "lucide-react";
import { api } from "../../api";
import { ClassificationDropdown } from "../../components/ClassificationDropdown";
import { usePersistentOperation } from "../../hooks/usePersistentOperation";
import type { ClassifiedMaterial, Product, SourceVideo, Tag, TagCategory } from "../../types";
import { fuzzyRows } from "../../utils/fuzzy";
import { ProductManager } from "./ProductManager";
import { TagManager } from "./TagManager";

export function Materials({ products, act }: { products: Product[]; act: (work: () => Promise<unknown>, success: string) => Promise<boolean> }) {
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
